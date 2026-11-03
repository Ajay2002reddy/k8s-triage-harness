#!/usr/bin/env bash
# Install the cluster add-ons a fault lists under `requires` in its truth.yaml.
# Add-ons are shared cluster infrastructure: fault resets leave them installed.
# Usage: scripts/addons.sh <fault-id>
# shellcheck source=lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"

id="${1:?usage: addons.sh <fault-id>}"
LOG_PREFIX="addons $id"
requirements="$(cd -- "$REPO_ROOT" && uv run --frozen --quiet python -m triage.evals.truth requires "$id")"

install_metrics_server() {
  # Vendored upstream manifest plus a kustomize patch for kind (ADR-003).
  k apply -k "$REPO_ROOT/cluster/addons/metrics-server"
  k -n kube-system rollout status deployment/metrics-server --timeout=180s
  k wait --for=condition=Available apiservice/v1beta1.metrics.k8s.io --timeout=180s
}

if [[ -z "$requirements" ]]; then
  log "no add-ons needed"
  exit 0
fi
for requirement in $requirements; do
  case "$requirement" in
    metrics-server) install_metrics_server ;;
    *) die "no installer for '$requirement' yet; add one here (see ADR-003)" ;;
  esac
  log "ready: $requirement"
done
