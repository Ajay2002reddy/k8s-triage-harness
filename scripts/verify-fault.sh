#!/usr/bin/env bash
# The CI lifecycle for one fault (ADR-003). A fault counts only if all five steps pass:
#   1. check fails before inject      -> the check isn't vacuous
#   2. inject, twice                  -> inject is idempotent
#   3. check passes                   -> the symptom really appears
#   4. reset, twice                   -> reset is idempotent
#   5. namespace gone, check fails    -> reset really cleans up
# Usage: scripts/verify-fault.sh <fault-id>
# shellcheck source=lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"

id="${1:?usage: verify-fault.sh <fault-id>}"
dir="$REPO_ROOT/faults/$id"
[[ -f "$dir/truth.yaml" ]] || die "unknown fault: $id"
ns="$(fault_namespace "$id")"
LOG_PREFIX="verify $id"
NEGATIVE_TIMEOUT=20 # how long a check may poll when it is expected to fail

log "1/5 check must fail before inject"
if CHECK_TIMEOUT=$NEGATIVE_TIMEOUT "$dir/check.sh"; then
  die "check passed although the fault isn't injected"
fi

log "2/5 inject (twice)"
"$dir/inject.sh"
"$dir/inject.sh"

log "3/5 check must pass"
"$dir/check.sh" || die "the symptom never appeared"

log "4/5 reset (twice)"
"$dir/reset.sh"
"$dir/reset.sh"

log "5/5 namespace $ns must be gone and check must fail again"
if k get namespace "$ns" >/dev/null 2>&1; then
  die "namespace $ns still exists after reset"
fi
if CHECK_TIMEOUT=$NEGATIVE_TIMEOUT "$dir/check.sh"; then
  die "check still passes after reset"
fi
log "PASS"
