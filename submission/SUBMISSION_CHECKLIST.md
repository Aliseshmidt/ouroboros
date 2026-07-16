# Чек-лист отправки

Легенда: `[x]` есть локально; `[ ]` отсутствует или не подтверждено.

## Markdown-пакет

- [x] `MVP_REPORT.md`
- [x] `DEMO_SCRIPT.md`
- [x] `VOICEOVER_TEXT.md`
- [x] `STORYBOARD.md`
- [x] `TEST_EXAMPLES.md`
- [x] `QUALITY_REPORT.md`
- [x] `ARCHITECTURE.md`
- [x] `AS_IS_TO_BE.md`
- [x] `SECURITY_REPORT.md`
- [x] `PATTERN_MINING_REPORT.md`
- [x] `EVOLUTION_REPORT.md`
- [x] `JURY_SCORECARD.md`
- [x] `KNOWN_LIMITATIONS.md`

## Обязательные бинарные материалы

- [x] `MVP_REPORT.pdf`
- [x] `TEST_EXAMPLES.pdf`
- [x] `QUALITY_REPORT.pdf`
- [x] `ARCHITECTURE.pdf`
- [x] `AS_IS_TO_BE.pdf`
- [x] `DEMO_VIDEO.mp4`
- [x] Русская аудиодорожка
- [x] Читаемые русские субтитры
- [x] `screenshots/`

## Code/evidence

- [x] `artifacts/hackathon_e2e.json` существует
- [x] `artifacts/test_results.json` отражает текущий green local-gate status
- [x] Generated Skill tree существует
- [x] v1/v2 и rollback history существуют в baseline
- [x] Исправлен determinism test
- [x] Focused suite 42/42, включая checked-in generated Skill
- [x] Три последовательных clean E2E runs
- [x] E2E artifact пересоздан после исправления
- [x] Generated checked-in skill test отдельно включён в focused run
- [x] Broader tests/lint green: 5 530 collected, 0 failed; Ruff F clean
- [x] Browser smoke/E2E green

## Security/legal

- [x] Все demo business data synthetic
- [x] Mock actions не делают external writes
- [x] Credit decision blocked by policy/test
- [x] Whole-repository common secret-pattern scan
- [x] Submission PII/secret scan
- [x] PDF metadata scan
- [x] Video frame/audio/subtitle review
- [x] Dependency/licence inventory (one undeclared metadata item documented)
- [ ] Public repository accessibility confirmed
- [x] Demo requires no paid proprietary runtime; paid API cost 0 USD

## Video verification

- [x] Duration <180 s: 164,112 s
- [x] Video stream exists: H.264, 1920×1080, 30 fps
- [x] Audio stream exists: AAC mono
- [x] File decodes end-to-end
- [x] Text legible in sampled frames
- [x] No broken UI or empty screens
- [x] No unsupported integration claims
- [x] Mock/synthetic labels visible

## Submission operations

- [ ] Team captain verifies final package
- [ ] Final email assembled
- [ ] Early submission timestamp planned
- [ ] Submission sent by captain
- [ ] Receipt/timestamp retained

Отправка email и публикация репозитория — внешние действия владельца/капитана и этим
локальным пакетом не выполняются.
