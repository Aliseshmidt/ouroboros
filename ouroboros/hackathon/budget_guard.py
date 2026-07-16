"""Strict, immutable USD 5 hackathon budget guard and evidence ledger."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from ouroboros.hackathon.models import stable_id

HARD_BUDGET_USD = 5.00
OPERATIONAL_CAP_USD = 4.50
EMERGENCY_RESERVE_USD = 0.50


class BudgetBlocked(RuntimeError):
    pass


@dataclass
class BudgetEntry:
    request_id: str
    timestamp: str
    development_stage: str
    purpose: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    actual_cost_usd: Optional[float]
    cumulative_spending_usd: float
    remaining_budget_usd: float
    justification: str
    status: str
    final_verification: bool


class BudgetGuard:
    """Conservative reservation guard; limits cannot be changed through this API."""

    def __init__(self, ledger_json: Path | None = None, ledger_markdown: Path | None = None) -> None:
        self._entries: List[BudgetEntry] = []
        self._spent = 0.0
        self._reserved = 0.0
        self._emergency_used = False
        self._ledger_json = ledger_json
        self._ledger_markdown = ledger_markdown

    @property
    def spent_usd(self) -> float:
        return round(self._spent, 6)

    @property
    def remaining_usd(self) -> float:
        return round(HARD_BUDGET_USD - self._spent - self._reserved, 6)

    def authorize(
        self,
        *,
        development_stage: str,
        purpose: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float | None,
        justification: str,
        pricing_known: bool,
        final_verification: bool = False,
    ) -> str:
        if not pricing_known or estimated_cost_usd is None:
            raise BudgetBlocked("unknown pricing is not admissible under the hackathon budget")
        estimate = round(float(estimated_cost_usd), 6)
        if estimate < 0:
            raise BudgetBlocked("estimated cost cannot be negative")
        projected = self._spent + self._reserved + estimate
        if projected > HARD_BUDGET_USD + 1e-9:
            raise BudgetBlocked("request may exceed the USD 5 hard budget")
        if projected > OPERATIONAL_CAP_USD + 1e-9:
            if not final_verification:
                raise BudgetBlocked("operational cap reached; reserve is final-verification-only")
            if self._emergency_used:
                raise BudgetBlocked("the emergency reserve has already been used")
            self._emergency_used = True
        request_id = stable_id("budget", [len(self._entries), development_stage, purpose, model], 12)
        self._reserved += estimate
        self._entries.append(
            BudgetEntry(
                request_id=request_id,
                timestamp=self._timestamp(len(self._entries)),
                development_stage=str(development_stage),
                purpose=str(purpose),
                model=str(model),
                input_tokens=max(0, int(input_tokens)),
                output_tokens=max(0, int(output_tokens)),
                estimated_cost_usd=estimate,
                actual_cost_usd=None,
                cumulative_spending_usd=round(self._spent, 6),
                remaining_budget_usd=round(HARD_BUDGET_USD - self._spent - self._reserved, 6),
                justification=str(justification),
                status="reserved",
                final_verification=bool(final_verification),
            )
        )
        self._persist()
        return request_id

    def settle(self, request_id: str, actual_cost_usd: float) -> BudgetEntry:
        entry = next((item for item in self._entries if item.request_id == request_id), None)
        if entry is None or entry.status != "reserved":
            raise BudgetBlocked("unknown or already-settled budget reservation")
        actual = round(float(actual_cost_usd), 6)
        if actual < 0 or actual > entry.estimated_cost_usd + 1e-9:
            raise BudgetBlocked("actual cost exceeds the conservative reservation")
        self._reserved -= entry.estimated_cost_usd
        self._spent += actual
        if self._spent > HARD_BUDGET_USD + 1e-9:
            raise BudgetBlocked("settlement exceeds the USD 5 hard budget")
        entry.actual_cost_usd = actual
        entry.status = "settled"
        entry.cumulative_spending_usd = round(self._spent, 6)
        entry.remaining_budget_usd = round(HARD_BUDGET_USD - self._spent - self._reserved, 6)
        self._persist()
        return entry

    def record_local_call(self, *, stage: str, purpose: str, model: str = "local/deterministic") -> BudgetEntry:
        request_id = self.authorize(
            development_stage=stage,
            purpose=purpose,
            model=model,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_usd=0.0,
            justification="Deterministic local operation; no paid API.",
            pricing_known=True,
        )
        return self.settle(request_id, 0.0)

    def snapshot(self) -> dict:
        return {
            "hard_budget_usd": HARD_BUDGET_USD,
            "operational_cap_usd": OPERATIONAL_CAP_USD,
            "emergency_reserve_usd": EMERGENCY_RESERVE_USD,
            "spent_usd": self.spent_usd,
            "reserved_usd": round(self._reserved, 6),
            "remaining_usd": self.remaining_usd,
            "entries": [asdict(entry) for entry in self._entries],
        }

    @staticmethod
    def _timestamp(index: int) -> str:
        base = datetime(2026, 6, 1, tzinfo=timezone.utc)
        return (base + timedelta(seconds=index)).isoformat()

    def _persist(self) -> None:
        if self._ledger_json:
            self._atomic_write(self._ledger_json, json.dumps(self.snapshot(), ensure_ascii=False, indent=2) + "\n")
        if self._ledger_markdown:
            lines = [
                "# Budget Ledger",
                "",
                f"Spent: ${self.spent_usd:.4f}",
                f"Remaining: ${self.remaining_usd:.4f}",
                "",
                "| Request | Stage | Purpose | Model | Estimate | Actual | Status |",
                "|---|---|---|---|---:|---:|---|",
            ]
            for entry in self._entries:
                actual = "—" if entry.actual_cost_usd is None else f"${entry.actual_cost_usd:.4f}"
                lines.append(
                    f"| {entry.request_id} | {entry.development_stage} | {entry.purpose} | {entry.model} | "
                    f"${entry.estimated_cost_usd:.4f} | {actual} | {entry.status} |"
                )
            self._atomic_write(self._ledger_markdown, "\n".join(lines) + "\n")

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
