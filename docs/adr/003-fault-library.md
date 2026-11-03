# ADR-003: Fault library: selection, neutral namespaces, image policy, one kind cluster per fault in CI

- **Status:** proposed
- **Date:** 2026-11-03
- **Milestone:** M1

## Context
M1 needs 12 faults that are verified in CI, each a folder following the add-fault skill. Forces:
- **Benchmark integrity.** The agent must not be able to read the answer in the cluster. The skill's namespace rule, `fault-<id>`, contradicts its own "neutral names" rule: `fault-oom-low-memory-limit` names the category.
- **CI is the only cluster** (ADR-001). Every symptom check has to work unattended on a fresh kind cluster.
- **kind specifics:** a default StorageClass exists, HPA needs metrics-server, ingress faults need a controller. ingress-nginx is retired: its README says best-effort maintenance ended in March 2026 ([announcement](https://www.kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)).
- **Pull limits:** anonymous Docker Hub pulls from shared CI IPs are rate-limited.

## Options
| Decision | Options considered | Chosen |
|---|---|---|
| Which 12 | (a) all 16 categories now; (b) 12 with no add-ons; (c) 11 with no add-ons + 1 metrics-server | (c): proves the `requires` path without a retired controller |
| Namespace | (a) skill's `fault-<id>`; (b) a neutral, unique `namespace:` in truth.yaml | (b); skill updated |
| Images | (a) Docker Hub; (b) registry.k8s.io test images (agnhost); (c) Docker Official Images via the ECR Public mirror | (c): realistic (nginx, busybox, python) and not Docker Hub |
| CI layout | (a) one cluster, faults in sequence; (b) a fresh cluster per fault (matrix) | (b): isolation; a failed reset can't poison other faults |

## Decision
- 12 faults in 12 categories. Only `hpa-missing-requests` needs an add-on (metrics-server). Deferred to the 12→20 growth: `quota_exceeded` and `scheduling_taint` (no add-ons; a taint fault that doesn't block every other pod needs a multi-node config), plus `ingress_backend_timeout` and `tls_secret`, which wait for the owner's ingress-controller decision.
- Each truth.yaml declares a neutral namespace (`storefront`, `ledger`, …). Resource names are neutral (`web`, `api`, `worker`). `tests/test_faults.py` rejects giveaway words and category names in names, labels and annotations, and rejects cluster-scoped objects (reset only deletes the namespace).
- Images come from `public.ecr.aws/docker/library/*`, pinned by tag, never `latest`, with the registry always named explicitly.
- CI (`faults.yml`) discovers faults from `faults/*/truth.yaml` and runs `scripts/verify-fault.sh` per fault on its own kind cluster. The check must fail before inject, pass after inject (inject runs twice for idempotency), and fail again after reset (reset also runs twice), and the namespace must be gone. On failure CI dumps diagnostics.
- metrics-server is vendored byte-identical (checksum-tested), plus a kustomize patch adding `--kubelet-insecure-tls`, acceptable only on a throwaway kind cluster.
- All fault scripts source `scripts/lib.sh` (the allowlist from ADR-002) and call the cluster only through `k`.

## Consequences
- Easier: adding a fault means adding a folder; the matrix picks it up. Faults are isolated and reproducible, and leakage is caught by tests rather than review.
- Harder / risk we accept: 12 kind clusters per run that touches faults (free on public repos, about 1 CPU-hour). Checks match upstream message text (busybox `wget` errors, HPA condition messages), so version bumps can break them. Tags aren't digests, so an upstream re-push could change an image. 4 categories aren't covered yet.
- How we'd know this was wrong: a fault job fails without a code change more than once in 20 runs (flaky check, so relax it or add retries); an M2 agent run cites a name or label rather than evidence (extend the leakage list); CI time per push becomes a bottleneck (move to a shared cluster for evals in M4).
