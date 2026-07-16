"""Typed deterministic domain contracts for the hackathon MVP."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

EVENT_FIELDS = (
    "event_id",
    "employee_id",
    "timestamp",
    "application",
    "action_type",
    "object_type",
    "object_id",
    "source",
    "destination",
    "duration_seconds",
    "metadata",
    "sensitivity_level",
    "result_status",
    "correlation_id",
)


def stable_id(prefix: str, value: Any, length: int = 12) -> str:
    """Return a reproducible identifier for JSON-serializable domain evidence."""
    packed = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(packed.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


@dataclass(frozen=True)
class TraceEvent:
    event_id: str
    employee_id: str
    timestamp: str
    application: str
    action_type: str
    object_type: str
    object_id: str
    source: str
    destination: str
    duration_seconds: int
    metadata: Dict[str, Any]
    sensitivity_level: str
    result_status: str
    correlation_id: str

    @classmethod
    def from_mapping(cls, value: Dict[str, Any]) -> "TraceEvent":
        missing = [name for name in EVENT_FIELDS if name not in value]
        if missing:
            raise ValueError(f"event is missing required fields: {', '.join(missing)}")
        metadata = value.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("event.metadata must be an object")
        try:
            datetime.fromisoformat(str(value["timestamp"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("event.timestamp must be ISO-8601") from exc
        try:
            duration = int(value["duration_seconds"])
        except (TypeError, ValueError) as exc:
            raise ValueError("event.duration_seconds must be an integer") from exc
        if duration < 0 or duration > 86_400:
            raise ValueError("event.duration_seconds must be between 0 and 86400")
        text_values = {
            name: str(value[name]).strip() for name in EVENT_FIELDS if name not in {"metadata", "duration_seconds"}
        }
        if any(not item for item in text_values.values()):
            raise ValueError("event string fields cannot be empty")
        if text_values["sensitivity_level"] not in {"public", "internal", "confidential", "restricted"}:
            raise ValueError("unsupported sensitivity_level")
        if text_values["result_status"] not in {"success", "failed", "blocked", "cancelled"}:
            raise ValueError("unsupported result_status")
        return cls(duration_seconds=duration, metadata=dict(metadata), **text_values)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class Pattern:
    pattern_id: str
    name: str
    representative_sequence: List[str]
    stable_actions: List[str]
    variable_actions: List[str]
    correlation_ids: List[str]
    frequency: int
    periodicity_days: float
    average_duration_seconds: float
    manual_steps: int
    potential_time_saving_seconds: float
    confidence: float
    variability: float
    risk_level: str
    automation_suitability: float

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class ApprovalReceipt:
    receipt_id: str
    proposal_id: str
    skill_id: str
    version: str
    employee_id: str
    approved_at: str
    scope: List[str]
    content_hash: str
    input_hash: str
    action_plan_hash: str
    expires_at: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class AuditEntry:
    sequence: int
    timestamp: str
    actor: str
    action: str
    status: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class SandboxResult:
    version: str
    case_id: str
    passed: bool
    expected: Dict[str, Any]
    actual: Dict[str, Any]
    differences: List[str]
    checks: List[Dict[str, Any]]
    errors: List[str]
    execution_seconds: float
    cost_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class SkillVersion:
    skill_id: str
    version: str
    status: str
    content_hash: str
    root_path: str
    source_pattern_id: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)
