#!/usr/bin/env bash
# Symptom: web restarts, and the events blame the liveness probe.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

restarted_by_liveness_probe() {
  local restarts messages
  restarts="$(pod_jsonpath app=web '{.items[*].status.containerStatuses[*].restartCount}')" || return 1
  messages="$(k get events -n "$NS" --field-selector reason=Unhealthy -o jsonpath='{.items[*].message}')" || return 1
  [[ "$restarts" =~ [1-9] && "$messages" == *"Liveness probe failed"* ]]
}

wait_for "$CHECK_TIMEOUT" "web restarted after 'Liveness probe failed' events" restarted_by_liveness_probe
