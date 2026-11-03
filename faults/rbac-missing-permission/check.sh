#!/usr/bin/env bash
# Symptom: the reporter's API calls are rejected with 403 Forbidden.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

forbidden_in_logs() {
  local logs
  logs="$(k logs -n "$NS" deploy/reporter --tail=20)" || return 1
  [[ "$logs" == *"HTTP 403"* && "$logs" == *"cannot list resource"* ]]
}

wait_for "$CHECK_TIMEOUT" "reporter logs a 403 'cannot list resource'" forbidden_in_logs
