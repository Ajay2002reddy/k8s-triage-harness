# Learning log

For each milestone: 5 interview questions the owner must be able to answer without AI, with short model answers. Use the `interview-coach` subagent to be quizzed.

Rule: if a question can't be answered from memory, re-read the code or ADR and rewrite the answer in your own words.

## M0 Scaffold

**1. (Design) Why does the allowlist parse the kubeconfig itself instead of running `kubectl config current-context`?**
A name check on that output trusts a string anyone can rename. Parsing the kubeconfig lets us also check where the context points: an https API server on loopback or 0.0.0.0. It also needs no kubectl and is unit-testable with fixture files. We copy kubectl's precedence (`--kubeconfig`, else `$KUBECONFIG` with first-file-wins, else `~/.kube/config`), so we check the cluster kubectl would really use. → `src/triage/harness/allowlist.py`, ADR-002.

**2. (Safety) A context named `kind-prod` points at an AKS API server. What stops the harness, and what wouldn't?**
`is_local_server` refuses because the host isn't loopback or unspecified, so the name alone isn't enough. It would *not* stop an SSH tunnel to a remote cluster listening on `https://127.0.0.1`: loopback isn't proof of locality. That's why ADR-002 calls this defence in depth, and why every call also pins `--context`. A post-connect check (e.g. kind node names) is a possible later addition. → `tests/test_allowlist.py::test_kind_named_context_pointing_at_a_remote_server_is_refused`.

**3. (Failure) Why both a Claude Code hook and a product allowlist, and what did testing the hook reveal?**
The hook guards Claude's own shell commands. It's lexical, so best effort. The allowlist guards what the product does, whoever runs it. Writing `tests/test_guard_hook.py` showed the hook only recognised `kubectl` after whitespace or `;&|(`$`, so `/usr/local/bin/kubectl get pods` and `sh -c 'kubectl …'` ran unchecked. The regex now accepts path and quote boundaries. Lesson: test safety code with adversarial inputs, not just the happy path.

**4. (Trade-off) Why pin Actions to commit SHAs and binaries to sha256 instead of version tags?**
Tags are mutable: whoever controls a repo can move `v4` to malicious code. That happened to `tj-actions/changed-files` in March 2025, whose re-pointed tags dumped CI secrets into logs. A SHA or checksum can't change underneath us. The cost is manual bumps and unreadable refs, which we mitigate with `# vX.Y.Z` comments and `tests/test_cluster_config.py`, which fails if anything is unpinned. → `cluster/versions.env`, `.github/workflows/*.yml`.

**5. (Code path) Walk through `make cluster` in CI.**
`make tools` downloads kind v0.33.0 and kubectl v1.37.0 and checks their sha256. `kind create cluster --config cluster/kind-config.yaml` boots `kindest/node:v1.37.0@sha256:…` (digest-pinned) and writes context `kind-triage` to the kubeconfig. `scripts/smoke.sh` sources `scripts/lib.sh`, which runs `python -m triage.harness.allowlist`. Only if that prints an allowed context does `k` (= `kubectl --context "$CTX"`) wait for nodes Ready and list them. → `Makefile`, `scripts/lib.sh`.

## M1 Fault library

**1. (Design) Why does each fault declare a neutral namespace (`storefront`) instead of the skill's original `fault-<id>`?**
The agent sees namespace names. `fault-oom-low-memory-limit` hands it the answer, and a benchmark that leaks labels measures reading, not diagnosis. The id stays descriptive for humans; truth.yaml maps it to a neutral namespace. `tests/test_faults.py` rejects giveaway words and category names in names, labels and annotations, and a test proves the detector fires. → ADR-003.

**2. (Failure) A check passes in CI. How do you know it isn't vacuous?**
`scripts/verify-fault.sh` adds negative controls: the check must *fail* before inject and again after reset, and the namespace must be gone. Inject and reset each run twice to prove idempotency. Checks assert observable symptoms (pod state, endpoints, request errors, HPA conditions), not the cause. Where a healthy cluster briefly looks broken (no endpoints yet), `holds_for` demands the symptom stay for 15s.

**3. (Safety) What stops `make fault` from applying manifests to an employer cluster?**
Every fault script sources `scripts/lib.sh`, which runs the Python allowlist before anything else and aborts if it refuses. All later calls go through `k`, which pins the validated `--context`, so a `use-context` elsewhere can't redirect a running script. A test fails if any script calls kubectl directly. Faults may only create namespaced objects, so reset (`delete namespace`) can't leave cluster-wide changes behind.

**4. (Trade-off) Why one fresh kind cluster per fault in CI rather than one shared cluster?**
Isolation and debuggability: a fault's leftovers (or a failed reset) can't break another fault, and failures are attributed to one job. The price is 12 cluster creations per run: about 26 runner-minutes in total, but only about 3 minutes wall-clock because the jobs run in parallel (measured in CI run 41659130300; free on public repos). For M4's N×faults eval loop a shared cluster with strict reset may be cheaper, so revisit then. → ADR-003.

**5. (Code path) How do the checks tell `selector_mismatch`, `port_mismatch` and `network_policy` apart, when all three look like "frontend can't reach api"?**
selector: the Service has **no endpoints** although pods are Ready (`holds_for 15 … no_endpoints`). port: endpoints exist, and busybox wget from the client gets **"Connection refused"**, because the packet reaches the pod but nothing listens on 8080. network policy: endpoints exist, and the request **never connects** (dropped, so it times out). Same symptom for a user, different evidence for the agent: exactly what the benchmark should test. → `faults/*/check.sh`, `scripts/lib.sh`.
