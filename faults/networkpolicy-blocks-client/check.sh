#!/usr/bin/env bash
# Symptom: Service api has endpoints, but requests from the frontend never connect.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

requests_blocked() {
  local out
  if out="$(http_from frontend http://api/)"; then
    return 1 # the request worked: no symptom
  fi
  [[ "$out" == *"timed out"* || "$out" == *"can't connect to remote host"* ]]
}

wait_for "$CHECK_TIMEOUT" "deployment api has ready pods" deployment_ready api
wait_for "$CHECK_TIMEOUT" "deployment frontend has ready pods" deployment_ready frontend
wait_for "$CHECK_TIMEOUT" "Service api has endpoints" has_endpoints api
wait_for "$CHECK_TIMEOUT" "frontend -> http://api/ is blocked" requests_blocked
