"""Reviewed extension surface for data-driven personal automations."""

from __future__ import annotations

from typing import Any

from .engine import PersonalAutomationEngine


def _schema(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties or {},
        **({"required": required} if required else {}),
        "additionalProperties": False,
    }


def register(api: Any) -> None:
    engine = PersonalAutomationEngine(api)

    api.register_tool(
        "observe_work",
        engine.observe_work,
        description=(
            "Analyse a bounded employee activity history and return only a plain-language automation proposal. "
            "Use the bundled synthetic history when no activity_history is supplied. Relay the returned text "
            "without exposing tool names, identifiers, schemas, implementation details, or raw data."
        ),
        schema=_schema({
            "activity_history": {
                "type": "string",
                "default": "",
                "description": "Optional JSON activity history. Leave empty for the bundled synthetic demonstration.",
            },
            "maximum_suggestions": {"type": "integer", "minimum": 1, "maximum": 5, "default": 5},
        }),
        timeout_sec=45,
    )
    api.register_tool(
        "prepare_automation",
        engine.prepare_automation,
        description=(
            "Prepare one numbered opportunity as a reusable personal micro-skill. Return only user-facing text; "
            "do not reveal internal files, identifiers, or formats. Preparation does not approve a run."
        ),
        schema=_schema({
            "choice": {
                "type": "string",
                "description": "The number or visible title of the opportunity chosen by the user.",
            }
        }, ["choice"]),
        timeout_sec=30,
    )
    api.register_tool(
        "verify_automation",
        engine.verify_automation,
        description=(
            "Verify the prepared micro-skill against its historical examples without external effects. "
            "Return a plain-language result, risk assessment, approval boundary, and rollback statement."
        ),
        schema=_schema({
            "show_each_check": {"type": "boolean", "default": False},
        }),
        timeout_sec=60,
    )
    api.register_tool(
        "approve_automation",
        engine.approve_automation,
        description=(
            "Record explicit approval only when confirmation exactly matches the sentence previously shown. "
            "Do not reinterpret a vague yes as approval. Return only plain-language status."
        ),
        schema=_schema({
            "confirmation": {"type": "string"},
        }, ["confirmation"]),
        timeout_sec=15,
    )
    api.register_tool(
        "run_automation",
        engine.run_automation,
        description=(
            "Run the currently approved micro-skill in the local synthetic workspace, create only new result "
            "files, and return a plain-language completion message. Never send mail or modify source data."
        ),
        schema=_schema(),
        timeout_sec=120,
    )
    api.register_tool(
        "rollback_automation",
        engine.rollback_automation,
        description=(
            "Remove only the result files created by the latest local run and preserve source data and audit history. "
            "Return only a plain-language outcome."
        ),
        schema=_schema(),
        timeout_sec=30,
    )
    api.register_tool(
        "record_feedback",
        engine.record_feedback,
        description=(
            "Record accepted, edited, or rejected feedback so future recommendation ranking adapts. "
            "Feedback never silently alters an approved automation."
        ),
        schema=_schema({
            "outcome": {"type": "string", "enum": ["accepted", "edited", "rejected"]},
            "comment": {"type": "string", "default": "", "maxLength": 500},
        }, ["outcome"]),
        timeout_sec=15,
    )
    api.register_tool(
        "automation_status",
        engine.automation_status,
        description=(
            "Summarise the current personal automation, measured value, and next safe action in plain language."
        ),
        schema=_schema(),
        timeout_sec=15,
    )
