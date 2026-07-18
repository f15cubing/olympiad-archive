#!/usr/bin/env python
"""Bulk import olympiad problems from canonical YAML into the archive.

Input is one YAML file per competition-year (see data/README.md and the schema below).
The importer is idempotent and resumable: it upserts problems on
``(competition, year, problem_number)`` — the unique key added in migration 0002 — so
re-running updates rows in place instead of duplicating them.

    # validate + KaTeX-check without writing
    python scripts/import_problems.py data/imo/2024.yaml --dry-run

    # import a file or a whole directory of YAML files
    python scripts/import_problems.py data/imo/2024.yaml
    python scripts/import_problems.py data/imo/

Behavior notes:
- Tags are normalized through the controlled vocabulary (backend/ai_tagging/tag_vocab.py).
- A curated ``difficulty`` in the YAML always wins; AI tagging never clobbers it.
- Solutions are matched by (author, content) so re-imports don't duplicate them and
  AI-generated alternate solutions added later are preserved.
- Every statement/solution is KaTeX-validated exactly the way the frontend renders it
  (scripts/katex_check.mjs). Problems whose math won't render are skipped by default;
  pass --allow-katex-errors to import them anyway, or --no-katex to skip the check.
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import AsyncSessionLocal
from backend.models import Competition, Problem, Solution, problem_tags
from backend.ai_tagging.db_integration import _get_or_create_tag

logger = logging.getLogger("import_problems")

SCRIPTS_DIR = Path(__file__).resolve().parent


# --------------------------------------------------------------------------- schema
class SolutionSpec(BaseModel):
    author: str = "Official"
    content: str = Field(..., min_length=1)


class ProblemSpec(BaseModel):
    number: int = Field(..., ge=1)
    statement: str = Field(..., min_length=1)
    author: Optional[str] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=10)
    source_url: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    solutions: list[SolutionSpec] = Field(default_factory=list)


class CompetitionSpec(BaseModel):
    name: str = Field(..., min_length=1)
    country: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None


class FileSpec(BaseModel):
    competition: CompetitionSpec
    year: int
    problems: list[ProblemSpec] = Field(..., min_length=1)

    @field_validator("problems")
    @classmethod
    def unique_numbers(cls, v: list[ProblemSpec]) -> list[ProblemSpec]:
        nums = [p.number for p in v]
        dupes = {n for n in nums if nums.count(n) > 1}
        if dupes:
            raise ValueError(f"duplicate problem numbers within file: {sorted(dupes)}")
        return v


# ----------------------------------------------------------------------- katex check
def katex_available() -> bool:
    return bool(shutil.which("node")) and (SCRIPTS_DIR / "node_modules" / "katex").is_dir()


def run_katex_check(items: list[dict]) -> dict[str, list[dict]]:
    """Return {id: [error, ...]} for the given [{id, text}] items."""
    proc = subprocess.run(
        ["node", str(SCRIPTS_DIR / "katex_check.mjs")],
        input=json.dumps(items),
        capture_output=True,
        text=True,
        cwd=str(SCRIPTS_DIR),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"katex_check.mjs failed: {proc.stderr.strip()}")
    results = json.loads(proc.stdout)
    return {r["id"]: r["errors"] for r in results if not r["ok"]}


def validate_katex_for_file(spec: FileSpec) -> dict[int, list[dict]]:
    """KaTeX-validate every statement/solution. Returns {problem_number: [errors]}."""
    items = []
    for p in spec.problems:
        items.append({"id": f"{p.number}::statement", "text": p.statement})
        for i, sol in enumerate(p.solutions):
            items.append({"id": f"{p.number}::solution[{i}]", "text": sol.content})
    raw = run_katex_check(items)
    by_problem: dict[int, list[dict]] = {}
    for item_id, errors in raw.items():
        number = int(item_id.split("::", 1)[0])
        for e in errors:
            by_problem.setdefault(number, []).append({"where": item_id, **e})
    return by_problem


# ---------------------------------------------------------------------------- upsert
async def _get_or_create_competition(session, spec: CompetitionSpec) -> Competition:
    comp = (
        await session.execute(select(Competition).where(Competition.name == spec.name))
    ).scalars().first()
    if comp is None:
        comp = Competition(
            name=spec.name, country=spec.country, url=spec.url, description=spec.description
        )
        session.add(comp)
        await session.flush()
        return comp
    # Only overwrite metadata that the file actually provides (non-destructive).
    if spec.country is not None:
        comp.country = spec.country
    if spec.url is not None:
        comp.url = spec.url
    if spec.description is not None:
        comp.description = spec.description
    return comp


async def _upsert_problem(session, comp: Competition, year: int, p: ProblemSpec) -> str:
    """Create or update one problem. Returns 'created' or 'updated'."""
    existing = (
        await session.execute(
            select(Problem).where(
                Problem.competition_id == comp.id,
                Problem.year == year,
                Problem.problem_number == p.number,
            )
        )
    ).scalars().first()

    if existing is None:
        problem = Problem(
            competition_id=comp.id,
            year=year,
            problem_number=p.number,
            statement=p.statement,
            author=p.author,
            difficulty=p.difficulty,
            source_url=p.source_url,
        )
        session.add(problem)
        await session.flush()
        outcome = "created"
    else:
        problem = existing
        problem.statement = p.statement
        problem.author = p.author
        problem.source_url = p.source_url
        if p.difficulty is not None:  # curated difficulty always wins
            problem.difficulty = p.difficulty
        outcome = "updated"

    # Solutions: add any not already present (matched by author + content).
    # Query the table directly rather than touching the (lazily-loaded) relationship,
    # which would trigger sync IO in this async context.
    have = {
        (author, content)
        for author, content in (
            await session.execute(
                select(Solution.author, Solution.content).where(
                    Solution.problem_id == problem.id
                )
            )
        ).all()
    }
    for sol in p.solutions:
        if (sol.author, sol.content) not in have:
            session.add(
                Solution(problem_id=problem.id, content=sol.content, author=sol.author)
            )
            have.add((sol.author, sol.content))

    # Tags: normalize + attach via the association table (same async reason as above).
    linked = {
        r[0]
        for r in (
            await session.execute(
                select(problem_tags.c.tag_id).where(
                    problem_tags.c.problem_id == problem.id
                )
            )
        ).all()
    }
    for raw in p.tags:
        tag = await _get_or_create_tag(session, raw)
        if tag.id not in linked:
            await session.execute(
                problem_tags.insert().values(problem_id=problem.id, tag_id=tag.id)
            )
            linked.add(tag.id)

    return outcome


# ------------------------------------------------------------------------------ main
def load_file(path: Path) -> FileSpec:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return FileSpec.model_validate(data)


def collect_yaml_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            paths.extend(sorted(p.rglob("*.yaml")))
            paths.extend(sorted(p.rglob("*.yml")))
        elif p.is_file():
            paths.append(p)
        else:
            raise FileNotFoundError(f"no such file or directory: {raw}")
    # de-dup while preserving order
    seen, unique = set(), []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(p)
    return unique


async def import_paths(
    paths: list[Path],
    dry_run: bool,
    check_katex: bool,
    allow_katex_errors: bool,
) -> dict:
    totals = {"created": 0, "updated": 0, "skipped": 0, "katex_failures": 0}

    async with AsyncSessionLocal() as session:
        for path in paths:
            spec = load_file(path)

            katex_bad: dict[int, list[dict]] = {}
            if check_katex:
                katex_bad = validate_katex_for_file(spec)
                for number, errors in sorted(katex_bad.items()):
                    totals["katex_failures"] += 1
                    for e in errors:
                        logger.warning(
                            "KaTeX [%s] %s #%s: %s",
                            path.name, e["where"], number,
                            e["error"].splitlines()[0],
                        )

            comp = await _get_or_create_competition(session, spec.competition)
            created = updated = skipped = 0
            for p in spec.problems:
                if p.number in katex_bad and not allow_katex_errors:
                    skipped += 1
                    continue
                outcome = await _upsert_problem(session, comp, spec.year, p)
                created += outcome == "created"
                updated += outcome == "updated"

            totals["created"] += created
            totals["updated"] += updated
            totals["skipped"] += skipped
            logger.info(
                "%s (%s %s): created=%d updated=%d skipped=%d",
                path.name, spec.competition.name, spec.year, created, updated, skipped,
            )

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    return totals


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("paths", nargs="+", help="YAML file(s) or director(ies)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate + KaTeX-check without writing to the database.")
    parser.add_argument("--no-katex", action="store_true",
                        help="Skip KaTeX validation (e.g. when Node/katex is unavailable).")
    parser.add_argument("--allow-katex-errors", action="store_true",
                        help="Import problems even if their math fails KaTeX validation.")
    parser.add_argument("--debug", action="store_true", help="Verbose logging.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    check_katex = not args.no_katex
    if check_katex and not katex_available():
        logger.error(
            "KaTeX validation requested but Node/katex is unavailable. "
            "Run `npm install` in scripts/, or pass --no-katex to skip."
        )
        sys.exit(2)

    try:
        paths = collect_yaml_paths(args.paths)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(2)
    if not paths:
        logger.error("no YAML files found in the given paths")
        sys.exit(2)

    try:
        totals = asyncio.run(
            import_paths(paths, args.dry_run, check_katex, args.allow_katex_errors)
        )
    except (ValidationError, RuntimeError) as e:
        logger.error("import failed: %s", e)
        sys.exit(1)

    prefix = "[dry-run] " if args.dry_run else ""
    logger.info(
        "%sTOTAL: created=%d updated=%d skipped=%d (katex failures=%d) across %d file(s)",
        prefix, totals["created"], totals["updated"], totals["skipped"],
        totals["katex_failures"], len(paths),
    )
    # Non-zero exit if anything was skipped for KaTeX errors, so it's noticed.
    sys.exit(1 if totals["skipped"] else 0)


if __name__ == "__main__":
    main()
