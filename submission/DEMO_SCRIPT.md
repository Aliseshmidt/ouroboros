# Сценарий демонстрации

**Статус:** сценарий исполнен в живом UI; финальный ролик — честно маркированный монтаж
из кадров server-backed E2E, а не непрерывная запись экрана.

Целевая длительность: 150–175 секунд, строго меньше 180 секунд.

## Подготовка

1. Подтвердить сохранённые 42/42 focused tests и три clean E2E run.
2. Проверить UI, отсутствие PII/secrets и маркировку mock.
3. Сбросить demo state в известное начальное состояние.

## Путь оператора

| Время | Действие | Что показать | Evidence status |
|---|---|---|---|
| 0–15 | Открыть landing | Проблема персональной рутины | Browser E2E verified |
| 15–32 | Импортировать demo trace | Synthetic label, 14 fields, 10 дней, count | Browser E2E verified |
| 32–52 | Запустить miner | Три паттерна, frequency/time/confidence/risk | Browser E2E verified |
| 52–70 | Открыть flagship hypothesis | Stable/variable steps и human controls | Browser E2E verified |
| 70–98 | Подтвердить hypothesis | Реальное дерево Skill v1/v2 | Browser E2E verified |
| 98–120 | Запустить sandbox | v1 diff, v2 match, checks | Browser E2E verified |
| 120–143 | Approval и исполнение | Bound receipt и approved mock run | Browser E2E verified |
| 143–160 | Показать evolution | Root cause, v2, promotion, rollback | Browser E2E verified |
| 160–175 | Открыть value dashboard | Simulated vs target labels | Browser E2E verified |

## Контрольные реплики оператора

- Всегда говорить «синтетические данные» и «mock-интеграция».
- Не говорить «production accuracy» для precision/recall 1,00.
- Не говорить «измеренная экономия 21:42,5»: это расчёт на симуляции.
- Не называть actor labels доказательством live A2A delegation.
- Не говорить, что email отправлен: создаётся только черновик.
- Не говорить, что система принимает кредитное решение.

## Финальная проверка файла

Для воспроизводимой проверки MP4:

```bash
ffprobe -v error -show_entries format=duration -show_streams submission/DEMO_VIDEO.mp4
ffmpeg -i submission/DEMO_VIDEO.mp4 -vf fps=1/15 tmp/demo-frame-%02d.png
```

Проверить video+audio streams, duration <180 s, субтитры, читаемость, отсутствие
секретов/PII/уведомлений и соответствие каждого кадра реальному прогону.
