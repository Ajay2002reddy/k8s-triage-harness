---
name: add-fault
description: Add a new reproducible Kubernetes fault to the benchmark library under faults/. Use when creating, fixing or extending a fault scenario (CrashLoop, OOM, ingress 504, TLS, NetworkPolicy, PVC, RBAC, etc.) or when a fault's check fails in CI.
---

# Add a fault

Every fault is a self-contained folder that CI can inject, check and reset with no human involved. A fault without a passing `check` doesn't count.

## Folder contract: `faults/<id>/`
`<id>` is kebab-case, e.g. `ingress-backend-timeout`.

| File | Purpose |
|---|---|
| `inject.sh` (or `manifests/` + `inject.sh`) | Creates the broken state in namespace `fault-<id>`. Idempotent. |
| `reset.sh` | Removes everything inject created (delete the namespace plus any cluster-scoped objects). Idempotent. |
| `check.sh` | Exits 0 only when the expected **symptom** is observable (e.g. pod in `CrashLoopBackOff`, curl returns 504). Waits with a timeout; never sleeps blindly. |
| `truth.yaml` | Ground truth for grading (schema below). |
| `README.md` | 3–5 lines: what breaks, why it's realistic, what a human would check first. |

## `truth.yaml` schema
```yaml
id: ingress-backend-timeout
category: ingress_backend_timeout   # must exist in src/triage/taxonomy.py
root_cause: "Backend pod sleeps 120s; ingress proxy-read-timeout is 30s"
evidence:                            # what a correct agent should cite
  - "kubectl logs shows request start with no response"
  - "ingress annotation nginx.ingress.kubernetes.io/proxy-read-timeout: 30"
fix: "Raise proxy-read-timeout or fix the slow handler"
requires: [ingress-nginx]            # cluster add-ons: ingress-nginx, metrics-server, multi-node, cert-manager
difficulty: medium                   # easy | medium | hard
```

## Steps
1. Pick a category from `src/triage/taxonomy.py`. If none fits, stop and write an ADR. Don't add categories casually.
2. Write `check.sh` **first** and confirm it fails on a healthy cluster. That's the test.
3. Write `inject.sh`, run it, confirm `check.sh` passes.
4. Write `reset.sh`, run it, confirm the namespace and cluster-scoped objects are gone, and that `check.sh` fails again.
5. Add the fault id to the CI matrix (inject → check → reset).
6. Update the fault table in the README and the count in `PROGRESS.md`.

## kind gotchas
- kind ships a default StorageClass (`standard`), so a PVC-pending fault needs a **non-existent** `storageClassName`.
- HPA faults need metrics-server, installed with `--kubelet-insecure-tls` on kind.
- TLS and ingress faults need ingress-nginx (kind-specific manifest) and `extraPortMappings` in the kind config.
- Taint/toleration faults need a multi-node kind config.
- Pin images by tag. Never use `:latest`.

## Don't
- Don't put the answer anywhere the agent can read in-cluster (labels, annotations or names like `oom-test`). Use neutral names (`web`, `api`, `worker`); otherwise the benchmark leaks.
- Don't touch any context other than `kind-*` / `k3d-*`.
