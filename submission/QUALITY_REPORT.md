# Отчёт о качестве

## Вердикт

**ENGINEERING CORE AND MEDIA PACK VERIFIED.** Focused/domain, checked-in
generated-Skill и UI/API tests зелёные; browser evidence и MP4 проверены. Полный
репозиторный suite и обязательный Ruff F gate также зелёные.

## Тесты

| Команда | Passed | Failed | Статус |
|---|---:|---:|---|
| Domain + checked-in generated Skill tests | 42 | 0 | Green |
| UI/static/API regression tests | 8 | 0 | Green |
| Full repository suite | 5 529 + 1 skip | 0 | Green |
| Ruff undefined-name gate | — | 0 | Green |

`artifacts/e2e_runs.json` фиксирует три чистых orchestrator run: по 179 событий,
`ok=true`, один и тот же report hash.

## Проверенное качество

- 14-field schema и JSON/CSV round trip;
- variation/noise/separation/low-evidence mining cases;
- BudgetGuard boundaries;
- safety negative cases;
- flagship validation, covenant, stop factor, approval rejection;
- generated skill tree, promotion gate, rollback;
- isolated complete E2E.

## Проверенное представление

- живой browser E2E прошёл весь guided path без console errors;
- девять server-backed UI-кадров сохранены в `submission/screenshots/`;
- MP4 декодируется end-to-end, длится 164,112 с и содержит video/audio/subtitle streams;
- PDF проходят render-to-PNG QA после каждой финальной сборки.

Непроверенными остаются production data drift, реальные connectors и production IAM/DLP.

## Metric credibility

Mining 1,00/1,00/0,00 — calculated on synthetic ground truth. AS IS 39:42,5 — simulated
event durations. TO BE 18:00 — scenario assumption. `0.08 s` — deterministic sandbox
field, not business wall-clock. Demo runtime paid cost 0 USD — local ledger only.
