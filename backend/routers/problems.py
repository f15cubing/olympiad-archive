from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import models, schemas
from database import get_db

router = APIRouter(prefix="/problems", tags=["problems"])

@router.get("/", response_model=List[schemas.ProblemResponse])
async def get_problems(db: AsyncSession = Depends(get_db)):
    # selectinload is required for async relationship fetching
    result = await db.execute(
        select(models.Problem).options(selectinload(models.Problem.tags))
    )
    return result.scalars().all()

# put search endpoint before the dynamic problem_id route so that
# "/search" doesnt get captured by the path parameter.
@router.get("/search", response_model=List[schemas.ProblemResponse])
async def search_problems(
    q: str = None,
    tag: str = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(models.Problem).options(selectinload(models.Problem.tags))
    if q:
        query = query.where(models.Problem.statement.ilike(f"%{q}%"))
    if tag:
        query = query.join(models.Problem.tags).where(models.Tag.name == tag)
    result = await db.execute(query)
    return result.scalars().unique().all()

@router.get("/{problem_id}", response_model=schemas.ProblemWithSolutions)
async def get_problem(problem_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Problem)
        .options(
            selectinload(models.Problem.tags),
            selectinload(models.Problem.solutions)
        )
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
        author=problem.author,
        difficulty=problem.difficulty,
        source_url=problem.source_url
    )

    if problem.tag_ids:
        tag_result = await db.execute(
            select(models.Tag).where(models.Tag.id.in_(problem.tag_ids))
        )
        db_problem.tags = tag_result.scalars().all()

    db.add(db_problem)
    await db.commit()
    await db.refresh(db_problem)
    return db_problem

@router.put("/{problem_id}", response_model=schemas.ProblemResponse)
async def update_problem(
    problem_id: int,
    problem_update: schemas.ProblemCreate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(models.Problem)
        .options(selectinload(models.Problem.tags))
        .where(models.Problem.id == problem_id)
    )
    db_problem = result.scalars().first()

    if not db_problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Update basic attributes (exclude tag_ids from the simple loop)
    update_data = problem_update.model_dump(exclude={"tag_ids"})
    for key, value in update_data.items():
        setattr(db_problem, key, value)

    # Sync tags
    if problem_update.tag_ids is not None:
        tag_result = await db.execute(
            select(models.Tag).where(models.Tag.id.in_(problem_update.tag_ids))
        )
        db_problem.tags = tag_result.scalars().all()

    await db.commit()
    await db.refresh(db_problem)
    return db_problem

@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_problem(problem_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Problem).where(models.Problem.id == problem_id))
    db_problem = result.scalars().first()

    if not db_problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    await db.delete(db_problem)
    await db.commit()
    return None

@router.get("/tag/{tag_name}", response_model=List[schemas.ProblemResponse])
async def get_problems_by_tag(tag_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Problem)
        .join(models.Problem.tags)
        .where(models.Tag.name == tag_name)
        .options(selectinload(models.Problem.tags))
    )
    return result.scalars().unique().all()
