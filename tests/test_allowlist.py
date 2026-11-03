"""Cluster allowlist: the harness may only target local kind-*/k3d-* clusters.

Written before src/triage/harness/allowlist.py. Every refusal case is a way an
employer cluster could be reached by accident; see docs/adr/002-cluster-allowlist.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from triage.harness.allowlist import (
    ContextNotAllowedError,
    is_allowed_context_name,
    is_local_server,
    kubeconfig_paths,
    resolve_target,
)

LOCAL = "https://127.0.0.1:6443"
REMOTE = "https://prod-dns-1a2b3c.hcp.westeurope.azmk8s.io:443"


def write_kubeconfig(
    path: Path,
    contexts: dict[str, str],
    current: str | None = None,
    cluster_suffix: str = "",
) -> Path:
    """Write a kubeconfig. ``contexts`` maps context name -> API server URL."""
    doc: dict[str, object] = {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [
            {"name": f"{name}{cluster_suffix}", "cluster": {"server": server}}
            for name, server in contexts.items()
        ],
        "contexts": [
            {"name": name, "context": {"cluster": f"{name}{cluster_suffix}", "user": "me"}}
            for name in contexts
        ],
        "users": [{"name": "me", "user": {}}],
    }
    if current is not None:
        doc["current-context"] = current
    path.write_text(yaml.safe_dump(doc))
    return path


def env_for(*paths: Path) -> dict[str, str]:
    return {"KUBECONFIG": ":".join(str(p) for p in paths), "HOME": "/nonexistent"}


# --- context names -------------------------------------------------------------------


@pytest.mark.parametrize("name", ["kind-kind", "kind-triage", "k3d-dev", "kind-a.b-1"])
def test_allowed_context_names(name: str) -> None:
    assert is_allowed_context_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "kind",  # no cluster part
        "kind-",
        "k3d",
        "minikube",
        "docker-desktop",
        "default",  # k3s/microk8s default context: not allowed without an ADR
        "aks-prod",
        "prod-kind-x",
        "xkind-dev",  # prefix must be at the start
        "KIND-dev",  # case matters
        "kind_dev",
        " kind-dev",
        "kind-dev\n",  # trailing newline must not slip through a `$` anchor
        "kind-dev prod",
        "kind-dev;rm",
        "k" + chr(0x456) + "nd-dev",  # Cyrillic lookalike of "i"
    ],
)
def test_refused_context_names(name: str) -> None:
    assert not is_allowed_context_name(name)


# --- API server ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "server",
    [
        "https://127.0.0.1:6443",
        "https://127.0.0.1:41235",
        "https://127.0.0.2:6443",
        "https://localhost:6443",
        "https://[::1]:6443",
        "https://0.0.0.0:6550",  # k3d's default
    ],
)
def test_local_servers(server: str) -> None:
    assert is_local_server(server)


@pytest.mark.parametrize(
    "server",
    [
        REMOTE,
        "https://10.0.0.1:6443",
        "https://192.168.49.2:8443",
        "https://localhost.example.com:6443",
        "https://127.0.0.1.nip.io:6443",
        "https://user@10.1.2.3:6443",
        "http://127.0.0.1:8001",  # plain http: e.g. `kubectl proxy` to a remote cluster
        "https://[::1",  # unparsable
        "not a url",
        "",
    ],
)
def test_non_local_servers(server: str) -> None:
    assert not is_local_server(server)


# --- resolving the target ------------------------------------------------------------


def test_current_context_is_used_when_no_explicit_context(tmp_path: Path) -> None:
    cfg = write_kubeconfig(tmp_path / "config", {"kind-triage": LOCAL}, current="kind-triage")
    target = resolve_target(env=env_for(cfg))
    assert target.context == "kind-triage"
    assert target.server == LOCAL


def test_explicit_context_overrides_current_context(tmp_path: Path) -> None:
    cfg = write_kubeconfig(
        tmp_path / "config", {"aks-prod": REMOTE, "kind-triage": LOCAL}, current="aks-prod"
    )
    assert resolve_target(context="kind-triage", env=env_for(cfg)).context == "kind-triage"


def test_explicit_disallowed_context_is_refused_even_if_current_is_allowed(
    tmp_path: Path,
) -> None:
    cfg = write_kubeconfig(
        tmp_path / "config", {"aks-prod": REMOTE, "kind-triage": LOCAL}, current="kind-triage"
    )
    with pytest.raises(ContextNotAllowedError, match="aks-prod"):
        resolve_target(context="aks-prod", env=env_for(cfg))


def test_disallowed_current_context_is_refused(tmp_path: Path) -> None:
    cfg = write_kubeconfig(tmp_path / "config", {"aks-prod": REMOTE}, current="aks-prod")
    with pytest.raises(ContextNotAllowedError, match="aks-prod"):
        resolve_target(env=env_for(cfg))


def test_empty_explicit_context_falls_back_to_current_like_kubectl(tmp_path: Path) -> None:
    cfg = write_kubeconfig(tmp_path / "config", {"aks-prod": REMOTE}, current="aks-prod")
    with pytest.raises(ContextNotAllowedError, match="aks-prod"):
        resolve_target(context="", env=env_for(cfg))


@pytest.mark.parametrize("current", [None, ""])
def test_missing_or_empty_current_context_fails_closed(tmp_path: Path, current: str | None) -> None:
    cfg = write_kubeconfig(tmp_path / "config", {"kind-triage": LOCAL}, current=current)
    with pytest.raises(ContextNotAllowedError, match="no context"):
        resolve_target(env=env_for(cfg))


def test_allowed_name_that_is_not_in_kubeconfig_fails_closed(tmp_path: Path) -> None:
    cfg = write_kubeconfig(tmp_path / "config", {"kind-triage": LOCAL}, current="kind-triage")
    with pytest.raises(ContextNotAllowedError, match="not found"):
        resolve_target(context="kind-other", env=env_for(cfg))


def test_context_pointing_at_unknown_cluster_fails_closed(tmp_path: Path) -> None:
    cfg = tmp_path / "config"
    cfg.write_text(
        yaml.safe_dump(
            {
                "current-context": "kind-triage",
                "contexts": [{"name": "kind-triage", "context": {"cluster": "ghost"}}],
                "clusters": [],
            }
        )
    )
    with pytest.raises(ContextNotAllowedError, match="ghost"):
        resolve_target(env=env_for(cfg))


def test_kind_named_context_pointing_at_a_remote_server_is_refused(tmp_path: Path) -> None:
    """A context name is just a string: a renamed AKS context must still be refused."""
    cfg = write_kubeconfig(tmp_path / "config", {"kind-prod": REMOTE}, current="kind-prod")
    with pytest.raises(ContextNotAllowedError, match="non-local API server"):
        resolve_target(env=env_for(cfg))


def test_missing_kubeconfig_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ContextNotAllowedError, match="no kubeconfig"):
        resolve_target(env=env_for(tmp_path / "does-not-exist"))


@pytest.mark.parametrize(
    "content",
    [
        "current-context: [unclosed",  # invalid YAML
        "- just\n- a list\n",  # not a mapping
        "current-context: kind-x\ncontexts: {kind-x: {}}\n",  # contexts must be a list
        "current-context: kind-x\ncontexts:\n- context: {cluster: c}\n",  # entry without name
    ],
)
def test_malformed_kubeconfig_fails_closed(tmp_path: Path, content: str) -> None:
    cfg = tmp_path / "config"
    cfg.write_text(content)
    with pytest.raises(ContextNotAllowedError, match="malformed kubeconfig"):
        resolve_target(context="kind-x", env=env_for(cfg))


# --- kubeconfig selection and merging (same rules as kubectl) --------------------------


def test_custom_kubeconfig_argument_wins_over_env(tmp_path: Path) -> None:
    from_env = write_kubeconfig(tmp_path / "env", {"aks-prod": REMOTE}, current="aks-prod")
    custom = write_kubeconfig(tmp_path / "custom", {"kind-triage": LOCAL}, current="kind-triage")
    target = resolve_target(kubeconfig=custom, env=env_for(from_env))
    assert target.context == "kind-triage"
    assert target.kubeconfig == (custom,)


def test_custom_kubeconfig_can_still_be_refused(tmp_path: Path) -> None:
    custom = write_kubeconfig(tmp_path / "custom", {"aks-prod": REMOTE}, current="aks-prod")
    with pytest.raises(ContextNotAllowedError):
        resolve_target(kubeconfig=custom, env={})


def test_default_kubeconfig_is_home_kube_config(tmp_path: Path) -> None:
    (tmp_path / ".kube").mkdir()
    write_kubeconfig(tmp_path / ".kube" / "config", {"kind-triage": LOCAL}, current="kind-triage")
    assert kubeconfig_paths(env={"HOME": str(tmp_path)}) == [tmp_path / ".kube" / "config"]
    assert resolve_target(env={"HOME": str(tmp_path)}).context == "kind-triage"


def test_kubeconfig_env_list_first_current_context_wins(tmp_path: Path) -> None:
    first = write_kubeconfig(tmp_path / "a", {"aks-prod": REMOTE}, current="aks-prod")
    second = write_kubeconfig(tmp_path / "b", {"kind-triage": LOCAL}, current="kind-triage")
    with pytest.raises(ContextNotAllowedError, match="aks-prod"):
        resolve_target(env=env_for(first, second))
    assert resolve_target(env=env_for(second, first)).context == "kind-triage"


def test_kubeconfig_env_list_first_definition_of_a_context_wins(tmp_path: Path) -> None:
    """Same context name in two files: kubectl uses the first. So must we."""
    local = write_kubeconfig(tmp_path / "a", {"kind-dev": LOCAL}, current="kind-dev")
    shadow = write_kubeconfig(tmp_path / "b", {"kind-dev": REMOTE}, cluster_suffix="-remote")
    assert resolve_target(env=env_for(local, shadow)).server == LOCAL
    with pytest.raises(ContextNotAllowedError, match="non-local"):
        resolve_target(env=env_for(shadow, local))


def test_missing_files_in_kubeconfig_list_are_skipped(tmp_path: Path) -> None:
    cfg = write_kubeconfig(tmp_path / "config", {"kind-triage": LOCAL}, current="kind-triage")
    target = resolve_target(env=env_for(tmp_path / "missing", cfg))
    assert target.context == "kind-triage"


# --- CLI used by the fault scripts -----------------------------------------------------


def run_cli(*args: str, kubeconfig: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "triage.harness.allowlist", *args],
        capture_output=True,
        text=True,
        env={"KUBECONFIG": str(kubeconfig), "HOME": "/nonexistent"},
        check=False,
    )


def test_cli_prints_the_allowed_context(tmp_path: Path) -> None:
    cfg = write_kubeconfig(tmp_path / "config", {"kind-triage": LOCAL}, current="kind-triage")
    result = run_cli(kubeconfig=cfg)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "kind-triage\n"


def test_cli_refuses_with_exit_1_and_no_stdout(tmp_path: Path) -> None:
    cfg = write_kubeconfig(tmp_path / "config", {"aks-prod": REMOTE}, current="aks-prod")
    result = run_cli("--context", "aks-prod", kubeconfig=cfg)
    assert result.returncode == 1
    assert result.stdout == ""  # callers do CTX=$(...): a refusal must never look like a name
    assert "refused" in result.stderr
