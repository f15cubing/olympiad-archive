"""Tests for the bulk importer (scripts/import_problems.py).

Pure schema/KaTeX tests run in-process; the full upsert/idempotency path runs the script
as a subprocess against a throwaway SQLite DB so it exercises the real code path
(migrations-equivalent schema + ORM upsert + KaTeX gate) without import-identity games.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import import_problems as imp  # noqa: E402


# ------------------------------------------------------------------ schema validation
def test_filespec_accepts_valid():
    spec = imp.FileSpec.model_validate(
        {
            "competition": {"name": "IMO"},
            "year": 2024,
            "problems": [{"number": 1, "statement": "Let $x$ be real."}],
        }
    )
    assert spec.competition.name == "IMO"
    assert spec.problems[0].difficulty is None


def test_filespec_rejects_duplicate_numbers():
    with pytest.raises(Exception):
        imp.FileSpec.model_validate(
            {
                "competition": {"name": "IMO"},
                "year": 2024,
                "problems": [
                    {"number": 1, "statement": "a"},
                    {"number": 1, "statement": "b"},
                ],
            }
        )


def test_filespec_rejects_out_of_range_difficulty():
    with pytest.raises(Exception):
        imp.FileSpec.model_validate(
            {
                "competition": {"name": "IMO"},
                "year": 2024,
                "problems": [{"number": 1, "statement": "a", "difficulty": 99}],
            }
        )


def test_collect_yaml_paths(tmp_path):
    d = tmp_path / "imo"
    d.mkdir()
    (d / "2024.yaml").write_text("x")
    (d / "2023.yml").write_text("y")
    (tmp_path / "note.txt").write_text("z")
    found = {p.name for p in imp.collect_yaml_paths([str(tmp_path)])}
    assert found == {"2024.yaml", "2023.yml"}


# --------------------------------------------------------------------- katex checking
requires_katex = pytest.mark.skipif(
    not imp.katex_available(), reason="node/katex not installed (run npm install in scripts/)"
)


@requires_katex
def test_katex_flags_bad_math():
    spec = imp.FileSpec.model_validate(
        {
            "competition": {"name": "IMO"},
            "year": 2024,
            "problems": [
                {"number": 1, "statement": "Good $a+b=c$"},
                {"number": 2, "statement": "Bad $\\notacommand{x}$"},
                {"number": 3, "statement": "Align $\\begin{align} x&=1 \\end{align}$"},
            ],
        }
    )
    bad = imp.validate_katex_for_file(spec)
    assert 1 not in bad
    assert 2 in bad and 3 in bad


# ------------------------------------------------------------------- end-to-end upsert
def _make_schema_db(db_path: Path):
    """Create the archive schema in a fresh SQLite file via the ORM metadata."""
    import asyncio

    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from sqlalchemy.ext.asyncio import create_async_engine
    import models

    async def go():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(go())


def _run_script(script: str, cwd: Path, *args: str):
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def _run_importer(cwd: Path, *args: str):
    return _run_script("import_problems.py", cwd, *args)


def test_import_is_idempotent(tmp_path):
    _make_schema_db(tmp_path / "olympiad.db")
    yaml_file = tmp_path / "2024.yaml"
    yaml_file.write_text(
        "competition:\n  name: IMO\nyear: 2024\nproblems:\n"
        "  - number: 1\n    difficulty: 4\n    statement: 'Let $a+b=c$.'\n"
        "    tags: [algebra, NT]\n"
        "  - number: 2\n    statement: 'Find $x$.'\n",
        encoding="utf-8",
    )

    first = _run_importer(tmp_path, str(yaml_file), "--no-katex")
    assert first.returncode == 0, first.stderr
    assert "created=2" in first.stderr

    second = _run_importer(tmp_path, str(yaml_file), "--no-katex")
    assert second.returncode == 0, second.stderr
    assert "created=0 updated=2" in second.stderr

    # No duplicate rows or tags after two runs.
    import sqlite3

    con = sqlite3.connect(tmp_path / "olympiad.db")
    assert con.execute("SELECT count(*) FROM problems").fetchone()[0] == 2
    # 'algebra' -> 'Algebra' and 'NT' -> 'Number Theory' -> 2 canonical tags, deduped.
    tag_names = {r[0] for r in con.execute("SELECT name FROM tags")}
    assert tag_names == {"Algebra", "Number Theory"}
    # curated difficulty preserved
    diffs = dict(con.execute("SELECT problem_number, difficulty FROM problems"))
    assert diffs[1] == 4
    con.close()


def test_dry_run_writes_nothing(tmp_path):
    _make_schema_db(tmp_path / "olympiad.db")
    yaml_file = tmp_path / "2024.yaml"
    yaml_file.write_text(
        "competition:\n  name: IMO\nyear: 2024\nproblems:\n"
        "  - number: 1\n    statement: 'Let $a+b=c$.'\n",
        encoding="utf-8",
    )
    res = _run_importer(tmp_path, str(yaml_file), "--no-katex", "--dry-run")
    assert res.returncode == 0, res.stderr
    assert "[dry-run]" in res.stderr

    import sqlite3

    con = sqlite3.connect(tmp_path / "olympiad.db")
    assert con.execute("SELECT count(*) FROM problems").fetchone()[0] == 0
    con.close()


# ------------------------------------------------------------- coverage_report.py
def test_coverage_report_json(tmp_path):
    _make_schema_db(tmp_path / "olympiad.db")
    yaml_file = tmp_path / "2024.yaml"
    yaml_file.write_text(
        "competition:\n  name: IMO\nyear: 2024\nproblems:\n"
        "  - number: 1\n    difficulty: 4\n    statement: 'Let $a$.'\n"
        "  - number: 2\n    statement: 'Find $x$.'\n",  # no difficulty -> flagged
        encoding="utf-8",
    )
    assert _run_importer(tmp_path, str(yaml_file), "--no-katex").returncode == 0

    res = _run_script("coverage_report.py", tmp_path, "--json")
    assert res.returncode == 0, res.stderr
    report = json.loads(res.stdout)
    assert report["totals"]["problems"] == 2
    assert report["totals"]["competitions"] == 1
    assert report["per_competition_year"]["IMO"] == {"2024": 2}
    assert report["flags"]["missing_difficulty"] == 1
    assert report["tagging"]["gemini_tagged"] == 0


# --------------------------------------------------------- merge_duplicate_tags.py
def test_merge_duplicate_tags(tmp_path):
    import sqlite3

    _make_schema_db(tmp_path / "olympiad.db")
    con = sqlite3.connect(tmp_path / "olympiad.db")
    con.execute("INSERT INTO competitions (id, name) VALUES (1, 'IMO')")
    con.execute(
        "INSERT INTO problems (id, competition_id, year, problem_number, statement) "
        "VALUES (1, 1, 2024, 1, 'x')"
    )
    # two names that collapse to the canonical 'Number Theory', both linked to problem 1
    con.execute("INSERT INTO tags (id, name) VALUES (1, 'Number theory'), (2, 'NT')")
    con.execute("INSERT INTO problem_tags (problem_id, tag_id) VALUES (1, 1), (1, 2)")
    con.commit()
    con.close()

    res = _run_script("merge_duplicate_tags.py", tmp_path)
    assert res.returncode == 0, res.stderr

    con = sqlite3.connect(tmp_path / "olympiad.db")
    names = {r[0] for r in con.execute("SELECT name FROM tags")}
    assert names == {"Number Theory"}
    # problem 1 ends up linked exactly once (redundant link dropped, not duplicated)
    assert con.execute(
        "SELECT count(*) FROM problem_tags WHERE problem_id = 1"
    ).fetchone()[0] == 1
    con.close()
