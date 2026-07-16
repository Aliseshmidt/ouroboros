"""Build reproducible hackathon evidence without network or paid model calls."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ouroboros.hackathon.orchestrator import run_demo  # noqa: E402
from ouroboros.hackathon.trace import generate_synthetic_trace  # noqa: E402


def _canonical_hash(payload: object) -> str:
    packed = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def _normalized_report(report: dict[str, object]) -> dict[str, object]:
    """Remove the intentionally run-local generated-skill path before hashing."""
    normalized = json.loads(json.dumps(report, ensure_ascii=False))
    normalized["skill"]["root"] = "skills/generated/credit_dossier_9b7dad31"
    return normalized


def _write_demo_data() -> dict[str, object]:
    trace = generate_synthetic_trace()
    output_dir = REPO_ROOT / "submission" / "demo_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "digital_trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    fields = list(trace["events"][0])
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(trace["events"])
    (output_dir / "digital_trace.csv").write_text(csv_buffer.getvalue(), encoding="utf-8")
    return {
        "events": len(trace["events"]),
        "working_days": len(trace["working_days"]),
        "ground_truth_cases": len(trace["ground_truth"]),
        "ground_truth_patterns": len(set(trace["ground_truth"].values())),
        "json_sha256": hashlib.sha256((output_dir / "digital_trace.json").read_bytes()).hexdigest(),
        "csv_sha256": hashlib.sha256((output_dir / "digital_trace.csv").read_bytes()).hexdigest(),
    }


def build() -> dict[str, object]:
    run_root = REPO_ROOT / "tmp" / "hackathon-evidence-runs"
    if run_root.exists():
        shutil.rmtree(run_root)
    runs: list[dict[str, object]] = []
    hashes: list[str] = []
    final_report: dict[str, object] = {}
    for index in range(1, 4):
        report = run_demo(run_root / f"run-{index}")
        report_hash = _canonical_hash(_normalized_report(report))
        hashes.append(report_hash)
        runs.append(
            {
                "run": index,
                "ok": report["ok"],
                "patterns": len(report["patterns"]),
                "events": report["trace"]["events"],
                "sandbox_v2_passed": report["sandbox"]["v2"]["passed"],
                "approved_execution_ok": report["execution"]["ok"],
                "active_version": report["skill"]["active_version"],
                "report_sha256": report_hash,
            }
        )
        final_report = report
    if not all(bool(run["ok"]) for run in runs):
        raise RuntimeError("one or more deterministic E2E runs failed")
    if len(set(hashes)) != 1:
        raise RuntimeError("deterministic E2E reports produced different hashes")

    artifacts = REPO_ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    final_report = _normalized_report(final_report)
    (artifacts / "hackathon_e2e.json").write_text(
        json.dumps(final_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    evidence = {
        "ok": True,
        "execution_mode": "local deterministic; no network or paid API calls",
        "consecutive_runs": runs,
        "stable_across_runs": len(set(hashes)) == 1,
        "demo_data": _write_demo_data(),
    }
    (artifacts / "e2e_runs.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return evidence


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
