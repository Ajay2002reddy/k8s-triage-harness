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
`make help` lists everything. Cluster targets need Docker + kind, so in cloud sessions they only run in CI.
- `make setup`: install pinned deps (`uv sync --frozen`)
- `make lint`: ruff, ruff format, mypy (strict), yamllint, shellcheck, bash -n
- `make test`: pytest, no cluster needed
- `make tools` / `make validate`: pinned kind, kubectl, kubeconform, actionlint (sha256-checked), then kubeconform + actionlint
- `make cluster` / `make cluster-down`: kind cluster `triage` (context `kind-triage`), smoke-tested
- `make addons|fault|check|reset|verify-fault|diagnose NAME=<id>`: fault lifecycle (`verify-fault` = what CI runs)
- `make eval`: from M4
- `make replay TRACE=<file>`: from M5

## CI (the only place a cluster exists for cloud sessions)
- `ci.yml` (every push): lint + test + validate, kind smoke. `faults.yml`: one kind cluster per fault.
- Read results via REST: `gh api "repos/Ajay2002reddy/k8s-triage-harness/actions/runs?branch=<b>&per_page=5"`; jobs `.../runs/<id>/jobs`; logs `.../actions/jobs/<id>/logs`. (`gh run`/`gh pr` use GraphQL, which may be blocked.)
- Shell scripts that touch a cluster must source `scripts/lib.sh` and use `k`, never kubectl directly (a test enforces this).

## Conventions
- Python 3.12, uv, ruff, pytest, typed code (`from __future__ import annotations`).
- Layout: `src/triage/` with `harness/`, `agent/`, `tools/`, `evals/`; `faults/<id>/`; `docs/adr/`.
- Faults: see the `add-fault` skill for the folder contract.
- Root-cause categories: one fixed enum in `src/triage/taxonomy.py`; change it only via an ADR.
- Disagree with the owner when they're wrong: give the reason, an alternative and the risk.
- Reports are concise bullets, conclusion first.
