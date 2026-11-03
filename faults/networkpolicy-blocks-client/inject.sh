#!/usr/bin/env bash
# Inject: apply the broken manifests. `apply` is declarative, so re-running is a no-op.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault
apply_manifests
