from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
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
