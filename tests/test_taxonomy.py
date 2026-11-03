"""The category enum is the grading contract; changing it needs an ADR (CLAUDE.md)."""

from __future__ import annotations

import re

from triage.taxonomy import DEFINITIONS, Category

# Verbatim from docs/PROJECT_BRIEF.md. If this test fails, you changed what "accuracy"
# means: write an ADR, then update this list in the same PR.
BRIEF_CATEGORIES = {
    "image_pull",
    "bad_command",
    "oom",
    "probe_misconfig",
    "selector_mismatch",
    "port_mismatch",
    "ingress_backend_timeout",
    "tls_secret",
    "network_policy",
    "pvc_unbound",
    "quota_exceeded",
    "config_missing",
    "dns",
    "scheduling_taint",
    "rbac_forbidden",
    "hpa_misconfig",
}


def test_categories_match_the_brief_exactly() -> None:
    assert {c.value for c in Category} == BRIEF_CATEGORIES


def test_every_category_has_a_definition() -> None:
    assert set(DEFINITIONS) == set(Category)
    assert all(text.strip().endswith(".") for text in DEFINITIONS.values())


def test_values_are_snake_case_and_parse_back() -> None:
    for category in Category:
        assert re.fullmatch(r"[a-z]+(_[a-z]+)*", category.value)
        assert Category(category.value) is category
