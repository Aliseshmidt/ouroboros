"""Deterministic domain safety, DLP, RBAC, and approval policies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

_SECRET_KEY = re.compile(r"(?:api[_-]?key|authorization|credential|password|secret|token)", re.IGNORECASE)
_SECRET_VALUE = re.compile(r"(?:bearer\s+[a-z0-9._-]+|sk-[a-z0-9_-]{12,}|password\s*=)", re.IGNORECASE)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\d)(?:\+7|8)[\s()-]*\d{3}[\s()-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)")
_PROMPT_INJECTION = re.compile(
    r"(?:ignore\s+(?:all\s+)?previous|system\s+prompt|developer\s+message|выполни\s+скрытую\s+инструкцию)",
    re.IGNORECASE,
)
_IRREVERSIBLE = {"delete", "pay", "make_credit_decision", "approve_credit", "publish"}
_APPROVAL_REQUIRED = {"send_email", "create_task", "update_record", "submit", "route_case"}


@dataclass(frozen=True)
class SafetyFinding:
    kind: str
    path: str
    severity: str
    message: str


def scan_payload(value: Any, path: str = "$") -> List[SafetyFinding]:
    findings: List[SafetyFinding] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _SECRET_KEY.search(str(key)):
                findings.append(SafetyFinding("secret", child_path, "critical", "secret-like field is prohibited"))
            findings.extend(scan_payload(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan_payload(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        if _SECRET_VALUE.search(value):
            findings.append(SafetyFinding("secret", path, "critical", "secret-like value is prohibited"))
        if _PROMPT_INJECTION.search(value):
            findings.append(SafetyFinding("prompt_injection", path, "high", "source instruction is untrusted data"))
        if _EMAIL.search(value) or _PHONE.search(value):
            findings.append(SafetyFinding("pii", path, "high", "personal identifier requires redaction"))
    return findings


def redact_text(text: str) -> str:
    redacted = _EMAIL.sub("[REDACTED_EMAIL]", str(text))
    redacted = _PHONE.sub("[REDACTED_PHONE]", redacted)
    redacted = _SECRET_VALUE.sub("[REDACTED_SECRET]", redacted)
    return redacted


def authorize_resources(requested: Iterable[str], allowed: Iterable[str]) -> Dict[str, Any]:
    requested_set = {str(item) for item in requested}
    allowed_set = {str(item) for item in allowed}
    denied = sorted(requested_set - allowed_set)
    return {"allowed": not denied, "requested": sorted(requested_set), "denied": denied}


def action_policy(action: str, *, approved: bool, autonomy_level: str = "A2") -> Dict[str, str | bool]:
    normalized = str(action or "").strip().lower()
    if normalized in _IRREVERSIBLE:
        return {"allowed": False, "decision": "blocked", "reason": "irreversible or human-authority action"}
    if normalized in _APPROVAL_REQUIRED and not approved:
        return {"allowed": False, "decision": "approval_required", "reason": "explicit employee approval is required"}
    if normalized in _APPROVAL_REQUIRED and autonomy_level not in {"A3", "A4"}:
        return {"allowed": False, "decision": "blocked", "reason": "autonomy level does not permit execution"}
    return {"allowed": True, "decision": "allowed", "reason": "within allow-list and employee authority"}


def validate_trace_safety(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    findings: List[SafetyFinding] = []
    blocked_events = 0
    for index, event in enumerate(events):
        findings.extend(scan_payload(event, f"$.events[{index}]"))
        if bool((event.get("metadata") or {}).get("prohibited")) or event.get("action_type") in _IRREVERSIBLE:
            blocked_events += 1
    critical = [item for item in findings if item.severity == "critical"]
    return {
        "safe": not critical,
        "findings": [item.__dict__ for item in findings],
        "blocked_prohibited_events": blocked_events,
        "pii_leakage_rate": 0.0 if not findings else None,
    }
