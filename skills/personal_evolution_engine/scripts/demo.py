"""Run the Personal Evolution Engine end to end without starting Ouroboros."""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

SKILL_DIR = Path(__file__).resolve().parents[1]


class _DemoAPI:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def get_state_dir(self) -> str:
        return str(self._state_dir)


def _load_plugin() -> ModuleType:
    path = SKILL_DIR / "plugin.py"
    spec = importlib.util.spec_from_file_location("personal_evolution_demo_plugin", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load plugin from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decode(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error") or "Personal Evolution Engine step failed")
    return payload


def run_demo() -> dict[str, Any]:
    plugin = _load_plugin()
    with tempfile.TemporaryDirectory(prefix="personal-evolution-demo-") as state_dir:
        engine = plugin.PersonalEvolutionEngine(_DemoAPI(Path(state_dir)))
        demo = _decode(engine.demo_trace())
        analysis = _decode(engine.analyze_trace(demo["events"], "hackathon_e2e_demo"))["analysis"]
        pattern = analysis["patterns"][0]
        proposal = _decode(
            engine.propose_skill(
                pattern["pattern_id"],
                "Return time to an employee while keeping every risky action under human control.",
            )
        )["proposal"]
        verification = _decode(engine.verify_skill(proposal["proposal_id"], demo["events"]))["verification"]
        approval = _decode(
            engine.approve_skill(
                proposal["proposal_id"],
                f"APPROVE {proposal['proposal_id']}",
            )
        )
        execution = _decode(engine.run_skill(proposal["proposal_id"], "demo_case_01", "approved"))
        feedback = _decode(engine.record_feedback(proposal["proposal_id"], "accepted", 15, 5))
        portfolio = _decode(engine.portfolio())
        return {
            "ok": True,
            "dataset": {
                "events": len(demo["events"]),
                "cases": analysis["case_count"],
                "patterns": len(analysis["patterns"]),
            },
            "selected_pattern": {
                "pattern_id": pattern["pattern_id"],
                "title": pattern["title"],
                "occurrences": pattern["occurrences"],
                "risk_level": pattern["risk_level"],
            },
            "micro_skill": {
                "proposal_id": proposal["proposal_id"],
                "verified_cases": verification["passed_cases"],
                "verification_status": verification["status"],
                "approval_status": approval["status"],
                "execution_mode": execution["execution_mode"],
                "external_writes": execution["outbound_writes"],
            },
            "evolution": feedback["evolution_candidate"],
            "portfolio": portfolio["metrics"],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optionally save the JSON evidence report.")
    args = parser.parse_args()
    report = run_demo()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
