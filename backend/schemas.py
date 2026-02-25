from pydantic import BaseModel
from typing import List, Optional

class ProblemBase(BaseModel):
    year: int
    problem_number: int
    statement: str
    difficulty: Optional[int] = None
    source_url: Optional[str] = None

class ProblemCreate(ProblemBase):
    competition_id: int

class ProblemResponse(ProblemBase):
    id: int
    competition_id: int

    class Config:
        from_attributes = True

class CompetitionCreate(BaseModel):
    name: str
    country: Optional[str] = None
    url: Optional[str] = None

class CompetitionResponse(CompetitionCreate):
    id: int
    class Config:
        from_attributes = True
