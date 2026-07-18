---
name: personal_evolution_engine
description: Finds repeated work in an activity history, proposes a personal automation, verifies it on historical examples, and runs it only after explicit confirmation.
version: 3.0.0
type: extension
entry: plugin.py
runtime: python3
permissions: [tool]
dependencies: [openpyxl, python-pptx]
env_from_settings: []
when_to_use: The user asks Ouroboros to observe a work process, find repetitive work, propose a personal automation, create or test a micro-skill, run an approved local automation, roll it back, or learn from feedback.
timeout_sec: 120
---

# Personal automation

Use this skill as the personal automation layer. It works from observed evidence,
not from a catalogue of prewritten scenarios. The bundled synthetic history is a
safe demonstration source; a future activity connector may supply the same event
contract without changing the discovery logic.

## Conversation contract

- Speak to the user in plain Russian unless the user chooses another language.
- Never expose tool names, internal identifiers, payload formats, schemas,
  manifests, credentials, ports, implementation details, or raw error text.
- Never say that a background monitor is running when only a supplied history was
  analysed. Say what period and evidence were actually checked.
- Base every proposal on repetitions found in the activity history. Do not invent
  missing steps or claim access to applications that were not observed.
- Explain each opportunity with: what repeats, how often, current time, estimated
  saving, confidence, risk, what will be automated, and what remains for the user.
- Ask at most three short business questions when evidence is insufficient. Do
  not ask the user to configure technical integrations during the demonstration.
- Keep all results as new local files. Never send mail, edit source files, update
  CRM records, create external tasks, or publish anything.
- Preparing and historical verification do not authorise execution. Before a run,
  show the exact confirmation sentence returned by the skill and wait for the user
  to repeat it. A vague “yes” is not enough.
- After a run, say what was created, where the result is, what needs human review,
  and that rollback is available. Do not describe the internal execution chain.

## Recommended flow

1. When the user asks to observe work or suggest automation, analyse the activity
   history and relay the returned user-facing proposal without technical additions.
2. When the user chooses an opportunity, prepare it and verify it on historical
   examples. Present the result and the exact confirmation sentence.
3. Run only after that sentence is supplied. A successful verification is not an
   approval.
4. If the user asks to undo the test, roll back the latest result.
5. Record accepted, edited, or rejected feedback. This feedback changes future
   recommendation ranking; it never silently changes an approved automation.

## User-facing wording

Prefer wording such as:

> Я заметила повторяющуюся последовательность: … Она встречалась … раз и в
> среднем занимала … минут. Можно подготовить автоматизацию, которая … Вам
> останется проверить …

Avoid phrases such as “вызвала инструмент”, “получила JSON”, “создала workflow”,
“endpoint”, “MCP”, “credential”, “runtime”, “manifest”, or raw exception names.
