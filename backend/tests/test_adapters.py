"""Tests for dataset adapters (scripts/adapters/)."""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "adapters"))

from base import normalize_statement  # noqa: E402
from imo_json import ImoJsonAdapter  # noqa: E402


# --------------------------------------------------------------- normalize_statement
def test_strips_markdown_emphasis():
    assert normalize_statement("A *sunny* line, **not** parallel.") == (
        "A sunny line, not parallel."
    )


def test_converts_display_math_to_inline():
    assert normalize_statement("Then $$a+b=c$$ holds.") == "Then $a+b=c$ holds."
    assert normalize_statement(r"Then \[a+b=c\] holds.") == "Then $a+b=c$ holds."
    assert normalize_statement(r"Then \(a+b\) holds.") == "Then $a+b$ holds."


def test_collapses_multiline_display_math():
    assert normalize_statement("$$\na +\nb = c\n$$") == "$a + b = c$"


def test_normalizes_bullets():
    assert normalize_statement("List:\n* one\n* two") == "List:\n- one\n- two"


def test_align_becomes_aligned():
    assert normalize_statement(r"$\begin{align} x&=1 \end{align}$") == (
        r"$\begin{aligned} x&=1 \end{aligned}$"
    )


def test_math_content_is_not_touched():
    # emphasis outside math is stripped; the math span is left intact
    assert normalize_statement(r"$a \le b$ and *x*") == r"$a \le b$ and x"


# --------------------------------------------------------------------- ImoJsonAdapter
def _write_json(tmp_path: Path, rows) -> Path:
    p = tmp_path / "src.json"
    p.write_text(json.dumps(rows), encoding="utf-8")
    return p


def test_parses_id_into_year_and_number(tmp_path):
    adapter = ImoJsonAdapter()
    rows = [
        {"id": "2025-imo-p1", "problem": "First $x$", "solution": None},
        {"id": "2025-imo-p2", "problem": "Second $y$", "solution": None},
    ]
    year_files = adapter.parse(_write_json(tmp_path, rows))
    assert len(year_files) == 1
    yf = year_files[0]
    assert yf.year == 2025
    assert yf.competition["name"] == "IMO"
    assert sorted(p.number for p in yf.problems) == [1, 2]


def test_bad_id_raises(tmp_path):
    adapter = ImoJsonAdapter()
    src = _write_json(tmp_path, [{"id": "garbage", "problem": "x", "solution": None}])
    with pytest.raises(ValueError):
        adapter.parse(src)


def test_emit_produces_importable_yaml(tmp_path):
    adapter = ImoJsonAdapter()
    rows = [{"id": "2025-imo-p1", "problem": "A *nice* line with $$a+b=c$$.", "solution": None}]
    src = _write_json(tmp_path, rows)
    paths = adapter.emit(src, tmp_path / "out", check_katex=False)
    assert paths == [tmp_path / "out" / "imo" / "2025.yaml"]

    # output must satisfy the importer's schema
    import yaml
    from import_problems import FileSpec

    data = yaml.safe_load(paths[0].read_text())
    spec = FileSpec.model_validate(data)
    assert spec.year == 2025
    assert spec.problems[0].statement == "A nice line with $a+b=c$."
