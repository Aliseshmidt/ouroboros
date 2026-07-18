"""Data-driven discovery, lifecycle, and feedback for personal automations."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any

from .adapters import execute_workflow, supported_operations

_MAX_ACTIVITY_BYTES = 2_000_000
_MAX_EVENTS = 5_000
_MIN_CASES = 4
_MIN_VERIFICATION_CASES = 10
_STATE_FILE = "automation_state.json"
_AUDIT_FILE = "audit.jsonl"
_SAFE_EFFECTS = {"read": 0, "sandbox": 1, "draft": 2, "write": 3, "send": 4, "delete": 5}
_RISK_TEXT = {
    0: "низкий: только чтение копий данных",
    1: "низкий: создаются только новые локальные результаты",
    2: "низкий: создаются черновики без отправки",
    3: "средний: перед изменением рабочих данных нужно отдельное подтверждение",
    4: "высокий: отправка всегда должна подтверждаться отдельно",
    5: "высокий: удаление не разрешено этой автоматизации",
}
_OUTCOME_WEIGHT = {"accepted": 0.25, "edited": 0.05, "rejected": -0.35}
_IDENTIFIER_RE = re.compile(r"[^a-z0-9]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_digest(value: Any) -> str:
    packed = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _safe_slug(text: str, fallback: str = "personal_automation") -> str:
    transliterated = text.lower().translate(str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }))
    slug = _IDENTIFIER_RE.sub("_", transliterated).strip("_")
    return (slug[:48] or fallback).strip("_")


def _parse_timestamp(raw: Any) -> datetime:
    value = str(raw or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _bounded_text(value: Any, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[:limit]


def _duration(value: Any) -> float:
    result = float(value)
    if result < 0 or result > 480:
        raise ValueError("Продолжительность одного действия выглядит некорректно.")
    return round(result, 2)


def _event_from_mapping(item: dict[str, Any], index: int) -> dict[str, Any]:
    required = ("case_id", "timestamp", "application", "action", "object_type", "duration_min")
    if any(field not in item for field in required):
        raise ValueError(f"В истории не хватает обязательных сведений о действии №{index + 1}.")
    automation = item.get("automation")
    if not isinstance(automation, dict) or not str(automation.get("operation") or "").strip():
        raise ValueError(f"Для действия №{index + 1} не указано, как его безопасно воспроизвести.")
    _parse_timestamp(item["timestamp"])
    effect = str(item.get("effect") or "read").strip().lower()
    if effect not in _SAFE_EFFECTS:
        raise ValueError(f"Для действия №{index + 1} указан неизвестный тип воздействия.")
    settings = automation.get("settings")
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError(f"Настройки действия №{index + 1} должны быть структурированными.")
    return {
        "case_id": _bounded_text(item["case_id"], 100),
        "timestamp": _parse_timestamp(item["timestamp"]).isoformat(),
        "application": _bounded_text(item["application"], 80),
        "action": _bounded_text(item["action"], 80),
        "object_type": _bounded_text(item["object_type"], 80),
        "activity": _bounded_text(item.get("activity") or item["action"], 180),
        "outcome": _bounded_text(item.get("outcome") or "готовый результат для проверки", 180),
        "duration_min": _duration(item["duration_min"]),
        "automation_share": min(1.0, max(0.0, float(item.get("automation_share", 0.75)))),
        "effect": effect,
        "status": str(item.get("status") or "success").strip().lower(),
        "automation": {
            "operation": str(automation["operation"]).strip(),
            "settings": settings,
        },
    }


def _expand_workflow_spec(payload: dict[str, Any]) -> list[dict[str, Any]]:
    workflows = payload.get("workflows")
    if not isinstance(workflows, list):
        raise ValueError("История действий не содержит процессов для анализа.")
    events: list[dict[str, Any]] = []
    for workflow_index, workflow in enumerate(workflows):
        if not isinstance(workflow, dict):
            raise ValueError("Описание рабочего процесса повреждено.")
        steps = workflow.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError("В одном из процессов нет наблюдаемых действий.")
        occurrences = int(workflow.get("occurrences", 0))
        if occurrences < 1 or occurrences > 100:
            raise ValueError("Число повторений процесса выходит за безопасные границы.")
        start = _parse_timestamp(workflow.get("start"))
        interval_days = float(workflow.get("interval_days", 1))
        case_prefix = str(workflow.get("case_prefix") or f"process_{workflow_index + 1}")
        outcome = _bounded_text(workflow.get("outcome") or "готовый результат для проверки", 180)
        failed = {int(value) for value in workflow.get("failed_occurrences", [])}
        for occurrence in range(occurrences):
            case_start = start + timedelta(days=interval_days * occurrence)
            elapsed = 0.0
            for step_index, step in enumerate(steps):
                if not isinstance(step, dict):
                    raise ValueError("Одно из наблюдаемых действий повреждено.")
                base_duration = float(step.get("duration_min", 0))
                variation = ((occurrence + step_index) % 5 - 2) * 0.04
                duration_min = max(0.05, round(base_duration * (1 + variation), 2))
                event = {
                    **step,
                    "case_id": f"{case_prefix}_{occurrence + 1:02d}",
                    "timestamp": (case_start + timedelta(minutes=elapsed)).isoformat(),
                    "duration_min": duration_min,
                    "outcome": outcome,
                    "status": "failed" if occurrence + 1 in failed else "success",
                }
                events.append(_event_from_mapping(event, len(events)))
                elapsed += duration_min
    return events


def _load_activity_text(raw: str) -> list[dict[str, Any]]:
    if len(raw.encode("utf-8")) > _MAX_ACTIVITY_BYTES:
        raise ValueError("История слишком велика для одной безопасной проверки.")
    payload = json.loads(raw)
    if isinstance(payload, dict) and isinstance(payload.get("workflows"), list):
        events = _expand_workflow_spec(payload)
    else:
        items = payload.get("events") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise ValueError("История действий имеет неподдерживаемый формат.")
        events = [_event_from_mapping(item, index) for index, item in enumerate(items) if isinstance(item, dict)]
    if not events or len(events) > _MAX_EVENTS:
        raise ValueError("Для анализа нужно от 1 до 5000 действий.")
    return events


def _group_cases(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["case_id"]].append(event)
    for case_events in grouped.values():
        case_events.sort(key=lambda item: item["timestamp"])
    return dict(grouped)


def _case_signature(events: list[dict[str, Any]]) -> tuple[tuple[str, str], ...]:
    return tuple((event["automation"]["operation"], event["object_type"]) for event in events)


def _frequency_text(starts: list[datetime]) -> str:
    if len(starts) < 2:
        return "периодичность пока не подтверждена"
    ordered = sorted(starts)
    gaps = [(right - left).total_seconds() / 86400 for left, right in zip(ordered, ordered[1:])]
    typical = median(gaps)
    if typical <= 1.5:
        return "почти каждый рабочий день"
    if typical <= 8:
        return "примерно раз в неделю"
    if typical <= 35:
        return "примерно раз в месяц"
    return f"примерно раз в {round(typical)} дней"


def _confidence(occurrences: int, settings_consistency: float, success_rate: float) -> float:
    evidence = min(1.0, occurrences / 12)
    return round(min(0.99, 0.45 + 0.25 * evidence + 0.15 * settings_consistency + 0.14 * success_rate), 2)


def _risk_level(events: list[dict[str, Any]]) -> int:
    return max((_SAFE_EFFECTS[event["effect"]] for event in events), default=0)


def _candidate_from_group(signature: tuple[tuple[str, str], ...], cases: list[list[dict[str, Any]]]) -> dict[str, Any]:
    first = cases[0]
    settings_digests = {
        _json_digest([event["automation"] for event in case_events])
        for case_events in cases
    }
    consistency = 1.0 / len(settings_digests)
    successful = sum(1 for case_events in cases if all(event["status"] == "success" for event in case_events))
    starts = [_parse_timestamp(case_events[0]["timestamp"]) for case_events in cases]
    average_minutes = sum(sum(event["duration_min"] for event in case_events) for case_events in cases) / len(cases)
    average_saving = sum(
        sum(event["duration_min"] * event["automation_share"] for event in case_events)
        for case_events in cases
    ) / len(cases)
    risk = max(_risk_level(case_events) for case_events in cases)
    candidate_key = _json_digest(signature)
    return {
        "key": candidate_key,
        "title": first[-1]["outcome"],
        "sequence": [event["activity"] for event in first],
        "applications": list(dict.fromkeys(event["application"] for event in first)),
        "occurrences": len(cases),
        "case_ids": [case_events[0]["case_id"] for case_events in cases],
        "frequency": _frequency_text(starts),
        "average_minutes": round(average_minutes, 1),
        "average_saving": round(average_saving, 1),
        "sample_saving": round(average_saving * len(cases), 1),
        "confidence": _confidence(len(cases), consistency, successful / len(cases)),
        "risk": risk,
        "risk_text": _RISK_TEXT[risk],
        "settings_consistency": round(consistency, 2),
        "success_rate": round(successful / len(cases), 2),
        "recipe": [event["automation"] for event in first],
        "signature": [list(item) for item in signature],
        "requires_approval": True,
    }


def discover_candidates(events: list[dict[str, Any]], preferences: dict[str, float]) -> list[dict[str, Any]]:
    grouped: dict[tuple[tuple[str, str], ...], list[list[dict[str, Any]]]] = defaultdict(list)
    for case_events in _group_cases(events).values():
        grouped[_case_signature(case_events)].append(case_events)
    candidates = [
        _candidate_from_group(signature, cases)
        for signature, cases in grouped.items()
        if len(cases) >= _MIN_CASES and len(signature) >= 2
    ]
    for candidate in candidates:
        preference = float(preferences.get(candidate["key"], 0.0))
        candidate["ranking_score"] = round(
            candidate["confidence"] * 2 + candidate["average_saving"] / 20 + preference,
            3,
        )
    candidates.sort(key=lambda item: (item["ranking_score"], item["sample_saving"]), reverse=True)
    return candidates


def _directory_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


class PersonalAutomationEngine:
    """Stateful extension handler with human-readable responses only."""

    def __init__(self, api: Any) -> None:
        info = api.get_runtime_info()
        self.api = api
        self.state_dir = Path(api.get_state_dir())
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.skill_dir = Path(str(info.get("skill_dir") or Path(__file__).parent))
        self.synthetic_spec = self.skill_dir / "assets" / "synthetic" / "activity_spec.json"
        self.synthetic_workspace = self.skill_dir / "assets" / "synthetic" / "workspace"

    def _default_state(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "preferences": {},
            "feedback": [],
            "candidates": [],
            "current": {},
            "runs": [],
            "metrics": {"runs": 0, "minutes_saved": 0.0, "rollbacks": 0},
        }

    def _load_state(self) -> dict[str, Any]:
        try:
            loaded = json.loads((self.state_dir / _STATE_FILE).read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and loaded.get("schema_version") == 1:
                return loaded
        except (OSError, json.JSONDecodeError):
            pass
        return self._default_state()

    def _save_state(self, state: dict[str, Any]) -> None:
        _atomic_json(self.state_dir / _STATE_FILE, state)

    def _audit(self, action: str, **fields: Any) -> None:
        record = {"timestamp": _now(), "action": action, **fields}
        path = self.state_dir / _AUDIT_FILE
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def _events(self, activity_history: str = "") -> list[dict[str, Any]]:
        if activity_history.strip():
            return _load_activity_text(activity_history)
        return _load_activity_text(self.synthetic_spec.read_text(encoding="utf-8"))

    def _candidate(self, state: dict[str, Any], choice: str) -> dict[str, Any] | None:
        raw = str(choice or "").strip()
        try:
            index = int(raw) - 1
        except ValueError:
            index = -1
        candidates = state.get("candidates") or []
        if 0 <= index < len(candidates):
            return candidates[index]
        lowered = raw.casefold()
        return next((item for item in candidates if lowered and lowered in item["title"].casefold()), None)

    def _current(self, state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
        current = state.get("current")
        if not isinstance(current, dict) or not current.get("candidate_key"):
            return None
        candidate = next(
            (item for item in state.get("candidates", []) if item.get("key") == current["candidate_key"]),
            None,
        )
        return (current, candidate) if candidate else None

    def observe_work(self, ctx: Any = None, activity_history: str = "", maximum_suggestions: int = 5) -> str:
        del ctx
        try:
            events = self._events(activity_history)
            state = self._load_state()
            candidates = discover_candidates(
                events, state.get("preferences") or {}
            )[: max(1, min(5, maximum_suggestions))]
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return f"Я не смогла надёжно разобрать историю действий: {_bounded_text(exc)}"
        state["candidates"] = candidates
        state["activity_source"] = "provided" if activity_history.strip() else "synthetic"
        state["observed_at"] = _now()
        state["current"] = {}
        self._save_state(state)
        self._audit("observed", events=len(events), candidates=len(candidates), source=state["activity_source"])
        if not candidates:
            return (
                "В этой истории пока недостаточно устойчивых повторений. Нужны хотя бы четыре одинаковых "
                "завершённых цикла с понятным результатом."
            )
        header = (
            f"Я проверила {len(events)} действий и нашла {len(candidates)} устойчивых возможностей для автоматизации."
        )
        blocks = []
        for index, candidate in enumerate(candidates, 1):
            sequence = " → ".join(candidate["sequence"])
            blocks.append(
                f"{index}. {candidate['title']}\n"
                f"Повторяется: {candidate['frequency']}, замечено {candidate['occurrences']} раз.\n"
                f"Сейчас: в среднем {candidate['average_minutes']} мин. Экономия: около "
                f"{candidate['average_saving']} мин за один цикл.\n"
                f"Последовательность: {sequence}.\n"
                f"Уверенность: {round(candidate['confidence'] * 100)}%. Риск: {candidate['risk_text']}.\n"
                "Я могу подготовить локальную автоматизацию; вам останется проверить созданный результат."
            )
        return header + "\n\n" + "\n\n".join(blocks) + "\n\nНапишите номер варианта, который подготовить первым."

    def prepare_automation(self, ctx: Any = None, choice: str = "") -> str:
        del ctx
        state = self._load_state()
        candidate = self._candidate(state, choice)
        if candidate is None:
            return "Не удалось сопоставить выбор с предложениями. Укажите номер варианта из последнего списка."
        version = 1 + sum(1 for item in state.get("feedback", []) if item.get("key") == candidate["key"])
        slug = f"{_safe_slug(candidate['title'])}_{candidate['key'][:8]}"
        package_dir = self.state_dir / "micro_skills" / slug / f"v{version}"
        package_dir.mkdir(parents=True, exist_ok=True)
        workflow = {
            "schema_version": 1,
            "name": candidate["title"],
            "created_at": _now(),
            "source_pattern": candidate["key"],
            "steps": candidate["recipe"],
            "approval_required": True,
            "source_files_immutable": True,
            "rollback": "remove_created_outputs",
        }
        _atomic_json(package_dir / "workflow.json", workflow)
        skill_text = (
            "---\n"
            f"name: {slug}\n"
            f"description: {candidate['title']}\n"
            f"version: {version}.0.0\n"
            "type: instruction\n"
            "---\n\n"
            f"# {candidate['title']}\n\n"
            "This micro-skill is generated from repeated observed work. Execute its reviewed workflow through "
            "Personal Evolution Engine only after explicit user confirmation. Keep sources unchanged, create "
            "new local results, and retain rollback metadata.\n"
        )
        (package_dir / "SKILL.md").write_text(skill_text, encoding="utf-8")
        state["current"] = {
            "candidate_key": candidate["key"],
            "title": candidate["title"],
            "version": version,
            "package_dir": str(package_dir),
            "workflow_hash": _json_digest(workflow),
            "status": "prepared",
            "prepared_at": _now(),
        }
        self._save_state(state)
        self._audit("prepared", key=candidate["key"], version=version)
        return (
            f"Я подготовила личную автоматизацию «{candidate['title']}». Она повторяет только найденную "
            f"последовательность из {len(candidate['sequence'])} действий, создаёт новые локальные результаты "
            "и не меняет исходные данные. Следующий шаг — проверить её на исторических примерах."
        )

    def verify_automation(self, ctx: Any = None, show_each_check: bool = False) -> str:
        del ctx
        state = self._load_state()
        pair = self._current(state)
        if pair is None:
            return "Сначала выберите и подготовьте одну из найденных автоматизаций."
        current, candidate = pair
        try:
            events = self._events()
        except (OSError, ValueError, json.JSONDecodeError):
            return "Исторические примеры сейчас недоступны, поэтому я не буду выдавать непроверенное заключение."
        cases = _group_cases(events)
        expected_signature = tuple(tuple(item) for item in candidate["signature"])
        expected_recipe_hash = _json_digest(candidate["recipe"])
        operations = supported_operations()
        results = []
        for position, case_id in enumerate(candidate["case_ids"], 1):
            case_events = cases.get(case_id, [])
            signature_ok = _case_signature(case_events) == expected_signature if case_events else False
            recipe_ok = _json_digest([event["automation"] for event in case_events]) == expected_recipe_hash
            status_ok = bool(case_events) and all(event["status"] == "success" for event in case_events)
            operations_ok = bool(case_events) and all(
                event["automation"]["operation"] in operations for event in case_events
            )
            passed = signature_ok and recipe_ok and status_ok and operations_ok
            results.append({"number": position, "passed": passed})
        passed_count = sum(1 for item in results if item["passed"])
        accuracy = passed_count / len(results) if results else 0.0
        verified = len(results) >= _MIN_VERIFICATION_CASES and accuracy >= 0.9
        current["verification"] = {
            "checked_at": _now(),
            "total": len(results),
            "passed": passed_count,
            "accuracy": round(accuracy, 4),
            "results": results,
        }
        current["status"] = "verified" if verified else "verification_failed"
        if verified:
            current["confirmation_phrase"] = (
                f"Подтверждаю запуск «{candidate['title']}» только в локальном тестовом контуре"
            )
        self._save_state(state)
        self._audit("verified", key=candidate["key"], passed=passed_count, total=len(results), verified=verified)
        details = ""
        if show_each_check:
            detail_lines = [
                f"Проверка {item['number']}: {'пройдена' if item['passed'] else 'не пройдена'}"
                for item in results
            ]
            details = "\n" + "\n".join(detail_lines)
        if not verified:
            return (
                f"Проверка не пройдена: совпало {passed_count} из {len(results)} примеров "
                f"({round(accuracy * 100)}%). Запуск заблокирован до исправления." + details
            )
        return (
            f"Автоматизация проверена на {len(results)} исторических примерах: {passed_count} пройдено, "
            f"{len(results) - passed_count} не пройдено, точность {round(accuracy * 100)}%.\n"
            f"Оценка риска: {candidate['risk_text']}.\n"
            "Разрешено: читать синтетические источники и создавать новые Excel, PowerPoint, черновики писем "
            "или локальные списки для проверки — в зависимости от выбранного процесса.\n"
            "Требует отдельного подтверждения: сам запуск. Отправка писем, изменения CRM, создание внешних "
            "задач и удаление данных не разрешены.\n"
            "Откат возможен полностью: будут удалены только файлы, созданные тестовым запуском.\n"
            f"Для запуска напишите точно: {current['confirmation_phrase']}" + details
        )

    def approve_automation(self, ctx: Any = None, confirmation: str = "") -> str:
        del ctx
        state = self._load_state()
        pair = self._current(state)
        if pair is None:
            return "Сначала подготовьте и проверьте автоматизацию."
        current, candidate = pair
        expected = str(current.get("confirmation_phrase") or "")
        if current.get("status") != "verified" or not expected:
            return "Автоматизация ещё не прошла историческую проверку, поэтому запуск не подтверждён."
        if " ".join(confirmation.split()) != expected:
            return "Подтверждение не совпало с показанной фразой. Я не разрешила запуск."
        current["status"] = "approved"
        current["approved_at"] = _now()
        current["approved_workflow_hash"] = current["workflow_hash"]
        self._save_state(state)
        self._audit("approved", key=candidate["key"])
        return (
            f"Подтверждение принято. Автоматизация «{candidate['title']}» разрешена для одного запуска "
            "только на синтетических данных."
        )

    def run_automation(self, ctx: Any = None) -> str:
        del ctx
        state = self._load_state()
        pair = self._current(state)
        if pair is None:
            return "Нет подготовленной автоматизации для запуска."
        current, candidate = pair
        if current.get("status") != "approved":
            return "Запуск не выполнен: сначала нужна точная фраза подтверждения из результата проверки."
        if current.get("approved_workflow_hash") != current.get("workflow_hash"):
            return "Автоматизация изменилась после подтверждения. Нужна повторная проверка и новое подтверждение."
        if not self.synthetic_workspace.is_dir():
            return "Синтетические исходные данные недоступны, поэтому запуск безопасно остановлен."
        source_before = _directory_digest(self.synthetic_workspace)
        run_token = uuid.uuid4().hex[:12]
        job_dir = Path(self.api.skill_job_dir(f"automation-{run_token}"))
        output_dir = job_dir / "output"
        try:
            result = execute_workflow(candidate["recipe"], self.synthetic_workspace, output_dir)
        except Exception as exc:
            self._audit("run_failed", key=candidate["key"], error_type=type(exc).__name__)
            return f"Запуск остановлен без изменения исходных данных: {_bounded_text(exc)}"
        source_after = _directory_digest(self.synthetic_workspace)
        if source_before != source_after:
            shutil.rmtree(output_dir, ignore_errors=True)
            self._audit("source_integrity_failed", key=candidate["key"])
            return "Запуск отменён: контроль целостности исходных данных не пройден. Созданные результаты удалены."
        artifacts = [str(Path(path)) for path in result.get("artifacts", [])]
        run_record = {
            "run_token": run_token,
            "candidate_key": candidate["key"],
            "title": candidate["title"],
            "created_at": _now(),
            "output_dir": str(output_dir),
            "artifacts": artifacts,
            "rolled_back": False,
            "estimated_minutes_saved": candidate["average_saving"],
        }
        state.setdefault("runs", []).append(run_record)
        state["runs"] = state["runs"][-30:]
        state["metrics"]["runs"] = int(state["metrics"].get("runs", 0)) + 1
        state["metrics"]["minutes_saved"] = round(
            float(state["metrics"].get("minutes_saved", 0)) + candidate["average_saving"], 1
        )
        current["status"] = "completed"
        current["last_run_token"] = run_token
        self._save_state(state)
        self._audit("completed", key=candidate["key"], artifacts=len(artifacts), source_unchanged=True)
        names = [Path(path).name for path in artifacts]
        created = ", ".join(names) if names else "результат для проверки"
        return (
            f"Готово. Создано: {created}.\n"
            f"Результаты находятся в папке: {output_dir}\n"
            "Исходные данные не изменялись. Письма не отправлялись, внешние задачи и записи не создавались. "
            f"Оценочная экономия этого запуска — около {candidate['average_saving']} минут. "
            "Если результат не подходит, я могу полностью откатить этот запуск."
        )

    def rollback_automation(self, ctx: Any = None) -> str:
        del ctx
        state = self._load_state()
        runs = state.get("runs") or []
        latest = next((item for item in reversed(runs) if not item.get("rolled_back")), None)
        if latest is None:
            return "Нет активного тестового результата, который можно откатить."
        output_dir = Path(str(latest.get("output_dir") or ""))
        jobs_root = (self.state_dir / "jobs").resolve()
        try:
            resolved = output_dir.resolve()
            if jobs_root not in resolved.parents or resolved.name != "output":
                raise ValueError("unsafe rollback target")
            shutil.rmtree(resolved, ignore_errors=False)
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            return "Не удалось подтвердить безопасную границу отката, поэтому файлы не удалены."
        latest["rolled_back"] = True
        latest["rolled_back_at"] = _now()
        state["metrics"]["rollbacks"] = int(state["metrics"].get("rollbacks", 0)) + 1
        pair = self._current(state)
        if pair is not None:
            pair[0]["status"] = "rolled_back"
        self._save_state(state)
        self._audit("rolled_back", run_token=latest.get("run_token"))
        return (
            "Откат завершён. Удалены только результаты последнего запуска; "
            "исходные данные и история проверки сохранены."
        )

    def record_feedback(self, ctx: Any = None, outcome: str = "", comment: str = "") -> str:
        del ctx
        state = self._load_state()
        pair = self._current(state)
        if pair is None:
            return "Сейчас нет выбранной автоматизации, к которой можно привязать отзыв."
        current, candidate = pair
        if outcome not in _OUTCOME_WEIGHT:
            return "Отметьте результат как принятый, требующий правок или отклонённый."
        preferences = state.setdefault("preferences", {})
        preferences[candidate["key"]] = round(
            max(-1.0, min(1.0, float(preferences.get(candidate["key"], 0.0)) + _OUTCOME_WEIGHT[outcome])),
            2,
        )
        state.setdefault("feedback", []).append({
            "timestamp": _now(),
            "key": candidate["key"],
            "outcome": outcome,
            "comment": _bounded_text(comment, 500),
            "version": current.get("version"),
        })
        state["feedback"] = state["feedback"][-100:]
        self._save_state(state)
        self._audit("feedback", key=candidate["key"], outcome=outcome)
        messages = {
            "accepted": "Принято. Похожие возможности будут получать более высокий приоритет в следующих наблюдениях.",
            "edited": (
                "Правка учтена как отдельный опыт. Текущая подтверждённая версия не изменена; при следующей "
                "подготовке будет создана новая версия для повторной проверки."
            ),
            "rejected": (
                "Отклонение учтено. Похожие предложения будут показываться реже, "
                "но история останется для аудита."
            ),
        }
        return messages[outcome]

    def automation_status(self, ctx: Any = None) -> str:
        del ctx
        state = self._load_state()
        pair = self._current(state)
        metrics = state.get("metrics") or {}
        if pair is None:
            return (
                f"Активная автоматизация не выбрана. Выполнено тестовых запусков: {metrics.get('runs', 0)}; "
                f"оценочно сэкономлено {metrics.get('minutes_saved', 0)} минут."
            )
        current, candidate = pair
        status_text = {
            "prepared": "подготовлена и ждёт исторической проверки",
            "verified": "проверена и ждёт точного подтверждения",
            "approved": "подтверждена для одного локального запуска",
            "completed": "выполнена; результат можно проверить или откатить",
            "rolled_back": "последний результат откатан",
            "verification_failed": "не прошла проверку и заблокирована",
        }.get(current.get("status"), "состояние требует повторной проверки")
        return (
            f"«{candidate['title']}» — {status_text}. Всего тестовых запусков: {metrics.get('runs', 0)}; "
            f"оценочно сэкономлено {metrics.get('minutes_saved', 0)} минут."
        )
