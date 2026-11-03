# shellcheck shell=bash
# Shared helpers for every script that touches a cluster. Source it; don't run it.
#
# Safety (ADR-002): sourcing this resolves the kube context with the Python allowlist
# (src/triage/harness/allowlist.py) and stops unless it's a local kind-*/k3d-* cluster.
# Every cluster call must then go through `k`, which pins --context, so a later
# `use-context` somewhere else can't redirect a running script. tests/test_faults.py
# fails if a script calls the CLI directly instead of `k`.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_PREFIX="${LOG_PREFIX:-triage}"

log() { printf '[%s] %s\n' "$LOG_PREFIX" "$*" >&2; }
die() {
  log "ERROR: $*"
  exit 1
}

# KUBE_CONTEXT may name a context explicitly; it's validated like any other.
CTX="$(cd -- "$REPO_ROOT" &&
  uv run --frozen --quiet python -m triage.harness.allowlist ${KUBE_CONTEXT:+--context "$KUBE_CONTEXT"})" ||
  die "refusing to touch this cluster (reason above). Use 'make cluster' for a kind cluster."
readonly CTX

# k: kubectl pinned to the validated context. Flags that pick a different target are
# refused: kubectl lets a later --context override ours, and --kubeconfig/--server/
# --cluster would point at something the allowlist never checked.
k() {
  local arg
  for arg in "$@"; do
    [[ "$arg" == "--" ]] && break # what follows is the command run inside a pod
    case "$arg" in
      --context | --context=* | --kubeconfig | --kubeconfig=* | --cluster | --cluster=* | \
        --server | --server=* | -s)
        die "k: refusing '$arg': it would bypass the cluster allowlist"
        ;;
    esac
  done
  command kubectl --context "$CTX" "$@"
}

# wait_for SECONDS DESCRIPTION CMD...: poll CMD every 3s until it succeeds; 1 on timeout.
wait_for() {
  local timeout="$1" what="$2"
  shift 2
  local deadline=$((SECONDS + timeout))
  until "$@" >/dev/null 2>&1; do
    if ((SECONDS >= deadline)); then
      log "timed out after ${timeout}s waiting for: $what"
      return 1
    fi
    sleep 3
  done
  log "ok: $what"
}

# holds_for SECONDS DESCRIPTION CMD...: CMD must keep succeeding for the whole window.
# For symptoms that a healthy cluster also shows briefly (e.g. "no endpoints yet").
holds_for() {
  local window="$1" what="$2"
  shift 2
  local end=$((SECONDS + window))
  while ((SECONDS < end)); do
    if ! "$@" >/dev/null 2>&1; then
      log "not stable for ${window}s: $what"
      return 1
    fi
    sleep 3
  done
  log "ok (held ${window}s): $what"
}

# --- fault helpers -------------------------------------------------------------------

# fault_namespace ID: the namespace from faults/ID/truth.yaml. Read with sed, so
# tests/test_faults.py enforces the plain `namespace: <name>` line this relies on.
fault_namespace() {
  local ns
  ns="$(sed -n 's/^namespace:[[:space:]]*//p' "$REPO_ROOT/faults/$1/truth.yaml")"
  [[ "$ns" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
    die "$1: missing or invalid 'namespace' in truth.yaml"
  printf '%s\n' "$ns"
}

# load_fault: call at the top of a fault script. Sets FAULT_DIR, FAULT_ID, NS and
# CHECK_TIMEOUT (seconds a check polls before giving up).
load_fault() {
  FAULT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[1]}")" && pwd)"
  FAULT_ID="$(basename -- "$FAULT_DIR")"
  NS="$(fault_namespace "$FAULT_ID")"
  LOG_PREFIX="fault $FAULT_ID"
  CHECK_TIMEOUT="${CHECK_TIMEOUT:-240}"
  export FAULT_DIR FAULT_ID NS CHECK_TIMEOUT
}

apply_manifests() { k apply -f "$FAULT_DIR/manifests/"; }

delete_namespace() { k delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s; }

# deployment_ready NAME: at least one ready replica.
deployment_ready() {
  local ready
  ready="$(k get deployment "$1" -n "$NS" -o jsonpath='{.status.readyReplicas}')" || return 1
  [[ "${ready:-0}" -ge 1 ]]
}

# service_endpoints NAME: print the endpoint addresses behind a Service (empty if none).
service_endpoints() {
  k get endpointslices -n "$NS" -l "kubernetes.io/service-name=$1" \
    -o jsonpath='{.items[*].endpoints[*].addresses[*]}'
}

has_endpoints() {
  local addrs
  addrs="$(service_endpoints "$1")" || return 1
  [[ -n "$addrs" ]]
}

# http_from DEPLOYMENT URL: fetch URL from inside a pod of DEPLOYMENT (busybox wget);
# prints wget's output, returns wget's status.
http_from() { k exec -n "$NS" "deploy/$1" -- wget -q -T 3 -O /dev/null "$2" 2>&1; }

# pod_jsonpath SELECTOR JSONPATH: evaluate JSONPATH over the pods matching SELECTOR.
pod_jsonpath() { k get pods -n "$NS" -l "$1" -o "jsonpath=$2"; }
