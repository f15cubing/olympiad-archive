#!/usr/bin/env python
"""Backfill Problem.difficulty from an AI estimate where it is NULL (Work item D.4).

Fills the curated ``difficulty`` column ONLY for problems that don't already have one;
a non-NULL (curated) difficulty is never overwritten. The estimate comes from the
per-problem tagging metadata: Claude writes ``claude_metadata``, Gemini writes
``ai_metadata``, and each dict (when present) carries a ``"difficulty"`` int in 1-10.

Idempotent and resumable: re-running only affects rows whose difficulty is still NULL.

    # fill NULLs, preferring Claude's estimate and falling back to Gemini
    python scripts/backfill_difficulty.py

    # use a single model's estimate only (no fallback)
    python scripts/backfill_difficulty.py --source claude
    python scripts/backfill_difficulty.py --source gemini

    # preview without writing (rolls back), with per-skip detail
    python scripts/backfill_difficulty.py --dry-run --debug
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Problem

logger = logging.getLogger("backfill_difficulty")


# --------------------------------------------------------------------------- helpers
def _metadata_difficulty(metadata) -> Optional[int]:
    """Pull an int difficulty out of an AI metadata dict, defensively.

    The dict may be None (never tagged) or present without a ``"difficulty"`` key
    (only topics/techniques). A non-int value is ignored too, so we never assign a
    bogus type to the Integer column.
    """
    if not isinstance(metadata, dict):
        return None
    value = metadata.get("difficulty")
    # bool is a subclass of int; a True/False here is bad data, not a difficulty.
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def choose_backfill_difficulty(problem, source: str = "auto") -> Optional[int]:
    """Return the AI-estimated difficulty to backfill for ``problem``, or None.

    - source="claude": use ``claude_metadata["difficulty"]``.
    - source="gemini": use ``ai_metadata["difficulty"]`` (Gemini writes ai_metadata).
    - source="auto":   Claude's estimate if present, else Gemini's.

    Returns None when the requested estimate is unavailable (metadata missing/None, no
    ``"difficulty"`` key, or a non-int value). A specific ``--source`` never falls back
    to the other model; only ``auto`` does.
    """
    claude = _metadata_difficulty(getattr(problem, "claude_metadata", None))
    gemini = _metadata_difficulty(getattr(problem, "ai_metadata", None))
    if source == "claude":
        return claude
    if source == "gemini":
        return gemini
    # auto: prefer Claude, fall back to Gemini
    return claude if claude is not None else gemini


def _resolved_source(problem, source: str) -> str:
    """Which model actually supplied the value (for logging under ``auto``)."""
    if source == "auto":
        if _metadata_difficulty(getattr(problem, "claude_metadata", None)) is not None:
            return "claude"
        return "gemini"
    return source


def _comp_name(problem) -> str:
    comp = getattr(problem, "competition", None)
    return comp.name if comp is not None else "?"


# ------------------------------------------------------------------------------ main
async def backfill_all(source: str = "auto", dry_run: bool = False) -> dict:
    backfilled = 0
    skipped = 0
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(select(Problem).where(Problem.difficulty.is_(None)))
        ).scalars().all()
        total = len(rows)
        logger.info("%d problems have NULL difficulty (source=%s)", total, source)

        for p in rows:
            value = choose_backfill_difficulty(p, source)
            if value is None:
                skipped += 1
                logger.debug(
                    "skipped problem %s (%s %s P%s): no AI difficulty available",
                    p.id, _comp_name(p), p.year, p.problem_number,
                )
                continue
            p.difficulty = value
            backfilled += 1
            logger.info(
                "backfilled problem %s (%s %s P%s) difficulty=%s from %s",
                p.id, _comp_name(p), p.year, p.problem_number, value,
                _resolved_source(p, source),
            )

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    return {"backfilled": backfilled, "skipped": skipped, "total": total}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source", choices=["auto", "claude", "gemini"], default="auto",
        help="Which AI estimate to use (auto: Claude first, else Gemini).",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute the backfill but roll back instead of committing.")
    parser.add_argument("--debug", action="store_true",
                        help="Verbose logging (also report skipped problems and why).")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    result = asyncio.run(backfill_all(source=args.source, dry_run=args.dry_run))
    prefix = "[dry-run] " if args.dry_run else ""
    print(
        f"{prefix}backfilled={result['backfilled']} "
        f"skipped={result['skipped']} total={result['total']}"
    )


if __name__ == "__main__":
    main()
