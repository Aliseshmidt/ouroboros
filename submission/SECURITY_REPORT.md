# Отчёт по безопасности

## Принцип

Агент не получает дополнительных прав и работает только в synthetic/mock-контуре.
Финальное решение, отправка, публикация и необратимые действия остаются у человека.

## Подтверждено focused tests

- prompt injection определяется как недоверенные данные;
- secret-like field/value обнаруживаются;
- email и телефон редактируются;
- запрос вне allow-list отклоняется;
- `make_credit_decision` блокируется даже при approval/A4;
- approved mode без receipt отклоняется;
- неизвестная цена и превышение бюджетов блокируются;
- dossier output не содержит внешних записей.

## Сохранённый E2E baseline

| Показатель | Значение | Класс |
|---|---:|---|
| Заблокировано prohibited events | 1 | Синтетическая симуляция |
| PII leakage rate | 0,0 | Валидатор synthetic trace, не production DLP |
| External writes | 0 | Mock execution |
| Demo runtime paid cost | 0 USD | Local deterministic ledger only |

## Approval

Receipt связывает proposal id, skill id, version 2.0.0, synthetic employee, scope,
content hash, input hash, action-plan hash и expiry. Повторное использование,
просрочка и подмена input блокируются tests. Persisted top manifest показывает
`approved`.

## Финальный локальный gate

- whole-repository/submission secret and PII scan выполняется перед commit;
- PDF metadata и sampled video frame проверены;
- dependency inventory сохраняется рядом с test evidence;
- evidence о 42/42 focused tests, 8/8 UI/API и трёх clean E2E runs входит в пакет.

Реальный RBAC/DLP/OAuth connector test не выполнялся: это честно ограниченный mock-контур.

## Вывод

Локальные security primitives, ключевые negative tests и media gate подтверждены;
production security этим MVP не заявляется.
