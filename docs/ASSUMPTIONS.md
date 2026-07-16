# Hackathon Assumptions and Decisions

1. The one-page Project Results scorecard and the regulations conflict. The MVP satisfies the union of both rubrics; the scorecard's 20/10/30/10/20/10 weights drive prioritization.
2. All employee, client, document, account, email, and task data is synthetic. It models a real process shape but is not evidence collected from a Bank system.
3. The existing untracked `skills/personal_evolution_engine/` directory is treated as a user-provided prototype. Its privacy and explicit-approval behavior will be preserved while its exact-signature mining and dictionary-only skill generation are replaced or extended.
4. No real corporate connector is required for the MVP. Mail, document store, CRM, BPM, BI, spreadsheets, and task tracker are deterministic mock adapters and are visibly labeled as such.
5. The product never makes a credit decision. It prepares evidence, calculations, risk flags, a task draft, and an email draft for an authorized employee.
6. Pattern detection is deterministic and independent of an LLM. Language-model classification may improve naming in a future pilot but is not required for demo correctness.
7. The generated runtime skill lives in private/demo state during execution and is exported to `skills/generated/<skill_id>/` as submission evidence. An enabled skill must not rewrite its own reviewed repository payload.
8. The canonical architecture file is `docs/ARCHITECTURE.md`. On the default macOS case-insensitive filesystem, the requested `docs/architecture.md` cannot coexist as a separate file; hackathon details will live in `docs/HACKATHON_ARCHITECTURE.md` and the canonical map will link to it.
9. The stricter USD 5.00 BudgetGuard is a hackathon-domain rail layered over Ouroboros's existing physical-attempt ledger; it does not weaken or replace core accounting. The deterministic demo makes no paid model calls.
10. The 45-minute AS IS, 18-minute target TO BE, and 27-minute potential saving are Proposal targets, not measured MVP results. Measured, simulated, estimated, and target metrics will be labeled separately.
11. The current Ouroboros repository provides internal subagent scheduling and task-tree communication, but no bundled external A2A transport. The demo may evidence internal role delegation; it will not claim external A2A interoperability without an installed reviewed transport skill.
12. Repository publication, email submission, and any irreversible external action require the user's authority and are outside this autonomous local build.
13. A Russian local system voice is acceptable for the required narrated demo; subtitles remain embedded and human-readable even if voice quality varies by host.
14. The final package will include synthetic test evidence because real banking data is explicitly out of scope. This limitation will be stated prominently rather than hidden.
