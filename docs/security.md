# Security Model for Personal Micro-Automation

This is the hackathon-domain security design. The canonical Ouroboros runtime safety
architecture remains in [`ARCHITECTURE.md`](ARCHITECTURE.md), and implementation
status remains in [`HACKATHON_REQUIREMENTS.md`](HACKATHON_REQUIREMENTS.md).

## Security objective

The agent receives no privileges beyond the employee's existing permissions. It may
observe approved metadata, transform permitted data locally, and prepare drafts. A
consequential action requires a reviewed capability, an explicit permission grant,
and approval of the exact action plan.

Jury-facing statement:

> **Принцип безопасности:** агент не получает дополнительных прав. Он работает
> только в контуре разрешений сотрудника, не сохраняет исходный цифровой след,
> показывает план и изменения до запуска и не выполняет критические действия без
> явного подтверждения.

## Status boundary

**Observed in the current extension:** bounded input size, a six-field allow-list,
secret-like field rejection, local state written with restrictive permissions,
synthetic fixtures, exact confirmation phrase, and draft-only execution with an empty
external-write list.

**Planned and not yet evidence-backed:** the required 14-field validator, PII/DLP
scanners, approval receipts bound to version/input/plan/expiry, RBAC enforcement,
prompt-injection tests, supply-chain report, domain BudgetGuard, container/process
isolation, real MCP connectors, and rollback evidence.

The existing `verify_skill` check is a deterministic historical-case validator. It
must not be described as an OS sandbox.

## Trust boundaries

1. **Untrusted trace and document data.** Content is data, never an instruction to
   the agent. Parsing is schema-first; unknown fields are rejected or redacted.
2. **Extension boundary.** The extension receives only declared grants and uses host
   routes/tools. It must not collect provider or connector credentials itself.
3. **Generated-skill boundary.** A generated payload is non-executable until
   preflight, independent review, owner enablement, and permission grants succeed.
4. **Connector boundary.** OAuth, source ACL, RBAC, DLP, and immutable audit remain
   enforced by the corporate connector. **Mock in MVP.**
5. **Human boundary.** Approval is a specific authorization, not a conversational hint.
6. **Evidence boundary.** A claim is valid only when linked to a test, log, receipt,
   screenshot, generated artifact, or measurement.

## Data policy

| Data class | MVP handling | Durable retention |
|---|---|---|
| Synthetic event trace | Local validation and feature extraction | Raw trace should be discarded after the run |
| Real employee/client data | Prohibited in the submission MVP | None |
| Pattern aggregate | Frequency, duration, stable/variable steps, confidence | Allowed without personal identifiers |
| Generated skill | Versioned files, policy, tests, hashes | Allowed in private/demo state |
| Approval | Exact version/input/plan binding | Planned audit receipt |
| Secrets and credentials | Rejected from payloads; never shown in UI/video | None |
| Logs and evidence | Redacted, bounded, provenance-labelled | Private artifact store/submission package |

The submission scan must include code, git history intended for publication, JSON,
PDF metadata, screenshots, filenames, logs, subtitles, and sampled video frames.

## Authorization and autonomy

| Level | Meaning | MVP rule |
|---|---|---|
| A0 | Observation only | Allowed for synthetic/read-only inputs |
| A1 | Recommendation | Default for newly detected patterns |
| A2 | Draft generation | Allowed after policy checks |
| A3 | Execution after explicit approval | Limited to deterministic demo/draft behavior |
| A4 | Pre-authorized autonomous low-risk execution | Out of scope |

Critical operations—send, submit, approve, pay, delete, publish, permission changes,
and source-record writes—remain blocked in the MVP.

## Approval contract

**Planned acceptance condition:** an approval receipt contains:

- proposal and skill identifiers;
- exact skill version and payload hash;
- normalized input hash;
- action plan and expected diff hash;
- required tool/permission set;
- risk level and cost ceiling;
- approver identity reference without submission PII;
- issued-at, expiry, and single-use nonce.

Any input, version, plan, permission, expected diff, or expiry change invalidates the
receipt. Rejection, replay, or absence fails closed. The current confirmation phrase
does not yet meet this stronger contract.

## Layered controls

### Input and privacy

- Strict schema and size/count limits.
- Synthetic identifiers in all demo assets.
- Field allow-list; unknown metadata quarantined or rejected.
- PII and secret detection before persistence and before artifact export.
- Minimum necessary retention: aggregates and hashes instead of raw content.

### Prompt injection

- External text remains quoted/untrusted data, never policy or tool instruction.
- Deterministic extraction precedes any model classification.
- Tool and operation allow-lists are host policy, not prompt text.
- Test cases include malicious document instructions and data-exfiltration requests.

### Tool and connector policy

- Read-only/mock adapters by default.
- Connector scopes cannot exceed the employee's ACL.
- External writes require a visible diff and fresh approval.
- No connector is described as live until authenticated integration evidence exists.

### Code and supply chain

- No hardcoded keys, passwords, tokens, or credential-shaped samples.
- Prefer repository and standard-library dependencies for the offline demo.
- Record licences and reject prohibited paid proprietary runtime dependencies.
- Generated code passes static checks, schema validation, tests, and independent Skill
  review before enablement.

### Runtime and audit

- Deterministic core sandbox/protected-path guards remain enabled in every safety mode.
- The owner controls safety coverage; the agent does not lower it.
- Every relevant tool call, approval decision, execution step, result, and rollback is
  expected to have a timestamped evidence reference.
- `/panic` remains the host-wide emergency stop.

### Budget

The hackathon domain requires a hard USD 5.00 cap, an operational cap of USD 4.50,
and a USD 0.50 final-verification reserve. The deterministic demo should make zero
paid calls. **Planned:** a BudgetGuard rejects unknown or unsafe estimates and writes
the submission ledger. Core usage accounting remains the monetary authority; the
domain guard narrows it and never replaces or weakens it.

## Threat-to-control matrix

| Threat | Required control | Evidence placeholder |
|---|---|---|
| PII in trace or output | Schema allow-list, redaction, PII scan | `artifacts/security_report.md` PII cases |
| Credential leak | Secret scanner and whole-pack scan | Zero-findings scan log |
| Prompt injection | Data/instruction separation and hostile fixture | Blocked test receipt |
| Permission escalation | RBAC plus tool/operation allow-list | Out-of-scope request test |
| Approval bypass/replay | Bound, expiring, single-use receipt | Negative integration tests |
| Unsafe generated code | Preflight, independent Skill review, grants | Review verdict and payload hash |
| Uncontrolled external write | Mock/read-only adapter and draft-only mode | `outbound_writes: []` plus tests |
| Cost overrun | Conservative BudgetGuard | Budget block test and ledger |
| Regression after evolution | Same-basket comparison and rollback | v1/v2/rollback report |
| Proprietary dependency conflict | Licence inventory | Submission dependency report |

## Residual limitations

- Synthetic data cannot validate production DLP or enterprise RBAC behavior.
- No live connector means production OAuth, revocation, audit retention, and source ACL
  enforcement are architectural contracts only.
- In-process deterministic verification is useful evidence but not strong isolation.
- Redaction and secret scanning remain planned until their reports and negative tests
  exist.
- The demo must say “черновик” and “mock-интеграция” wherever no real action occurs.
