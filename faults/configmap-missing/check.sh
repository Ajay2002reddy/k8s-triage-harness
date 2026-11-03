#!/usr/bin/env bash
# Symptom: the api container can't be created because its configuration is missing.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

config_error() {
  local reasons
  reasons="$(pod_jsonpath app=api '{.items[*].status.containerStatuses[*].state.waiting.reason}')" || return 1
  [[ "$reasons" == *CreateContainerConfigError* ]]
}

wait_for "$CHECK_TIMEOUT" "api container waiting in CreateContainerConfigError" config_error
