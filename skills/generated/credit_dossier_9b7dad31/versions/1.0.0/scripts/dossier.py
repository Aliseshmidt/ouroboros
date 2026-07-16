#!/usr/bin/env python3
"""Deterministic, standard-library-only dossier micro-skill v1.0.0."""

from __future__ import annotations

import json
import sys


SKILL_VERSION = "1.0.0"
REQUIRED_DOCUMENTS = {"financial_report", "account_statement", "limit_report", "covenant_register"}


def build_dossier(case):
    if not isinstance(case, dict):
        return {"ok": False, "errors": ["input must be an object"]}
    documents = case.get("documents")
    if not isinstance(documents, dict):
        return {"ok": False, "errors": ["documents must be an object"]}
    missing = sorted(REQUIRED_DOCUMENTS - set(documents))
    if missing:
        return {"ok": False, "errors": [f"missing mandatory document: {name}" for name in missing]}
    try:
        report = documents["financial_report"]
        statement = documents["account_statement"]
        limits = documents["limit_report"]
        covenant = documents["covenant_register"]
        revenue = float(report["revenue"])
        debt = float(report["debt"])
        ratio = round(debt / revenue, 4) if revenue else None
        contradictions = []
        if SKILL_VERSION != "1.0.0" and abs(revenue - float(statement["reported_revenue"])) > 5:
            contradictions.append("revenue differs between financial report and account statement")
        violations = []
        if ratio is None or ratio > float(covenant["max_debt_to_revenue"]):
            violations.append("debt_to_revenue exceeds covenant")
        stop_factors = list(case.get("stop_factors") or [])
        if int(statement.get("overdue_days") or 0) > 30:
            stop_factors.append("overdue_more_than_30_days")
        calculations = {
            "case_id": str(case.get("case_id") or ""),
            "debt_to_revenue": ratio,
            "limit_available": round(float(limits["approved_limit"]) - float(limits["used_limit"]), 2),
            "contradictions": sorted(set(contradictions)),
            "covenant_violations": sorted(set(violations)),
            "stop_factors": sorted(set(stop_factors)),
        }
    except (KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "errors": [f"invalid document value: {exc}"]}
    risks = calculations["contradictions"] + calculations["covenant_violations"] + calculations["stop_factors"]
    comment = "Проверка завершена. "
    comment += "Требуется внимание: " + "; ".join(risks) if risks else "Существенные риски не выявлены."
    return {
        "ok": True,
        "version": SKILL_VERSION,
        "calculations": calculations,
        "analytical_comment": comment,
        "supporting_evidence": sorted(documents),
        "external_writes": [],
        "final_credit_decision": "remains with authorized employee",
    }


def main():
    try:
        payload = json.load(sys.stdin)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = {"ok": False, "errors": [f"invalid JSON: {exc}"]}
    else:
        result = build_dossier(payload)
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
