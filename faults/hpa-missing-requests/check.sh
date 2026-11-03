#!/usr/bin/env bash
# Symptom: the HPA can't compute CPU utilization because the pods have no CPU request.
# This takes a minute or two: metrics-server must scrape the pod first.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

missing_cpu_request() {
  local message
  message="$(k get hpa api -n "$NS" -o jsonpath='{.status.conditions[?(@.type=="ScalingActive")].message}')" || return 1
  [[ "$message" == *"missing request for cpu"* ]]
}

wait_for "$CHECK_TIMEOUT" "HPA api reports 'missing request for cpu'" missing_cpu_request
