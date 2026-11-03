#!/usr/bin/env bash
# Symptom: PVC uploads is Pending and the web pod can't be scheduled because of it.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

pending_on_unbound_claim() {
  local phase message
  phase="$(k get pvc uploads -n "$NS" -o jsonpath='{.status.phase}')" || return 1
  message="$(pod_jsonpath app=web '{.items[*].status.conditions[?(@.type=="PodScheduled")].message}')" || return 1
  [[ "$phase" == Pending && "$message" == *unbound* ]]
}

wait_for "$CHECK_TIMEOUT" "PVC uploads Pending and web unschedulable (unbound claim)" pending_on_unbound_claim
