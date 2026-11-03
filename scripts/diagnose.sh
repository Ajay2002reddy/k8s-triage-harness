#!/usr/bin/env bash
# Print everything useful about a fault's namespace. CI runs it when a fault fails.
# Usage: scripts/diagnose.sh <fault-id>
# shellcheck source=lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"

id="${1:?usage: diagnose.sh <fault-id>}"
ns="$(fault_namespace "$id")"
LOG_PREFIX="diagnose $id"

section() { printf '\n===== %s\n' "$*"; }

section "objects in $ns"
k get all,endpointslices,configmaps,pvc,hpa,networkpolicies,serviceaccounts,roles,rolebindings \
  -n "$ns" -o wide || true
section "events in $ns"
k get events -n "$ns" --sort-by=.lastTimestamp || true
section "pods (describe)"
k describe pods -n "$ns" || true
for pod in $(k get pods -n "$ns" -o name 2>/dev/null); do
  section "logs $pod"
  k logs -n "$ns" "$pod" --all-containers --tail=40 || true
  section "previous logs $pod"
  k logs -n "$ns" "$pod" --all-containers --previous --tail=40 || true
done
section "nodes"
k get nodes -o wide || true
