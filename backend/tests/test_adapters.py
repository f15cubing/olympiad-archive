"""Tests for dataset adapters (scripts/adapters/)."""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "adapters"))

from base import normalize_statement, normalize_latex, find_residual_latex  # noqa: E402
from imo_json import ImoJsonAdapter  # noqa: E402
from imo_tex_tree import ImoTexTreeAdapter, _parse_year_range  # noqa: E402
from imo_jonaskg import ImoJonaskgAdapter, _expand_macros, KNOWN_FIXES  # noqa: E402


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


# ------------------------------------------------------------------- normalize_latex
def test_enumerate_alph_to_lettered_list():
    out = normalize_latex(
        r"Prove:" "\n"
        r"\begin{enumerate}[label = (\alph*)]" "\n"
        r"\item first $x$" "\n"
        r"\item second $y$" "\n"
        r"\end{enumerate}"
    )
    assert "(a) first $x$" in out and "(b) second $y$" in out


def test_enumerate_roman_and_itemize():
    assert "(i) one" in normalize_latex(
        r"\begin{enumerate}[label = (\roman*)]\item one\item two\end{enumerate}"
    )
    assert "- a\n- b" in normalize_latex(r"\begin{itemize}\item a\item b\end{itemize}")


def test_unwrap_emph_and_rem_spanning_math():
    # \rem argument contains $...$ — brace-balanced unwrap must keep the math
    assert normalize_latex(r"\emph{anti-Pascal} and \rem{see $1 \le i \le n$ here}") == (
        r"anti-Pascal and see $1 \le i \le n$ here"
    )


def test_strips_comments_and_grader_notes():
    assert normalize_latex("Solve $x$. % hidden comment\nDone.") == "Solve $x$.\nDone."
    assert "Note" not in normalize_latex(r"Real part. \textit{Note. weaker results.}")


def test_display_bracket_and_multiline_math_flattened():
    out = normalize_latex("Then \\[a +\nb = c\\] holds.")
    assert out == "Then $a + b = c$ holds."
    # a pre-existing multiline inline span is flattened too
    assert normalize_latex("$x =\n1$") == "$x = 1$"


def test_bare_dots_in_prose_wrapped():
    assert normalize_latex(r"terms $x_1$, \dots, $x_n$") == r"terms $x_1$, $\ldots$, $x_n$"


def test_find_residual_latex():
    assert find_residual_latex(r"ok $x$ \item leftover") == [r"\item"]
    assert find_residual_latex(r"clean $\frac12$ text") == []


# --------------------------------------------------------------------- tex-tree adapter
def test_tex_tree_parses_tree(tmp_path):
    f = tmp_path / "2019" / "1" / "problem_en.tex"
    f.parent.mkdir(parents=True)
    f.write_text(r"Let $n \ge 3$." "\n\\begin{enumerate}[label=(\\alph*)]\n\\item go\n\\end{enumerate}")
    (tmp_path / "2019" / "1" / "number.tex").write_text("1")
    yfs = ImoTexTreeAdapter().parse(tmp_path)
    assert len(yfs) == 1 and yfs[0].year == 2019
    assert "(a) go" in yfs[0].problems[0].statement


def test_parse_year_range():
    assert _parse_year_range("2015-2017") == {2015, 2016, 2017}
    assert _parse_year_range("2015,2020") == {2015, 2020}
    assert _parse_year_range(None) is None


# ---------------------------------------------------------------------- jonaskg adapter
def test_expand_evan_macros():
    assert _expand_macros(r"$f:\RR^+ \to \RR^+$") == r"$f:\mathbb{R}^+ \to \mathbb{R}^+$"
    assert _expand_macros(r"the $k$\ts{th} coin") == r"the $k$th coin"
    assert _expand_macros(r"$a \dotsb b$") == r"$a \cdots b$"


def test_jonaskg_applies_known_fix(tmp_path):
    src = tmp_path / "imo.jsonl"
    src.write_text(
        '{"year": 2023, "problem_number": 1, "problem": "BROKEN placeholder", "solution": ""}\n'
    )
    yfs = ImoJonaskgAdapter(years={2023}).parse(src)
    stmt = yfs[0].problems[0].statement
    assert "BROKEN" not in stmt
    assert "$1 = d_1 < d_2 < \\dots < d_k = n$" in stmt  # the restored clause
