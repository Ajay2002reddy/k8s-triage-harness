"""The Claude Code PreToolUse hook (.claude/hooks/guard_kube_context.py).

The hook guards Claude's own Bash calls; the product code has its own guard
(triage.harness.allowlist). Each case runs the real hook script with a fake kubectl
on PATH whose `config current-context` prints FAKE_CURRENT_CONTEXT.
Exit 0 = allowed, exit 2 = blocked.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "guard_kube_context.py"
ALLOWED, BLOCKED = 0, 2

FAKE_KUBECTL = """#!/bin/sh
if [ "$1 $2" = "config current-context" ]; then
  printf '%s\\n' "$FAKE_CURRENT_CONTEXT"
fi
"""


@pytest.fixture
def fake_path(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    kubectl = bin_dir / "kubectl"
    kubectl.write_text(FAKE_KUBECTL)
    kubectl.chmod(0o755)
    return bin_dir


def run_hook(payload: str, path: Path, current: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env={"PATH": str(path), "FAKE_CURRENT_CONTEXT": current},
        check=False,
    )


def bash_payload(command: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


CASES = [
    # (command, current-context, expected exit code)
    ("ls -la", "aks-prod", ALLOWED),
    ("make test", "aks-prod", ALLOWED),
    ("cat notes/kubectl-tips.md", "aks-prod", ALLOWED),
    ("kubectl get pods", "kind-triage", ALLOWED),
    ("kubectl get pods", "aks-prod", BLOCKED),
    ("kubectl get pods", "", BLOCKED),
    ("kubectl --context kind-triage get pods", "aks-prod", ALLOWED),
    ("kubectl --context=k3d-dev get nodes", "aks-prod", ALLOWED),
    ("kubectl --context 'kind-triage' get pods", "aks-prod", ALLOWED),
    ("kubectl --context=aks-prod get pods", "kind-triage", BLOCKED),
    ("kubectl --context kind-triage get pods && kubectl get nodes", "aks-prod", BLOCKED),
    ("ls; kubectl get nodes", "aks-prod", BLOCKED),
    ("echo hi | kubectl apply -f -", "aks-prod", BLOCKED),
    ("echo $(kubectl get ns)", "aks-prod", BLOCKED),
    ("kubectl config use-context kind-triage", "aks-prod", ALLOWED),
    ("kubectl config use-context aks-prod", "kind-triage", BLOCKED),
    ("kubectx aks-prod", "kind-triage", BLOCKED),
    ("helm list -A", "kind-triage", ALLOWED),
    ("helm install web ./chart", "aks-prod", BLOCKED),
    ("helm --kube-context kind-triage list", "aks-prod", ALLOWED),
    ("stern web", "aks-prod", BLOCKED),
    ("KUBECONFIG=/tmp/other kubectl get pods", "kind-triage", BLOCKED),
    ("kubectl --kubeconfig /tmp/other get pods", "kind-triage", BLOCKED),
    # Invocations the original token regex missed (fixed in the same commit as this test):
    ("/usr/local/bin/kubectl get pods", "aks-prod", BLOCKED),
    ("sh -c 'kubectl get pods'", "aks-prod", BLOCKED),
    ('bash -c "kubectl delete ns web"', "aks-prod", BLOCKED),
    ("sh -c 'kubectl get pods'", "kind-triage", ALLOWED),
]


@pytest.mark.parametrize(("command", "current", "expected"), CASES)
def test_hook_decision(fake_path: Path, command: str, current: str, expected: int) -> None:
    result = run_hook(bash_payload(command), fake_path, current)
    assert result.returncode == expected, result.stderr
    if expected == BLOCKED:
        assert "Blocked by guard_kube_context" in result.stderr


def test_blocks_when_kubectl_is_missing_so_context_is_unknown(tmp_path: Path) -> None:
    """No kubectl on PATH -> current context unknown -> fail closed."""
    empty = tmp_path / "empty"
    empty.mkdir()
    result = run_hook(bash_payload("kubectl get pods"), empty)
    assert result.returncode == BLOCKED
    assert "<unknown>" in result.stderr


def test_malformed_payload_is_left_to_claude_code(fake_path: Path) -> None:
    assert run_hook("{not json", fake_path).returncode == ALLOWED
