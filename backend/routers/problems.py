from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import models, schemas
from database import get_db

router = APIRouter(prefix="/problems", tags=["problems"])

@router.get("/", response_model=List[schemas.ProblemResponse])
async def get_problems(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Problem).options(selectinload(models.Problem.tags))
    )
    return result.scalars().all()

@router.get("/{problem_id}", response_model=schemas.ProblemResponse)
async def get_problem(problem_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Problem)
        .options(selectinload(models.Problem.tags))
        .where(models.Problem.id == problem_id)
    )
    db_problem = result.scalars().first()
    if not db_problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return db_problem

@router.post("/", response_model=schemas.ProblemResponse)
async def create_problem(problem: schemas.ProblemCreate, db: AsyncSession = Depends(get_db)):
    db_problem = models.Problem(
        competition_id=problem.competition_id,
        year=problem.year,
        problem_number=problem.problem_number,
        statement=problem.statement,
        difficulty=problem.difficulty,
        source_url=problem.source_url
    )
    db.add(db_problem)
    await db.commit()
    await db.refresh(db_problem)
    return db_problem
