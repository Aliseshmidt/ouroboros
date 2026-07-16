"""Deterministic, domain-neutral recurring sequence clustering."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Sequence, Tuple

from ouroboros.hackathon.models import Pattern, TraceEvent, stable_id

_APPROVAL_ACTIONS = {"approve", "send_email", "make_credit_decision", "delete", "pay", "submit"}
_WRITE_MARKERS = ("create_", "update_", "save_", "send_", "submit", "approve")


def _sessions(events: Iterable[TraceEvent]) -> Dict[str, List[TraceEvent]]:
    grouped: Dict[str, List[TraceEvent]] = defaultdict(list)
    for event in events:
        grouped[event.correlation_id].append(event)
    return {
        correlation: sorted(rows, key=lambda item: (item.timestamp, item.event_id))
        for correlation, rows in grouped.items()
    }


def _sequence(rows: Sequence[TraceEvent]) -> List[str]:
    sequence: List[str] = []
    for event in rows:
        if event.metadata.get("noise") or event.result_status in {"blocked", "cancelled"}:
            continue
        token = f"{event.application}:{event.action_type}"
        if sequence and sequence[-1] == token and event.metadata.get("retry"):
            continue
        sequence.append(token)
    return sequence


def _similarity(left: Sequence[str], right: Sequence[str]) -> float:
    if not left or not right:
        return 0.0
    ordered = SequenceMatcher(a=list(left), b=list(right), autojunk=False).ratio()
    overlap = len(set(left) & set(right)) / max(1, len(set(left) | set(right)))
    return 0.75 * ordered + 0.25 * overlap


def _cluster_sequences(items: List[Tuple[str, List[str]]], threshold: float) -> List[List[Tuple[str, List[str]]]]:
    clusters: List[List[Tuple[str, List[str]]]] = []
    for item in sorted(items, key=lambda value: (-len(value[1]), value[0])):
        best_index = -1
        best_score = 0.0
        for index, cluster in enumerate(clusters):
            score = sum(_similarity(item[1], existing[1]) for existing in cluster) / len(cluster)
            if score > best_score:
                best_index, best_score = index, score
        if best_index >= 0 and best_score >= threshold:
            clusters[best_index].append(item)
        else:
            clusters.append([item])
    return clusters


def _medoid(cluster: List[Tuple[str, List[str]]]) -> List[str]:
    ranked = []
    for correlation, sequence in cluster:
        score = sum(_similarity(sequence, other) for _, other in cluster)
        ranked.append((score, len(sequence), correlation, sequence))
    return max(ranked, key=lambda item: (item[0], item[1], item[2]))[3]


def _pattern_name(sequence: Sequence[str]) -> str:
    actions = {token.split(":", 1)[-1] for token in sequence}
    if {"check_covenants", "check_stop_factors", "fill_personal_template"} <= actions:
        return "Подготовка клиентского мини-досье"
    if {"fill_report_template", "save_report"} <= actions:
        return "Подготовка персонального еженедельного отчёта"
    if {"receive_status_email", "update_task_draft"} <= actions:
        return "Обновление задачи по входящему письму"
    last = sequence[-1].split(":", 1)[-1].replace("_", " ") if sequence else "workflow"
    return f"Recurring {last} workflow"


def _periodicity(cluster: List[Tuple[str, List[str]]], session_rows: Dict[str, List[TraceEvent]]) -> float:
    starts = sorted(datetime.fromisoformat(session_rows[corr][0].timestamp) for corr, _ in cluster)
    deltas = [(right - left).total_seconds() / 86_400 for left, right in zip(starts, starts[1:])]
    return round(statistics.median(deltas), 2) if deltas else 0.0


def _risk(sequence: Sequence[str]) -> str:
    actions = {token.split(":", 1)[-1] for token in sequence}
    if actions & _APPROVAL_ACTIONS:
        return "high"
    if any(action.startswith(_WRITE_MARKERS) for action in actions):
        return "medium"
    return "low"


def _build_pattern(cluster: List[Tuple[str, List[str]]], session_rows: Dict[str, List[TraceEvent]]) -> Pattern:
    representative = _medoid(cluster)
    action_support = Counter(action for _, sequence in cluster for action in set(sequence))
    stable = [action for action in representative if action_support[action] / len(cluster) >= 0.75]
    variable = sorted({action for _, sequence in cluster for action in sequence if action not in stable})
    durations = [sum(event.duration_seconds for event in session_rows[corr]) for corr, _ in cluster]
    lengths = [len(sequence) for _, sequence in cluster]
    similarities = [_similarity(sequence, representative) for _, sequence in cluster]
    variability = 1.0 - sum(similarities) / len(similarities)
    frequency_factor = min(1.0, len(cluster) / 8)
    confidence = max(0.0, min(0.99, 0.45 * frequency_factor + 0.55 * (1.0 - variability)))
    risk = _risk(representative)
    automation_ratio = sum(1 for action in representative if action.split(":", 1)[-1] not in _APPROVAL_ACTIONS) / len(
        representative
    )
    saving = statistics.mean(durations) * automation_ratio * 0.65
    suitability = confidence * automation_ratio * ({"low": 1.0, "medium": 0.8, "high": 0.45}[risk])
    return Pattern(
        pattern_id=stable_id("pat", representative, 12),
        name=_pattern_name(representative),
        representative_sequence=list(representative),
        stable_actions=stable,
        variable_actions=variable,
        correlation_ids=sorted(correlation for correlation, _ in cluster),
        frequency=len(cluster),
        periodicity_days=_periodicity(cluster, session_rows),
        average_duration_seconds=round(statistics.mean(durations), 2),
        manual_steps=round(statistics.median(lengths)),
        potential_time_saving_seconds=round(saving, 2),
        confidence=round(confidence, 4),
        variability=round(variability, 4),
        risk_level=risk,
        automation_suitability=round(suitability, 4),
    )


def mine_patterns(
    events: Iterable[TraceEvent],
    *,
    min_frequency: int = 3,
    similarity_threshold: float = 0.56,
) -> List[Pattern]:
    if min_frequency < 2:
        raise ValueError("min_frequency must be at least 2")
    session_rows = _sessions(events)
    items = [(correlation, _sequence(rows)) for correlation, rows in session_rows.items()]
    items = [(correlation, sequence) for correlation, sequence in items if len(sequence) >= 2]
    clusters = _cluster_sequences(items, similarity_threshold)
    patterns = [_build_pattern(cluster, session_rows) for cluster in clusters if len(cluster) >= min_frequency]
    return sorted(patterns, key=lambda item: (-item.frequency, item.pattern_id))


def evaluate_pattern_mining(patterns: Sequence[Pattern], ground_truth: Dict[str, str]) -> Dict[str, float | int]:
    predicted: Dict[str, str] = {}
    true_positive = 0
    for pattern in patterns:
        labels = Counter(ground_truth.get(correlation, "") for correlation in pattern.correlation_ids)
        labels.pop("", None)
        assigned = labels.most_common(1)[0][0] if labels else pattern.pattern_id
        for correlation in pattern.correlation_ids:
            predicted[correlation] = assigned
            if ground_truth.get(correlation) == assigned:
                true_positive += 1
    predicted_positive = len(predicted)
    actual_positive = len(ground_truth)
    precision = true_positive / predicted_positive if predicted_positive else 0.0
    recall = true_positive / actual_positive if actual_positive else 0.0
    false_positive_rate = (predicted_positive - true_positive) / predicted_positive if predicted_positive else 0.0
    return {
        "detected_patterns": len(patterns),
        "true_positive_cases": true_positive,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
    }
