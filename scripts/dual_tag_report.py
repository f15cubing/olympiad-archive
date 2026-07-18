#!/usr/bin/env python
"""Gemini-vs-Claude dual-tagging agreement report (Phase B).

Read-only. For every problem tagged by both providers (ai_metadata AND claude_metadata),
compares the two classifications and reports agreement, so a routing policy can be chosen
(e.g. "Gemini everywhere, Claude where Gemini confidence <= 6").

    python scripts/dual_tag_report.py          # human-readable
    python scripts/dual_tag_report.py --json     # machine-readable

Metrics per problem:
- field: exact match of the single field label.
- difficulty: exact, and within-1 (|gemini - claude| <= 1).
- techniques/topics: Jaccard overlap of the (normalized) sets — informational; different
  phrasings legitimately lower this even when the providers agree in spirit.
"""

import argparse
import asyncio
import json
import os
import sys
from statistics import mean

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.database import DATABASE_URL
from backend.models import Problem
from backend.ai_tagging.tag_vocab import normalize_topic


def _jaccard(a, b) -> float:
    sa = {normalize_topic(x) for x in a}
    sb = {normalize_topic(x) for x in b}
    if not sa and not sb:
        return 1.0
    return round(len(sa & sb) / len(sa | sb), 2) if (sa | sb) else 0.0


async def gather() -> dict:
    engine = create_async_engine(DATABASE_URL, echo=False)
    sm = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with sm() as session:
            problems = (await session.execute(select(Problem))).scalars().all()
            rows, both = [], 0
            for p in problems:
                if not (p.ai_metadata and p.claude_metadata):
                    continue
                both += 1
                g, c = p.ai_metadata, p.claude_metadata
                rows.append({
                    "problem": f"{p.year} P{p.problem_number}",
                    "gemini_field": g.get("field"), "claude_field": c.get("field"),
                    "field_match": g.get("field") == c.get("field"),
                    "gemini_difficulty": g.get("difficulty"), "claude_difficulty": c.get("difficulty"),
                    "difficulty_exact": g.get("difficulty") == c.get("difficulty"),
                    "difficulty_within_1": abs((g.get("difficulty") or 0) - (c.get("difficulty") or 0)) <= 1,
                    "technique_jaccard": _jaccard(g.get("techniques", []), c.get("techniques", [])),
                    "topic_jaccard": _jaccard(g.get("topics", []), c.get("topics", [])),
                })
    finally:
        await engine.dispose()

    summary = {"problems_tagged_by_both": both}
    if rows:
        summary.update({
            "field_agreement_pct": round(100 * mean(r["field_match"] for r in rows), 1),
            "difficulty_exact_pct": round(100 * mean(r["difficulty_exact"] for r in rows), 1),
            "difficulty_within_1_pct": round(100 * mean(r["difficulty_within_1"] for r in rows), 1),
            "mean_technique_jaccard": round(mean(r["technique_jaccard"] for r in rows), 2),
            "mean_topic_jaccard": round(mean(r["topic_jaccard"] for r in rows), 2),
        })
    return {"summary": summary, "rows": rows}


def format_text(report: dict) -> str:
    s, rows = report["summary"], report["rows"]
    out = ["=" * 68, "GEMINI vs CLAUDE — DUAL-TAG AGREEMENT (Phase B)", "=" * 68,
           f"Problems tagged by both providers: {s['problems_tagged_by_both']}"]
    if not rows:
        out.append("\n(no problems tagged by both yet — run tag_problems.py and tag_problems_claude.py)")
        return "\n".join(out)
    out += [
        f"Field agreement:        {s['field_agreement_pct']}%",
        f"Difficulty exact:       {s['difficulty_exact_pct']}%",
        f"Difficulty within 1:    {s['difficulty_within_1_pct']}%",
        f"Mean technique overlap: {s['mean_technique_jaccard']} (Jaccard)",
        f"Mean topic overlap:     {s['mean_topic_jaccard']} (Jaccard)",
        "", "Disagreements (field or difficulty > 1 apart):",
    ]
    disagreements = [r for r in rows if not r["field_match"] or not r["difficulty_within_1"]]
    if disagreements:
        for r in disagreements:
            out.append(f"  {r['problem']}: field {r['gemini_field']} vs {r['claude_field']}; "
                       f"difficulty {r['gemini_difficulty']} vs {r['claude_difficulty']}")
    else:
        out.append("  (none — field matched and difficulty within 1 on every problem)")
    out.append("=" * 68)
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = asyncio.run(gather())
    print(json.dumps(report, indent=2) if args.json else format_text(report))


if __name__ == "__main__":
    main()
