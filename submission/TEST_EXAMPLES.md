# Примеры и тестовая корзина

## Статус

Все входы синтетические. Проверка 17.07.2026: 42 focused tests собрано, 42 прошло.
Три clean E2E run дали одинаковый report hash.

| № | Сценарий | Ожидаемое поведение | Текущий результат |
|---:|---|---|---|
| 1 | Полная 14-полевая схема | Все поля присутствуют | Passed |
| 2 | Пропущен `employee_id` | Явный schema error | Passed |
| 3 | JSON round trip | События совпадают | Passed |
| 4 | CSV round trip | События совпадают | Passed |
| 5 | ≥7 рабочих дней | Dataset accepted | Passed |
| 6 | Variations/noise/failure/prohibited | Все классы есть | Passed |
| 7 | Три повторяющихся паттерна | Найдены 3 | Passed |
| 8 | Optional correspondence step | Flagship остаётся одним кластером | Passed |
| 9 | Случайный шум | Не попадает в паттерны | Passed |
| 10 | Два похожих draft-flow | Разделены | Passed |
| 11 | Недостаточная частота | Паттерн не создаётся | Passed |
| 12 | Synthetic mining metrics | 1/1/0 на ground truth | Passed |
| 13 | Unknown pricing | BudgetGuard block | Passed |
| 14 | Operational cap exhausted | Nonessential request blocked | Passed |
| 15 | Emergency reserve | Только final verification | Passed |
| 16 | Hard budget >5 USD | Block | Passed |
| 17 | Prompt injection | Finding `prompt_injection` | Passed |
| 18 | Secret field/value | Finding `secret` | Passed |
| 19 | Email/phone | Redaction | Passed |
| 20 | Ресурс вне ACL | Denied | Passed |
| 21 | Credit decision | Block даже с approval | Passed |
| 22 | Полный dossier input | Evidence-backed draft, no writes | Passed |
| 23 | Нет account statement | Loud missing-document error | Passed |
| 24 | v1 controlled defect | Expected/actual mismatch | Passed |
| 25 | v2 correction | Empty diff | Passed |
| 26 | Covenant violation | Flag present | Passed |
| 27 | Stop factor | Flag present | Passed |
| 28 | Invalid input type | Loud error | Passed |
| 29 | Approved execution without receipt | Block | Passed |
| 30 | Generated skill tree | Required entries present | Passed |
| 31 | Generated manifest least privilege | Executable Skill contract and minimal permissions | Passed |
| 32 | Generated script fixture | Script detects contradiction | Passed |
| 33 | Complete version snapshot | Rollback files are present | Passed |
| 34 | Promotion without approval | Block; exact approval required | Passed |
| 35 | Rollback | v1 restored in lifecycle | Passed |
| 36 | Complete E2E | `ok=true`, 3 patterns, v2 active | Passed |
| 37 | Two clean deterministic runs | Reports identical | Passed |
| 38 | Guided stateful workflow | Ordered workflow state works | Passed |
| 39 | Guided repair before approval | v1 repaired before UI approval | Passed |
| 40 | Checked-in generated Skill | Fixture executes, no external writes | Passed |
| 41 | Approval expiry/replay/input-plan binding | Expired/replayed receipt blocked | Passed |
| 42 | Receipt bound to different input | Changed input rejected | Passed |

## Flagship expected/actual

### Version 1.0.0

Expected contradictions:

`revenue differs between financial report and account statement`

Actual contradictions: empty. Result: failed by design.

### Version 2.0.0

Expected and actual match:

- debt/revenue: 0,68;
- available limit: 8,0;
- one revenue contradiction;
- covenant violation;
- no stop factor in base case;
- no external writes;
- final decision remains with employee.

## Ограничения

- Rich expected/actual artifact показан для одного flagship-кейса; регуляторный порог
  10+ примеров нужно оформить отдельным итоговым report.
- Checked-in generated skill включён в focused run и дополнительно исполняется fixture-тестом.
- UI/static/API: 8/8; PDFs и video прошли render/decode verification.
