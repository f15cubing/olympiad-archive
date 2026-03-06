"""Router for AI tagging endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import models
import schemas
from database import get_db
from ai_tagging.tagging_service import AITaggerService
from ai_tagging.schemas import TaggingBatchResult

router = APIRouter(prefix="/tagging", tags=["tagging"])


@router.post("/{problem_id}", response_model=TaggingBatchResult)
async def tag_single_problem(
    problem_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Tag a single problem using AI.

    Args:
        problem_id: The ID of the problem to tag
        db: Database session

    Returns:
        TaggingBatchResult with the tagging result for the single problem
    """
    # Verify problem exists
    result = await db.execute(
        select(models.Problem).where(models.Problem.id == problem_id)
    )
    problem = result.scalars().first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Tag the problem
    tagger = AITaggerService()
    tagging_result = await tagger.tag_batch(
        session=db,
        problem_ids=[problem_id]
    )

    return tagging_result


@router.post("/batch", response_model=TaggingBatchResult)
async def tag_batch(
    request: schemas.TaggingBatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Tag multiple problems in a batch using AI.

    Args:
        request: Request body containing list of problem IDs
        db: Database session

    Returns:
        TaggingBatchResult with tagging results for all problems
    """
    if not request.problem_ids:
        raise HTTPException(
            status_code=400,
            detail="problem_ids list cannot be empty"
        )

    if len(request.problem_ids) > 50:
        raise HTTPException(
            status_code=400,
            detail="Cannot tag more than 50 problems at once"
        )

    # Verify all problems exist
    result = await db.execute(
        select(models.Problem).where(models.Problem.id.in_(request.problem_ids))
    )
    problems = result.scalars().all()
    if len(problems) != len(request.problem_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more problem IDs not found"
        )

    # Tag the problems
    tagger = AITaggerService()
    tagging_result = await tagger.tag_batch(
        session=db,
        problem_ids=request.problem_ids
    )

    return tagging_result
