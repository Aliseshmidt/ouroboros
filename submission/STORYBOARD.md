# Storyboard демонстрационного видео

**Статус:** MP4 собран из девяти кадров фактического server-backed browser E2E.

| Кадр | Время | Визуал | Текст на экране | Доказательство |
|---:|---:|---|---|---|
| 1 | 0–8 | Landing, общий цикл | «Уникальная рутина → безопасный микронавык» | `01_overview.png` |
| 2 | 8–15 | AS IS employee flow | «10–40 минут, слишком мало для RPA-проекта» | `01_overview.png` |
| 3 | 15–25 | Trace upload | «DEMO · полностью синтетические данные» | `02_trace.png` |
| 4 | 25–32 | Schema/count | «14 полей · 10 рабочих дней · 179 событий» | Fresh baseline exists |
| 5 | 32–43 | Pattern feed | Три карточки паттернов | Backend baseline exists |
| 6 | 43–52 | Miner metrics | «Метрики только на synthetic ground truth» | Artifact exists |
| 7 | 52–62 | Mini-dossier hypothesis | 10 повторений, 11 шагов, medium risk | Artifact exists |
| 8 | 62–70 | Human-control block | «Решение и отправка остаются у сотрудника» | Policy/source exists |
| 9 | 70–83 | Generated tree | SKILL.md, schemas, policy, tests | Files exist |
| 10 | 83–98 | Permissions/version | v1/v2, allow/deny, content hash | Files/artifact exist; manifest approved |
| 11 | 98–108 | Sandbox v1 | Красный diff: пропущено противоречие | Artifact exists |
| 12 | 108–120 | Sandbox v2 | Зелёный expected=actual | Artifact exists, one case only |
| 13 | 120–128 | Approval gate | «Hash-bound receipt · TTL» | `06_approval.png`; focused tests |
| 14 | 128–136 | Approval | Version 2.0.0 + content hash + mock scope | Artifact exists |
| 15 | 136–143 | Result | Debt/revenue, limit, contradiction, covenant | Artifact exists |
| 16 | 143–152 | Evolution history | v1 → v2 → rollback → v2 | Artifact exists |
| 17 | 152–165 | Value dashboard | Simulated 39:42,5 → assumed 18:00 | `08_value.png` |
| 18 | 165–175 | Final statement | «Время возвращается, контроль остаётся» | `09_evolution.png` |

## Правила монтажа

- Не показывать терминал дольше необходимого.
- Не подменять работающий UI статичной композицией.
- Маркировать synthetic/mock в каждом релевантном кадре.
- Не скрывать test status: запись разрешена только после green rerun.
- Удалять ожидание монтажом можно; скрывать ошибки нельзя.
- Субтитры должны быть читаемы на итоговом разрешении.
