#!/usr/bin/env python
"""Collapse existing near-duplicate tags onto their canonical vocabulary form.

The tag-normalization layer (`backend/ai_tagging/tag_vocab.py`) keeps *new* tags
canonical, but a database tagged before it landed may hold near-dupes ("number theory"
vs "Number Theory" vs "NT"). This one-off pass rewrites every tag to its canonical name,
repoints problem<->tag links off the duplicates, and deletes the emptied rows.

Idempotent: a second run is a no-op. Use --dry-run to preview.

    python scripts/merge_duplicate_tags.py --dry-run
    python scripts/merge_duplicate_tags.py
"""

import argparse
import asyncio
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, select, update

from backend.database import AsyncSessionLocal
from backend.models import Tag, problem_tags
from backend.ai_tagging.tag_vocab import normalize_tag


async def _problem_ids_for_tag(session, tag_id):
    rows = await session.execute(
        select(problem_tags.c.problem_id).where(problem_tags.c.tag_id == tag_id)
    )
    return {r[0] for r in rows}


async def merge_duplicate_tags(dry_run: bool = False) -> dict:
    """Merge duplicate tags. Returns a summary dict."""
    summary = {"tags_before": 0, "renamed": 0, "merged": 0, "tags_after": 0}

    async with AsyncSessionLocal() as session:
        tags = (await session.execute(select(Tag))).scalars().all()
        summary["tags_before"] = len(tags)

        # Group existing tags by their canonical name.
        by_canonical = defaultdict(list)
        for tag in tags:
            by_canonical[normalize_tag(tag.name)].append(tag)

        for canonical, group in by_canonical.items():
            # Prefer a tag that already carries the canonical name as the survivor.
            group.sort(key=lambda t: (t.name != canonical, t.id))
            survivor = group[0]
            duplicates = group[1:]

            if survivor.name != canonical:
                print(f"rename: {survivor.name!r} -> {canonical!r}")
                summary["renamed"] += 1
                if not dry_run:
                    survivor.name = canonical

            survivor_problems = await _problem_ids_for_tag(session, survivor.id)
            for dup in duplicates:
                print(f"merge:  {dup.name!r} (#{dup.id}) -> {canonical!r} (#{survivor.id})")
                summary["merged"] += 1
                if dry_run:
                    continue

                dup_problems = await _problem_ids_for_tag(session, dup.id)
                # Repoint links whose problem isn't already tied to the survivor.
                to_move = dup_problems - survivor_problems
                if to_move:
                    await session.execute(
                        update(problem_tags)
                        .where(
                            problem_tags.c.tag_id == dup.id,
                            problem_tags.c.problem_id.in_(to_move),
                        )
                        .values(tag_id=survivor.id)
                    )
                    survivor_problems |= to_move
                # Drop any remaining links (problems already on the survivor) + the dup.
                await session.execute(
                    delete(problem_tags).where(problem_tags.c.tag_id == dup.id)
                )
                await session.delete(dup)

        if not dry_run:
            await session.commit()

        remaining = (await session.execute(select(Tag))).scalars().all()
        summary["tags_after"] = len(remaining) if not dry_run else summary["tags_before"]

    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing."
    )
    args = parser.parse_args()

    summary = asyncio.run(merge_duplicate_tags(dry_run=args.dry_run))
    prefix = "[dry-run] " if args.dry_run else ""
    print(
        f"\n{prefix}tags before={summary['tags_before']} "
        f"renamed={summary['renamed']} merged={summary['merged']} "
        f"tags after={summary['tags_after']}"
    )


if __name__ == "__main__":
    main()
