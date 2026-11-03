#!/usr/bin/env bash
# Smoke test: the allowlist accepts the current context and every node is Ready.
# shellcheck source=lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
LOG_PREFIX="smoke"

log "context $CTX passed the allowlist"
k wait --for=condition=Ready nodes --all --timeout=120s
k get nodes -o wide
