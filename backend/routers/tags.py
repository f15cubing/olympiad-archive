from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import models, schemas
from database import get_db

router = APIRouter(prefix="/tags", tags=["tags"])

@router.get("/", response_model=List[schemas.TagResponse])
async def get_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Tag))
    return result.scalars().all()

@router.post("/", response_model=schemas.TagResponse)
async def create_tag(tag: schemas.TagCreate, db: AsyncSession = Depends(get_db)):
    # Check if tag already exists
    existing = await db.execute(select(models.Tag).where(models.Tag.name == tag.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Tag already exists")

    db_tag = models.Tag(name=tag.name)
    db.add(db_tag)
    await db.commit()
    await db.refresh(db_tag)
    return db_tag
