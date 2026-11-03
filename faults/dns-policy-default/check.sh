#!/usr/bin/env bash
# Symptom: the api Service is healthy, but its cluster DNS name doesn't resolve from the
# worker pod.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

name_does_not_resolve() {
  local out
  if out="$(http_from worker "http://api.$NS.svc.cluster.local/")"; then
    return 1 # the request worked: no symptom
  fi
  [[ "$out" == *"bad address"* ]]
}

wait_for "$CHECK_TIMEOUT" "deployment api has ready pods" deployment_ready api
wait_for "$CHECK_TIMEOUT" "Service api has endpoints" has_endpoints api
wait_for "$CHECK_TIMEOUT" "deployment worker has ready pods" deployment_ready worker
wait_for "$CHECK_TIMEOUT" "worker can't resolve api.$NS.svc.cluster.local" name_does_not_resolve
