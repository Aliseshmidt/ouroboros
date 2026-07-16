"""Deterministic synthetic Credit Analyst mini-dossier executor."""

from __future__ import annotations

from typing import Any, Dict, List

from ouroboros.hackathon.models import ApprovalReceipt, SandboxResult, stable_id
from ouroboros.hackathon.safety import action_policy, scan_payload

REQUIRED_DOCUMENTS = {"financial_report", "account_statement", "limit_report", "covenant_register"}
APPROVED_ACTION_PLAN = ["create_task", "create_email_draft"]


def demo_dossier_case() -> Dict[str, Any]:
    return {
        "case_id": "credit_demo_001",
        "employee_id": "employee_credit_001",
        "client_id": "synthetic_client_001",
        "documents": {
            "financial_report": {"revenue": 100.0, "debt": 68.0, "currency": "RUB_mln"},
            "account_statement": {"reported_revenue": 92.0, "overdue_days": 0},
            "limit_report": {"approved_limit": 80.0, "used_limit": 72.0},
            "covenant_register": {"max_debt_to_revenue": 0.65},
        },
        "stop_factors": [],
        "source_notice": "Synthetic fixture; no real client data.",
    }


def validate_dossier_input(case: Dict[str, Any]) -> List[str]:
    if not isinstance(case, dict):
        return ["input must be an object"]
    documents = case.get("documents")
    if not isinstance(documents, dict):
        return ["documents must be an object"]
    missing = sorted(REQUIRED_DOCUMENTS - set(documents))
    errors = [f"missing mandatory document: {name}" for name in missing]
    if scan_payload(case):
        errors.append("input failed DLP/prompt-injection safety checks")
    return errors


def _calculate(case: Dict[str, Any], version: str) -> Dict[str, Any]:
    documents = case["documents"]
    report = documents["financial_report"]
    statement = documents["account_statement"]
    limits = documents["limit_report"]
    covenant = documents["covenant_register"]
    revenue = float(report["revenue"])
    debt = float(report["debt"])
    ratio = round(debt / revenue, 4) if revenue else None
    contradictions: List[str] = []
    if version != "1.0.0" and abs(revenue - float(statement["reported_revenue"])) > 5:
        contradictions.append("revenue differs between financial report and account statement")
    covenant_violations = []
    if ratio is None or ratio > float(covenant["max_debt_to_revenue"]):
        covenant_violations.append("debt_to_revenue exceeds covenant")
    stop_factors = list(case.get("stop_factors") or [])
    if int(statement.get("overdue_days") or 0) > 30:
        stop_factors.append("overdue_more_than_30_days")
    return {
        "case_id": case["case_id"],
        "debt_to_revenue": ratio,
        "limit_available": round(float(limits["approved_limit"]) - float(limits["used_limit"]), 2),
        "contradictions": sorted(set(contradictions)),
        "covenant_violations": sorted(set(covenant_violations)),
        "stop_factors": sorted(set(stop_factors)),
    }


def expected_dossier(case: Dict[str, Any]) -> Dict[str, Any]:
    return _calculate(case, "2.0.0")


def execute_dossier(
    case: Dict[str, Any],
    *,
    version: str,
    approval: ApprovalReceipt | None,
    proposal_id: str,
    execution_mode: str = "sandbox",
) -> Dict[str, Any]:
    errors = validate_dossier_input(case)
    if errors:
        return {"ok": False, "errors": errors, "actions": []}
    if execution_mode == "approved":
        valid_approval = approval is not None and all(
            (
                approval.proposal_id == proposal_id,
                approval.version == version,
                approval.input_hash == stable_id("input", case, 24),
                approval.action_plan_hash == stable_id("plan", APPROVED_ACTION_PLAN, 24),
            )
        )
        if not valid_approval:
            return {"ok": False, "errors": ["valid explicit approval receipt required"], "actions": []}
    calculations = _calculate(case, version)
    risk_items = calculations["contradictions"] + calculations["covenant_violations"] + calculations["stop_factors"]
    comment = "Проверка завершена. " + (
        "Требуется внимание: " + "; ".join(risk_items) if risk_items else "Существенные риски не выявлены."
    )
    actions = [
        {
            "action": "create_task",
            "mode": "mock",
            **action_policy("create_task", approved=approval is not None, autonomy_level="A3"),
        },
        {
            "action": "create_email_draft",
            "mode": "mock",
            **action_policy("create_email_draft", approved=approval is not None, autonomy_level="A3"),
        },
    ]
    return {
        "ok": True,
        "version": version,
        "mode": execution_mode,
        "calculations": calculations,
        "analytical_comment": comment,
        "supporting_evidence": sorted(case["documents"]),
        "actions": actions,
        "external_writes": [],
        "final_credit_decision": "remains with authorized employee",
    }


def sandbox_test(case: Dict[str, Any], version: str) -> SandboxResult:
    expected = expected_dossier(case)
    response = execute_dossier(case, version=version, approval=None, proposal_id="sandbox", execution_mode="sandbox")
    actual = response.get("calculations") if response.get("ok") else {}
    differences = []
    for key in sorted(set(expected) | set(actual)):
        if expected.get(key) != actual.get(key):
            differences.append(f"{key}: expected={expected.get(key)!r}, actual={actual.get(key)!r}")
    checks = [
        {"name": "input_schema", "passed": not validate_dossier_input(case)},
        {"name": "expected_actual_match", "passed": not differences},
        {"name": "no_external_writes", "passed": response.get("external_writes") == []},
        {
            "name": "human_final_decision",
            "passed": response.get("final_credit_decision") == "remains with authorized employee",
        },
    ]
    return SandboxResult(
        version=version,
        case_id=str(case.get("case_id") or "invalid"),
        passed=bool(response.get("ok")) and all(check["passed"] for check in checks),
        expected=expected,
        actual=actual,
        differences=differences,
        checks=checks,
        errors=list(response.get("errors") or []),
        execution_seconds=0.08,
        cost_usd=0.0,
    )
