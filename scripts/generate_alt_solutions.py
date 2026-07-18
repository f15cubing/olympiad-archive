#!/usr/bin/env python
"""Generate one original AI (Claude) alternate solution per selected problem (Work item D.3).

For each problem id, ask Claude for a fresh, self-contained solution (see
backend/ai_tagging/claude_solution.py), KaTeX-validate it exactly the way the importer and
frontend do (scripts/katex_check.mjs), and — only if it renders — store it as a
``Solution`` labeled ``author="AI (Claude)"``.

Metered spend is bounded on purpose: there is no "all" mode, so you must name the ids.
Re-running is idempotent — a problem that already has an ``AI (Claude)`` solution is
skipped, and a solution whose math fails KaTeX is skipped (never saved broken).

    # generate for problems 1 and 2 and save
    python scripts/generate_alt_solutions.py --ids 1 2

    # dry run — generate + KaTeX-check, then roll back instead of saving
    python scripts/generate_alt_solutions.py --ids 1 2 3 --dry-run

    # verbose logging (includes the generated text)
    python scripts/generate_alt_solutions.py --ids 5 --debug

Requires ANTHROPIC_AUTH_TOKEN (and, on the TrueFoundry gateway, ANTHROPIC_CUSTOM_HEADERS)
in the environment; Node + katex in scripts/ enable the KaTeX gate (skipped with a warning
if unavailable).
"""

import argparse
import asyncio
import logging
import os
import sys

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import AsyncSessionLocal
from backend.models import Problem, Solution
from backend.ai_tagging.claude_solution import ClaudeSolutionClient

# run_katex_check / katex_available live in the importer; scripts/ is on sys.path[0] when
# this file is run as a script (and is added explicitly by the test).
from import_problems import run_katex_check, katex_available

logger = logging.getLogger("generate_alt_solutions")

# Label that marks a solution as Claude-generated. Also the idempotency key.
AI_AUTHOR = "AI (Claude)"


def katex_errors(text: str) -> list[dict]:
    """Return the KaTeX errors for a solution text ([] if it renders cleanly)."""
    return run_katex_check([{"id": "solution", "text": text}]).get("solution", [])


async def _has_ai_solution(session, problem_id: int) -> bool:
    """True if an ``AI (Claude)`` solution already exists for this problem."""
    row = (
        await session.execute(
            select(Solution.id).where(
                Solution.problem_id == problem_id, Solution.author == AI_AUTHOR
            )
        )
    ).first()
    return row is not None


async def process_problem(session, client: ClaudeSolutionClient, problem_id: int,
                          check_katex: bool) -> str:
    """Generate + validate + stage one AI solution for ``problem_id`` (no commit here).

    Returns 'generated', 'skipped', or 'failed'.
    """
    problem = await session.get(Problem, problem_id)
    if problem is None:
        logger.warning("Problem %s not found — skipping", problem_id)
        return "skipped"

    # Idempotent: never add a second AI (Claude) solution.
    if await _has_ai_solution(session, problem_id):
        logger.info("Problem %s already has an %s solution — skipping", problem_id, AI_AUTHOR)
        return "skipped"

    try:
        text = await client.generate_solution(problem.statement, year=problem.year)
    except Exception as e:  # network/gateway/parse — treat as a per-problem failure
        logger.error("Problem %s: Claude generation failed: %s", problem_id, e)
        return "failed"

    if not text:
        logger.error("Problem %s: Claude returned no usable solution — skipping", problem_id)
        return "failed"

    logger.debug("Problem %s generated solution:\n%s", problem_id, text)

    if check_katex:
        errors = katex_errors(text)
        if errors:
            for e in errors:
                logger.warning("Problem %s KaTeX: %s", problem_id, e["error"].splitlines()[0])
            logger.error("Problem %s: generated solution failed KaTeX — skipping (not saved)",
                         problem_id)
            return "failed"

    session.add(Solution(problem_id=problem_id, content=text, author=AI_AUTHOR))
    await session.flush()
    logger.info("Problem %s: generated %s solution (%d chars)", problem_id, AI_AUTHOR, len(text))
    return "generated"


async def generate_for_ids(ids: list[int], dry_run: bool, check_katex: bool) -> dict:
    totals = {"generated": 0, "skipped": 0, "failed": 0}
    # Construct the client up front so a missing token fails before we open a session.
    client = ClaudeSolutionClient()

    async with AsyncSessionLocal() as session:
        for problem_id in ids:
            outcome = await process_problem(session, client, problem_id, check_katex)
            totals[outcome] += 1

        if dry_run:
            await session.rollback()
            logger.info("[dry-run] rolled back — nothing saved")
        else:
            await session.commit()

    return totals


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--ids", nargs="+", type=int, required=True,
                        help="Problem id(s) to generate an alternate solution for (REQUIRED).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate + KaTeX-check but roll back instead of saving.")
    parser.add_argument("--debug", action="store_true",
                        help="Verbose logging (includes the generated solution text).")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    check_katex = katex_available()
    if not check_katex:
        logger.warning(
            "Node/katex unavailable in scripts/ — KaTeX validation SKIPPED; generated math "
            "will not be verified. Run `npm install` in scripts/ to enable it."
        )

    try:
        totals = asyncio.run(generate_for_ids(args.ids, args.dry_run, check_katex))
    except Exception as e:
        logger.error("generation run failed: %s", e)
        sys.exit(1)

    prefix = "[dry-run] " if args.dry_run else ""
    logger.info("%sTOTAL: generated=%d skipped=%d failed=%d",
                prefix, totals["generated"], totals["skipped"], totals["failed"])
    # Non-zero exit if any problem failed (generation error or broken math), so it's noticed.
    sys.exit(1 if totals["failed"] else 0)


if __name__ == "__main__":
    main()
