#!/usr/bin/env bash
# Symptom: web pods are stuck pulling their image.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

stuck_pulling() {
  local reasons
  reasons="$(pod_jsonpath app=web '{.items[*].status.containerStatuses[*].state.waiting.reason}')" || return 1
  [[ "$reasons" == *ErrImagePull* || "$reasons" == *ImagePullBackOff* ]]
}

wait_for "$CHECK_TIMEOUT" "web pods waiting in ErrImagePull/ImagePullBackOff" stuck_pulling
