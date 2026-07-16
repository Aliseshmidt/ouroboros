# Архитектура решения

## Контур

| Этап | Вход → выход | Контроль |
|---:|---|---|
| 1 | Synthetic JSON/CSV → валидированный trace | 14 полей, PII/secret checks |
| 2 | Trace → три повторяемых паттерна | Noise/variation и synthetic ground truth |
| 3 | Паттерн → automation hypothesis | Риск, права, human-controlled steps |
| 4 | Hypothesis → versioned Micro-Skill | Полное дерево файлов и content hash |
| 5 | Skill + fixtures → expected/actual/diff | Sandbox, v1 defect, v2 correction |
| 6 | Reviewed plan → approval receipt | Version/input/action-plan binding, TTL |
| 7 | Receipt → mock task/email drafts | Нет external writes и кредитного решения |
| 8 | Result → value/evolution/rollback | Promotion gate и immutable snapshots |

Все бизнес-данные синтетические, интеграции mock, внешние записи отсутствуют.

## Модули

| Модуль | Назначение | Текущий статус |
|---|---|---|
| `trace.py` | 14 полей, JSON/CSV, synthetic trace | Реализовано; fresh baseline 179 событий |
| `pattern_miner.py` | Сессии, similarity/clustering, метрики | Реализовано на синтетике |
| `safety.py` | Secret/PII/injection/RBAC/action policy | Точечные тесты проходят; final static scan включён в gate |
| `skill_builder.py` | Полное дерево Skill, версии, receipt, rollback | Реализовано; persisted top manifest имеет статус `approved` |
| `dossier.py` | Детерминированные расчёты и mock drafts | Реализовано на synthetic fixture |
| `budget_guard.py` | 5/4,5/0,5 USD limits | Точечные тесты проходят |
| `orchestrator.py` | E2E и audit | Три чистых прогона дали одинаковый report hash |

## Роль Ouroboros

Ouroboros предоставляет базовую модель Skills, safety boundaries, review/grants,
контекст, task execution, audit, budget accounting и rollback. Доменный MVP не создаёт
вторую платформу управления, а формирует capability в формате Ouroboros Skill.

Однако текущая E2E-реализация вызывает доменные модули последовательно. Audit-метки
`Trace Ingestion Agent`, `Safety Agent` и другие — роли процесса, но не доказательство
live scheduling отдельных subagents. Внутренний subagent/task-tree механизм есть в
Ouroboros core; его использование именно этим MVP требует отдельного trace.

## A2A caveat

Поддерживается архитектурная модель внутреннего делегирования Ouroboros. Внешний A2A
transport/interoperability не реализован и не заявляется. MCP — граница инструментов и
коннекторов, а не доказательство A2A.

## Data flow и хранение

1. Trace содержит synthetic ids и минимальные metadata.
2. Miner формирует агрегаты и correlation ids.
3. Builder создаёт Skill files и immutable version snapshots.
4. Sandbox сохраняет expected/actual/diff.
5. Receipt связывает proposal/version/content hash/scope.
6. Execution создаёт только mock task и email draft, `external_writes = []`.
7. Audit хранит 12 последовательных событий сохранённого baseline.

## Границы безопасности

- финальное кредитное решение заблокировано;
- отправка email и реальные source writes отсутствуют;
- реальные client/employee data запрещены;
- source content считается недоверенными данными;
- точечный BudgetGuard уже есть, общая стоимость разработки им не подтверждается;
- approval receipt имеет expiry, input/action-plan binding и single-use enforcement.

## Evidence и границы

- focused suite 42/42 и три deterministic clean run проходят;
- browser/UI E2E и 8/8 UI/API regression tests проходят;
- нет evidence фактического internal subagent delegation;
- нет production connectors;
- PDF/video/screenshots собраны и визуально проверены;
- production security/licence audit остаётся вне границ локального MVP.
