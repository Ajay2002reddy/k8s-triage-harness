#!/usr/bin/env python3
"""Claude Code PreToolUse hook: block Kubernetes commands outside kind/k3d clusters.

Reads the hook payload (JSON) from stdin. If the Bash command invokes kubectl, helm,
k9s, kubectx or stern, every targeted kube context must match ^(kind|k3d)-.
Exit 2 blocks the tool call and shows stderr to Claude. Fails closed: if the
context can't be determined, the command is blocked.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

ALLOWED = re.compile(r"^(kind|k3d)-")
# A tool name counts as an invocation at the start, after a separator, after a path
# (/usr/local/bin/kubectl) or after a quote (sh -c 'kubectl ...'). Lookarounds so that
# adjacent invocations aren't swallowed. Best effort: the product code enforces the
# allowlist itself (src/triage/harness/allowlist.py).
KUBE_TOOLS = re.compile(
    r"(?:^|(?<=[\s;&|(`$/'\"\\]))(kubectl|helm|k9s|kubectx|stern)(?=[\s'\"`;&|)]|$)"
)
EXPLICIT_CTX = re.compile(r"--(?:kube-)?context(?:=|\s+)([^\s;&|]+)")
USE_CTX = re.compile(r"(?:config\s+use-context|kubectx)\s+([^\s;&|-][^\s;&|]*)")


def current_context() -> str:
    kubectl = shutil.which("kubectl")
    if not kubectl:
        return ""
    try:
        out = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [kubectl, "config", "current-context"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def block(reason: str) -> None:
    print(
        f"Blocked by guard_kube_context: {reason}\n"
        "This repo only touches kind-* or k3d-* clusters (see CLAUDE.md). "
        "Create one with `make cluster` or pass --context kind-<name>.",
        file=sys.stderr,
    )
    sys.exit(2)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # not our concern; let Claude Code handle malformed input

    cmd = (payload.get("tool_input") or {}).get("command", "") or ""
    if not KUBE_TOOLS.search(cmd):
        sys.exit(0)

    if "--kubeconfig" in cmd or "KUBECONFIG=" in cmd:
        block(
            "custom kubeconfig paths are not allowed; "
            "use the default kubeconfig with a kind/k3d context"
        )

    explicit = [c.strip("'\"") for c in EXPLICIT_CTX.findall(cmd)]
    switched = [c.strip("'\"") for c in USE_CTX.findall(cmd)]
    targets = explicit + switched
    # Any kube invocation without its own --context uses the current context: check it too.
    # Context-switch invocations (use-context / kubectx) are checked by their target instead.
    if len(explicit) < len(KUBE_TOOLS.findall(cmd)) - len(switched):
        targets.append(current_context())

    bad = [c or "<unknown>" for c in targets if not ALLOWED.match(c)]
    if bad:
        block(f"context {', '.join(bad)} is not in the allowlist")
    sys.exit(0)


if __name__ == "__main__":
    main()
