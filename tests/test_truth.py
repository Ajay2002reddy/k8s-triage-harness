"""truth.yaml schema: the parser must reject anything that would make grading ambiguous."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from triage.evals.truth import TruthError, load_truth, parse_truth
from triage.taxonomy import Category

VALID: dict[str, Any] = {
    "id": "example-fault",
    "namespace": "shop",
    "category": "oom",
    "root_cause": "Memory limit 64Mi is below what the worker allocates",
    "evidence": ["lastState.terminated.reason is OOMKilled"],
    "fix": "Raise the memory limit",
    "requires": [],
    "difficulty": "easy",
}


def test_valid_document_parses() -> None:
    truth = parse_truth(VALID)
    assert truth.category is Category.OOM
    assert truth.requires == ()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"category": "out_of_memory"}, "not in triage.taxonomy.Category"),
        ({"category": None}, "'category' must be a non-empty string"),
        ({"id": "Example_Fault"}, "kebab-case"),
        ({"namespace": "Shop"}, "DNS label"),
        ({"evidence": []}, "non-empty list"),
        ({"evidence": "one string"}, "non-empty list"),
        ({"evidence": ["ok", ""]}, "only non-empty strings"),
        ({"requires": ["istio"]}, "'requires'"),
        ({"requires": [{"x": 1}]}, "'requires'"),
        ({"requires": "metrics-server"}, "'requires'"),
        ({"difficulty": "trivial"}, "'difficulty'"),
        ({"difficulty": ["easy"]}, "'difficulty'"),
        ({"extra": 1}, "unknown fields: extra"),
    ],
)
def test_invalid_documents_are_rejected(change: dict[str, Any], message: str) -> None:
    with pytest.raises(TruthError, match=message):
        parse_truth({**VALID, **change})


def test_missing_field_is_reported() -> None:
    doc = {k: v for k, v in VALID.items() if k != "fix"}
    with pytest.raises(TruthError, match="missing fields: fix"):
        parse_truth(doc)


def test_id_must_match_folder(tmp_path: Path) -> None:
    folder = tmp_path / "other-name"
    folder.mkdir()
    (folder / "truth.yaml").write_text(yaml.safe_dump(VALID))
    with pytest.raises(TruthError, match="doesn't match folder"):
        load_truth(folder)


def test_cli_matrix_lists_faults_with_requirements(tmp_path: Path) -> None:
    for fault_id, requires in [("a-fault", []), ("b-fault", ["metrics-server"])]:
        (tmp_path / fault_id).mkdir()
        doc = {**VALID, "id": fault_id, "requires": requires}
        (tmp_path / fault_id / "truth.yaml").write_text(yaml.safe_dump(doc))
    result = subprocess.run(
        [sys.executable, "-m", "triage.evals.truth", "--root", str(tmp_path), "matrix"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == [
        {"id": "a-fault", "requires": ""},
        {"id": "b-fault", "requires": "metrics-server"},
    ]
