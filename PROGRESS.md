# Progress

Updated at the end of every session (`milestone-close` skill). This file is the project's memory across sessions.

## Status
| Milestone | State | Verified in CI | PR |
|---|---|---|---|
| M0 Scaffold | done, awaiting owner review | ✅ [ci 41661299430](https://github.com/Ajay2002reddy/k8s-triage-harness/actions/runs/41661299430) (lint + test + validate, kind smoke) | PR_LINK |
| M1 Fault library (12 → 20) | 12 faults, awaiting owner review | ✅ 12/12 [faults 41661299299](https://github.com/Ajay2002reddy/k8s-triage-harness/actions/runs/41661299299) | PR_LINK |
| M2 Agent + tools | not started | – | – |
| M3 Harness | not started | – | – |
| M4 Evals + CI gate | not started | – | – |
| M5 Observability + replay | not started | – | – |
| M6 Red-team | not started | – | – |
| M7 Benchmark + write-up | not started | – | – |

## Next
- **M2 Agent + tools**, only after the owner reviews the M0+M1 PR and picks the LLM provider. First 3 steps:
  1. ADR-004: agent loop (plain loop vs framework) and the LLM provider interface (Anthropic + OpenAI-compatible), written before code.
  2. Fixtures: a CI job that injects each fault and saves `kubectl get/describe/logs/events -o json` as `tests/fixtures/<fault>/`, so the tools and the rule-only baseline are unit-testable without a cluster. `scripts/diagnose.sh` already prints the human-readable version.
  3. MCP server with read-only kubectl tools (get, describe, logs with tail + truncation, events, top). Every call goes through `resolve_target` and pins `--context`; tests cover the verb allowlist and refuse `--server/--kubeconfig/--context` overrides (same rule as `k` in lib.sh). The eval cluster then needs metrics-server for every fault (`top`). The agent gets no file access to the repo, where truth.yaml lives.

## Verified
- 2026-11-03, CI on GitHub Actions [Verified: ran it]:
  - **M0:** `lint + test` (now including `make validate`) and `kind smoke` passed on every push of `m0-m1`, e.g. [41657703325](https://github.com/Ajay2002reddy/k8s-triage-harness/actions/runs/41657703325) (first) and [41661299430](https://github.com/Ajay2002reddy/k8s-triage-harness/actions/runs/41661299430) (final). Smoke: kind v0.33.0 creates `kind-triage` from `kindest/node:v1.37.0@sha256:a1ed56cf…`, the allowlist accepts it, the node is Ready, `get nodes` prints it, and the cluster is deleted.
  - **M1:** all 12 faults passed the full lifecycle in three consecutive runs: [41659130300](https://github.com/Ajay2002reddy/k8s-triage-harness/actions/runs/41659130300), [41659914079](https://github.com/Ajay2002reddy/k8s-triage-harness/actions/runs/41659914079) and [41661299299](https://github.com/Ajay2002reddy/k8s-triage-harness/actions/runs/41661299299). The lifecycle: check fails before inject; inject ×2; check passes; reset ×2; namespace gone; check fails again. One cluster per fault: about 28 runner-minutes, 3.3 min wall-clock. Symptom detection takes 0.7–46s per fault, with a 240s timeout.
  - **Evidence:** the snapshot logged after each passing check (run 41659914079) contains the key evidence strings in every truth.yaml. Examples: `wget: download timed out` (NetworkPolicy); `bad address 'api.orders.svc.cluster.local'` (DNS); `Connection refused` with the EndpointSlice on port 8080 (port) vs `<unset>` (selector); `statuscode: 404` (probe); the exact 403 text (RBAC); `missing request for cpu` (HPA). Not captured: the DNS pod's resolv.conf contents and the cluster's StorageClass list (both descriptive claims in truth.yaml).
  - A flaky check was found and fixed by timing: bad-command took 6s in one run and 179s in the next, because it relied on the `CrashLoopBackOff` reason. It now uses restartCount and the exit code, and took 19.5s in the final run.
- 2026-11-03, local (cloud session, no cluster) [Verified: ran it]: `make lint` clean (ruff, ruff format, mypy --strict, yamllint --strict, shellcheck, bash -n); `make test` 247 passed; `make validate`: kubeconform -strict 54/54 resources valid against 1.37.0, actionlint clean. `make fault` refused a missing kubeconfig, an `aks-prod` context and a `kind-prod` context pointing at an AKS URL, each before any cluster call.
- Earlier probe (2026-11-03): cloud sessions run Docker but not kind (nested runc fails). So CI is the cluster.

## Unverified / assumptions / known limits
- **Negative controls are "fault absent", not "fault fixed".** No CI step applies a corrected manifest and shows the check failing. A `fixed/` variant per fault would close this, and M4 needs one anyway to measure false positives.
- Nothing ran on the owner's laptop: `make tools` / `make cluster` on Linux/WSL2 are [Unverified]. `install-tools.sh` pins linux-amd64 only; scripts need bash 4.4+.
- k3d contexts are accepted by the allowlist per unit tests only; no k3d cluster was used.
- Fault images are pinned by tag, not digest, so an upstream re-push could change a fault.
- Review leftovers (minor, accepted for now): the kubeconfig could be edited between the allowlist check and later `k` calls (fix: snapshot the validated context into a temporary kubeconfig, M3). `reset` deletes the namespace named in truth.yaml even if the fault didn't create it (fine on disposable kind clusters). CI runs on `push` only, so fork PRs get no CI.
- The `harness-reviewer` checklist was applied by hand (the session couldn't spawn the subagent). Findings and fixes are in the PR description.

## Open decisions (owner)
- LLM provider and key for M2+ (Anthropic API vs local Ollama). Blocks M2.
- Ingress controller for the `ingress_backend_timeout` and `tls_secret` faults. ingress-nginx is retired (its README: best-effort maintenance ended March 2026). Options: ingress-nginx anyway (familiar, unpatched) or a Gateway API implementation (Envoy Gateway, NGINX Gateway Fabric), which is more future-proof.
- Add an `unknown` (abstain) category to the taxonomy? It changes what accuracy means, so it needs an ADR before M2's output schema.
- Accept or amend ADR-001/002/003 (all `proposed`) and the deviations they record: the allowlist also requires a local https API server (stricter than the brief); fault namespaces are neutral instead of `fault-<id>` (add-fault skill updated); the Claude Code hook regex was widened after its tests found bypasses.
- Eval accuracy-drop threshold X for the CI gate (M4).

## Log
- 2026-11-03: repo created; Claude Code setup added (CLAUDE.md, skills, agents, hook, brief).
- 2026-11-03: cloud environment probe; kind fails (nested runc). Decided on one repo with CI-as-cluster workflow.
- 2026-11-03: M0 + M1 built on `m0-m1`. Scaffold, allowlist (ADR-002), hook tests (closed 3 bypasses), pinned tooling, CI; 12 faults verified in 3 CI runs (ADR-003); flaky bad-command check fixed. PR opened for review.
