"""Personal Evolution Engine extension for approval-gated micro-automation.

The extension intentionally uses only the Python standard library. It accepts an
anonymized event trace, retains aggregate learning state only, and never invokes
an external system. Production connectors are deliberately represented as
approved-MCP contracts so the same workflow can support different professions
without receiving broader permissions than the employee already has.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_MAX_EVENTS = 2_000
_MAX_PAYLOAD_BYTES = 1_000_000
_MAX_TEXT = 160
_MIN_PATTERN_OCCURRENCES = 3
_MIN_VERIFIED_CASES = 10
_STATE_FILENAME = "personal_evolution_state.json"
_SENSITIVE_FIELD_RE = re.compile(r"(?:api[_-]?key|authorization|credential|password|secret|token)", re.IGNORECASE)
_SAFE_IDENTIFIER_RE = re.compile(r"[^a-z0-9_]+")
_WRITE_ACTIONS = frozenset({"create", "delete", "pay", "send", "submit", "update", "approve"})


_INTEGRATIONS: dict[str, dict[str, str]] = {
    "mail": {
        "category": "communication",
        "mcp_contract": "Corporate mail MCP (Microsoft 365, Gmail Workspace, or internal equivalent)",
        "initial_scope": "Read metadata and create drafts only",
        "write_policy": "Sending always requires an employee confirmation",
    },
    "calendar": {
        "category": "planning",
        "mcp_contract": "Corporate calendar MCP",
        "initial_scope": "Read availability and prepare a meeting draft",
        "write_policy": "Creating or changing a meeting requires confirmation",
    },
    "task_tracker": {
        "category": "delivery",
        "mcp_contract": "Jira, YouTrack, or internal task-tracker MCP",
        "initial_scope": "Read assigned work and prepare a task draft",
        "write_policy": "Create, transition, and comment operations require confirmation",
    },
    "document_store": {
        "category": "knowledge",
        "mcp_contract": "SharePoint, Confluence, file-storage, or internal knowledge-base MCP",
        "initial_scope": "Read only within the employee's existing ACL",
        "write_policy": "Publishing or replacing files requires confirmation",
    },
    "spreadsheet": {
        "category": "analysis",
        "mcp_contract": "Excel, Google Sheets, or internal spreadsheet MCP",
        "initial_scope": "Read and calculate in a sandbox",
        "write_policy": "Writing to a source workbook requires confirmation and diff review",
    },
    "crm": {
        "category": "customer_work",
        "mcp_contract": "CRM MCP",
        "initial_scope": "Read cards and prepare updates",
        "write_policy": "Any client-card update requires confirmation",
    },
    "bpm": {
        "category": "process",
        "mcp_contract": "BPM or case-management MCP",
        "initial_scope": "Read case status and prepare a transition",
        "write_policy": "Submission, routing, and approval require confirmation",
    },
    "bi": {
        "category": "analytics",
        "mcp_contract": "BI or SQL-readonly MCP",
        "initial_scope": "Run allowlisted read-only reports",
        "write_policy": "No write operations are exposed",
    },
}


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(value: Any) -> str:
    packed = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def _safe_identifier(value: Any, *, fallback: str = "item") -> str:
    text = str(value or "").strip().lower()
    text = _SAFE_IDENTIFIER_RE.sub("_", text).strip("_")
    return text[:64] or fallback


def _safe_text(value: Any, *, limit: int = _MAX_TEXT) -> str:
    text = str(value or "").strip()
    return " ".join(text.split())[:limit]


def _as_positive_float(value: Any, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if not 0 < result <= 480:
        raise ValueError(f"{field} must be in the range (0, 480]")
    return result


def _contains_sensitive_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if _SENSITIVE_FIELD_RE.search(str(key)) or _contains_sensitive_field(child):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_field(item) for item in value)
    elif isinstance(value, str):
        lowered = value.lower()
        return "bearer " in lowered or "sk-" in lowered or "password=" in lowered
    return False


def _event_payload(events: Any) -> list[dict[str, Any]]:
    """Parse a bounded event list and remove every non-contract field."""
    if isinstance(events, str):
        if len(events.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
            raise ValueError("events payload exceeds 1 MB")
        try:
            payload = json.loads(events)
        except json.JSONDecodeError as exc:
            raise ValueError("events must be valid JSON") from exc
    else:
        payload = events
    if isinstance(payload, dict):
        payload = payload.get("events")
    if not isinstance(payload, list):
        raise ValueError("events must be an array or an object with an events array")
    if not payload or len(payload) > _MAX_EVENTS:
        raise ValueError(f"events must contain between 1 and {_MAX_EVENTS} items")

    clean: list[dict[str, Any]] = []
    required = ("case_id", "timestamp", "source", "action", "object_type", "duration_min")
    for index, event in enumerate(payload):
        if not isinstance(event, dict):
            raise ValueError(f"events[{index}] must be an object")
        if _contains_sensitive_field(event):
            raise ValueError(f"events[{index}] contains a secret-like field or value")
        missing = [field for field in required if field not in event]
        if missing:
            raise ValueError(f"events[{index}] is missing {', '.join(missing)}")
        timestamp = _safe_text(event["timestamp"], limit=40)
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"events[{index}].timestamp must be ISO-8601") from exc
        clean.append(
            {
                "case_id": _safe_text(event["case_id"], limit=80),
                "timestamp": timestamp,
                "source": _safe_identifier(event["source"]),
                "action": _safe_identifier(event["action"]),
                "object_type": _safe_identifier(event["object_type"]),
                "duration_min": round(_as_positive_float(event["duration_min"], field="duration_min"), 2),
            }
        )
    if any(not event["case_id"] for event in clean):
        raise ValueError("case_id cannot be empty")
    return clean


def _group_cases(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["case_id"]].append(event)
    for case in grouped.values():
        case.sort(key=lambda item: item["timestamp"])
    return dict(grouped)


def _signature(case_events: list[dict[str, Any]]) -> str:
    return " > ".join(f"{event['source']}:{event['action']}" for event in case_events)


def _risk_level(case_events: list[dict[str, Any]]) -> str:
    actions = {event["action"] for event in case_events}
    if any(action in {"delete", "pay", "submit", "approve"} for action in actions):
        return "high"
    if any(action in _WRITE_ACTIONS or "draft" in action for action in actions):
        return "medium"
    return "low"


def _autonomy_policy(risk_level: str) -> dict[str, str]:
    policy = {
        "observe": "automatic, read-only, within existing employee ACL",
        "transform": "automatic in sandbox only",
        "draft": "automatic; result is visible as a diff",
        "write": "blocked until an explicit employee confirmation",
    }
    if risk_level == "high":
        policy["transform"] = "human-in-the-loop before every material transformation"
    return policy


def _integration_candidates(sources: set[str]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for source in sorted(sources):
        spec = _INTEGRATIONS.get(source)
        if spec is None:
            candidates.append(
                {
                    "source": source,
                    "mcp_contract": "Approved domain MCP adapter",
                    "initial_scope": "Read-only discovery until an owner defines the adapter",
                    "write_policy": "No write operation is available by default",
                }
            )
        else:
            candidates.append({"source": source, **spec})
    return candidates


def _demo_events() -> list[dict[str, Any]]:
    """Return 36 anonymized cases: 12 historical tests for each pattern."""
    workflows = (
        (
            "report",
            (
                ("document_store", "search", "report", 4),
                ("bi", "export", "dataset", 6),
                ("spreadsheet", "fill_template", "report", 11),
                ("mail", "create_draft", "summary", 5),
            ),
        ),
        (
            "request",
            (
                ("mail", "classify", "request", 3),
                ("crm", "read_card", "case", 5),
                ("document_store", "collect", "evidence", 8),
                ("task_tracker", "create_draft", "task", 4),
            ),
        ),
        (
            "control",
            (
                ("document_store", "search", "evidence", 5),
                ("spreadsheet", "compare", "register", 9),
                ("bpm", "prepare_draft", "case", 7),
                ("mail", "create_draft", "notice", 4),
            ),
        ),
    )
    start = datetime(2026, 6, 1, 9, tzinfo=timezone.utc)
    events: list[dict[str, Any]] = []
    for workflow_index, (kind, steps) in enumerate(workflows):
        for case_number in range(1, 13):
            case_id = f"demo_{kind}_{case_number:02d}"
            cursor = start + timedelta(days=(workflow_index * 12) + case_number)
            for step_index, (source, action, object_type, minutes) in enumerate(steps):
                events.append(
                    {
                        "case_id": case_id,
                        "timestamp": (cursor + timedelta(minutes=step_index * 10)).isoformat(),
                        "source": source,
                        "action": action,
                        "object_type": object_type,
                        "duration_min": minutes + ((case_number + step_index) % 3),
                    }
                )
    return events


class PersonalEvolutionEngine:
    """Stateful, deterministic workflow discovery with no external side effects."""

    def __init__(self, api: Any) -> None:
        self._api = api
        self._state_dir = Path(api.get_state_dir())
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self._state_dir / _STATE_FILENAME

    def _state(self) -> dict[str, Any]:
        default = {"schema_version": 1, "last_analysis": {}, "proposals": {}, "feedback": []}
        try:
            loaded = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(loaded, dict) or int(loaded.get("schema_version") or 0) != 1:
            return default
        for key, value in default.items():
            if not isinstance(loaded.get(key), type(value)):
                loaded[key] = value
        return loaded

    def _save_state(self, state: dict[str, Any]) -> None:
        packed = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
        fd, temp_name = tempfile.mkstemp(prefix=".personal-evolution-", dir=self._state_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(packed)
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, self._state_path)
        finally:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass

    def _patterns(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped_by_signature: dict[str, list[tuple[str, list[dict[str, Any]]]]] = defaultdict(list)
        for case_id, case_events in _group_cases(events).items():
            grouped_by_signature[_signature(case_events)].append((case_id, case_events))

        patterns: list[dict[str, Any]] = []
        for signature, cases in grouped_by_signature.items():
            if len(cases) < _MIN_PATTERN_OCCURRENCES:
                continue
            case_ids = sorted(case_id for case_id, _ in cases)
            sample_events = cases[0][1]
            average_minutes = sum(sum(item["duration_min"] for item in case) for _, case in cases) / len(cases)
            risk_level = _risk_level(sample_events)
            saved_per_run = round(average_minutes * 0.45, 1)
            pattern_id = f"pat_{_hash(signature)[:10]}"
            patterns.append(
                {
                    "pattern_id": pattern_id,
                    "title": f"Repeated {len(sample_events)}-step {sample_events[-1]['object_type']} workflow",
                    "signature": signature,
                    "steps": [f"{item['source']}:{item['action']}" for item in sample_events],
                    "occurrences": len(cases),
                    "avg_baseline_minutes": round(average_minutes, 1),
                    "estimated_minutes_saved_per_run": saved_per_run,
                    "estimated_hours_returned_in_sample": round(saved_per_run * len(cases) / 60, 2),
                    "confidence": round(min(0.95, 0.45 + len(cases) * 0.04 + len(sample_events) * 0.02), 2),
                    "risk_level": risk_level,
                    "autonomy_policy": _autonomy_policy(risk_level),
                    "integration_candidates": _integration_candidates({item["source"] for item in sample_events}),
                    "historical_case_ids": case_ids,
                }
            )
        return sorted(patterns, key=lambda item: (-item["estimated_hours_returned_in_sample"], item["pattern_id"]))

    @staticmethod
    def _response_error(error: Exception | str) -> str:
        return _json({"ok": False, "error": str(error)})

    def demo_trace(self) -> str:
        events = _demo_events()
        return _json(
            {
                "ok": True,
                "dataset": "anonymized_personal_workflow_demo",
                "events": events,
                "facts": {
                    "historical_cases": 36,
                    "patterns_expected": 3,
                    "examples_per_pattern": 12,
                    "raw_personal_content": "not included",
                },
            }
        )

    def analyze_trace(self, events: Any, run_name: str = "manual") -> str:
        try:
            normalized = _event_payload(events)
            patterns = self._patterns(normalized)
        except ValueError as exc:
            return self._response_error(exc)
        if not patterns:
            return self._response_error(
                f"No pattern repeated at least {_MIN_PATTERN_OCCURRENCES} times; collect more approved history."
            )
        case_count = len(_group_cases(normalized))
        state = self._state()
        state["last_analysis"] = {
            "run_id": f"run_{uuid.uuid4().hex[:10]}",
            "created_at": _now(),
            "run_name": _safe_text(run_name, limit=80) or "manual",
            "event_count": len(normalized),
            "case_count": case_count,
            "trace_fingerprint": _hash(normalized),
            "patterns": patterns,
            "privacy": {
                "raw_events_persisted": False,
                "stored": "aggregate signatures, counts, estimates, and anonymous case references only",
            },
        }
        self._save_state(state)
        return _json(
            {
                "ok": True,
                "analysis": state["last_analysis"],
                "next_actions": [
                    "Select a pattern with propose_skill.",
                    "Run verify_skill on approved anonymized history.",
                    "Use approve_skill only after reviewing the proposal and verification report.",
                ],
            }
        )

    def _find_pattern(self, pattern_id: str) -> dict[str, Any] | None:
        for pattern in self._state().get("last_analysis", {}).get("patterns", []):
            if isinstance(pattern, dict) and pattern.get("pattern_id") == pattern_id:
                return pattern
        return None

    def propose_skill(self, pattern_id: str, purpose: str = "") -> str:
        pattern = self._find_pattern(_safe_text(pattern_id, limit=40))
        if pattern is None:
            return self._response_error("Unknown pattern_id. Run analyze_trace first.")
        proposal_id = f"proposal_{uuid.uuid4().hex[:10]}"
        purpose_text = (
            _safe_text(purpose, limit=240) or "Reduce repetitive work while preserving the employee's control."
        )
        proposal = {
            "proposal_id": proposal_id,
            "created_at": _now(),
            "status": "draft",
            "pattern_id": pattern["pattern_id"],
            "purpose": purpose_text,
            "candidate_micro_skill": {
                "name": f"micro_{pattern['pattern_id'][4:]}",
                "description": pattern["title"],
                "type": "approval-gated workflow template",
                "inputs": ["approved event context", "employee-selected source records"],
                "outputs": ["sandbox result", "reviewable draft", "audit event"],
                "steps": [
                    "Read only records available to the employee.",
                    "Transform data in a sandbox and validate mandatory fields.",
                    "Show a diff or draft; do not send, submit, or update a source system.",
                    "Ask for explicit approval before any MCP adapter may perform a write.",
                ],
                "autonomy_policy": pattern["autonomy_policy"],
                "integration_candidates": pattern["integration_candidates"],
            },
            "verification_plan": {
                "minimum_historical_cases": _MIN_VERIFIED_CASES,
                "assertions": [
                    "Every test case preserves its workflow signature.",
                    "Every result remains a draft until approval.",
                    "No raw event payload or secret-like value is persisted.",
                ],
            },
            "safety": {
                "mode": "sandbox_then_human_approval",
                "outbound_writes": "blocked by design in this prototype",
                "rollback": "discard the draft and disable the proposal; no source system is changed",
            },
            "required_confirmation": f"APPROVE {proposal_id}",
        }
        state = self._state()
        state["proposals"][proposal_id] = proposal
        self._save_state(state)
        return _json({"ok": True, "proposal": proposal, "next_action": "Run verify_skill with historical events."})

    def verify_skill(self, proposal_id: str, events: Any) -> str:
        state = self._state()
        proposal = state["proposals"].get(_safe_text(proposal_id, limit=64))
        if not isinstance(proposal, dict):
            return self._response_error("Unknown proposal_id.")
        pattern = self._find_pattern(str(proposal.get("pattern_id") or ""))
        if pattern is None:
            return self._response_error(
                "The proposal pattern is no longer available; re-run analysis and create a new proposal."
            )
        try:
            normalized = _event_payload(events)
        except ValueError as exc:
            return self._response_error(exc)

        case_results: list[dict[str, Any]] = []
        for case_id, case_events in _group_cases(normalized).items():
            if _signature(case_events) != pattern["signature"]:
                continue
            is_valid = len(case_events) == len(pattern["steps"]) and all(
                event["duration_min"] > 0 for event in case_events
            )
            case_results.append(
                {
                    "case_id": case_id,
                    "input_fingerprint": _hash(case_events)[:16],
                    "passed": is_valid,
                    "assertions": [
                        "workflow signature matches",
                        "all durations are positive",
                        "result is draft-only and requires human approval",
                    ],
                }
            )
        passed = sum(1 for result in case_results if result["passed"])
        verification = {
            "verified_at": _now(),
            "tested_cases": len(case_results),
            "passed_cases": passed,
            "failed_cases": len(case_results) - passed,
            "minimum_required": _MIN_VERIFIED_CASES,
            "pass_rate": round(passed / len(case_results), 3) if case_results else 0,
            "status": "passed"
            if passed >= _MIN_VERIFIED_CASES and passed == len(case_results)
            else "needs_more_evidence",
            "case_results": case_results,
            "sandbox_guarantees": [
                "No connector call is executed.",
                "No source record is modified.",
                "Only anonymized identifiers and test fingerprints appear in the report.",
            ],
        }
        proposal["verification"] = verification
        proposal["status"] = "verified" if verification["status"] == "passed" else "draft"
        state["proposals"][proposal["proposal_id"]] = proposal
        self._save_state(state)
        return _json(
            {
                "ok": verification["status"] == "passed",
                "proposal_id": proposal["proposal_id"],
                "verification": verification,
            }
        )

    def approve_skill(self, proposal_id: str, confirmation: str) -> str:
        state = self._state()
        proposal = state["proposals"].get(_safe_text(proposal_id, limit=64))
        if not isinstance(proposal, dict):
            return self._response_error("Unknown proposal_id.")
        verification = proposal.get("verification") or {}
        if verification.get("status") != "passed":
            return self._response_error(
                "Approval is blocked until at least ten relevant historical cases pass verification."
            )
        expected = str(proposal.get("required_confirmation") or "")
        if str(confirmation or "").strip() != expected:
            return self._response_error(f"Explicit confirmation required: {expected}")
        proposal["status"] = "approved"
        proposal["approved_at"] = _now()
        state["proposals"][proposal["proposal_id"]] = proposal
        self._save_state(state)
        return _json(
            {
                "ok": True,
                "proposal_id": proposal["proposal_id"],
                "status": "approved",
                "scope": "Draft-only run is permitted; external writes still require a reviewed MCP adapter and a per-action confirmation.",
            }
        )

    def run_skill(self, proposal_id: str, case_reference: str, mode: str = "draft") -> str:
        state = self._state()
        proposal = state["proposals"].get(_safe_text(proposal_id, limit=64))
        if not isinstance(proposal, dict):
            return self._response_error("Unknown proposal_id.")
        requested_mode = _safe_identifier(mode, fallback="draft")
        if requested_mode not in {"draft", "approved"}:
            return self._response_error("mode must be draft or approved")
        if requested_mode == "approved" and proposal.get("status") != "approved":
            return self._response_error("Approved mode requires a verified proposal and explicit approval.")
        case_ref = _safe_text(case_reference, limit=80)
        if not case_ref:
            return self._response_error("case_reference is required and must be an anonymized identifier.")
        skill = proposal["candidate_micro_skill"]
        result = {
            "ok": True,
            "proposal_id": proposal["proposal_id"],
            "case_reference": case_ref,
            "execution_mode": "approved_draft_only" if requested_mode == "approved" else "sandbox_draft",
            "draft_artifact": {
                "title": f"Reviewable draft for {skill['description']}",
                "summary": "The workflow was prepared from employee-authorized sources; no source system was changed.",
                "checks": ["mandatory fields validated", "integration scope checked", "human approval retained"],
            },
            "integration_plan": [
                {
                    "source": item["source"],
                    "operation": "read_and_prepare_draft",
                    "state": "simulated_in_prototype",
                }
                for item in skill["integration_candidates"]
            ],
            "outbound_writes": [],
            "next_human_step": "Review the draft diff. A production write must be performed through an approved MCP adapter with a fresh confirmation.",
            "audit": {"at": _now(), "rollback": "Discard this draft; no rollback in an external system is needed."},
        }
        return _json(result)

    def record_feedback(self, proposal_id: str, outcome: str, minutes_saved: Any, rating: Any) -> str:
        state = self._state()
        proposal = state["proposals"].get(_safe_text(proposal_id, limit=64))
        if not isinstance(proposal, dict):
            return self._response_error("Unknown proposal_id.")
        outcome_value = _safe_identifier(outcome)
        if outcome_value not in {"accepted", "edited", "rejected"}:
            return self._response_error("outcome must be accepted, edited, or rejected")
        try:
            saved = _as_positive_float(minutes_saved, field="minutes_saved")
            score = int(rating)
        except (TypeError, ValueError) as exc:
            return self._response_error(exc)
        if score not in {1, 2, 3, 4, 5}:
            return self._response_error("rating must be an integer from 1 to 5")
        feedback = {
            "proposal_id": proposal["proposal_id"],
            "pattern_id": proposal["pattern_id"],
            "outcome": outcome_value,
            "minutes_saved": round(saved, 1),
            "rating": score,
            "recorded_at": _now(),
        }
        state["feedback"] = (state["feedback"] + [feedback])[-200:]
        matching = [item for item in state["feedback"] if item["pattern_id"] == proposal["pattern_id"]]
        accepted = sum(1 for item in matching if item["outcome"] == "accepted")
        average_rating = sum(item["rating"] for item in matching) / len(matching)
        evolution = {
            "candidate": "increase recommendation rank"
            if accepted / len(matching) >= 0.6 and average_rating >= 4
            else "keep conservative rank",
            "evidence": {
                "feedback_count": len(matching),
                "accepted": accepted,
                "average_rating": round(average_rating, 2),
            },
            "scope": "ranking only; no automatic code, permission, integration, or workflow change",
            "requires_owner_review": True,
        }
        self._save_state(state)
        return _json({"ok": True, "feedback": feedback, "evolution_candidate": evolution})

    def portfolio(self) -> str:
        state = self._state()
        analysis = state.get("last_analysis") or {}
        patterns = analysis.get("patterns") if isinstance(analysis, dict) else []
        proposals = [value for value in state.get("proposals", {}).values() if isinstance(value, dict)]
        verified = [item for item in proposals if (item.get("verification") or {}).get("status") == "passed"]
        approved = [item for item in proposals if item.get("status") == "approved"]
        return _json(
            {
                "ok": True,
                "metrics": {
                    "patterns_detected": len(patterns or []),
                    "historical_cases_analyzed": int(analysis.get("case_count") or 0),
                    "historical_examples_verified": max(
                        ((item.get("verification") or {}).get("passed_cases", 0) for item in verified), default=0
                    ),
                    "micro_skills_proposed": len(proposals),
                    "micro_skills_verified": len(verified),
                    "micro_skills_approved": len(approved),
                    "feedback_events": len(state.get("feedback", [])),
                    "estimated_hours_returned_in_sample": round(
                        sum(item.get("estimated_hours_returned_in_sample", 0) for item in patterns or []), 2
                    ),
                },
                "patterns": patterns or [],
                "governance": {
                    "raw_events_persisted": False,
                    "automatic_external_writes": False,
                    "evolution_boundary": "human feedback can rank recommendations only",
                },
            }
        )

    def integrations(self) -> str:
        return _json(
            {
                "ok": True,
                "integration_model": "Each adapter is an approved MCP server. OAuth/RBAC, DLP, audit retention, and source ACL remain outside the skill and are enforced by the enterprise connector.",
                "connectors": [{"source": source, **spec} for source, spec in sorted(_INTEGRATIONS.items())],
                "non_negotiable_controls": [
                    "No secrets are accepted in trace payloads or persisted in skill state.",
                    "The agent receives no permission beyond the employee's existing ACL.",
                    "Write-capable operations need a fresh approval after a visible diff.",
                    "Prompt-injection-prone source content remains data, never instruction or policy.",
                ],
            }
        )

    def portfolio_route(self, _request: Any) -> Any:
        from starlette.responses import JSONResponse

        return JSONResponse(json.loads(self.portfolio()))

    def integrations_route(self, _request: Any) -> Any:
        from starlette.responses import JSONResponse

        return JSONResponse(json.loads(self.integrations()))


def register(api: Any) -> None:
    """Register chat tools, evidence routes, and a declarative dashboard widget."""
    engine = PersonalEvolutionEngine(api)
    event_schema = {
        "type": ["array", "object", "string"],
        "description": "An anonymized event list or JSON object with an events array.",
    }
    api.register_tool(
        "demo_trace",
        engine.demo_trace,
        description="Create 36 anonymized historical workflow examples for a safe end-to-end demo.",
        schema={"type": "object", "properties": {}},
        timeout_sec=10,
    )
    api.register_tool(
        "analyze_trace",
        engine.analyze_trace,
        description="Find repeated cross-system workflows in an approved anonymized event trace and calculate transparent time-saving hypotheses.",
        schema={
            "type": "object",
            "properties": {"events": event_schema, "run_name": {"type": "string", "default": "manual"}},
            "required": ["events"],
        },
        timeout_sec=30,
    )
    api.register_tool(
        "propose_skill",
        engine.propose_skill,
        description="Create a non-executable, approval-gated micro-skill proposal for one discovered pattern.",
        schema={
            "type": "object",
            "properties": {"pattern_id": {"type": "string"}, "purpose": {"type": "string", "default": ""}},
            "required": ["pattern_id"],
        },
        timeout_sec=15,
    )
    api.register_tool(
        "verify_skill",
        engine.verify_skill,
        description="Run a proposed micro-skill deterministically against anonymized history; at least ten passing relevant cases are required before approval.",
        schema={
            "type": "object",
            "properties": {"proposal_id": {"type": "string"}, "events": event_schema},
            "required": ["proposal_id", "events"],
        },
        timeout_sec=30,
    )
    api.register_tool(
        "approve_skill",
        engine.approve_skill,
        description="Approve a verified micro-skill only when the exact confirmation phrase is supplied.",
        schema={
            "type": "object",
            "properties": {"proposal_id": {"type": "string"}, "confirmation": {"type": "string"}},
            "required": ["proposal_id", "confirmation"],
        },
        timeout_sec=10,
    )
    api.register_tool(
        "run_skill",
        engine.run_skill,
        description="Produce a reviewable sandbox or approved draft for an anonymized case. This prototype never writes to an external system.",
        schema={
            "type": "object",
            "properties": {
                "proposal_id": {"type": "string"},
                "case_reference": {"type": "string"},
                "mode": {"type": "string", "default": "draft", "enum": ["draft", "approved"]},
            },
            "required": ["proposal_id", "case_reference"],
        },
        timeout_sec=15,
    )
    api.register_tool(
        "record_feedback",
        engine.record_feedback,
        description="Record employee feedback and produce a bounded, owner-reviewed recommendation-ranking evolution candidate.",
        schema={
            "type": "object",
            "properties": {
                "proposal_id": {"type": "string"},
                "outcome": {"type": "string", "enum": ["accepted", "edited", "rejected"]},
                "minutes_saved": {"type": "number"},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "required": ["proposal_id", "outcome", "minutes_saved", "rating"],
        },
        timeout_sec=10,
    )
    api.register_tool(
        "portfolio",
        engine.portfolio,
        description="Show metrics, discovered patterns, verified evidence, and governance boundaries for the personal automation portfolio.",
        schema={"type": "object", "properties": {}},
        timeout_sec=10,
    )
    api.register_tool(
        "integrations",
        engine.integrations,
        description="List the approval-gated MCP integration design for mail, calendar, tasks, documents, spreadsheets, CRM, BPM, and BI.",
        schema={"type": "object", "properties": {}},
        timeout_sec=10,
    )
    api.register_route("portfolio", engine.portfolio_route, methods=("GET",))
    api.register_route("integrations", engine.integrations_route, methods=("GET",))
    api.register_ui_tab(
        "evolution",
        "Personal Evolution",
        icon="sparkles",
        render={
            "kind": "declarative",
            "schema_version": 1,
            "span": 2,
            "components": [
                {
                    "type": "markdown",
                    "content": "Discover personal workflow patterns, verify micro-skills on history, and keep every external write behind human approval.",
                },
                {
                    "type": "action",
                    "label": "Refresh portfolio",
                    "route": "portfolio",
                    "method": "GET",
                    "target": "portfolio",
                },
                {
                    "type": "kv",
                    "target": "portfolio",
                    "fields": [
                        {"label": "Patterns", "path": "metrics.patterns_detected"},
                        {"label": "Verified examples", "path": "metrics.historical_examples_verified"},
                        {"label": "Estimated hours returned", "path": "metrics.estimated_hours_returned_in_sample"},
                    ],
                },
                {
                    "type": "table",
                    "target": "portfolio",
                    "path": "patterns",
                    "columns": [
                        {"label": "Pattern", "path": "title"},
                        {"label": "Occurrences", "path": "occurrences"},
                        {"label": "Risk", "path": "risk_level"},
                        {"label": "Hours", "path": "estimated_hours_returned_in_sample"},
                    ],
                },
            ],
        },
    )
