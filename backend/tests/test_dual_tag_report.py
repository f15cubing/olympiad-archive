"""Unit tests for the dual-tag agreement report helpers (Phase B)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dual_tag_report import _jaccard  # noqa: E402


def test_jaccard_identical():
    assert _jaccard(["induction", "pigeonhole"], ["pigeonhole", "induction"]) == 1.0


def test_jaccard_disjoint():
    assert _jaccard(["algebra"], ["geometry"]) == 0.0


def test_jaccard_partial():
    # {a,b} vs {b,c} -> intersection 1, union 3
    assert _jaccard(["a", "b"], ["b", "c"]) == round(1 / 3, 2)


def test_jaccard_both_empty():
    assert _jaccard([], []) == 1.0


def test_jaccard_normalizes_aliases():
    # normalize_topic maps "functional equation" -> "functional equations"
    assert _jaccard(["functional equation"], ["functional equations"]) == 1.0
