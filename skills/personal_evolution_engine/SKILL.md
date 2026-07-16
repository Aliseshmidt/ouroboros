---
name: personal_evolution_engine
description: Privacy-preserving personal-process discovery, approval-gated micro-skill generation, and feedback-driven evolution.
version: 1.0.0
type: extension
entry: plugin.py
runtime: python3
timeout_sec: 60
permissions: [fs, tool, route, widget]
when_to_use: Discover repetitive employee workflows from an anonymized event trace, propose a reusable micro-skill, verify it on history, and run an approval-gated draft.
---

# Personal Evolution Engine

This extension turns a permitted, anonymized activity trace into safe personal
automation candidates for any profession. It deliberately learns the workflow,
not an employee's private content: raw events are never persisted; only aggregate
signatures, counts, and non-sensitive test fingerprints are retained.

The closed loop is:

1. Observe read-only events from approved connectors.
2. Discover repeated cross-system workflows and calculate a transparent time-saving hypothesis.
3. Propose a non-executable micro-skill with integration scope, tests, and an autonomy policy.
4. Verify it in a deterministic sandbox against at least ten historical cases.
5. Require explicit `APPROVE <proposal_id>` before an approved draft run.
6. Learn from employee feedback by adjusting only recommendation ranking; it never self-grants access, changes code, or performs unapproved writes.

`demo_trace` creates 36 fully anonymized examples (12 for each of three
industry-agnostic workflow patterns), so a full end-to-end demo can meet the
hackathon evidence threshold without live banking data. Read
[`README.md`](README.md) for the four-step demo and [`INTEGRATIONS.md`](INTEGRATIONS.md)
for the MCP integration design.
