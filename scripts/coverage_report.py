#!/usr/bin/env python
"""Corpus coverage & quality report for the archive.

Read-only. Summarizes what's in the database so taxonomy bloat, missing solutions, and
untagged problems are visible before scaling sourcing/tagging (see the Quality Control
section of docs/plans/03-populating-the-archive.md).

    python scripts/coverage_report.py            # human-readable
    python scripts/coverage_report.py --json      # machine-readable

Reports:
- problems per competition/year,
- % of problems with >= 1 solution,
- % tagged by Gemini (ai_metadata) and Claude (claude_metadata, if that column exists),
- problems missing a curated difficulty,
- distinct tag count + the most common tags (catch taxonomy bloat),
- residual near-duplicate tags: existing tag names that collapse to the same canonical
  form under the vocabulary (i.e. merge_duplicate_tags.py would still merge them).
"""

import argparse
import asyncio
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.database import DATABASE_URL
from backend.models import Competition, Problem, Solution, Tag, problem_tags
from backend.ai_tagging.tag_vocab import normalize_tag


def _pct(n: int, total: int) -> float:
    return round(100.0 * n / total, 1) if total else 0.0


async def gather(session) -> dict:
    problems = (await session.execute(select(Problem))).scalars().all()
    total = len(problems)

    comps = (await session.execute(select(Competition))).scalars().all()
    comp_name = {c.id: c.name for c in comps}

    # problems per competition/year
    matrix: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for p in problems:
        matrix[comp_name.get(p.competition_id, f"<comp {p.competition_id}>")][p.year] += 1

    # solutions
    total_solutions = (
        await session.execute(select(func.count()).select_from(Solution))
    ).scalar() or 0
    problems_with_solution = {
        r[0] for r in (
            await session.execute(select(Solution.problem_id).distinct())
        ).all()
    }
    with_sol = sum(1 for p in problems if p.id in problems_with_solution)

    # tagging coverage
    gemini_tagged = sum(1 for p in problems if p.ai_metadata is not None)
    has_claude_col = hasattr(Problem, "claude_metadata")
    claude_tagged = (
        sum(1 for p in problems if getattr(p, "claude_metadata", None) is not None)
        if has_claude_col
        else None
    )

    missing_difficulty = sum(1 for p in problems if p.difficulty is None)

    # tag histogram
    tag_counts = Counter()
    rows = (
        await session.execute(
            select(Tag.name, func.count(problem_tags.c.problem_id))
            .select_from(Tag)
            .join(problem_tags, Tag.id == problem_tags.c.tag_id, isouter=True)
            .group_by(Tag.id)
        )
    ).all()
    for name, count in rows:
        tag_counts[name] = count or 0

    # residual near-duplicates: distinct names that normalize to the same canonical form
    canon_groups: dict[str, list[str]] = defaultdict(list)
    for name in tag_counts:
        canon_groups[normalize_tag(name)].append(name)
    residual_dupes = {c: sorted(v) for c, v in canon_groups.items() if len(v) > 1}

    return {
        "totals": {
            "competitions": len(comps),
            "problems": total,
            "solutions": total_solutions,
            "distinct_tags": len(tag_counts),
        },
        "per_competition_year": {
            comp: dict(sorted(years.items())) for comp, years in sorted(matrix.items())
        },
        "solutions": {
            "problems_with_solution": with_sol,
            "pct_with_solution": _pct(with_sol, total),
        },
        "tagging": {
            "gemini_tagged": gemini_tagged,
            "pct_gemini": _pct(gemini_tagged, total),
            "claude_tagged": claude_tagged,
            "pct_claude": _pct(claude_tagged, total) if claude_tagged is not None else None,
        },
        "flags": {
            "missing_difficulty": missing_difficulty,
        },
        "top_tags": tag_counts.most_common(15),
        "residual_duplicate_tags": residual_dupes,
    }


def format_text(r: dict) -> str:
    t = r["totals"]
    lines = [
        "=" * 60,
        "ARCHIVE COVERAGE REPORT",
        "=" * 60,
        f"Competitions: {t['competitions']}   Problems: {t['problems']}   "
        f"Solutions: {t['solutions']}   Distinct tags: {t['distinct_tags']}",
        "",
        "Problems per competition/year:",
    ]
    if r["per_competition_year"]:
        for comp, years in r["per_competition_year"].items():
            span = ", ".join(f"{y}:{n}" for y, n in years.items())
            lines.append(f"  {comp}: {span}  (total {sum(years.values())})")
    else:
        lines.append("  (none)")

    s = r["solutions"]
    tag = r["tagging"]
    lines += [
        "",
        f"With >=1 solution: {s['problems_with_solution']}/{t['problems']} "
        f"({s['pct_with_solution']}%)",
        f"Gemini-tagged:     {tag['gemini_tagged']}/{t['problems']} ({tag['pct_gemini']}%)",
    ]
    if tag["claude_tagged"] is not None:
        lines.append(
            f"Claude-tagged:     {tag['claude_tagged']}/{t['problems']} ({tag['pct_claude']}%)"
        )
    lines.append(f"Missing difficulty: {r['flags']['missing_difficulty']}")

    lines += ["", "Top tags:"]
    if r["top_tags"]:
        for name, count in r["top_tags"]:
            lines.append(f"  {count:>4}  {name}")
    else:
        lines.append("  (none)")

    if r["residual_duplicate_tags"]:
        lines += ["", "⚠ Residual near-duplicate tags (run merge_duplicate_tags.py):"]
        for canon, names in r["residual_duplicate_tags"].items():
            lines.append(f"  {canon} <- {names}")
    lines.append("=" * 60)
    return "\n".join(lines)


async def _run() -> dict:
    # Dedicated quiet engine so the report isn't drowned by the shared echo=True engine.
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_maker() as session:
            return await gather(session)
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    report = asyncio.run(_run())
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_text(report))


if __name__ == "__main__":
    main()
