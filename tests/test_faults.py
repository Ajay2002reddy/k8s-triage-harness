"""Static checks of the fault library's contract (add-fault skill, ADR-003).

These run anywhere. Whether each symptom really appears on a cluster is checked in CI
by .github/workflows/faults.yml (scripts/verify-fault.sh).
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from triage.evals.truth import fault_dirs, load_truth
from triage.taxonomy import Category

ROOT = Path(__file__).resolve().parents[1]
FAULTS = fault_dirs(ROOT / "faults")
IDS = [f.name for f in FAULTS]
SCRIPTS = ("inject.sh", "check.sh", "reset.sh")
ALL_SHELL = sorted([*ROOT.glob("scripts/*.sh"), *ROOT.glob("faults/*/*.sh")])
RESERVED_NAMESPACES = {
    "default",
    "kube-system",
    "kube-public",
    "kube-node-lease",
    "local-path-storage",
    "ingress-nginx",
}
# Words that would hint at the answer if the agent saw them in a name, label or annotation.
GIVEAWAYS = (
    "fault",
    "broken",
    "break",
    "bug",
    "fail",
    "error",
    "wrong",
    "bad",
    "missing",
    "invalid",
    "typo",
    "crash",
    "oom",
    "mismatch",
    "misconfig",
    "unbound",
    "exceed",
    "forbid",
    "denied",
    "timeout",
    "taint",
    "inject",
    "chaos",
    "test",
    "debug",
    "bench",
    "triage",
)
IDENTIFIER_KEYS = {"name", "namespace", "serviceAccountName", "claimName", "storageClassName"}
LABEL_KEYS = {"labels", "annotations", "matchLabels", "selector"}


def manifests(fault: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for path in sorted((fault / "manifests").glob("*.yaml")):
        docs += [doc for doc in yaml.safe_load_all(path.read_text()) if doc]
    return docs


def visible_identifiers(node: Any) -> Iterator[str]:
    """Names, namespaces, label and annotation keys/values: what `get` shows the agent."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in LABEL_KEYS and isinstance(value, dict):
                yield from (str(k) for k in value)
                yield from (v for v in value.values() if isinstance(v, str))
            elif key in IDENTIFIER_KEYS and isinstance(value, str):
                yield value
            yield from visible_identifiers(value)
    elif isinstance(node, list):
        for item in node:
            yield from visible_identifiers(item)


def images(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "image" and isinstance(value, str):
                yield value
            yield from images(value)
    elif isinstance(node, list):
        for item in node:
            yield from images(item)


def code_lines(script: Path) -> list[str]:
    return [line for line in script.read_text().splitlines() if not line.lstrip().startswith("#")]


def test_library_has_at_least_12_faults() -> None:
    assert len(FAULTS) >= 12


@pytest.mark.parametrize("fault", FAULTS, ids=IDS)
def test_folder_contract(fault: Path) -> None:
    for name in (*SCRIPTS, "truth.yaml", "README.md"):
        assert (fault / name).is_file(), f"missing {name}"
    assert list((fault / "manifests").glob("*.yaml")), "missing manifests/*.yaml"
    for name in SCRIPTS:
        script = fault / name
        assert script.stat().st_mode & 0o111, f"{name} is not executable"
        text = script.read_text()
        assert text.startswith("#!/usr/bin/env bash\n"), name
        assert "/../../scripts/lib.sh" in text, f"{name} must source scripts/lib.sh"
        assert "\nload_fault\n" in text, f"{name} must call load_fault"
    readme_lines = [line for line in (fault / "README.md").read_text().splitlines() if line]
    assert 3 <= len(readme_lines) <= 6, "README.md: a title plus 3-5 short lines"


@pytest.mark.parametrize("fault", FAULTS, ids=IDS)
def test_truth_is_valid_and_parseable_by_the_scripts(fault: Path) -> None:
    truth = load_truth(fault)  # raises TruthError on any schema problem
    assert truth.category in Category
    assert truth.namespace not in RESERVED_NAMESPACES
    # scripts/lib.sh reads the namespace with sed, so it must be a plain line.
    text = (fault / "truth.yaml").read_text()
    assert re.search(rf"^namespace: {re.escape(truth.namespace)}$", text, re.MULTILINE)


def test_namespaces_are_unique() -> None:
    namespaces = [load_truth(f).namespace for f in FAULTS]
    assert len(namespaces) == len(set(namespaces))


@pytest.mark.parametrize("fault", FAULTS, ids=IDS)
def test_everything_lives_in_the_fault_namespace(fault: Path) -> None:
    """Reset deletes the namespace; a cluster-scoped object would survive it."""
    namespace = load_truth(fault).namespace
    docs = manifests(fault)
    assert docs[0]["kind"] == "Namespace", "the Namespace must be applied first"
    assert docs[0]["metadata"]["name"] == namespace
    for doc in docs[1:]:
        where = f"{doc['kind']}/{doc['metadata']['name']}"
        assert doc["metadata"].get("namespace") == namespace, where


@pytest.mark.parametrize("fault", FAULTS, ids=IDS)
def test_images_are_pinned_and_avoid_docker_hub(fault: Path) -> None:
    found = list(images(manifests(fault)))
    assert found
    for image in found:
        registry, _, rest = image.partition("/")
        assert "." in registry, f"{image}: name the registry explicitly (no implicit Docker Hub)"
        assert ":" in rest, f"{image}: pin a tag"
        assert not image.endswith(":latest"), image


CATEGORY_WORDS = {c.value for c in Category} | {c.value.replace("_", "-") for c in Category}


def leaks(identifier: str) -> list[str]:
    lowered = identifier.lower()
    return list(dict.fromkeys(w for w in (*GIVEAWAYS, *sorted(CATEGORY_WORDS)) if w in lowered))


def kubectl_calls(lines: list[str]) -> list[str]:
    return [line for line in lines if re.search(r"(^|[^\w/.-])kubectl\b", line)]


def test_detectors_catch_bad_input() -> None:
    """The two guards below must actually fire, or their passing means nothing."""
    leaky = {
        "metadata": {"name": "oom-test", "namespace": "shop", "labels": {"app": "api"}},
        "spec": {"selector": {"scenario": "broken-dns"}, "template": {"spec": {"containers": []}}},
    }
    found = {i: leaks(i) for i in visible_identifiers(leaky)}
    assert found["oom-test"] == ["oom", "test"]
    assert "fault" not in found.get("shop", [])
    assert leaks("broken-dns") == ["broken", "dns"]
    assert kubectl_calls(["kubectl get pods", "x=$(kubectl get ns)", "k get pods"]) == [
        "kubectl get pods",
        "x=$(kubectl get ns)",
    ]
    assert kubectl_calls(["curl -o /usr/local/bin/kubectl.sha256 url"]) == []


@pytest.mark.parametrize("fault", FAULTS, ids=IDS)
def test_no_answer_leaks_into_the_cluster(fault: Path) -> None:
    truth = load_truth(fault)
    category_words = CATEGORY_WORDS
    for identifier in visible_identifiers(manifests(fault)):
        assert not leaks(identifier), f"{identifier!r} hints at the answer: {leaks(identifier)}"
    # Anywhere in the manifest text: no fault id and no multi-word category name
    # (single words like "dns" also occur legitimately, e.g. dnsPolicy).
    text = "\n".join(p.read_text() for p in (fault / "manifests").glob("*.yaml")).lower()
    for word in {truth.id} | {w for w in category_words if "_" in w or "-" in w}:
        assert word not in text, f"manifest text contains {word!r}"


@pytest.mark.parametrize("fault", FAULTS, ids=IDS)
def test_checks_poll_with_a_timeout_instead_of_sleeping(fault: Path) -> None:
    lines = code_lines(fault / "check.sh")
    assert any(re.match(r"\s*(wait_for|holds_for) ", line) for line in lines)
    assert not any(re.search(r"\bsleep\b", line) for line in lines)


@pytest.mark.parametrize("script", ALL_SHELL, ids=lambda p: str(p.relative_to(ROOT)))
def test_scripts_parse(script: Path) -> None:
    subprocess.run(["bash", "-n", str(script)], check=True)  # noqa: S607


def test_only_lib_sh_invokes_kubectl() -> None:
    """Every cluster call must go through `k` (pinned --context). install-tools only downloads."""
    allowed = {ROOT / "scripts" / "lib.sh", ROOT / "scripts" / "install-tools.sh"}
    offenders = [
        f"{script.relative_to(ROOT)}: {line.strip()}"
        for script in ALL_SHELL
        if script not in allowed
        for line in kubectl_calls(code_lines(script))
    ]
    assert not offenders, offenders
