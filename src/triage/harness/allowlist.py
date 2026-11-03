"""Cluster allowlist: the harness only ever talks to a local kind or k3d cluster.

Hard constraint #1 in docs/PROJECT_BRIEF.md; the design is in docs/adr/002-cluster-allowlist.md.

Two checks, both fail closed (anything we can't positively verify is refused):
1. The context name fully matches ``(kind|k3d)-<cluster name>``.
2. That context's cluster has an https API server on a loopback or unspecified address,
   because a context name is only a string: anyone can rename an AKS context "kind-x".

The kubeconfig is resolved with kubectl's rules (``--kubeconfig``, else ``$KUBECONFIG``
as a path list where the first file to set a key wins, else ``~/.kube/config``), so the
context we check is the one kubectl would use. Callers must then pass
``--context <target.context>`` on every kubectl call, so a later ``use-context`` can't
redirect them.

CLI for shell scripts: ``python -m triage.harness.allowlist [--context X]`` prints the
allowed context name, or prints the reason to stderr and exits 1.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

# kind accepts cluster names matching ^[a-z0-9.-]+$ (sigs.k8s.io/kind, validate.go).
ALLOWED_CONTEXT = re.compile(r"(?:kind|k3d)-[a-z0-9.-]+", re.ASCII)


class ContextNotAllowedError(Exception):
    """The target cluster is not provably a local kind/k3d cluster."""


@dataclass(frozen=True)
class ClusterTarget:
    """A context that passed every check, with what it resolves to."""

    context: str
    cluster: str
    server: str
    kubeconfig: tuple[Path, ...]


def is_allowed_context_name(name: str) -> bool:
    # fullmatch, not match + "$": "$" would also accept a trailing newline.
    return ALLOWED_CONTEXT.fullmatch(name) is not None


def is_local_server(server: str) -> bool:
    """True for an https URL whose host is localhost, a loopback IP or 0.0.0.0 (k3d)."""
    try:
        url = urlsplit(server)
        host = url.hostname
    except ValueError:
        return False
    if url.scheme != "https" or host is None:
        return False
    if host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:  # any other DNS name could resolve anywhere
        return False
    return ip.is_loopback or ip.is_unspecified


def kubeconfig_paths(
    kubeconfig: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> list[Path]:
    """The kubeconfig files kubectl would read, in precedence order."""
    if kubeconfig:
        return [Path(kubeconfig)]
    env = os.environ if env is None else env
    listed = [Path(p) for p in env.get("KUBECONFIG", "").split(os.pathsep) if p]
    if listed:
        return listed
    home = env.get("HOME") or str(Path.home())
    return [Path(home) / ".kube" / "config"]


@dataclass(frozen=True)
class _Kubeconfig:
    current_context: str
    contexts: dict[str, str]  # context name -> cluster name
    servers: dict[str, str]  # cluster name -> API server URL


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _read(path: Path) -> dict[str, Any]:
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ContextNotAllowedError(f"malformed kubeconfig {path}: {exc}") from exc
    except OSError as exc:
        raise ContextNotAllowedError(f"unreadable kubeconfig {path}: {exc}") from exc
    if doc is None:  # an empty file is an empty config
        return {}
    if not isinstance(doc, dict):
        raise ContextNotAllowedError(f"malformed kubeconfig {path}: top level is not a mapping")
    return doc


def _entries(doc: dict[str, Any], key: str, path: Path) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (name, body) for each entry of the 'contexts' or 'clusters' list."""
    items = doc.get(key) or []
    if not isinstance(items, list):
        raise ContextNotAllowedError(f"malformed kubeconfig {path}: '{key}' is not a list")
    for item in items:
        name = item.get("name") if isinstance(item, dict) else None
        body = item.get(key.removesuffix("s")) if isinstance(item, dict) else None
        if not isinstance(name, str) or not name or not isinstance(body, dict | None):
            raise ContextNotAllowedError(f"malformed kubeconfig {path}: bad entry in '{key}'")
        yield name, body or {}


def _load(paths: Sequence[Path]) -> _Kubeconfig:
    """Merge kubeconfig files like kubectl: for every key, the first file that sets it wins."""
    current = ""
    contexts: dict[str, str] = {}
    servers: dict[str, str] = {}
    found = False
    for path in paths:
        if not path.is_file():
            continue  # kubectl skips missing files in a $KUBECONFIG list
        found = True
        doc = _read(path)
        current = current or _as_str(doc.get("current-context"))
        for name, body in _entries(doc, "contexts", path):
            contexts.setdefault(name, _as_str(body.get("cluster")))
        for name, body in _entries(doc, "clusters", path):
            servers.setdefault(name, _as_str(body.get("server")))
    if not found:
        looked = ", ".join(str(p) for p in paths)
        raise ContextNotAllowedError(f"no kubeconfig file found (looked at: {looked})")
    return _Kubeconfig(current, contexts, servers)


def resolve_target(
    context: str | None = None,
    kubeconfig: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> ClusterTarget:
    """Return the cluster kubectl would talk to, or raise ContextNotAllowedError.

    ``context`` is the explicit --context (empty means "use current-context", as in
    kubectl). ``env`` defaults to os.environ; tests pass their own.
    """
    paths = kubeconfig_paths(kubeconfig, env)
    config = _load(paths)
    name = context or config.current_context
    if not name:
        raise ContextNotAllowedError(
            "no context selected (current-context is empty); pass --context kind-<name>"
        )
    if not is_allowed_context_name(name):
        raise ContextNotAllowedError(f"context {name!r} is not a kind-*/k3d-* context")
    cluster = config.contexts.get(name)
    if cluster is None:
        raise ContextNotAllowedError(f"context {name!r} not found in kubeconfig")
    server = config.servers.get(cluster)
    if server is None:
        raise ContextNotAllowedError(
            f"context {name!r} uses cluster {cluster!r}, which the kubeconfig doesn't define"
        )
    if not is_local_server(server):
        raise ContextNotAllowedError(
            f"context {name!r} points at non-local API server {server!r}; "
            "only https on loopback/0.0.0.0 counts as kind/k3d"
        )
    return ClusterTarget(context=name, cluster=cluster, server=server, kubeconfig=tuple(paths))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m triage.harness.allowlist",
        description="Print the kube context if it is a local kind/k3d cluster; exit 1 if not.",
    )
    parser.add_argument("--context", help="context to check instead of current-context")
    parser.add_argument("--kubeconfig", help="kubeconfig file instead of $KUBECONFIG")
    args = parser.parse_args(argv)
    try:
        target = resolve_target(context=args.context, kubeconfig=args.kubeconfig)
    except ContextNotAllowedError as exc:
        print(f"allowlist: refused: {exc}", file=sys.stderr)
        return 1
    print(target.context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
