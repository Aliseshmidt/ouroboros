"""Standalone localhost server for the Sber AI Hack guided demo."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import inspect
import os
from pathlib import Path
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "web" / "hackathon"
DEFAULT_WORK_DIR = REPO_ROOT / "tmp" / "hackathon-demo"
MAX_REQUEST_BYTES = 2 * 1024 * 1024
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class OrchestratorUnavailable(RuntimeError):
    """Raised when the independently shipped demo backend is unavailable."""


class DemoAdapter:
    """Thin defensive adapter around ``DemoOrchestrator``."""

    def __init__(self, orchestrator: Any | None = None) -> None:
        self._orchestrator = orchestrator
        self._load_error: str | None = None
        self._load_lock = asyncio.Lock()
        self._report: dict[str, Any] | None = None
        self._stage = 0
        self._approved = False
        self._selected_pattern_id = ""

    @property
    def load_error(self) -> str | None:
        return self._load_error

    async def get_orchestrator(self) -> Any:
        if self._orchestrator is not None:
            return self._orchestrator
        async with self._load_lock:
            if self._orchestrator is not None:
                return self._orchestrator
            try:
                try:
                    from ouroboros.hackathon.orchestrator import DemoOrchestrator as OrchestratorClass
                except ImportError:
                    from ouroboros.hackathon.orchestrator import DeterministicOrchestrator as OrchestratorClass

                signature = inspect.signature(OrchestratorClass)
                parameters = signature.parameters
                work_dir = Path(os.environ.get("OUROBOROS_HACKATHON_WORK_DIR", DEFAULT_WORK_DIR))
                kwargs: dict[str, Path] = {}
                if "repo_root" in parameters:
                    kwargs["repo_root"] = REPO_ROOT
                if "work_dir" in parameters:
                    kwargs["work_dir"] = work_dir
                if "output_root" in parameters:
                    kwargs["output_root"] = work_dir
                self._orchestrator = OrchestratorClass(**kwargs)
                self._load_error = None
            except Exception as exc:
                self._load_error = f"{type(exc).__name__}: {exc}"
                raise OrchestratorUnavailable(
                    "Демо-движок ещё не готов. Запустите сервер после установки backend-модуля."
                ) from exc
        return self._orchestrator

    async def call(self, method_name: str, *args: Any) -> Any:
        orchestrator = await self.get_orchestrator()
        method = getattr(orchestrator, method_name, None)
        if callable(method):
            result = method(*args)
            if inspect.isawaitable(result):
                result = await result
            return result
        if callable(getattr(orchestrator, "run", None)):
            return await self._call_run_report_backend(method_name, *args)
        raise OrchestratorUnavailable(f"Демо-движок не реализует операцию {method_name}.")

    async def snapshot(self) -> dict[str, Any]:
        orchestrator = await self.get_orchestrator()
        if not callable(getattr(orchestrator, "snapshot", None)) and callable(getattr(orchestrator, "run", None)):
            return self._report_snapshot()
        result = await self.call("snapshot")
        normalized = _jsonable(result)
        if not isinstance(normalized, dict):
            raise RuntimeError("snapshot() должен возвращать JSON-объект")
        return normalized

    async def _ensure_report(self) -> dict[str, Any]:
        if self._report is None:
            orchestrator = await self.get_orchestrator()
            result = await asyncio.to_thread(orchestrator.run)
            normalized = _jsonable(result)
            if not isinstance(normalized, dict):
                raise RuntimeError("run() должен возвращать JSON-объект")
            self._report = normalized
        return self._report

    async def _call_run_report_backend(self, method_name: str, *args: Any) -> Any:
        if method_name == "reset_demo":
            self._report = None
            self._stage = 0
            self._approved = False
            self._selected_pattern_id = ""
            return {"reset": True}

        report = await self._ensure_report()
        stage_by_method = {
            "import_trace": 2,
            "detect_patterns": 4,
            "select_hypothesis": 5,
            "generate_skill": 6,
            "run_sandbox": 7,
            "approve": 8,
            "execute": 9,
            "export_template": 11,
            "evolve": 12,
            "promote": 12,
            "rollback": 12,
        }
        if method_name not in stage_by_method:
            raise OrchestratorUnavailable(f"Операция {method_name} не поддерживается demo report backend.")
        if method_name == "select_hypothesis":
            self._selected_pattern_id = str(args[0]) if args else ""
        if method_name == "approve":
            self._approved = True
        if method_name == "execute" and not self._approved:
            raise ValueError("Сначала подтвердите план на экране согласования")
        self._stage = max(self._stage, stage_by_method[method_name])
        slices = {
            "import_trace": {"trace": report.get("trace"), "safety": report.get("safety")},
            "detect_patterns": {"patterns": report.get("patterns"), "metrics": report.get("mining_metrics")},
            "select_hypothesis": {"proposal_id": report.get("proposal_id")},
            "generate_skill": report.get("skill"),
            "run_sandbox": report.get("sandbox"),
            "approve": report.get("approval"),
            "execute": report.get("execution"),
            "export_template": {"skill": report.get("skill"), "mode": "local_demo"},
            "evolve": {"sandbox": report.get("sandbox"), "history": report.get("evolution_history")},
            "promote": {"active_version": report.get("skill", {}).get("active_version")},
            "rollback": {"history": report.get("evolution_history")},
        }
        return slices[method_name]

    def _report_snapshot(self) -> dict[str, Any]:
        return {
            "stage": self._stage,
            "approved": self._approved,
            "selected_pattern_id": self._selected_pattern_id,
            "mode": "deterministic_local_demo",
            "report": self._report or {},
        }


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _jsonable(dataclasses.asdict(value))
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _jsonable(model_dump())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


async def _read_json_object(request: Request) -> dict[str, Any]:
    content_length = request.headers.get("content-length", "")
    if content_length.isdigit() and int(content_length) > MAX_REQUEST_BYTES:
        raise ValueError("Запрос превышает лимит 2 МБ")
    try:
        body = await request.json()
    except Exception as exc:
        raise ValueError("Ожидается корректный JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("Тело запроса должно быть JSON-объектом")
    return body


async def _action_response(adapter: DemoAdapter, method_name: str, *args: Any) -> JSONResponse:
    result = await adapter.call(method_name, *args)
    snapshot = await adapter.snapshot()
    return JSONResponse(
        {
            "ok": True,
            "action": method_name,
            "result": _jsonable(result),
            "snapshot": snapshot,
        }
    )


def _error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, OrchestratorUnavailable):
        return JSONResponse({"ok": False, "error": str(exc), "code": "backend_unavailable"}, status_code=503)
    if isinstance(exc, (ValueError, KeyError)):
        return JSONResponse({"ok": False, "error": str(exc), "code": "invalid_request"}, status_code=400)
    return JSONResponse(
        {"ok": False, "error": "Операция не выполнена. Проверьте журнал демо.", "code": "operation_failed"},
        status_code=500,
    )


def create_app(orchestrator: Any | None = None) -> Starlette:
    """Create an injectable Starlette app without starting a real port."""
    adapter = DemoAdapter(orchestrator)

    async def index_page(_request: Request) -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", media_type="text/html")

    async def health(_request: Request) -> JSONResponse:
        try:
            await adapter.get_orchestrator()
            return JSONResponse({"ok": True, "service": "ouroboros-hackathon", "mode": "local-demo"})
        except Exception as exc:
            response = _error_response(exc)
            response.status_code = 200
            return response

    async def state(_request: Request) -> JSONResponse:
        try:
            return JSONResponse({"ok": True, "snapshot": await adapter.snapshot()})
        except Exception as exc:
            return _error_response(exc)

    async def reset(_request: Request) -> JSONResponse:
        try:
            return await _action_response(adapter, "reset_demo")
        except Exception as exc:
            return _error_response(exc)

    async def import_trace(request: Request) -> JSONResponse:
        try:
            body = await _read_json_object(request)
            trace_format = str(body.get("format", "json")).lower()
            if trace_format not in {"json", "csv"}:
                raise ValueError("Поддерживаются только форматы JSON и CSV")
            payload = body.get("payload")
            if payload is None:
                raise ValueError("Поле payload обязательно")
            return await _action_response(adapter, "import_trace", payload, trace_format)
        except Exception as exc:
            return _error_response(exc)

    def simple_action(method_name: str):
        async def endpoint(_request: Request) -> JSONResponse:
            try:
                return await _action_response(adapter, method_name)
            except Exception as exc:
                return _error_response(exc)

        return endpoint

    async def select_hypothesis(request: Request) -> JSONResponse:
        try:
            body = await _read_json_object(request)
            pattern_id = str(body.get("pattern_id", "")).strip()
            if not pattern_id:
                raise ValueError("Выберите паттерн автоматизации")
            return await _action_response(adapter, "select_hypothesis", pattern_id)
        except Exception as exc:
            return _error_response(exc)

    async def run_sandbox(request: Request) -> JSONResponse:
        try:
            body = await _read_json_object(request)
            version = str(body.get("version", "v1")).strip() or "v1"
            return await _action_response(adapter, "run_sandbox", version)
        except Exception as exc:
            return _error_response(exc)

    async def approve(request: Request) -> JSONResponse:
        try:
            body = await _read_json_object(request)
            action = str(body.get("action", "execute")).strip() or "execute"
            return await _action_response(adapter, "approve", action)
        except Exception as exc:
            return _error_response(exc)

    simple_methods = {
        "detect_patterns",
        "generate_skill",
        "execute",
        "evolve",
        "promote",
        "rollback",
        "export_template",
    }
    routes = [
        Route("/", index_page),
        Route("/api/health", health),
        Route("/api/state", state),
        Route("/api/reset", reset, methods=["POST"]),
        Route("/api/import", import_trace, methods=["POST"]),
        Route("/api/hypothesis/select", select_hypothesis, methods=["POST"]),
        Route("/api/sandbox/run", run_sandbox, methods=["POST"]),
        Route("/api/approve", approve, methods=["POST"]),
    ]
    for method_name in sorted(simple_methods):
        path = f"/api/action/{method_name}"
        routes.append(Route(path, simple_action(method_name), methods=["POST"], name=method_name))
    routes.append(Mount("/static", StaticFiles(directory=WEB_DIR), name="static"))
    app = Starlette(debug=False, routes=routes)
    app.state.demo_adapter = adapter
    return app


app = create_app()


def main() -> int:
    parser = argparse.ArgumentParser(description="Локальный сервер демо Sber AI Hack")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8776)
    args = parser.parse_args()
    if args.host not in LOOPBACK_HOSTS:
        parser.error("hackathon demo binds only to localhost")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
