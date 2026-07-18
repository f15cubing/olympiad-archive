"""Database integration for AI tagging."""

import logging
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

# Handle imports from different contexts (root vs backend directory)
try:
    from backend.models import Problem, Tag, problem_tags
except ModuleNotFoundError:
    from models import Problem, Tag, problem_tags

from .schemas import AITagMetadata
from .tag_vocab import normalize_tag

logger = logging.getLogger(__name__)


async def get_untagged_problems(session: AsyncSession, limit: int = 100) -> List[Problem]:
    """Get problems that haven't been tagged with AI metadata yet."""
    query = select(Problem).where(Problem.ai_metadata.is_(None)).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def get_problems_by_ids(session: AsyncSession, problem_ids: List[int]) -> List[Problem]:
    """Get specific problems by their IDs."""
    query = select(Problem).where(Problem.id.in_(problem_ids))
    result = await session.execute(query)
    return result.scalars().all()


async def get_claude_untagged_problems(session: AsyncSession, limit: int = 100) -> List[Problem]:
    """Get problems that haven't been Claude-tagged yet (claude_metadata IS NULL)."""
    query = select(Problem).where(Problem.claude_metadata.is_(None)).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def save_claude_tagging_result(
    session: AsyncSession,
    problem_id: int,
    metadata: AITagMetadata,
) -> None:
    """Save Claude tagging metadata to `claude_metadata` — non-destructive.

    Deliberately does NOT touch problem.difficulty, ai_metadata, tags, or the Gemini
    `tagged_at`: Claude runs as a parallel provider so the two can be compared per problem
    before a routing policy is decided (Phase B). No Tag rows are created here.
    """
    problem = await session.get(Problem, problem_id)
    if not problem:
        logger.warning(f"Problem {problem_id} not found in database")
        return
    problem.claude_metadata = metadata.model_dump()
    problem.claude_tagged_at = datetime.utcnow()
    await session.commit()
    logger.info(f"Saved Claude tagging result for problem {problem_id}")


async def save_tagging_result(
    session: AsyncSession,
    problem_id: int,
    metadata: AITagMetadata,
    create_tags: bool = True
) -> None:
    """
    Save AI tagging result to database.

    Args:
        session: Async SQLAlchemy session
        problem_id: ID of the problem
        metadata: AITagMetadata from Gemini
        create_tags: Whether to create/link tags
    """
    # Convert metadata to dict for JSON storage
    metadata_dict = metadata.model_dump()

    # Update problem with metadata
    problem = await session.get(Problem, problem_id)
    if not problem:
        logger.warning(f"Problem {problem_id} not found in database")
        return

    problem.ai_metadata = metadata_dict
    problem.tagged_at = datetime.utcnow()
    # Difficulty precedence: a curated (human) difficulty always wins. The AI value
    # is preserved inside ai_metadata; we only fill problem.difficulty when it's unset.
    if problem.difficulty is None:
        problem.difficulty = metadata.difficulty

    # Create or link tags
    if create_tags:
        # Create "field" tag if it doesn't exist
        field_tag = await _get_or_create_tag(session, metadata.field)
        if field_tag not in problem.tags:
            problem.tags.append(field_tag)

        # Create tags for techniques
        for technique in metadata.techniques:
            technique_tag = await _get_or_create_tag(session, f"technique: {technique}")
            if technique_tag not in problem.tags:
                problem.tags.append(technique_tag)

        # Create tags for topics
        for topic in metadata.topics:
            topic_tag = await _get_or_create_tag(session, topic)
            if topic_tag not in problem.tags:
                problem.tags.append(topic_tag)

    await session.commit()
    logger.info(f"Saved tagging result for problem {problem_id}")


async def _get_or_create_tag(session: AsyncSession, tag_name: str) -> Tag:
    """Get or create a tag, matching on its normalized (canonical) name."""
    canonical = normalize_tag(tag_name)

    # Check if tag exists (by canonical name)
    query = select(Tag).where(Tag.name == canonical)
    result = await session.execute(query)
    existing_tag = result.scalars().first()

    if existing_tag:
        return existing_tag

    # Create new tag
    new_tag = Tag(name=canonical)
    session.add(new_tag)
    await session.flush()  # Ensure the tag is inserted
    logger.debug(f"Created new tag: {canonical}")
    return new_tag


async def get_problem_data(session: AsyncSession, problem_id: int) -> dict:
    """Get problem statement and solution for AI processing."""
    problem = await session.get(Problem, problem_id)
    if not problem:
        return None

    solution_content = None
    if problem.solutions:
        # Use the first solution if multiple exist
        solution_content = problem.solutions[0].content

    return {
        "problem_id": problem.id,
        "problem_statement": problem.statement,
        "solution_content": solution_content,
        "year": problem.year,
        "problem_number": problem.problem_number,
    }


async def get_tagging_statistics(session: AsyncSession) -> dict:
    """Get statistics about tagging progress."""
    # Total problems
    total_query = select(Problem)
    total_result = await session.execute(total_query)
    total_problems = len(total_result.scalars().all())

    # Tagged problems
    tagged_query = select(Problem).where(Problem.ai_metadata.isnot(None))
    tagged_result = await session.execute(tagged_query)
    tagged_problems = len(tagged_result.scalars().all())

    return {
        "total_problems": total_problems,
        "tagged_problems": tagged_problems,
        "untagged_problems": total_problems - tagged_problems,
        "tagging_progress": (tagged_problems / total_problems * 100) if total_problems > 0 else 0,
    }
