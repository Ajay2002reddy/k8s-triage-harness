"""Ground truth for each fault: ``faults/<id>/truth.yaml``.

The schema is the add-fault skill's contract (.claude/skills/add-fault/SKILL.md). M1 uses
it to validate the fault library and to build the CI matrix; M4 will grade agent answers
against ``category``. The agent must never read these files: its tools only see the
cluster.

CLI (run from the repo root):
  python -m triage.evals.truth matrix          # JSON list for the CI fault matrix
  python -m triage.evals.truth requires <id>   # one requirement per line
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from triage.taxonomy import Category

FIELDS = ("id", "namespace", "category", "root_cause", "evidence", "fix", "requires", "difficulty")
REQUIREMENTS = frozenset({"ingress-nginx", "metrics-server", "multi-node", "cert-manager"})
DIFFICULTIES = frozenset({"easy", "medium", "hard"})
ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
DNS_LABEL_RE = re.compile(r"[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?")


class TruthError(ValueError):
    """truth.yaml doesn't follow the schema."""


@dataclass(frozen=True)
class Truth:
    id: str
    namespace: str
    category: Category
    root_cause: str
    evidence: tuple[str, ...]
    fix: str
    requires: tuple[str, ...]
    difficulty: str


def _text(doc: dict[str, Any], key: str, problems: list[str]) -> str:
    value = doc.get(key)
    if not isinstance(value, str) or not value.strip():
        problems.append(f"'{key}' must be a non-empty string")
        return ""
    return value


def _text_list(doc: dict[str, Any], key: str, problems: list[str]) -> tuple[str, ...]:
    value = doc.get(key)
    if not isinstance(value, list) or not value:
        problems.append(f"'{key}' must be a non-empty list of strings")
        return ()
    if not all(isinstance(v, str) and v.strip() for v in value):
        problems.append(f"'{key}' must contain only non-empty strings")
        return ()
    return tuple(value)


def parse_truth(doc: Any, source: str = "truth.yaml") -> Truth:
    """Validate a parsed truth.yaml; raise TruthError listing every problem found."""
    if not isinstance(doc, dict):
        raise TruthError(f"{source}: top level must be a mapping")
    problems: list[str] = []
    missing = [f for f in FIELDS if f not in doc]
    unknown = sorted(set(doc) - set(FIELDS))
    if missing:
        problems.append(f"missing fields: {', '.join(missing)}")
    if unknown:
        problems.append(f"unknown fields: {', '.join(unknown)}")

    fault_id = _text(doc, "id", problems)
    if fault_id and not ID_RE.fullmatch(fault_id):
        problems.append(f"'id' must be kebab-case, got {fault_id!r}")
    namespace = _text(doc, "namespace", problems)
    if namespace and not DNS_LABEL_RE.fullmatch(namespace):
        problems.append(f"'namespace' must be a DNS label, got {namespace!r}")
    raw_category = _text(doc, "category", problems)
    category = None
    if raw_category:
        try:
            category = Category(raw_category)
        except ValueError:
            problems.append(f"'category' {raw_category!r} is not in triage.taxonomy.Category")
    root_cause = _text(doc, "root_cause", problems)
    fix = _text(doc, "fix", problems)
    evidence = _text_list(doc, "evidence", problems)
    requires = doc.get("requires")
    if not isinstance(requires, list) or not all(
        isinstance(r, str) and r in REQUIREMENTS for r in requires
    ):
        problems.append(f"'requires' must be a list drawn from {sorted(REQUIREMENTS)}")
        requires = []
    difficulty = doc.get("difficulty")
    if not isinstance(difficulty, str) or difficulty not in DIFFICULTIES:
        problems.append(f"'difficulty' must be one of {sorted(DIFFICULTIES)}")

    if problems or category is None:
        raise TruthError(f"{source}: " + "; ".join(problems))
    return Truth(
        id=fault_id,
        namespace=namespace,
        category=category,
        root_cause=root_cause,
        evidence=evidence,
        fix=fix,
        requires=tuple(requires),
        difficulty=str(difficulty),
    )


def load_truth(fault_dir: Path) -> Truth:
    path = fault_dir / "truth.yaml"
    truth = parse_truth(yaml.safe_load(path.read_text()), str(path))
    if truth.id != fault_dir.name:
        raise TruthError(f"{path}: id {truth.id!r} doesn't match folder {fault_dir.name!r}")
    return truth


def fault_dirs(root: Path) -> list[Path]:
    """Every fault folder under ``root`` (sub-directories; files like a README are skipped)."""
    return sorted(p for p in root.iterdir() if p.is_dir())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m triage.evals.truth")
    parser.add_argument("--root", type=Path, default=Path("faults"), help="fault library folder")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("matrix", help="print the CI matrix as JSON")
    requires = sub.add_parser("requires", help="print a fault's cluster requirements")
    requires.add_argument("fault_id")
    args = parser.parse_args(argv)

    try:
        if args.command == "matrix":
            rows = [
                {"id": t.id, "requires": " ".join(t.requires)}
                for t in (load_truth(d) for d in fault_dirs(args.root))
            ]
            print(json.dumps(rows))
        else:
            for requirement in load_truth(args.root / args.fault_id).requires:
                print(requirement)
    except (OSError, TruthError, yaml.YAMLError) as exc:
        print(f"truth: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
