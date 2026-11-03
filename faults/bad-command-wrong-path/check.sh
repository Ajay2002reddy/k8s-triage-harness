#!/usr/bin/env bash
# Symptom: the worker crash-loops: it keeps restarting after non-zero exits.
# Uses restartCount (monotonic) instead of the waiting reason "CrashLoopBackOff": in CI run
# 41659914079 that reason was visible only intermittently, and detection took 179s
# instead of 6s.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

crash_looping() {
  local restarts exit_codes
  restarts="$(pod_jsonpath app=worker '{.items[*].status.containerStatuses[*].restartCount}')" || return 1
  exit_codes="$(pod_jsonpath app=worker '{.items[*].status.containerStatuses[*].lastState.terminated.exitCode}')" || return 1
  at_least 2 "$restarts" && [[ "$exit_codes" =~ [1-9] ]]
}

wait_for "$CHECK_TIMEOUT" "worker restarted at least twice after non-zero exits" crash_looping
