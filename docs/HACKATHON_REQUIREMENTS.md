# Sber AI Hack Requirements Matrix

Final local evidence status on 17 July 2026. `Verified` means reproducibly checked in
the local synthetic/mock scope; it does not imply production validation.

| ID | Criterion | Weight/gate | Evidence | Status | Honest residual risk |
|---|---|---:|---|---|---|
| DEMO-01 | Demo video | 30% | `submission/DEMO_VIDEO.mp4`: 164.112 s, H.264/AAC/RU subtitles; sampled frames | Verified | Evidence montage, not continuous capture |
| MVP-01 | MVP report | 20% | `submission/MVP_REPORT.pdf`, traceability and limitations | Verified | No production dataset |
| EX-01 | Results on examples | 20% | 42 core/generated-Skill tests, 8 UI/API tests, v1/v2 diff, 20 pattern cases | Verified | Rich dossier diff covers one flagship case |
| OBR-01 | GigaAgent/Ouroboros role | 10% | Native Skill tree, permissions, audit, approval, versioning, evolution, rollback | Implemented | Domain roles run deterministically in one process; no live A2A claim |
| CODE-01 | Documentation and code | 10% | README quick start, `make demo`, architecture, tests, generated files | Verified locally | Public accessibility is a captain action |
| STAB-01 | Stability and presentation | 10% | 3 identical E2E runs, 5,530-test suite green, browser path, nine screenshots | Verified | One local browser environment |
| FUNC-01 | End-to-end functionality | Gate | Trace -> patterns -> hypothesis -> Skill -> sandbox -> approval -> execution -> value | Verified | Connectors are mock |
| DOC-01 | Reproduction path | Gate | Fewer than five commands; no mandatory provider key | Verified locally | Fresh external machine not separately provisioned |
| MET-01 | Metric confirmation | Gate | Provenance labels in value artifacts and AS IS/TO BE PDF | Verified | Production effect not measured |
| SEC-01 | Security | Gate | Injection/secret/PII/ACL/action/approval/budget tests and static scans | Verified locally | Not production DLP/IAM |
| TRACE-01 | 14-field JSON/CSV trace | Gate | 179 events, 10 working days, schema/round-trip tests | Verified | Synthetic only |
| PM-01 | Pattern Miner | Gate | 3 clusters, variations/noise/separation/low-evidence tests | Verified | Metrics use embedded ground truth |
| HYP-01 | Automation hypothesis | Gate | Frequency/duration/steps/confidence/risk/source pattern in API/UI | Verified | Heuristic confidence is not calibrated probability |
| SKILL-01 | Versioned Micro-Skill generation | Gate | Complete executable on-disk tree with v1/v2 snapshots | Verified | One flagship generated Skill |
| SBOX-01 | Sandbox | Gate | Expected/actual/rich diff, v1 failure, v2 pass, no external writes | Verified | Single rich flagship fixture |
| APP-01 | Human approval | Gate | Expiry, single-use, version/content/input/action-plan binding tests | Verified | Demo identity and clock |
| EXEC-01 | Credit dossier | Gate | Calculations, contradiction, covenant, drafts, human final decision | Verified | Synthetic/mock sources |
| EVO-01 | Safe evolution | Gate | Controlled defect, repair, regression, promotion, rollback | Verified | Narrow regression basket |
| VAL-01 | Business value | Gate | Measured/simulated/assumed/target values separated | Verified | Returned time is calculated on simulation |
| BUD-01 | USD 5 cap | Gate | 5.00/4.50/0.50 BudgetGuard and 0 USD ledger | Verified | Ledger covers demo runtime only |
| GEN-01 | Generality | Gate | Same miner detects dossier, email-to-task and weekly-report flows | Verified | Profession-specific demo framing |
| LIC-01 | Dependency rights | Gate | `artifacts/dependency_inventory.md` | Verified with note | `tree-sitter` metadata omitted a license expression |
| PII-01 | No submission PII/secrets | Gate | Synthetic identifiers, static scan, PDF/video metadata review | Verified locally | Static scan is not production DLP |

## Submission timing

The regulations set the Project Results deadline at 20 July 2026, 23:59 Moscow time.
Equal scores are ordered by email submission time. Publication, repository access
verification, email submission, and receipt retention remain captain actions.
