"""Deterministic end-to-end orchestration and evidence assembly."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from ouroboros.hackathon.budget_guard import BudgetGuard
from ouroboros.hackathon.dossier import demo_dossier_case, execute_dossier, sandbox_test
from ouroboros.hackathon.models import AuditEntry, Pattern, TraceEvent, stable_id
from ouroboros.hackathon.pattern_miner import evaluate_pattern_mining, mine_patterns
from ouroboros.hackathon.safety import validate_trace_safety
from ouroboros.hackathon.skill_builder import SkillLifecycle, build_micro_skill
from ouroboros.hackathon.trace import generate_synthetic_trace, parse_csv_events, parse_json_events


class DeterministicOrchestrator:
    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root
        self.audit: List[AuditEntry] = []
        self.budget = BudgetGuard(
            output_root / "artifacts" / "budget_ledger.json",
            output_root / "artifacts" / "budget_ledger.md",
        )

    def _record(self, actor: str, action: str, status: str, evidence: Dict[str, Any]) -> None:
        sequence = len(self.audit) + 1
        timestamp = (datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(seconds=sequence)).isoformat()
        self.audit.append(AuditEntry(sequence, timestamp, actor, action, status, evidence))

    @staticmethod
    def _flagship(patterns: List[Pattern]) -> Pattern:
        for pattern in patterns:
            if any(token.endswith(":check_covenants") for token in pattern.representative_sequence):
                return pattern
        raise RuntimeError("flagship pattern was not detected")

    def run(self) -> Dict[str, Any]:
        trace = generate_synthetic_trace()
        events = parse_json_events(trace["events"])
        self.budget.record_local_call(stage="trace", purpose="generate and import synthetic digital trace")
        self._record("Trace Ingestion Agent", "ingest_trace", "passed", {"events": len(events)})

        safety = validate_trace_safety(trace["events"])
        self._record("Safety Agent", "validate_trace", "passed" if safety["safe"] else "blocked", safety)
        patterns = mine_patterns(events)
        mining_metrics = evaluate_pattern_mining(patterns, trace["ground_truth"])
        self.budget.record_local_call(stage="mining", purpose="cluster recurring event sequences")
        self._record("Pattern Miner Agent", "mine_patterns", "passed", mining_metrics)

        pattern = self._flagship(patterns)
        proposal_id = stable_id("proposal", pattern.to_dict(), 14)
        self._record(
            "Automation Hypothesis Agent",
            "create_hypothesis",
            "passed",
            {
                "proposal_id": proposal_id,
                "pattern_id": pattern.pattern_id,
                "saving_seconds": pattern.potential_time_saving_seconds,
            },
        )

        generated_root = self.output_root / "skills" / "generated"
        lifecycle = SkillLifecycle()
        version_one = build_micro_skill(generated_root, pattern, "1.0.0")
        lifecycle.add(version_one)
        self._record(
            "Micro-Skill Builder Agent",
            "generate_version",
            "passed",
            {
                "skill_id": version_one.skill_id,
                "version": version_one.version,
                "status": version_one.status,
                "content_hash": version_one.content_hash,
                "source_pattern_id": version_one.source_pattern_id,
                "created_at": version_one.created_at,
            },
        )

        case = demo_dossier_case()
        v1_result = sandbox_test(case, "1.0.0")
        self._record(
            "Sandbox Test Agent", "test_version_1", "failed" if not v1_result.passed else "passed", v1_result.to_dict()
        )
        version_two = build_micro_skill(generated_root, pattern, "2.0.0")
        lifecycle.add(version_two)
        self._record(
            "Evolution Agent",
            "generate_version_2",
            "passed",
            {
                "root_cause": "v1 omitted cross-document revenue comparison",
                "version": "2.0.0",
            },
        )
        v2_result = sandbox_test(case, "2.0.0")
        self._record(
            "Quality Reviewer Agent", "test_version_2", "passed" if v2_result.passed else "failed", v2_result.to_dict()
        )

        approval = lifecycle.approve(
            proposal_id,
            "2.0.0",
            "employee_credit_001",
            f"APPROVE {proposal_id} 2.0.0",
        )
        self._record("Employee", "approve_and_promote", "passed", approval.to_dict())
        lifecycle.consume_approval(approval)
        lifecycle.promote("2.0.0")
        execution = execute_dossier(
            case,
            version="2.0.0",
            approval=approval,
            proposal_id=proposal_id,
            execution_mode="approved",
        )
        self._record("Execution Agent", "execute_approved_skill", "passed" if execution["ok"] else "failed", execution)

        lifecycle.rollback("1.0.0")
        lifecycle.promote("2.0.0")
        self._record("Evolution Agent", "verify_rollback", "passed", {"history": lifecycle.history[-2:]})
        returned_seconds = max(0.0, pattern.average_duration_seconds - 18 * 60)
        value = {
            "as_is_seconds": pattern.average_duration_seconds,
            "to_be_seconds": 18 * 60,
            "returned_seconds_per_execution": round(returned_seconds, 2),
            "manual_steps_as_is": pattern.manual_steps,
            "manual_steps_to_be": 3,
            "metric_basis": "simulated synthetic trace and deterministic executor",
        }
        self._record("Value Tracker Agent", "calculate_value", "passed", value)
        self.budget.record_local_call(stage="e2e", purpose="final deterministic verification")

        report = {
            "ok": v2_result.passed and execution["ok"] and len(patterns) >= 3,
            "trace": {"events": len(events), "working_days": len(trace["working_days"])},
            "patterns": [item.to_dict() for item in patterns],
            "mining_metrics": mining_metrics,
            "proposal_id": proposal_id,
            "skill": {"root": version_two.root_path, "active_version": lifecycle.active_version},
            "sandbox": {"v1": v1_result.to_dict(), "v2": v2_result.to_dict()},
            "approval": approval.to_dict(),
            "execution": execution,
            "evolution_history": lifecycle.history,
            "value": value,
            "safety": safety,
            "budget": self.budget.snapshot(),
            "audit": [entry.to_dict() for entry in self.audit],
        }
        artifacts = self.output_root / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        import json

        (artifacts / "hackathon_e2e.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return report


def run_demo(output_root: Path) -> Dict[str, Any]:
    return DeterministicOrchestrator(output_root).run()


class DemoOrchestrator:
    """Stateful, synchronous API used by the localhost guided-demo server."""

    def __init__(self, repo_root: Path | None = None, work_dir: Path | None = None) -> None:
        self.repo_root = Path(repo_root or Path.cwd()).resolve()
        self.work_dir = Path(work_dir or self.repo_root / "tmp" / "hackathon-demo").resolve()
        self.reset_demo()

    def _record(self, actor: str, action: str, status: str, evidence: Dict[str, Any]) -> None:
        sequence = len(self.audit) + 1
        timestamp = (datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(seconds=sequence)).isoformat()
        self.audit.append(AuditEntry(sequence, timestamp, actor, action, status, evidence))

    @staticmethod
    def _version_label(version: str) -> str:
        normalized = str(version).strip().lower()
        aliases = {"v1": "1.0.0", "1": "1.0.0", "v2": "2.0.0", "2": "2.0.0"}
        return aliases.get(normalized, normalized)

    def _require_pattern(self) -> Pattern:
        if self.selected_pattern is None:
            raise ValueError("select an automation hypothesis first")
        return self.selected_pattern

    @staticmethod
    def _skill_evidence(version: Any) -> Dict[str, Any]:
        return {
            "skill_id": version.skill_id,
            "version": version.version,
            "status": version.status,
            "content_hash": version.content_hash,
            "source_pattern_id": version.source_pattern_id,
            "created_at": version.created_at,
        }

    def reset_demo(self) -> Dict[str, Any]:
        self.stage = "ready"
        self.events: List[TraceEvent] = []
        self.trace_metadata: Dict[str, Any] = {}
        self.safety: Dict[str, Any] = {}
        self.patterns: List[Pattern] = []
        self.mining_metrics: Dict[str, Any] = {}
        self.selected_pattern: Pattern | None = None
        self.proposal_id = ""
        self.hypothesis: Dict[str, Any] = {}
        self.lifecycle = SkillLifecycle()
        self.sandbox_results: Dict[str, Any] = {}
        self.approval = None
        self.execution: Dict[str, Any] = {}
        self.evolution: Dict[str, Any] = {}
        self.value: Dict[str, Any] = {}
        self.template: Dict[str, Any] = {}
        self.audit: List[AuditEntry] = []
        artifacts = self.work_dir / "artifacts"
        self.budget = BudgetGuard(artifacts / "budget_ledger.json", artifacts / "budget_ledger.md")
        self._record("Demo Controller", "reset_demo", "passed", {"mode": "deterministic"})
        return self.snapshot()

    def import_trace(self, payload: Any, trace_format: str = "json") -> Dict[str, Any]:
        normalized_format = str(trace_format).strip().lower()
        generated: Dict[str, Any] | None = None
        if isinstance(payload, str) and payload in {"demo", "synthetic"}:
            generated = generate_synthetic_trace()
        elif isinstance(payload, dict) and payload.get("demo") is True and "events" not in payload:
            generated = generate_synthetic_trace()
        if generated is not None:
            events = parse_json_events(generated["events"])
            ground_truth = dict(generated["ground_truth"])
            working_days = list(generated["working_days"])
        elif normalized_format == "json":
            events = parse_json_events(payload)
            ground_truth = dict(payload.get("ground_truth") or {}) if isinstance(payload, dict) else {}
            working_days = sorted({event.timestamp[:10] for event in events})
        elif normalized_format == "csv":
            events = parse_csv_events(payload)
            ground_truth = {}
            working_days = sorted({event.timestamp[:10] for event in events})
        else:
            raise ValueError("trace format must be json or csv")
        raw_events = [event.to_dict() for event in events]
        safety = validate_trace_safety(raw_events)
        if not safety["safe"]:
            self._record("Safety Agent", "validate_trace", "blocked", safety)
            raise ValueError("trace failed critical DLP safety checks")
        self.events = events
        self.trace_metadata = {
            "event_count": len(events),
            "working_days": working_days,
            "ground_truth": ground_truth,
            "format": normalized_format,
            "synthetic": generated is not None,
        }
        self.safety = safety
        self.patterns = []
        self.selected_pattern = None
        self.proposal_id = ""
        self.stage = "trace_imported"
        self.budget.record_local_call(stage="trace", purpose="import and validate digital trace")
        self._record(
            "Trace Ingestion Agent",
            "import_trace",
            "passed",
            {
                "events": len(events),
                "working_days": len(working_days),
                "format": normalized_format,
            },
        )
        return dict(self.trace_metadata)

    def detect_patterns(self) -> List[Dict[str, Any]]:
        if not self.events:
            raise ValueError("import a trace before detecting patterns")
        self.patterns = mine_patterns(self.events)
        self.mining_metrics = evaluate_pattern_mining(
            self.patterns,
            dict(self.trace_metadata.get("ground_truth") or {}),
        )
        self.stage = "patterns_detected"
        self.budget.record_local_call(stage="mining", purpose="cluster recurring event sequences")
        self._record(
            "Pattern Miner Agent",
            "detect_patterns",
            "passed",
            {
                "patterns": len(self.patterns),
                **self.mining_metrics,
            },
        )
        return [pattern.to_dict() for pattern in self.patterns]

    def select_hypothesis(self, pattern_id: str) -> Dict[str, Any]:
        pattern = next((item for item in self.patterns if item.pattern_id == pattern_id), None)
        if pattern is None:
            raise ValueError("unknown pattern_id")
        self.selected_pattern = pattern
        self.proposal_id = stable_id("proposal", pattern.to_dict(), 14)
        self.hypothesis = {
            "proposal_id": self.proposal_id,
            "pattern_id": pattern.pattern_id,
            "name": pattern.name,
            "confidence": pattern.confidence,
            "risk_level": pattern.risk_level,
            "potential_time_saving_seconds": pattern.potential_time_saving_seconds,
            "status": "selected",
        }
        self.stage = "hypothesis_selected"
        self._record("Automation Hypothesis Agent", "select_hypothesis", "passed", dict(self.hypothesis))
        return dict(self.hypothesis)

    def generate_skill(self) -> Dict[str, Any]:
        pattern = self._require_pattern()
        version = build_micro_skill(self.work_dir / "skills" / "generated", pattern, "1.0.0")
        self.lifecycle.add(version)
        self.stage = "skill_generated"
        evidence = self._skill_evidence(version)
        self._record("Micro-Skill Builder Agent", "generate_skill", "passed", evidence)
        return {**evidence, "root_path": version.root_path}

    def run_sandbox(self, version: str = "v1") -> Dict[str, Any]:
        version_number = self._version_label(version)
        if version_number not in self.lifecycle.versions:
            raise ValueError(f"skill version {version_number} has not been generated")
        result = sandbox_test(demo_dossier_case(), version_number)
        self.sandbox_results[version_number] = result
        self.stage = "sandbox_passed" if result.passed else "sandbox_failed"
        self._record(
            "Sandbox Test Agent",
            "run_sandbox",
            "passed" if result.passed else "failed",
            result.to_dict(),
        )
        return result.to_dict()

    def approve(self, action: str = "execute") -> Dict[str, Any]:
        if not self.proposal_id:
            raise ValueError("select an automation hypothesis first")
        if str(action).strip().lower() == "hypothesis":
            self.hypothesis["status"] = "approved"
            self._record("Employee", "approve_hypothesis", "passed", {"proposal_id": self.proposal_id})
            return dict(self.hypothesis)
        passing = [version for version, result in self.sandbox_results.items() if result.passed]
        if not passing and (self.sandbox_results.get("1.0.0") is not None):
            # The guided UI treats the controlled v1 regression as a review note.
            # Repair and regression-test it before issuing any execution receipt.
            self.evolve()
            passing = [version for version, result in self.sandbox_results.items() if result.passed]
        if not passing:
            raise ValueError("a passing sandbox result is required before approval")
        version = sorted(passing)[-1]
        confirmation = f"APPROVE {self.proposal_id} {version}"
        self.approval = self.lifecycle.approve(
            self.proposal_id,
            version,
            "employee_credit_001",
            confirmation,
        )
        self.stage = "approved"
        self._record("Employee", "approve_execution", "passed", self.approval.to_dict())
        return self.approval.to_dict()

    def execute(self) -> Dict[str, Any]:
        if self.approval is None:
            raise ValueError("explicit execution approval is required")
        version = self.approval.version
        self.lifecycle.consume_approval(self.approval)
        if self.lifecycle.active_version != version:
            self.lifecycle.promote(version)
        self.execution = execute_dossier(
            demo_dossier_case(),
            version=version,
            approval=self.approval,
            proposal_id=self.proposal_id,
            execution_mode="approved",
        )
        self.stage = "executed"
        self._record(
            "Execution Agent",
            "execute",
            "passed" if self.execution.get("ok") else "failed",
            self.execution,
        )
        pattern = self._require_pattern()
        returned = max(0.0, pattern.average_duration_seconds - 18 * 60)
        self.value = {
            "as_is_seconds": pattern.average_duration_seconds,
            "to_be_seconds": 18 * 60,
            "returned_seconds_per_execution": round(returned, 2),
            "manual_steps_as_is": pattern.manual_steps,
            "manual_steps_to_be": 3,
            "metric_basis": "simulated synthetic trace and deterministic executor",
        }
        return dict(self.execution)

    def evolve(self) -> Dict[str, Any]:
        pattern = self._require_pattern()
        if self.evolution and "2.0.0" in self.lifecycle.versions:
            version = self.lifecycle.versions["2.0.0"]
            return {**self.evolution, "skill": {**self._skill_evidence(version), "root_path": version.root_path}}
        v1 = self.sandbox_results.get("1.0.0")
        if v1 is None or v1.passed:
            raise ValueError("the controlled v1 sandbox failure is required before evolution")
        version = build_micro_skill(self.work_dir / "skills" / "generated", pattern, "2.0.0")
        self.lifecycle.add(version)
        v2 = sandbox_test(demo_dossier_case(), "2.0.0")
        self.sandbox_results["2.0.0"] = v2
        self.evolution = {
            "from_version": "1.0.0",
            "to_version": "2.0.0",
            "root_cause": "v1 omitted cross-document revenue comparison",
            "fix": "compare financial report revenue with account-statement reported revenue",
            "passed": v2.passed,
        }
        self.stage = "evolved"
        self._record("Evolution Agent", "evolve", "passed" if v2.passed else "failed", dict(self.evolution))
        return {**self.evolution, "skill": {**self._skill_evidence(version), "root_path": version.root_path}}

    def promote(self) -> Dict[str, Any]:
        if self.approval is None:
            raise ValueError("explicit approval is required before promotion")
        self.lifecycle.promote(self.approval.version)
        self.stage = "promoted"
        result = {"active_version": self.lifecycle.active_version, "approval_id": self.approval.receipt_id}
        self._record("Evolution Agent", "promote", "passed", result)
        return result

    def rollback(self) -> Dict[str, Any]:
        if not self.lifecycle.active_version:
            raise ValueError("there is no active version to roll back")
        current = self.lifecycle.active_version
        candidates = [version for version in sorted(self.lifecycle.versions) if version != current]
        if not candidates:
            raise ValueError("there is no rollback target")
        target = candidates[-1] if current == "1.0.0" else candidates[0]
        self.lifecycle.rollback(target)
        self.stage = "rolled_back"
        result = {"from_version": current, "active_version": target}
        self._record("Evolution Agent", "rollback", "passed", result)
        return result

    def export_template(self) -> Dict[str, Any]:
        pattern = self._require_pattern()
        template = {
            "schema_version": 1,
            "template_id": stable_id("template", [pattern.pattern_id, "credit_dossier"], 14),
            "name": "Evidence-backed client mini-dossier",
            "source_pattern": {
                "representative_sequence": pattern.representative_sequence,
                "stable_actions": pattern.stable_actions,
                "variable_actions": pattern.variable_actions,
            },
            "required_documents": [
                "account_statement",
                "covenant_register",
                "financial_report",
                "limit_report",
            ],
            "contains_personal_data": False,
            "external_writes": False,
        }
        destination = self.work_dir / "artifacts" / "anonymized_skill_template.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.template = {**template, "path": str(destination)}
        self.stage = "template_exported"
        self._record(
            "Template Export Agent",
            "export_template",
            "passed",
            {
                "template_id": template["template_id"],
                "contains_personal_data": False,
            },
        )
        return dict(self.template)

    def snapshot(self) -> Dict[str, Any]:
        versions = {
            key: {**self._skill_evidence(value), "root_path": value.root_path}
            for key, value in sorted(self.lifecycle.versions.items())
        }
        return {
            "stage": self.stage,
            "trace": dict(self.trace_metadata),
            "safety": dict(self.safety),
            "patterns": [pattern.to_dict() for pattern in self.patterns],
            "mining_metrics": dict(self.mining_metrics),
            "selected_pattern_id": self.selected_pattern.pattern_id if self.selected_pattern else None,
            "hypothesis": dict(self.hypothesis),
            "skill": {
                "versions": versions,
                "active_version": self.lifecycle.active_version,
                "history": list(self.lifecycle.history),
            },
            "sandbox": {key: value.to_dict() for key, value in sorted(self.sandbox_results.items())},
            "approval": self.approval.to_dict() if self.approval else None,
            "execution": dict(self.execution),
            "evolution": dict(self.evolution),
            "value": dict(self.value),
            "template": dict(self.template),
            "budget": self.budget.snapshot(),
            "audit": [entry.to_dict() for entry in self.audit],
        }
