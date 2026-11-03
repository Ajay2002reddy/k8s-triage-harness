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
- 2026-11-03, cloud session environment probe [Verified: ran it]:
  - `dockerd` starts manually (`dockerd &`), and single-level containers work. Docker 29.9.2, cgroup v1.
  - `go install sigs.k8s.io/kind@latest` works (kind v0.33.0); kubectl downloads from dl.k8s.io.
  - **kind cluster creation FAILS**, both on the default image and on `kindest/node:v1.32.2`. Nested runc inside the kind node errors with `can't get final child's PID from pipe: EOF`, so the control-plane pods never start.
  - GitHub release downloads by `/releases/latest` redirect didn't resolve through the proxy; use `go install` or pinned URLs.
- The kube-context hook passes 15 allow/block test cases (run by hand, not yet in CI).

## Unverified / assumptions
- **Workflow decision: one repo, CI as the cluster.** Cloud sessions write code plus fixture-based unit tests; GitHub Actions (free for public repos) runs kind for every fault and integration test; the session reads results with `gh run list` / `gh run view`.
- Untested option: k3s installed directly on the cloud VM (no nesting) might work. If tried, the allowlist must be extended by ADR (k3s's context is `default`).

## Open decisions (owner)
- LLM provider and key for M2+ (Anthropic API vs local Ollama).
- Eval accuracy-drop threshold X for the CI gate (M4).

## Log
- 2026-11-03: repo created; Claude Code setup added (CLAUDE.md, skills, agents, hook, brief).
- 2026-11-03: cloud environment probe; kind fails (nested runc). Decided on one repo with CI-as-cluster workflow.
