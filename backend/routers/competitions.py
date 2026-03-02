from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import models, schemas
from database import get_db

router = APIRouter(prefix="/competitions", tags=["competitions"])

@router.get("/", response_model=List[schemas.CompetitionResponse])
async def get_competitions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Competition))
    return result.scalars().all()

@router.post("/", response_model=schemas.CompetitionResponse)
async def create_competition(comp: schemas.CompetitionCreate, db: AsyncSession = Depends(get_db)):
    db_comp = models.Competition(**comp.model_dump())
    db.add(db_comp)
    await db.commit()
    await db.refresh(db_comp)
    return db_comp

@router.delete("/{comp_id}/")
async def delete_competition(comp_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Competition).where(models.Competition.id == comp_id))
    db_comp = result.scalars().first()
    if not db_comp:
        raise HTTPException(status_code=404, detail="Competition not found")
    await db.delete(db_comp)
    await db.commit()
    return {"message": "Competition deleted successfully"}
