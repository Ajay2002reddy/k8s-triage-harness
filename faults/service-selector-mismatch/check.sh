#!/usr/bin/env bash
# Symptom: the api pods are Ready, yet Service api has no endpoints. A healthy Service can
# also look empty for a second after the pods become Ready, so it must stay empty.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault

no_endpoints() {
  local addresses
  addresses="$(service_endpoints api)" || return 1
  [[ -z "$addresses" ]]
}

wait_for "$CHECK_TIMEOUT" "deployment api has ready pods" deployment_ready api
holds_for 15 "Service api has no endpoints while api pods are ready" no_endpoints
