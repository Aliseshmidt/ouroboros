"""Static and adapter contracts for the standalone hackathon demo."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from starlette.routing import Mount, Route

from ouroboros.hackathon.orchestrator import DemoOrchestrator
from ouroboros.hackathon.server import LOOPBACK_HOSTS, DemoAdapter, create_app

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web" / "hackathon"


def _read(name: str) -> str:
    return (WEB_ROOT / name).read_text(encoding="utf-8")


def test_guided_demo_has_exactly_twelve_populated_screens():
    html = _read("index.html")
    screens = (
        "overview",
        "upload",
        "trace",
        "patterns",
        "hypothesis",
        "builder",
        "sandbox",
        "approval",
        "result",
        "value",
        "library",
        "evolution",
    )
    assert html.count('class="demo-screen') == 12
    for screen in screens:
        assert html.count(f'data-screen="{screen}"') == 1
        assert f'data-screen-target="{screen}"' in html
    assert "01 / 12" in html
    assert "Следующий шаг" in html


def test_demo_is_honest_local_and_never_visually_empty():
    html = _read("index.html")
    for label in (
        "Только синтетические данные",
        "MOCK-КОННЕКТОРЫ",
        "не замер MVP",
        "Не отправлено",
        "Запуски в проде",
        "Human-in-the-loop",
        "Safe evolution",
    ):
        assert label in html
    assert "empty-state" not in html
    assert "<section" in html and "<article" in html


def test_static_assets_are_self_contained_and_have_no_inline_styles():
    html = _read("index.html")
    js = _read("app.js")
    assert 'href="/static/style.css"' in html
    assert 'src="/static/app.js"' in html
    assert "style=" not in html.lower()
    assert "<script>" not in html.lower()
    assert ".style." not in js
    for source in (html, _read("style.css"), js):
        assert "https://" not in source
        assert "http://" not in source
        assert "//cdn" not in source.lower()


def test_every_product_action_is_wired_to_a_json_route():
    html = _read("index.html")
    js = _read("app.js")
    actions = (
        "reset",
        "import",
        "detect_patterns",
        "select_hypothesis",
        "generate_skill",
        "run_sandbox",
        "approve",
        "execute",
        "export_template",
        "evolve",
        "promote",
        "rollback",
    )
    for action in actions:
        assert f'data-action="{action}"' in html
        assert f"{action}:" in js
    for route in (
        "/api/reset",
        "/api/import",
        "/api/action/detect_patterns",
        "/api/hypothesis/select",
        "/api/action/generate_skill",
        "/api/sandbox/run",
        "/api/approve",
        "/api/action/execute",
        "/api/action/evolve",
        "/api/action/promote",
        "/api/action/rollback",
        "/api/action/export_template",
    ):
        assert route in js
    assert 'headers: { "Content-Type": "application/json" }' in js
    assert "response.ok" in js


def test_responsive_design_and_accessibility_contracts():
    html = _read("index.html")
    css = _read("style.css")
    js = _read("app.js")
    assert 'lang="ru"' in html
    assert 'aria-label="Шаги демонстрации"' in html
    assert 'aria-live="polite"' in html
    assert "@media (max-width: 760px)" in css
    assert "@media (max-width: 480px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ":focus-visible" in css
    assert 'event.key === "Escape"' in js
    assert "aria-current" in js


def test_server_exposes_only_standalone_static_and_json_surface():
    app = create_app(orchestrator=object())
    route_paths = {route.path for route in app.routes if isinstance(route, (Route, Mount))}
    assert {
        "/",
        "/api/health",
        "/api/state",
        "/api/reset",
        "/api/import",
        "/api/hypothesis/select",
        "/api/sandbox/run",
        "/api/approve",
        "/static",
    } <= route_paths
    for method_name in (
        "detect_patterns",
        "generate_skill",
        "execute",
        "evolve",
        "promote",
        "rollback",
        "export_template",
    ):
        assert f"/api/action/{method_name}" in route_paths
    assert LOOPBACK_HOSTS == frozenset({"127.0.0.1", "localhost", "::1"})


def test_run_only_backend_facade_advances_and_fails_closed_before_approval():
    class RunOnlyBackend:
        def __init__(self) -> None:
            self.calls = 0

        def run(self):
            self.calls += 1
            return {
                "trace": {"events": 124},
                "patterns": [{"pattern_id": "pattern-credit-dossier"}],
                "mining_metrics": {"precision": 1.0},
                "proposal_id": "proposal-demo",
                "skill": {"active_version": "2.0.0"},
                "sandbox": {"v1": {"passed": False}, "v2": {"passed": True}},
                "approval": {"approved": True},
                "execution": {"ok": True},
                "evolution_history": [],
                "budget": {"spent_usd": 0.0},
            }

    backend = RunOnlyBackend()
    adapter = DemoAdapter(backend)
    baseline = asyncio.run(adapter.snapshot())
    assert baseline["stage"] == 0
    imported = asyncio.run(adapter.call("import_trace", {"events": []}, "json"))
    assert imported["trace"]["events"] == 124
    assert backend.calls == 1
    try:
        asyncio.run(adapter.call("execute"))
    except ValueError as exc:
        assert "Сначала подтвердите" in str(exc)
    else:
        raise AssertionError("execute must fail closed before approve")
    asyncio.run(adapter.call("approve", "execute"))
    executed = asyncio.run(adapter.call("execute"))
    assert executed["ok"] is True
    snapshot = asyncio.run(adapter.snapshot())
    assert snapshot["approved"] is True
    assert snapshot["stage"] == 9
    assert backend.calls == 1


def test_real_json_routes_complete_guided_workflow(tmp_path):
    async def exercise() -> None:
        orchestrator = DemoOrchestrator(repo_root=tmp_path, work_dir=tmp_path / "demo")
        app = create_app(orchestrator=orchestrator)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            imported = await client.post("/api/import", json={"payload": {"demo": True}, "format": "json"})
            assert imported.status_code == 200
            detected = await client.post("/api/action/detect_patterns", json={})
            assert detected.status_code == 200
            patterns = detected.json()["snapshot"]["patterns"]
            assert len(patterns) == 3
            flagship = next(item for item in patterns if "check_covenants" in " ".join(item["representative_sequence"]))
            steps = (
                ("/api/hypothesis/select", {"pattern_id": flagship["pattern_id"]}),
                ("/api/action/generate_skill", {}),
                ("/api/sandbox/run", {"version": "1.0.0"}),
                ("/api/approve", {"action": "execute"}),
                ("/api/action/execute", {}),
                ("/api/action/evolve", {}),
                ("/api/action/promote", {}),
                ("/api/action/rollback", {}),
                ("/api/action/export_template", {}),
            )
            for path, payload in steps:
                response = await client.post(path, json=payload)
                assert response.status_code == 200, (path, response.text)
                assert response.json()["ok"] is True

    asyncio.run(exercise())
