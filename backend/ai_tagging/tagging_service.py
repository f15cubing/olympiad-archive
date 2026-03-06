"""Main tagging script to tag problems using Gemini AI."""

import asyncio
import logging
import sys
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

# Handle imports from different contexts (root vs backend directory)
try:
    from backend.database import AsyncSessionLocal
except ModuleNotFoundError:
    from database import AsyncSessionLocal

from .gemini_client import GeminiClient
from .schemas import TaggingBatchResult, TaggingResult
from .db_integration import (
    get_untagged_problems,
    get_problem_data,
    save_tagging_result,
    get_tagging_statistics,
    get_problems_by_ids,
)
from .config import BATCH_SIZE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AITaggerService:
    """Service for tagging problems with AI metadata."""

    def __init__(self):
        """Initialize the tagging service."""
        self.gemini_client = GeminiClient()
        self.total_tokens = 0
        self.total_cost = 0

    async def tag_batch(
        self,
        session: AsyncSession,
        limit: int = BATCH_SIZE,
        problem_ids: Optional[List[int]] = None
    ) -> TaggingBatchResult:
        """
        Tag a batch of problems.

        Args:
            session: Async database session
            limit: Maximum problems to tag in this batch
            problem_ids: Specific problem IDs to tag (if None, gets untagged ones)

        Returns:
            TaggingBatchResult with summary and individual results
        """
        # Get problems to tag
        if problem_ids:
            problems = await get_problems_by_ids(session, problem_ids)
        else:
            problems = await get_untagged_problems(session, limit)

        if not problems:
            logger.info("No problems found to tag")
            return TaggingBatchResult(
                total_processed=0,
                successful=0,
                failed=0,
                results=[],
                total_tokens=0,
                total_cost_estimate=0
            )

        logger.info(f"Starting batch tagging for {len(problems)} problems")
        results = []

        for problem in problems:
            # Get problem data
            problem_data = await get_problem_data(session, problem.id)

            # Tag the problem
            tagging_result = await self.gemini_client.tag_problem(
                problem_id=problem_data["problem_id"],
                problem_statement=problem_data["problem_statement"],
                solution_content=problem_data["solution_content"],
                year=problem_data["year"]
            )
            results.append(tagging_result)

            # Save result if successful
            if tagging_result.success and tagging_result.metadata:
                try:
                    await save_tagging_result(session, problem.id, tagging_result.metadata)
                    logger.info(f"Saved tagging for problem {problem.id}")
                except Exception as e:
                    logger.error(f"Failed to save tagging for problem {problem.id}: {str(e)}")
                    tagging_result.success = False
                    tagging_result.error = f"Database save failed: {str(e)}"

            # Track tokens
            if tagging_result.tokens_used:
                self.total_tokens += tagging_result.tokens_used

        # Summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        # Estimate cost: Gemini 2.0 Flash is ~$0.075 per 1M input tokens, ~$0.3 per 1M output tokens
        # Rough estimate: average 500 tokens per request
        estimated_tokens = self.total_tokens
        estimated_cost = (estimated_tokens / 1_000_000) * 0.1  # Rough average

        batch_result = TaggingBatchResult(
            total_processed=len(results),
            successful=successful,
            failed=failed,
            results=results,
            total_tokens=self.total_tokens,
            total_cost_estimate=estimated_cost
        )

        logger.info(
            f"Batch complete: {successful}/{len(results)} successful, "
            f"{failed} failed, {estimated_tokens} tokens used"
        )

        return batch_result

    async def tag_all_untagged(self, session: AsyncSession) -> TaggingBatchResult:
        """
        Tag all untagged problems in the database.

        Args:
            session: Async database session

        Returns:
            Final TaggingBatchResult with all results
        """
        all_results = []
        batch_num = 0

        while True:
            batch_num += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing batch {batch_num}")
            logger.info(f"{'='*60}")

            batch_result = await self.tag_batch(session, limit=BATCH_SIZE)
            all_results.extend(batch_result.results)

            if batch_result.total_processed == 0:
                break

            if batch_result.successful == 0 and batch_result.failed > 0:
                logger.warning("Batch had failures. Pausing before next batch...")
                await asyncio.sleep(5)

        # Aggregate results
        successful = sum(1 for r in all_results if r.success)
        failed = len(all_results) - successful

        return TaggingBatchResult(
            total_processed=len(all_results),
            successful=successful,
            failed=failed,
            results=all_results,
            total_tokens=self.total_tokens,
            total_cost_estimate=(self.total_tokens / 1_000_000) * 0.1
        )

    async def print_statistics(self, session: AsyncSession) -> None:
        """Print tagging statistics."""
        stats = await get_tagging_statistics(session)

        print("\n" + "="*60)
        print("TAGGING STATISTICS")
        print("="*60)
        print(f"Total Problems: {stats['total_problems']}")
        print(f"Tagged Problems: {stats['tagged_problems']}")
        print(f"Untagged Problems: {stats['untagged_problems']}")
        print(f"Progress: {stats['tagging_progress']:.1f}%")
        print("="*60 + "\n")


async def main(problem_ids: Optional[List[int]] = None):
    """
    Main entry point for tagging.

    Args:
        problem_ids: Specific problem IDs to tag (if None, tags all untagged)
    """
    try:
        async with AsyncSessionLocal() as session:
            # Print initial statistics
            service = AITaggerService()
            await service.print_statistics(session)

            # Tag problems
            if problem_ids:
                logger.info(f"Tagging specific problems: {problem_ids}")
                result = await service.tag_batch(session, problem_ids=problem_ids)
            else:
                logger.info("Tagging all untagged problems...")
                result = await service.tag_all_untagged(session)

            # Print results summary
            print("\n" + "="*60)
            print("BATCH RESULTS SUMMARY")
            print("="*60)
            print(f"Total Processed: {result.total_processed}")
            print(f"Successfully Tagged: {result.successful}")
            print(f"Failed: {result.failed}")
            print(f"Total Tokens Used: {result.total_tokens:,}")
            print(f"Estimated Cost: ${result.total_cost_estimate:.4f}")
            print("="*60 + "\n")

            # Print detailed results for failed items
            if result.failed > 0:
                print("Failed Items:")
                print("-"*60)
                for r in result.results:
                    if not r.success:
                        print(f"Problem {r.problem_id}: {r.error}")
                print("-"*60 + "\n")

            # Print final statistics
            await service.print_statistics(session)

            return result

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the tagging service
    result = asyncio.run(main())
