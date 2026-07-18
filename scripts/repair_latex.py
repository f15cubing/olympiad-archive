#!/usr/bin/env python
"""Repair LaTeX that fails KaTeX validation by routing it through Claude (Work item D.2).

Reads canonical problem YAML (the same competition/year/problems[].statement format as
data/imo/2024.yaml), KaTeX-validates every statement exactly the way the frontend renders
it (scripts/katex_check.mjs), and for each statement whose math won't render asks Claude
for a KaTeX-safe rewrite, then RE-validates the rewrite and reports whether the repair
fixed it.

    # report which statements fail KaTeX, without calling Claude
    python scripts/repair_latex.py data/imo/2024.yaml --dry-run

    # repair failing statements via Claude and re-validate
    python scripts/repair_latex.py data/imo/2024.yaml
    python scripts/repair_latex.py data/imo/

This is a reporting/repair aid: it prints before/after text and a summary
(checked/failed/repaired) but does NOT write to the database. Requires Node + the KaTeX
package in scripts/ (run `npm install` there); the actual repair also needs
ANTHROPIC_AUTH_TOKEN set (not required for --dry-run).
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from import_problems import collect_yaml_paths, katex_available, run_katex_check
from backend.ai_tagging.latex_repair import repair_latex

logger = logging.getLogger("repair_latex")


def load_statements(path: Path) -> list[dict]:
    """Return ``[{id, file, number, text}]`` for every statement in a canonical YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    records: list[dict] = []
    for p in data.get("problems", []) or []:
        statement = p.get("statement")
        if not statement:
            continue
        number = p.get("number")
        records.append(
            {
                "id": f"{path.name}::{number}",
                "file": path.name,
                "number": number,
                "text": statement,
            }
        )
    return records


def _errs_to_lines(errors: list[dict]) -> list[str]:
    """Flatten katex_check error dicts into human-readable one-liners."""
    lines: list[str] = []
    for e in errors:
        raw = e.get("error") if isinstance(e, dict) else None
        lines.append(raw.splitlines()[0] if raw else str(e))
    return lines


async def repair_paths(paths: list[Path], dry_run: bool) -> dict:
    records: list[dict] = []
    for path in paths:
        records.extend(load_statements(path))

    totals = {"checked": len(records), "failed": 0, "repaired": 0}
    if not records:
        return totals

    failures = run_katex_check([{"id": r["id"], "text": r["text"]} for r in records])

    for r in records:
        errors = failures.get(r["id"])
        if not errors:
            continue
        totals["failed"] += 1
        err_lines = _errs_to_lines(errors)
        logger.info("FAIL %s problem %s:", r["file"], r["number"])
        for line in err_lines:
            logger.info("    - %s", line)
        logger.info("  before: %s", r["text"].strip())

        if dry_run:
            continue

        try:
            repaired = await repair_latex(r["text"], errors=err_lines)
        except Exception as exc:
            logger.error("  repair FAILED (Claude error): %s", exc)
            continue

        recheck = run_katex_check([{"id": r["id"], "text": repaired}])
        logger.info("  after:  %s", repaired.strip())
        if r["id"] not in recheck:
            totals["repaired"] += 1
            logger.info("  result: REPAIRED (passes KaTeX)")
        else:
            logger.info(
                "  result: STILL FAILING: %s",
                "; ".join(_errs_to_lines(recheck[r["id"]])),
            )

    return totals


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("paths", nargs="+", help="canonical problem YAML file(s) or director(ies)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report KaTeX failures without calling Claude.")
    parser.add_argument("--debug", action="store_true", help="Verbose logging.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if not katex_available():
        logger.error(
            "KaTeX validation unavailable: install Node and run `npm install` in scripts/."
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

    totals = asyncio.run(repair_paths(paths, args.dry_run))

    prefix = "[dry-run] " if args.dry_run else ""
    logger.info(
        "%sSUMMARY: checked=%d failed=%d repaired=%d",
        prefix, totals["checked"], totals["failed"], totals["repaired"],
    )
    # Exit non-zero while KaTeX failures remain unfixed, so CI/eyes notice.
    if args.dry_run:
        sys.exit(1 if totals["failed"] else 0)
    sys.exit(1 if totals["failed"] > totals["repaired"] else 0)


if __name__ == "__main__":
    main()
