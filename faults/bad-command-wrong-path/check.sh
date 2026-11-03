#!/usr/bin/env bash
# Symptom: the worker crash-loops with a non-zero exit code.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

crash_looping() {
  local waiting exit_codes
  waiting="$(pod_jsonpath app=worker '{.items[*].status.containerStatuses[*].state.waiting.reason}')" || return 1
  exit_codes="$(pod_jsonpath app=worker '{.items[*].status.containerStatuses[*].lastState.terminated.exitCode}')" || return 1
  [[ "$waiting" == *CrashLoopBackOff* && "$exit_codes" =~ [1-9] ]]
}

wait_for "$CHECK_TIMEOUT" "worker in CrashLoopBackOff with a non-zero exit code" crash_looping
