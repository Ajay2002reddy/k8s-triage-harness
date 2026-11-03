# Project Brief: K8s Incident-Triage Agent + Production Harness

> Source of truth for scope, constraints and milestones. Change it only through an ADR.

## Role
You're a senior agent-infrastructure engineer pairing with me. I'm a DevOps/Platform engineer (about 3 years: AKS, Kubernetes ingress, Azure, Python, MCP) moving into AI platform / agent-infra roles. This repo is my public portfolio piece. It must prove I can build the **harness** around an agent (sandboxing, permissions, context, budgets, evals, traces), not just call an LLM. It must also teach me: I have to be able to explain every line in an interview.

## Goal
Build an agent that finds the root cause of Kubernetes incidents, plus the production harness around it. Prove its quality with an objective benchmark: injected faults with known root causes. Compare it against k8sgpt and HolmesGPT on the same faults.

## Hard constraints
1. **Cluster allowlist, enforced in code.** The harness refuses any kubeconfig context that doesn't match `kind-*` or `k3d-*`. My laptop kubeconfig may contain employer clusters, so this is the first safety feature. Unit-test it. Never use employer systems, data or code.
2. **Read-only by default.** Mutating verbs require an approval hook. Destructive verbs (delete namespace/node/PV/CRD, drain, scale to 0) are hard-blocked in the harness, not just in the prompt.
3. **Budget near ₹0.** Use open-source tools and free tiers; ask me before anything costs money.
4. **Pluggable LLM provider.** Anthropic API by default, plus an OpenAI-compatible endpoint for Ollama/vLLM. Keys come only from env vars; never commit secrets. M0–M1 need no LLM key.
5. **Readable over clever.** Small modules, no heavy framework unless an ADR justifies it.
6. **Pin versions** (Python, kind, k8s node image, every dependency). License: Apache-2.0.

## Environment reality: check first, report which path you took
- This cloud container probably can't run Docker/kind. Check first.
- If it can't, use **GitHub Actions with kind** as the real test bed, plus recorded fixtures (captured `kubectl` JSON output) for local unit tests.
- Never claim something ran if it only ran in theory.

## Continuity: sessions are short-lived, so the repo is the memory
Keep these files updated at the end of every session:
- `CLAUDE.md`: project conventions, commands, constraints above (short).
- `PROGRESS.md`: milestone status, what's verified versus unverified, open decisions, next 3 steps.
- `docs/adr/NNN-*.md`: one ADR per real decision.
- `LEARNING.md`: for each milestone, 5 interview questions I should be able to answer about what was built, plus short answers. I'll quiz myself on these.

## Root-cause taxonomy (makes grading objective)
- Define a fixed enum of root-cause categories, e.g.:
  - `image_pull`, `bad_command`, `oom`, `probe_misconfig`, `selector_mismatch`, `port_mismatch`
  - `ingress_backend_timeout`, `tls_secret`, `network_policy`, `pvc_unbound`, `quota_exceeded`, `config_missing`
  - `dns`, `scheduling_taint`, `rbac_forbidden`, `hpa_misconfig`
- The agent must output one category plus free-text detail.
- **Primary metric:** exact category match.
- An LLM judge is secondary, and only after it's checked against 30 hand labels.

## Milestones
Each milestone ends with: code, tests, a README section, the PROGRESS/LEARNING updates, a commit, and a PR to `main` for my review.

- **M0 Scaffold.**
  - Python 3.12 + uv; ruff + pytest.
  - GitHub Actions: lint/test on PR, plus a kind smoke job that creates a cluster and runs `kubectl get nodes`.
  - Makefile; ADR-001 (architecture: harness ↔ agent loop ↔ MCP tools ↔ cluster).
  - Cluster-allowlist module with tests.
- **M1 Fault library.** Start with **12 faults that are verified in CI**; grow to 20 by M4.
  - Each fault is a folder: `inject.sh` or manifests, `reset.sh`, `truth.yaml` (category, root_cause, evidence, fix), `requires` (e.g. ingress-nginx, metrics-server, multi-node), and a `check` that asserts the symptom actually appears.
  - Use kind specifics: kind has a default StorageClass, so PVC-pending needs a non-existent class. HPA needs metrics-server. TLS faults need an ingress controller.
  - `make fault NAME=x` and `make reset`. CI runs every fault's inject → check → reset.
- **M2 Agent + tools.**
  - kubectl tools over MCP: get, describe, logs (tail + truncated), events, top.
  - Agent loop with structured output: `category`, `root_cause`, `confidence`, `evidence[]` (each tied to a tool-call id), `suggested_fix`.
  - Baseline to beat: a rule-only triage (no LLM) on the same faults.
- **M3 Harness.**
  - Permission tiers (read / approve-to-write / blocked).
  - Read-only RBAC ServiceAccount for tool execution.
  - Context management: truncation/summarisation of logs and events, with token accounting.
  - Per-run step, token and cost budgets.
  - Timeouts and retries with backoff.
  - Structured log of every policy decision.
- **M4 Evals + CI gate.**
  - N runs × all faults.
  - Metrics: category accuracy, evidence-grounding rate, steps, tokens, cost, p50/p95 latency.
  - Output JSON + markdown report.
  - PR fails if accuracy drops more than X points versus `main`. Show the gate failing on a deliberately broken PR.
- **M5 Observability + replay.**
  - OpenTelemetry spans per LLM and tool call, sent to Langfuse or Grafana/Tempo via docker-compose.
  - `make replay TRACE=…` re-runs recorded tool outputs against the current agent and diffs the result.
- **M6 Red-team.**
  - Prompt injection hidden in pod logs, annotations, ConfigMaps and event messages.
  - Measure the attack success rate before and after defences; add the attacks as permanent eval cases.
- **M7 Benchmark + write-up.**
  - Run k8sgpt and HolmesGPT on the same suite; results table.
  - 600-word write-up: what I built, 2 trade-offs, 1 mistake, the numbers.
  - 3-min demo script; one upstream PR idea.

## Session scope rule
- Each session works only on the milestone(s) listed under **Next** in `PROGRESS.md`. The first session is **M0 + M1**.
- Stop at the milestone boundary and report in bullets:
  1. what runs, tagged [Verified: ran it] or [Unverified]
  2. CI status with a link to the run
  3. decisions I need to make
  4. the plan for the next milestone
- Never start the next milestone without my go-ahead.

## Working rules
- ADR before code for any real decision. Small commits with clear messages.
- Never fake test results, CI status or eval numbers. If something can't be verified here, say so.
- Tests first for harness logic (allowlist, permissions, budgets).
- When I'm wrong, disagree: give the reason, an alternative and the risk.
- Concise reports: no filler, conclusion first.

## Definition of done (whole project)
- Eval report: accuracy, grounding and cost, compared against the rule baseline, k8sgpt and HolmesGPT.
- Injection attack success rate shown before and after defences.
- CI eval gate demonstrated on a bad PR.
- A README a recruiter can scan in 60 seconds: problem, architecture diagram, results table, how to run.
- **External proof:** one upstream PR submitted; the write-up published.
- **Kill rule:** if the M4 eval suite isn't running by end of week 5, cut M5/M6 extras and keep the evals.
