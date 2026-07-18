"""Claude tagging service — parallel provider to the Gemini AITaggerService (Phase D).

Mirrors AITaggerService but routes through ClaudeClient and writes results to the separate
`claude_metadata` column (non-destructive). Resumable: re-queries Claude-untagged problems.
"""

import asyncio
import logging
import sys
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.database import AsyncSessionLocal
except ModuleNotFoundError:
    from database import AsyncSessionLocal

from .claude_client import ClaudeClient
from .config import BATCH_SIZE
from .db_integration import (
    get_claude_untagged_problems,
    get_problem_data,
    get_problems_by_ids,
    save_claude_tagging_result,
)
from .schemas import TaggingBatchResult

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ClaudeTaggerService:
    """Tag problems with Claude, storing results in `claude_metadata`."""

    def __init__(self):
        self.claude_client = ClaudeClient()
        self.total_tokens = 0

    async def tag_batch(self, session: AsyncSession, limit: int = BATCH_SIZE,
                        problem_ids: Optional[List[int]] = None) -> TaggingBatchResult:
        if problem_ids:
            problems = await get_problems_by_ids(session, problem_ids)
        else:
            problems = await get_claude_untagged_problems(session, limit)

        if not problems:
            logger.info("No problems found to Claude-tag")
            return TaggingBatchResult(total_processed=0, successful=0, failed=0,
                                      results=[], total_tokens=0, total_cost_estimate=0)

        logger.info(f"Starting Claude batch tagging for {len(problems)} problems")
        results = []
        for problem in problems:
            data = await get_problem_data(session, problem.id)
            result = await self.claude_client.tag_problem(
                problem_id=data["problem_id"],
                problem_statement=data["problem_statement"],
                solution_content=data["solution_content"],
                year=data["year"],
            )
            results.append(result)
            if result.success and result.metadata:
                try:
                    await save_claude_tagging_result(session, problem.id, result.metadata)
                except Exception as e:
                    logger.error(f"Failed to save Claude tagging for {problem.id}: {e}")
                    result.success = False
                    result.error = f"Database save failed: {e}"
            if result.tokens_used:
                self.total_tokens += result.tokens_used

        successful = sum(1 for r in results if r.success)
        return TaggingBatchResult(
            total_processed=len(results), successful=successful,
            failed=len(results) - successful, results=results,
            total_tokens=self.total_tokens, total_cost_estimate=0,
        )

    async def tag_all_untagged(self, session: AsyncSession) -> TaggingBatchResult:
        all_results = []
        consecutive_all_failed = 0
        while True:
            batch = await self.tag_batch(session, limit=BATCH_SIZE)
            all_results.extend(batch.results)
            if batch.total_processed == 0:
                break
            if batch.successful == 0 and batch.failed > 0:
                # Failed problems stay untagged and get re-fetched — abort after 3
                # consecutive all-failed batches so a persistent error can't spin forever.
                consecutive_all_failed += 1
                if consecutive_all_failed >= 3:
                    logger.error("3 consecutive all-failed Claude batches; aborting "
                                 "(likely auth failure or gateway issue).")
                    break
                logger.warning("Claude batch had only failures. Pausing before next batch...")
                await asyncio.sleep(5)
            else:
                consecutive_all_failed = 0
        successful = sum(1 for r in all_results if r.success)
        return TaggingBatchResult(
            total_processed=len(all_results), successful=successful,
            failed=len(all_results) - successful, results=all_results,
            total_tokens=self.total_tokens, total_cost_estimate=0,
        )


async def main(problem_ids: Optional[List[int]] = None) -> TaggingBatchResult:
    async with AsyncSessionLocal() as session:
        service = ClaudeTaggerService()
        if problem_ids:
            logger.info(f"Claude-tagging specific problems: {problem_ids}")
            result = await service.tag_batch(session, problem_ids=problem_ids)
        else:
            logger.info("Claude-tagging all untagged problems...")
            result = await service.tag_all_untagged(session)

        print("\n" + "=" * 60)
        print("CLAUDE TAGGING SUMMARY")
        print("=" * 60)
        print(f"Total Processed: {result.total_processed}")
        print(f"Successfully Tagged: {result.successful}")
        print(f"Failed: {result.failed}")
        print(f"Total Tokens Used: {result.total_tokens:,}")
        print("=" * 60 + "\n")
        if result.failed:
            print("Failed Items:")
            for r in result.results:
                if not r.success:
                    print(f"  Problem {r.problem_id}: {r.error}")
        return result


if __name__ == "__main__":
    asyncio.run(main())
