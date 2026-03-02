from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import models, schemas
from database import get_db

router = APIRouter(prefix="/solutions", tags=["solutions"])

@router.post("/", response_model=schemas.SolutionResponse)
async def create_solution(sol: schemas.SolutionCreate, db: AsyncSession = Depends(get_db)):
    db_sol = models.Solution(**sol.model_dump())
    db.add(db_sol)
    await db.commit()
    await db.refresh(db_sol)
    return db_sol

@router.delete("/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_solution(solution_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Solution).where(models.Solution.id == solution_id))
    db_sol = result.scalars().first()

    if not db_sol:
        raise HTTPException(status_code=404, detail="Solution not found")

    await db.delete(db_sol)
    await db.commit()
    return None
