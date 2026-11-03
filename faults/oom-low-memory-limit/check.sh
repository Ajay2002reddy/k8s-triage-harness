#!/usr/bin/env bash
# Symptom: the worker container was OOMKilled.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

oom_killed() {
  local reasons
  reasons="$(pod_jsonpath app=worker '{.items[*].status.containerStatuses[*].lastState.terminated.reason} {.items[*].status.containerStatuses[*].state.terminated.reason}')" || return 1
  [[ "$reasons" == *OOMKilled* ]]
}

wait_for "$CHECK_TIMEOUT" "worker container terminated with reason OOMKilled" oom_killed
