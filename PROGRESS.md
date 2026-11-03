# Progress

Updated at the end of every session (`milestone-close` skill). This file is the project's memory across sessions.

## Status
| Milestone | State | Verified in CI | PR |
|---|---|---|---|
| M0 Scaffold | not started | – | – |
| M1 Fault library (12 → 20) | not started | – | – |
| M2 Agent + tools | not started | – | – |
| M3 Harness | not started | – | – |
| M4 Evals + CI gate | not started | – | – |
| M5 Observability + replay | not started | – | – |
| M6 Red-team | not started | – | – |
| M7 Benchmark + write-up | not started | – | – |

## Next
- **M0 + M1.** Then stop and report (see "Session scope rule" in the brief).

## Verified
- (nothing yet)

## Unverified / assumptions
- Docker/kind may not run in cloud sessions → CI (GitHub Actions + kind) is the real test bed.
- Local dev is assumed to be on Linux/WSL2 with Docker, kind, kubectl, uv and python3 installed.

## Open decisions (owner)
- LLM provider and key for M2+ (Anthropic API vs local Ollama).
- Eval accuracy-drop threshold X for the CI gate (M4).

## Log
- 2026-11-03: repo created; Claude Code setup added (CLAUDE.md, skills, agents, hook, brief).
