#!/usr/bin/env python
"""Embed problem statements for semantic search (Phase C).

Resumable: only embeds problems whose `embedding` is NULL. Batches to keep API calls down.
Uses Gemini embeddings (free lane; separate quota from chat tagging).

    python scripts/embed_problems.py            # embed all un-embedded problems
    python scripts/embed_problems.py --dry-run   # count only, no writes
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Problem
from backend.ai_tagging.config import EMBEDDING_MODEL
from backend.ai_tagging.embeddings import embed_texts


async def embed_all(batch_size: int = 20, dry_run: bool = False) -> dict:
    embedded = 0
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(select(Problem).where(Problem.embedding.is_(None)))
        ).scalars().all()
        print(f"{len(rows)} problems need embedding (model={EMBEDDING_MODEL})")
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            if dry_run:
                embedded += len(chunk)
                continue
            # embed_texts is blocking (network); run off the event loop
            vectors = await asyncio.get_event_loop().run_in_executor(
                None, embed_texts, [p.statement for p in chunk]
            )
            now = datetime.utcnow()
            for p, vec in zip(chunk, vectors):
                p.embedding = vec
                p.embedding_model = EMBEDDING_MODEL
                p.embedded_at = now
            await session.commit()
            embedded += len(chunk)
            print(f"embedded {embedded}/{len(rows)}")
    return {"embedded": embedded, "total": len(rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(embed_all(batch_size=args.batch_size, dry_run=args.dry_run))
    prefix = "[dry-run] " if args.dry_run else ""
    print(f"{prefix}done: {result['embedded']}/{result['total']}")


if __name__ == "__main__":
    main()
