# ADR-002: Cluster allowlist: kubectl-compatible resolution, name + local API server, fail closed

- **Status:** proposed
- **Date:** 2026-11-03
- **Milestone:** M0

## Context
Hard constraint #1: refuse any context that doesn't match `kind-*` or `k3d-*`, in code, with tests. The owner's laptop kubeconfig may hold employer AKS contexts, so this is the first safety feature. Problems with a naive check:
- A context name is only a string. Anyone, or any tool, can name an AKS context `kind-dev`.
- kubectl picks the kubeconfig from `--kubeconfig`, else `$KUBECONFIG` (a path list where the first file to set a key wins), else `~/.kube/config`. A check that reads a different file checks a different cluster.
- Check-then-use races: if a script checks `current-context` and later runs plain `kubectl`, a `use-context` in between redirects it.
- Fault scripts (bash) need the same rule as the Python harness.

## Options
| Option | Pros | Cons |
|---|---|---|
| A. Regex on `kubectl config current-context` output (what the Claude Code hook does) | Tiny | Needs kubectl; name-only; nothing pins later calls |
| B. Parse the kubeconfig in-process with kubectl's precedence and merge rules; require the name **and** an https API server on loopback/0.0.0.0; return the context, and require every call to pass `--context` | Unit-testable with fixture files; catches renamed contexts; one module for Python and bash (CLI) | Re-implements part of kubectl's kubeconfig loading; may diverge on exotic configs |
| C. kubernetes Python client's config loader | Exact client semantics | Heavy dependency for a 150-line check; still name-only unless we add B's checks |
| D. Ask the API server (node names `*-control-plane`, kindnet) | Strongest signal | Sends credentials to a cluster before we know it's safe |

## Decision
Option B, in `src/triage/harness/allowlist.py`. The name must fully match `(kind|k3d)-[a-z0-9.-]+` (kind's own cluster-name charset); the context must exist and point at an `https` server whose host is `localhost`, a loopback IP or the unspecified address (k3d writes `0.0.0.0`). Anything unreadable, missing or ambiguous is refused. Shell scripts call it through `python -m triage.harness.allowlist` (sourced once in `scripts/lib.sh`), then use `k`, which always passes `--context`.

## Consequences
- Easier: one source of truth, about 60 tests, and a clear refusal message for each case; no kubectl needed to decide.
- Harder / risk we accept:
  - A loopback server isn't proof of a local cluster: `kubectl proxy` or an SSH tunnel to a remote cluster also listens on 127.0.0.1. The name check and the `https` requirement (which rules out `kubectl proxy`'s plain http) make this unlikely, but it's defence in depth, not proof. Option D could be added after M3's read-only ServiceAccount exists.
  - Legitimate setups are refused until an ADR extends the rule: k3s's `default` context, kind on a remote Docker host, in-cluster ServiceAccount config.
  - The harness must never pass `--server`, `--cluster` or `--kubeconfig` overrides to kubectl, because those bypass what we checked. A test should assert this when the M2 tools exist.
- How we'd know this was wrong: any kubectl call in repo code without `--context` (tests/test_faults.py greps the scripts), or the owner hitting a false refusal on a normal kind or k3d install.
