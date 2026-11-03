#!/usr/bin/env bash
# Reset: delete the namespace and wait until it's gone. This fault creates nothing
# cluster-scoped (tests/test_faults.py enforces that), so that's everything.
# shellcheck source=../../scripts/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts/lib.sh"
load_fault
delete_namespace
