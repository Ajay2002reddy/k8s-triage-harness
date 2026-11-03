# k8s-triage-harness

An agent that finds the root cause of Kubernetes incidents, inside a production-grade harness: sandboxing, permission tiers, context management, budgets, eval-gated CI, OpenTelemetry traces and prompt-injection defence. It's benchmarked on injected faults with known root causes against a rule-only baseline, k8sgpt and HolmesGPT.

> **Status:** in progress. See [PROGRESS.md](PROGRESS.md). No results are claimed until CI produces them.

## Why
Most "AI for Kubernetes" demos show the model. Production depends on the harness: what the agent is allowed to touch, how much it can spend, how it handles hostile log text, and whether a prompt change silently breaks it. This repo measures all of that.

## Results
_Filled from CI eval runs (M4+)._

| Agent | Category accuracy | Evidence grounding | Cost / incident | p95 latency |
|---|---|---|---|---|
| Rule-only baseline | – | – | – | – |
| This agent | – | – | – | – |
| k8sgpt | – | – | – | – |
| HolmesGPT | – | – | – | – |

## Project docs
- Scope and milestones: [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md)
- Decisions: [docs/adr/](docs/adr/)
- What I learned: [LEARNING.md](LEARNING.md)

## Working with Claude Code
This repo ships its own Claude Code setup:
- `CLAUDE.md`: project memory, auto-loaded.
- `.claude/skills/`: `add-fault`, `write-adr`, `run-evals`, `milestone-close`.
- `.claude/agents/`: `harness-reviewer` (pre-PR safety review), `interview-coach` (quizzes me).
- `.claude/hooks/guard_kube_context.py`: blocks kubectl/helm against any cluster except `kind-*` / `k3d-*`.

Start a session with [docs/KICKOFF_PROMPT.md](docs/KICKOFF_PROMPT.md).
