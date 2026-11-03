# k8s-triage-harness

An agent that finds the root cause of Kubernetes incidents, plus the production harness around it: sandboxing, permissions, context management, budgets, eval-gated CI, traces and injection defence. It's a portfolio project; the owner must be able to explain every line.

## Always loaded
- Scope, constraints, milestones: @docs/PROJECT_BRIEF.md
- Current state and next steps: @PROGRESS.md

## Non-negotiables
- **Kind/k3d clusters only.** Never run kubectl/helm against a context not matching `kind-*` or `k3d-*`. A hook in `.claude/hooks/guard_kube_context.py` enforces this for Claude Code, and the harness must enforce it in product code too.
- **Agent is read-only by default.** Mutations need an approval hook; destructive verbs are hard-blocked in code.
- **No secrets in git.** Keys come only from env vars (`ANTHROPIC_API_KEY`, `OPENAI_BASE_URL`, …). `.env*` is gitignored and unreadable by Claude.
- **No employer systems, data or code. Ever.**
- **Never fake results.** Tag claims [Verified: ran it] or [Unverified]; no invented CI status or eval numbers.

## How to work here
- Work on the milestone(s) under **Next** in `PROGRESS.md`; stop at the boundary and report.
- Write an ADR before any real decision: use the `write-adr` skill.
- Write tests first for harness logic (allowlist, permissions, budgets, truncation).
- Small commits with clear messages. Open a PR to `main` per milestone.
- End every session with the `milestone-close` skill: update `PROGRESS.md` and `LEARNING.md`.
- Before a PR, run the `harness-reviewer` subagent on the diff.

## Commands
These are added in M0; update this list when they exist.
- `make setup`: install deps (uv)
- `make lint` / `make test`
- `make cluster` / `make cluster-down`: kind cluster
- `make fault NAME=<id>` / `make reset NAME=<id>`
- `make eval`: from M4
- `make replay TRACE=<file>`: from M5

## Conventions
- Python 3.12, uv, ruff, pytest, typed code (`from __future__ import annotations`).
- Layout: `src/triage/` with `harness/`, `agent/`, `tools/`, `evals/`; `faults/<id>/`; `docs/adr/`.
- Faults: see the `add-fault` skill for the folder contract.
- Root-cause categories: one fixed enum in `src/triage/taxonomy.py`; change it only via an ADR.
- Disagree with the owner when they're wrong: give the reason, an alternative and the risk.
- Reports are concise bullets, conclusion first.
