# Hackathon Demo Guide

This guide separates the **currently reproducible fallback** from the **planned final
UI/video path**. Do not record or narrate a planned screen as implemented.

## Current reproducible fallback

Run from the repository root:

```bash
python3 skills/personal_evolution_engine/scripts/demo.py
```

Observed on 17 July 2026, the command returned:

- 144 synthetic events in 36 cases;
- three exact-signature patterns;
- one proposal verified on 12 cases;
- explicit proposal approval;
- an approved draft-only execution;
- zero external writes.

This is useful smoke evidence, not the final hackathon demonstration. It does not show
the required 14-field trace, variation-tolerant mining, complete generated skill tree,
rich expected/actual diffs, independent review, Credit Analyst output, or v1/v2
rollback.

## Final demo entry criteria

Record the UI only after all of the following are **Verified**:

- one-command local start with no paid or corporate dependency;
- required synthetic 14-field dataset imports successfully;
- at least three patterns are discovered without labels;
- the flagship hypothesis cites trace evidence and human-controlled steps;
- a complete on-disk micro-skill is generated and its tests run;
- expected/actual/diff and security checks are visible;
- execution without approval is rejected;
- the approved run creates drafts only and logs every step;
- v1 fails the controlled case, v2 fixes it, and rollback passes;
- every metric is labelled measured, simulated, estimated, or target;
- three consecutive end-to-end runs pass;
- no secrets or personal data appear in UI, logs, screenshots, subtitles, or video.

Until these gates pass, the corresponding video segment is an **evidence placeholder**.

## Operator preflight

1. Use a clean local checkout and deterministic demo state.
2. Confirm no real connector credentials are configured for the demo.
3. Run the relevant fast tests and security/secret scans.
4. Run the end-to-end path three times and retain hashes/results.
5. Confirm mock adapters are visibly labelled `DEMO` / `MOCK`.
6. Reset to the known starting state.
7. Open the UI at the final recording resolution and verify no overflow or empty cards.
8. Close unrelated notifications and applications.
9. Rehearse against the 150–175 second timing sheet.

## Planned end-to-end click path

| Step | Operator action | Required visible evidence | Status |
|---|---|---|---|
| 1 | Select the synthetic seven-day trace and import it | 14-field validation, anonymization notice, row/case counts | Planned |
| 2 | Start pattern analysis | Three clusters, frequency, duration, confidence, risk, saving | Planned |
| 3 | Open “Подготовка мини-досье” | Stable/variable steps, source cases, human-controlled actions | Planned |
| 4 | Approve the hypothesis | Explicit transition to skill generation | Planned |
| 5 | Open Micro-Skill Builder | Actual generated files, version, tools, permissions, policy, tests | Planned |
| 6 | Run historical tests | Expected/actual/diff, 10+ cases, security checks, reviewer verdict | Planned |
| 7 | Try execution without approval | Fail-closed rejection | Planned |
| 8 | Review plan and approve exact run | Input/version/plan/diff/risk/cost binding | Planned |
| 9 | Run flagship case | Evidence collection, calculations, risk flags, task/email drafts, audit | Planned |
| 10 | Show v1 defect and v2 correction | Same-basket metrics, diff, promotion decision, rollback | Planned |
| 11 | Open Value Dashboard | Provenance labels and matched AS IS/TO BE measurement | Planned |

If any control is static, broken, or unsupported, remove that segment instead of
simulating a click.

## Russian 175-second narration plan

### 0–15 seconds — problem

> У каждого сотрудника есть небольшие повторяющиеся процессы, которые занимают
> десятки минут, но слишком индивидуальны для отдельного проекта автоматизации.
> Персональный агент Ouroboros находит такие процессы и превращает их в безопасные
> микронавыки.

### 15–32 seconds — trace

> Загружаем синтетический цифровой след за семь рабочих дней. В нём нет реальных
> клиентов, писем или персональных данных. Алгоритм получает события, а не готовый
> список паттернов.

### 32–52 seconds — mining

> Детерминированный Pattern Miner обнаруживает три повторяющихся процесса и
> показывает частоту, время, вариативность, уверенность, риск и потенциальный
> эффект. Эталонные метки используются только для последующей проверки качества.

### 52–70 seconds — hypothesis

> В основном сценарии аналитик регулярно готовит клиентское мини-досье. Агент
> предлагает автоматизировать сбор разрешённых данных, заполнение шаблона и
> проверки. Финальное решение и отправка остаются за сотрудником.

### 70–98 seconds — Ouroboros builds the skill

> После подтверждения гипотезы Ouroboros планирует работу и создаёт отдельный
> версионированный микронавык: SKILL.md, workflow, схемы, инструменты, разрешения,
> safety policy и тесты. Независимый контур проверки оценивает тот же неизменный
> хеш версии.

Use this wording only when the file tree and independent review are visible and
verified.

### 98–120 seconds — sandbox

> Навык запускается на обезличенной истории. Для каждого примера видны вход,
> ожидаемый и фактический результат, diff, проверки утечек, инъекций, разрешений,
> стоимости и времени. До подтверждения выполнение заблокировано.

### 120–143 seconds — approved draft

> Сотрудник видит точный план, данные, изменения и риск. После подтверждения агент
> собирает синтетические доказательства, выполняет расчёты, отмечает противоречия и
> готовит черновики задачи и письма. Ничего не отправляется автоматически.

### 143–160 seconds — evolution

> В первой версии мы воспроизводимо показываем контролируемую ошибку. Ouroboros
> формирует вторую версию, запускает тот же набор регрессий и показывает улучшение.
> Продвижение и откат выполняются только по решению сотрудника.

### 160–175 seconds — value and close

> Дашборд разделяет измеренный результат, расчёт на синтетических данных и целевой
> эффект. Ouroboros возвращает сотруднику время, не забирая контроль: уникальная
> рутина становится безопасным, проверяемым и переиспользуемым микронавыком.

## AS IS / TO BE screen copy

> **AS IS:** 11 ручных шагов: поиск документов и выписок, сверка лимитов и
> ковенантов, перенос показателей, проверка стоп-факторов, подготовка комментария,
> задачи и письма.
>
> **TO BE:** агент собирает разрешённые данные, проверяет полноту, выполняет
> детерминированные расчёты, показывает доказательства и готовит черновики. Человек
> проверяет риски, принимает решение и подтверждает каждое значимое действие.

The 45-minute AS IS, 18-minute target TO BE, and 27-minute potential saving are
Proposal targets. Display them only with the label `Целевой ориентир`; place measured
MVP timing beside them when evidence exists.

## Recording and verification

Target 150–175 seconds; the rule is strictly under three minutes. The final MP4 must
contain video, Russian narration, and readable Russian subtitles.

Example verification commands after the artifact exists:

```bash
ffprobe -v error -show_entries format=duration -show_streams submission/DEMO_VIDEO.mp4
ffmpeg -i submission/DEMO_VIDEO.mp4 -vf fps=1/15 tmp/demo-frame-%02d.png
```

Required review:

- duration is less than 180 seconds;
- both video and audio streams exist;
- sampled frames contain no PII, secrets, notifications, broken UI, or unsupported
  claims;
- subtitles remain legible at the submission resolution;
- waiting time is edited out without hiding failures;
- every shown button triggered real server-backed behavior in the recorded run.

## Demo limitations to state aloud or on screen

> Данные полностью синтетические. Корпоративные коннекторы представлены mock-
> адаптерами. Прототип готовит черновики и не принимает кредитных решений, не
> отправляет письма и не меняет записи во внешних системах. Внешняя A2A-
> совместимость не заявляется; роли взаимодействуют внутри Ouroboros.

## Recovery plan

- If the final UI path is not verified, use the CLI smoke output as engineering
  evidence and do not disguise it as the complete product.
- If local speech quality is poor, keep Russian subtitles embedded and re-record the
  voice; do not exceed the duration to compensate.
- If a metric differs between runs, stop recording, retain the failing artifact, and
  fix reproducibility before resuming.
- If any personal or secret-like value appears, discard the recording and rescan all
  source artifacts before recording again.
