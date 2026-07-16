"""Digital-trace import and reproducible synthetic trace generation."""

from __future__ import annotations

import csv
import io
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Tuple

from ouroboros.hackathon.models import EVENT_FIELDS, TraceEvent, stable_id

_BASE_TIME = datetime(2026, 6, 1, 8, 30, tzinfo=timezone.utc)


def parse_json_events(payload: str | bytes | List[Dict[str, Any]] | Dict[str, Any]) -> List[TraceEvent]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid trace JSON: {exc}") from exc
    if isinstance(payload, dict):
        payload = payload.get("events")
    if not isinstance(payload, list):
        raise ValueError("trace JSON must be an event array or an object with events")
    events = [TraceEvent.from_mapping(item) for item in payload if isinstance(item, dict)]
    if len(events) != len(payload):
        raise ValueError("every trace event must be an object")
    return _validate_event_batch(events)


def parse_csv_events(payload: str | bytes) -> List[TraceEvent]:
    text = payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or set(EVENT_FIELDS) - set(reader.fieldnames):
        missing = sorted(set(EVENT_FIELDS) - set(reader.fieldnames or []))
        raise ValueError(f"trace CSV is missing columns: {', '.join(missing)}")
    events: List[TraceEvent] = []
    for row_number, row in enumerate(reader, start=2):
        try:
            row["metadata"] = json.loads(row.get("metadata") or "{}")
            events.append(TraceEvent.from_mapping(row))
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid trace CSV row {row_number}: {exc}") from exc
    return _validate_event_batch(events)


def events_to_csv(events: Iterable[TraceEvent]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(EVENT_FIELDS), lineterminator="\n")
    writer.writeheader()
    for event in events:
        row = event.to_dict()
        row["metadata"] = json.dumps(row["metadata"], ensure_ascii=False, sort_keys=True)
        writer.writerow(row)
    return output.getvalue()


def _validate_event_batch(events: List[TraceEvent]) -> List[TraceEvent]:
    if not events:
        raise ValueError("trace must contain at least one event")
    ids = [event.event_id for event in events]
    if len(ids) != len(set(ids)):
        raise ValueError("trace event_id values must be unique")
    return sorted(events, key=lambda item: (item.timestamp, item.event_id))


def _working_days(count: int) -> List[datetime]:
    days: List[datetime] = []
    cursor = _BASE_TIME
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _event(
    *,
    employee: str,
    correlation: str,
    timestamp: datetime,
    application: str,
    action: str,
    object_type: str,
    duration: int,
    index: int,
    status: str = "success",
    sensitivity: str = "internal",
    metadata: Dict[str, Any] | None = None,
) -> TraceEvent:
    seed = [employee, correlation, timestamp.isoformat(), application, action, index]
    return TraceEvent(
        event_id=stable_id("evt", seed, 16),
        employee_id=employee,
        timestamp=timestamp.isoformat(),
        application=application,
        action_type=action,
        object_type=object_type,
        object_id=stable_id("obj", [correlation, object_type], 10),
        source=application,
        destination=str((metadata or {}).get("destination") or application),
        duration_seconds=duration,
        metadata=dict(metadata or {}),
        sensitivity_level=sensitivity,
        result_status=status,
        correlation_id=correlation,
    )


def _workflow_events(
    day: datetime,
    employee: str,
    label: str,
    occurrence: int,
    steps: List[Tuple[str, str, str, int]],
    rng: random.Random,
) -> List[TraceEvent]:
    correlation = stable_id("case", [label, occurrence], 10)
    cursor = day + timedelta(minutes=occurrence % 4 * 7)
    events: List[TraceEvent] = []
    for index, (application, action, object_type, baseline) in enumerate(steps):
        if action == "search_correspondence" and occurrence % 4 == 0:
            continue
        duration = max(15, baseline + rng.choice((-20, -10, 0, 10, 20)))
        # The flagship runs every working day, so this deterministic failure is
        # guaranteed to exist even when optional workflows use a different cadence.
        status = "failed" if action == "check_limits" and occurrence == 3 else "success"
        metadata = {
            "demo": True,
            "synthetic": True,
            "automation_candidate": action not in {"human_verify", "approve", "send_email"},
        }
        events.append(
            _event(
                employee=employee,
                correlation=correlation,
                timestamp=cursor,
                application=application,
                action=action,
                object_type=object_type,
                duration=duration,
                index=index,
                status=status,
                metadata=metadata,
            )
        )
        cursor += timedelta(seconds=duration + 25)
        if status == "failed":
            events.append(
                _event(
                    employee=employee,
                    correlation=correlation,
                    timestamp=cursor,
                    application=application,
                    action=action,
                    object_type=object_type,
                    duration=duration + 15,
                    index=index + 100,
                    metadata={**metadata, "retry": True},
                )
            )
            cursor += timedelta(seconds=duration + 40)
    return events


def generate_synthetic_trace(seed: int = 2026, working_day_count: int = 10) -> Dict[str, Any]:
    """Create real event sequences; ground truth is returned only for evaluation."""
    if working_day_count < 7:
        raise ValueError("synthetic trace requires at least seven working days")
    rng = random.Random(seed)
    employee = "employee_credit_001"
    flagship = [
        ("task_tracker", "receive_task", "credit_task", 90),
        ("document_store", "find_latest_reports", "financial_report", 260),
        ("document_store", "find_account_statements", "account_statement", 220),
        ("crm", "check_limits", "credit_limit", 180),
        ("mail", "search_correspondence", "correspondence", 160),
        ("spreadsheet", "fill_personal_template", "mini_dossier", 420),
        ("spreadsheet", "check_covenants", "covenant", 260),
        ("risk", "check_stop_factors", "stop_factor", 200),
        ("editor", "draft_analytical_comment", "comment", 300),
        ("task_tracker", "create_task_draft", "task_draft", 130),
        ("mail", "create_email_draft", "email_draft", 150),
    ]
    weekly_report = [
        ("file_store", "open_source_files", "source_files", 180),
        ("bi", "export_indicators", "indicators", 250),
        ("spreadsheet", "fill_report_template", "weekly_report", 360),
        ("editor", "draft_summary", "summary", 180),
        ("file_store", "save_report", "weekly_report", 80),
        ("mail", "create_email_draft", "email_draft", 120),
    ]
    email_task = [
        ("mail", "receive_status_email", "status_email", 60),
        ("task_tracker", "find_related_task", "task", 150),
        ("mail", "extract_status", "status", 130),
        ("task_tracker", "update_task_draft", "task_draft", 180),
        ("task_tracker", "create_comment_draft", "comment", 140),
        ("mail", "create_response_draft", "email_draft", 150),
    ]
    events: List[TraceEvent] = []
    truth: Dict[str, str] = {}
    days = _working_days(working_day_count)
    for index, day in enumerate(days):
        for label, steps, enabled in (
            ("credit_dossier", flagship, True),
            ("weekly_report", weekly_report, index % 2 == 0),
            ("email_task_update", email_task, index % 2 == 1),
        ):
            if not enabled:
                continue
            generated = _workflow_events(day, employee, label, index, steps, rng)
            events.extend(generated)
            truth[generated[0].correlation_id] = label
        noise_corr = stable_id("noise", [index], 10)
        events.append(
            _event(
                employee=employee,
                correlation=noise_corr,
                timestamp=day + timedelta(hours=7),
                application="browser",
                action=f"one_off_lookup_{index}",
                object_type="web_page",
                duration=35 + index,
                index=index,
                metadata={"demo": True, "noise": True},
            )
        )
    prohibited_corr = stable_id("case", ["prohibited", 1], 10)
    events.append(
        _event(
            employee=employee,
            correlation=prohibited_corr,
            timestamp=days[-1] + timedelta(hours=8),
            application="risk",
            action="make_credit_decision",
            object_type="credit_decision",
            duration=5,
            index=0,
            status="blocked",
            sensitivity="confidential",
            metadata={"demo": True, "prohibited": True, "reason": "human authority required"},
        )
    )
    return {
        "schema_version": 1,
        "seed": seed,
        "working_days": [day.date().isoformat() for day in days],
        "events": [event.to_dict() for event in _validate_event_batch(events)],
        "ground_truth": truth,
        "disclaimer": "Fully synthetic demo data; no real employee or client information.",
    }
