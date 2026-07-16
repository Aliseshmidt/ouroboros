# Известные ограничения

1. **Только синтетические данные.** Ни один показатель не подтверждён на реальных
   банковских процессах, сотрудниках или клиентах.
2. **Focused scope ограничен.** 42/42 domain/generated-Skill tests, 8/8 UI/API tests и
   три clean E2E run зелёные; это не заменяет production validation.
3. **Baseline synthetic-only.** Fresh artifact содержит 179 синтетических событий и
   не доказывает production behavior.
4. **Видео — evidence montage.** MP4 смонтирован из кадров реального server-backed
   browser E2E, а не является непрерывной записью экрана; озвучка и soft-subtitles есть.
5. **PDF и скриншоты локальные.** Они проверяют представление MVP, но не доказывают
   доступность публичного репозитория.
6. **UI проверен на одном окружении.** Browser E2E пройден локально; кросс-браузерная
   матрица и accessibility audit не выполнялись.
7. **Интеграции mock.** Нет Outlook/Jira/CRM/BPM/BI/SharePoint writes, OAuth, real RBAC
   или production DLP.
8. **Нет внешнего A2A.** Actor labels в audit — последовательные доменные роли, не
   доказательство live subagents. External A2A interoperability не заявляется.
9. **Approval остаётся demo-bound.** Receipt имеет expiry, single-use и
   input/action-plan binding, но использует синтетическую identity и фиксированный
   demo clock вместо production IAM/time source.
10. **Active state локальный.** Manifest approved, а promotion/rollback подтверждены
    локальным lifecycle; production skill-loader deployment не выполнялся.
11. **Evolution evidence узкое.** Rich before/after diff показан на одном synthetic
    flagship case, не на полном regression basket.
12. **Mining metrics synthetic-only.** Precision/recall 1,00 не являются production
    accuracy; confidence heuristic и не калиброван как вероятность.
13. **Value simulated.** 39:42,5 — synthetic AS IS; 18:00 — scenario assumption; 21:42,5 —
    вычисленная разница, не measured returned time.
14. **`0.08 s` не wall-clock.** Это детерминированное тестовое поле sandbox.
15. **Budget scope узкий.** 0 USD относится к local demo ledger, а не ко всей стоимости
    разработки/агентов.
16. **Scans статические.** Whole-pack secret/PII и metadata scans не заменяют
    production DLP, SCA или юридический review лицензий.
17. **Public repo не подтверждён.** Доступ жюри и clean-start instructions требуют
    отдельной проверки.
18. **GigaAgent mapping архитектурный.** Центральная роль Ouroboros доказана форматом
    Skill, lifecycle, audit, approval и rollback, но live internal delegation не заявляется.

Внешняя отправка, публикация репозитория и проверка доступности остаются действиями
капитана команды.
