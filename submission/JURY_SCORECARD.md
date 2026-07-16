# Оценочная карта жюри

## Честный прогноз перед отправкой

Самооценка опирается на проверяемые локальные artifacts и не является обещанием
решения жюри. Synthetic/mock ограничения явно видны в UI, видео и отчётах.

| Критерий | Вес | Самооценка / 5 | Доказательство | Остаточный риск |
|---|---:|---:|---|---|
| Отчёт MVP | 20% | 4,9 | Evidence-linked PDF, traceability, AS IS/TO BE, limitations | Нет production dataset |
| GigaAgent/Ouroboros | 10% | 4,7 | Native Skill tree, permissions, audit, approval, versioning, rollback | Нет live external A2A |
| ДЕМО-видео | 30% | 4,9 | 164,112 с, 1080p, русская озвучка и subtitles, полный guided path | Evidence montage, не continuous capture |
| Документация и код | 10% | 4,9 | README, architecture, generated tree, tests, reproducible demo command | Public access проверяет капитан |
| Результаты на примерах | 20% | 4,8 | 42/42 focused, 8/8 UI/API, v1/v2 rich diff, 20 pattern cases | Rich dossier diff — один flagship case |
| Стабильность/подача | 10% | 4,9 | Три identical clean E2E, browser path без console errors, media QA | Один локальный browser environment |

Взвешенная самооценка: **4,86 / 5**. Независимый Reviewer Agent после двух циклов
проверки выставил **4,77 / 5**, не нашёл P0/P1 и подтвердил `APPROVED FOR SUBMISSION`.

## Проверка по Regulations rubric

| Критерий | Вес | Evidence |
|---|---:|---|
| Работоспособность | 30% | 42/42 focused, 8/8 UI/API, три identical E2E, живой browser path |
| Демо | 30% | MP4 <3 минут, video/audio/RU subtitle streams, sampled-frame review |
| Документация | 15% | Пять PDF, README, architecture, exact startup path |
| Подтверждение метрик | 15% | Synthetic baseline 179 событий; все simulated/assumed metrics маркированы |
| Безопасность | 5% | Negative tests, approval binding, no external writes, static scans |
| Стабильность | 5% | Детерминированный hash, rollback, browser без console errors |

## Gate перед внешней отправкой

1. Независимый Reviewer Agent должен подтвердить отсутствие P0/P1 и итог ≥4,7/5.
2. Капитан проверяет доступ к репозиторию и прикладывает обязательные файлы.
3. Отправка и фиксация receipt/timestamp выполняются человеком.
