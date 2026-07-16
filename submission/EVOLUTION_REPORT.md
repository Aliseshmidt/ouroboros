# Отчёт об эволюции микронавыка

## Область

Эволюция относится только к синтетическому микронавыку клиентского мини-досье. Она
не изменяет Ouroboros core и не выполняет production deployment.

## Контролируемый дефект v1

Версия 1.0.0 рассчитывает debt/revenue и проверяет ковенант, но намеренно не сравнивает
выручку финансового отчёта и выписки.

На кейсе `credit_demo_001`:

- expected: одно противоречие выручки;
- actual: пустой список противоречий;
- expected/actual check: failed;
- schema, no-writes и human-final-decision checks: passed.

## Root cause и v2

Root cause в audit: `v1 omitted cross-document revenue comparison`.

Версия 2.0.0 добавляет сравнение `financial_report.revenue` и
`account_statement.reported_revenue` с порогом разницы. На том же кейсе expected и
actual совпали, diff пуст.

| Метрика | v1 | v2 | Тип |
|---|---:|---:|---|
| Expected/actual match | 0 | 1 | Synthetic single-case test |
| Contradiction detected | 0 | 1 | Synthetic single-case test |
| External writes | 0 | 0 | Mock execution |
| Final decision with human | Да | Да | Policy/test |

## Promotion и rollback

Сохранённая lifecycle history:

1. generated 1.0.0;
2. generated 2.0.0;
3. approved 2.0.0;
4. promoted 2.0.0;
5. rolled back 2.0.0 → 1.0.0;
6. promoted 2.0.0.

Rollback проверен lifecycle и записан в E2E artifact. Top-level generated
`manifest.yaml` синхронизирован со статусом `approved`.

## Ограничения доказательства

- before/after показан на одном flagship-кейсе;
- нет отдельного 10+/20-case regression report по v1/v2;
- независимый Quality Reviewer представлен ролью в последовательном orchestrator, а
  не доказанным live-subagent trace;
- receipt expiry, single-use и input/action-plan binding проходят focused tests;
- focused suite 42/42 и три clean deterministic E2E run зелёные.

## Итог

Механизм controlled defect → root cause → v2 → promotion → rollback реализован и
локально воспроизводится на синтетике в трёх чистых прогонах. Production-grade
evolution не подтверждена.
