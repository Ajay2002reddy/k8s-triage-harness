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
| `manifests/*.yaml` + `inject.sh` | Creates the broken state in the fault's **neutral** namespace (from `truth.yaml`, never `fault-<id>`, which would leak the answer). The Namespace is the first document. Idempotent. |
| `reset.sh` | Removes everything inject created (delete the namespace). Cluster-scoped objects are rejected by `tests/test_faults.py`; if you really need one, extend reset and that test. Idempotent. |
| `check.sh` | Exits 0 only when the expected **symptom** is observable (e.g. pod in `CrashLoopBackOff`, curl returns 504). Polls with `wait_for`/`holds_for` and `$CHECK_TIMEOUT`; never sleeps blindly. |
| `truth.yaml` | Ground truth for grading (schema below). |
| `README.md` | 3–5 lines: what breaks, why it's realistic, what a human would check first. |

All three scripts start by sourcing `scripts/lib.sh` and calling `load_fault`. lib.sh runs the cluster allowlist and provides `k` (kubectl with a pinned `--context`). Never call kubectl directly; a test fails if you do. Copy `inject.sh`/`reset.sh` from an existing fault.

## `truth.yaml` schema
```yaml
id: ingress-backend-timeout
namespace: shop                      # neutral, unique across faults; a plain line (lib.sh reads it with sed)
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
5. Run `make test` (contract, schema, leakage). CI (`.github/workflows/faults.yml`) discovers the new folder automatically and runs `scripts/verify-fault.sh` on a fresh kind cluster: check fails, inject, check passes, reset, check fails. Locally: `make verify-fault NAME=<id>`.
6. Update the fault table in the README and the count in `PROGRESS.md`.

## kind gotchas
- kind ships a default StorageClass (`standard`), so a PVC-pending fault needs a **non-existent** `storageClassName`.
- HPA faults need metrics-server (`requires: [metrics-server]`; `make addons NAME=<id>` installs the vendored copy with `--kubelet-insecure-tls`).
- TLS and ingress faults need an ingress controller. ingress-nginx is retired (ADR-003), so choose the controller in an ADR first.
- Taint/toleration faults need a multi-node kind config.
- Pin images by tag and name the registry: use `public.ecr.aws/docker/library/<image>:<tag>`, not Docker Hub (CI pull limits). Never use `:latest`.

## Don't
- Don't put the answer anywhere the agent can read in-cluster (labels, annotations or names like `oom-test`). Use neutral names (`web`, `api`, `worker`); otherwise the benchmark leaks.
- Don't touch any context other than `kind-*` / `k3d-*`.
