# Pattern Mining Design

## Goal and evidence discipline

The Pattern Miner should discover repeatable personal workflows from an anonymized
event stream without receiving precomputed pattern labels. The primary algorithm is
deterministic so the same input produces the same clusters, scores, and explanation.

**Observed baseline:** the current extension groups cases by an exact sequence of
`source:action`, filters groups with fewer than three occurrences, and reports basic
frequency, duration, risk, confidence, and estimated saving.

**Planned target:** a 14-field trace, variation-tolerant mining, noise handling,
stable/variable segments, periodicity, automation suitability, and independently
measured precision/recall/false-positive rate. The baseline must not be presented as
evidence that these target capabilities work.

## Target event contract

| Field | Meaning | Validation rule |
|---|---|---|
| `event_id` | Unique synthetic event id | Non-empty, unique |
| `employee_id` | Synthetic employee id | Non-empty; no real identity |
| `timestamp` | Event time | ISO-8601, monotonic within a case after sorting |
| `application` | UI/system category | Allow-listed normalized token |
| `action_type` | User/system action | Allow-listed normalized token |
| `object_type` | Document/task/report/etc. | Normalized token |
| `object_id` | Synthetic object reference | No business content |
| `source` | Origin system/category | Allow-listed adapter id |
| `destination` | Destination system/category | Allow-listed or null |
| `duration_seconds` | Observed/simulated duration | Finite, non-negative, bounded |
| `metadata` | Minimal structured attributes | Schema-limited; no free secrets/PII |
| `sensitivity_level` | Synthetic classification | Closed enum |
| `result_status` | Success/failure/cancelled | Closed enum |
| `correlation_id` | Case/session link | Non-empty synthetic id |

The current six-field prototype schema is not compatible evidence for this contract.

## Planned deterministic pipeline

1. **Validate and normalize.** Reject oversized payloads, invalid timestamps, secrets,
   real identifiers, and unknown security-sensitive fields. Canonicalize applications,
   actions, and object types.
2. **Build cases.** Prefer `correlation_id`; otherwise use explicit fixture case ids.
   A time-window fallback is permitted only when its threshold is recorded.
3. **Remove known noise for mining, not for audit.** Navigation, retries, failures, and
   irregular events remain in raw test evidence but are tagged so mining can test
   robustness.
4. **Generate sequence candidates.** Mine frequent contiguous and bounded-gap
   subsequences above a minimum support. Labels remain separate from the miner.
5. **Compare and cluster.** Use normalized longest-common-subsequence similarity plus
   application/action compatibility. Deterministic tie-breaking uses canonical ids.
6. **Describe stable and variable segments.** A step is stable when it appears at the
   aligned position in the configured share of cluster cases; optional, reordered, and
   parameter-varying steps are variable.
7. **Calculate features.** Frequency, periodicity, duration distribution, manual steps,
   variability, confidence, risk, potential saving, and automation suitability.
8. **Apply safety eligibility.** Patterns containing irreversible, high-risk, or
   permission-expanding actions remain visible but cannot be auto-promoted.
9. **Produce an evidence-linked hypothesis.** Every statement cites cluster cases and
   measured features; no LLM may invent source facts.

Thresholds must live in one configuration surface and appear in the report. They are
not frozen here because they require validation against the final synthetic corpus.

## Scoring model

The target score is an explainable composition rather than a learned black box:

- **Support:** how many independent cases contain the sequence.
- **Consistency:** aligned stable-step coverage.
- **Duration confidence:** sample size and dispersion of observed durations.
- **Noise penalty:** unmatched/irregular events around the sequence.
- **Risk penalty:** irreversible, regulated, or permission-sensitive actions.
- **Value:** conservative time that can be removed while retaining human controls.

The exact coefficients are **Planned** and must be reported with sensitivity analysis.
Confidence is not a probability unless calibrated; the UI should label it “уверенность
модели поиска паттерна,” not a guarantee of business correctness.

## Test corpus

The target corpus spans at least seven synthetic working days and contains:

- repeated flagship mini-dossier cases with minor variations;
- a personalized weekly-report workflow;
- an email-to-task-update workflow;
- irregular actions and unrelated noise;
- variable durations and failed actions;
- similar but distinct sequences;
- prohibited and approval-required actions;
- insufficient-support examples.

Ground-truth labels are used only by the evaluator after mining. Passing labels into
candidate generation would make the result precomputed.

## Metrics

| Metric | Definition | Evidence status |
|---|---|---|
| Precision | Correct detected clusters / all detected clusters | Placeholder |
| Recall | Ground-truth patterns detected / all ground-truth patterns | Placeholder |
| False-positive rate | Incorrect candidates / evaluated non-pattern candidates | Placeholder |
| Variation coverage | Variant cases assigned to the correct cluster | Placeholder |
| Separation | Similar-but-distinct workflows kept apart | Placeholder |
| Stability | Identical output hashes on repeated runs | Placeholder |

Metrics must be calculated from saved expected and actual outputs. Synthetic results
must be labelled “calculated on synthetic data,” never “production accuracy.”

## Jury-facing explanation

> **Как работает поиск паттернов.** Система получает обезличенный поток действий,
> самостоятельно собирает события в рабочие кейсы и ищет повторяющиеся
> последовательности. Эталонные метки не передаются алгоритму: они используются
> только после расчёта, чтобы проверить точность. Алгоритм учитывает вариации,
> шум, длительность и риск, а в карточке показывает, какие шаги стабильны, какие
> меняются и почему процесс подходит или не подходит для автоматизации.

Example hypothesis (illustrative, not measured):

> **Обнаружен паттерн «Подготовка мини-досье».** Он повторился 12 раз в
> синтетической выборке. Стабильные шаги: поиск отчётов, сверка показателей,
> заполнение шаблона и подготовка черновика. Ручная проверка стоп-факторов и
> финальное решение сохраняются за аналитиком. Числовой эффект будет показан
> только после воспроизводимого замера AS IS и TO BE.

## AS IS / TO BE measurement

- **AS IS measured/simulated:** sum event durations for the complete manual case.
- **TO BE measured:** wall-clock or deterministic step telemetry for the same fixture,
  plus explicitly retained human-review time.
- **Saved time:** AS IS minus TO BE for matched inputs; never substitute the Proposal
  target for this measurement.
- **Manual-step reduction:** count only steps genuinely removed, not hidden in a mock.

The Proposal values 45/18/27 minutes remain **target** values until the final report
contains matched-run evidence.

## Known limitations

- The current miner uses exact signatures and will split minor sequence variations.
- The current confidence formula is heuristic and uncalibrated.
- Estimated time saving in the current prototype is a fixed proportion of baseline
  duration, not measured execution evidence.
- Synthetic traces cannot prove behavior on production process drift.
- Semantic naming may later use an LLM, but deterministic clustering remains the
  authority for membership and metrics.
