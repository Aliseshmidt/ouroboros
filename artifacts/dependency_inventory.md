# Dependency inventory — 2026-07-17

The inventory was read from the isolated `.venv` used for the final test run.
It is evidence, not legal advice or a full transitive SCA audit. The hackathon demo
itself performs no provider call and requires no paid proprietary runtime.

| Direct requirement | Resolved | Declared license |
|---|---:|---|
| openai | 2.45.0 | Apache-2.0 |
| gigachat | 0.2.1 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| httpx | 0.28.1 | BSD-3-Clause |
| ddgs | 9.14.4 | MIT |
| dulwich | 1.2.11 | Apache-2.0 OR GPL-2.0-or-later |
| starlette | 1.3.1 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| Pillow | 12.3.0 | MIT-CMU |
| pypdf | 6.14.2 | BSD-3-Clause |
| uvicorn | 0.51.0 | BSD-3-Clause |
| websockets | 16.1 | BSD-3-Clause |
| huggingface-hub | 1.23.0 | Apache-2.0 |
| PyYAML | 6.0.3 | MIT |
| croniter | 6.2.4 | MIT |
| tree-sitter | 0.23.2 | not declared in installed metadata |
| tree-sitter-language-pack | 0.9.1 | MIT OR Apache-2.0 |
| tzdata | 2026.3 | Apache-2.0 |
| pytest | 9.1.1 | MIT |
| pytest-xdist | 3.8.0 | MIT |
| pytest-timeout | 2.4.0 | MIT |
| claude-agent-sdk | 0.2.120 | MIT |
| mcp | 1.28.1 | MIT |
| playwright | 1.61.0 | Apache-2.0 |
| playwright-stealth | 2.0.3 | MIT |

Open item: `tree-sitter` did not expose a license expression in installed package
metadata, so a future distribution/legal review should verify it from the upstream
source. This does not affect the standard-library-only generated micro-skill.
