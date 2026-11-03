"""scripts/lib.sh: the guard every cluster-touching shell script sources.

Runs the real lib.sh (and through it the Python allowlist) with a fake kubectl on PATH
that just echoes its arguments, so we can see exactly what would be executed.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "scripts" / "lib.sh"


def kubeconfig(path: Path, current: str) -> Path:
    servers = {"kind-triage": "https://127.0.0.1:6443", "aks-prod": "https://prod.example.com"}
    path.write_text(
        yaml.safe_dump(
            {
                "current-context": current,
                "clusters": [{"name": n, "cluster": {"server": s}} for n, s in servers.items()],
                "contexts": [{"name": n, "context": {"cluster": n}} for n in servers],
            }
        )
    )
    return path


def make_env(tmp_path: Path, current: str = "kind-triage", **extra: str) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "kubectl"
    fake.write_text('#!/bin/sh\necho "kubectl $*"\n')
    fake.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != "KUBE_CONTEXT"}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"  # uv and bash stay reachable
    env["KUBECONFIG"] = str(kubeconfig(tmp_path / "config", current))
    env.update(extra)
    return env


def run(snippet: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{LIB}"; {snippet}'],  # noqa: S607
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_k_pins_the_validated_context(tmp_path: Path) -> None:
    result = run("k get pods -n web", make_env(tmp_path))
    assert result.returncode == 0, result.stderr
    assert result.stdout == "kubectl --context kind-triage get pods -n web\n"


def test_sourcing_stops_on_a_disallowed_current_context(tmp_path: Path) -> None:
    result = run("echo reached", make_env(tmp_path, current="aks-prod"))
    assert result.returncode == 1
    assert "reached" not in result.stdout
    assert "refusing to touch this cluster" in result.stderr


def test_kube_context_override_is_validated_too(tmp_path: Path) -> None:
    result = run("echo reached", make_env(tmp_path, KUBE_CONTEXT="aks-prod"))
    assert result.returncode == 1
    assert "reached" not in result.stdout


TARGET_FLAGS = [
    "--context=aks-prod",
    "--context aks-prod",
    "--kubeconfig=/tmp/other",
    "--server=https://x",
    "-s x",
]


@pytest.mark.parametrize("flag", TARGET_FLAGS)
def test_k_refuses_flags_that_change_the_target(tmp_path: Path, flag: str) -> None:
    result = run(f"k get pods {flag}", make_env(tmp_path))
    assert result.returncode == 1
    assert "would bypass the cluster allowlist" in result.stderr
    assert "kubectl" not in result.stdout  # nothing was executed


@pytest.mark.parametrize(
    ("call", "expected"),
    [
        ('at_least 2 "0"', False),
        ('at_least 2 "1"', False),
        ('at_least 2 "2"', True),
        ('at_least 2 "10"', True),
        ('at_least 2 "0 3"', True),  # one value per pod: any pod counts
        ('at_least 2 "abc"', False),
        ('at_least 2 ""', False),
    ],
)
def test_at_least(tmp_path: Path, call: str, expected: bool) -> None:
    assert (run(call, make_env(tmp_path)).returncode == 0) is expected


def test_k_ignores_flags_meant_for_the_pod_command(tmp_path: Path) -> None:
    result = run("k exec deploy/web -- wget -s http://api/", make_env(tmp_path))
    assert result.returncode == 0, result.stderr
    assert result.stdout == "kubectl --context kind-triage exec deploy/web -- wget -s http://api/\n"
