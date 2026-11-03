"""Pinned versions stay pinned and consistent (brief: hard constraint #6)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def read_versions() -> dict[str, str]:
    pairs = {}
    for line in (ROOT / "cluster" / "versions.env").read_text().splitlines():
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            pairs[key] = value
    return pairs


def test_every_tool_has_a_version_and_a_sha256() -> None:
    versions = read_versions()
    tools = {key.removesuffix("_VERSION") for key in versions if key.endswith("_VERSION")}
    assert tools, "no tools pinned"
    for tool in tools:
        assert re.fullmatch(r"v?\d+\.\d+\.\d+", versions[f"{tool}_VERSION"]), tool
        assert re.fullmatch(r"[0-9a-f]{64}", versions.get(f"{tool}_SHA256", "")), tool


def test_kind_node_image_is_digest_pinned_and_matches_kubectl() -> None:
    config = yaml.safe_load((ROOT / "cluster" / "kind-config.yaml").read_text())
    images = [node["image"] for node in config["nodes"]]
    assert images, "kind config must pin a node image"
    for image in images:
        match = re.fullmatch(r"kindest/node:(v\d+\.\d+\.\d+)@sha256:[0-9a-f]{64}", image)
        assert match, f"node image must be pinned by tag and digest: {image}"
        assert match.group(1) == read_versions()["KUBECTL_VERSION"], "kubectl/node version skew"


def test_vendored_metrics_server_is_byte_identical_to_upstream() -> None:
    vendored = ROOT / "cluster" / "addons" / "metrics-server" / "components.yaml"
    digest = hashlib.sha256(vendored.read_bytes()).hexdigest()
    assert digest == read_versions()["METRICS_SERVER_SHA256"], "edit the kustomize patch instead"


def test_github_actions_are_pinned_to_commit_shas() -> None:
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows
    uses = [
        line.split("uses:", 1)[1].split("#", 1)[0].strip()
        for wf in workflows
        for line in wf.read_text().splitlines()
        if line.strip().startswith(("uses:", "- uses:"))
    ]
    assert uses
    for ref in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", ref), f"not SHA-pinned: {ref}"
