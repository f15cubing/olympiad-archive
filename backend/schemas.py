from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ProblemBase(BaseModel):
    year: int
    problem_number: int
    statement: str
    author: Optional[str] = None
    difficulty: Optional[int] = None
    source_url: Optional[str] = None

class ProblemCreate(ProblemBase):
    competition_id: int
    tag_ids: Optional[List[int]] = []

class ProblemResponse(ProblemBase):
    id: int
    competition_id: int
    tags: List[TagResponse] = []
    model_config = ConfigDict(from_attributes=True)

class CompetitionBase(BaseModel):
    name: str
    country: Optional[str] = None
    url: Optional[str] = None

class CompetitionCreate(CompetitionBase):
    pass

class CompetitionResponse(CompetitionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class SolutionBase(BaseModel):
    content: str
    author: Optional[str] = None

class SolutionCreate(SolutionBase):
    problem_id: int

class SolutionResponse(SolutionBase):
    id: int
    problem_id: int
    model_config = ConfigDict(from_attributes=True)

class ProblemWithSolutions(ProblemResponse):
    solutions: List[SolutionResponse] = []

class CompetitionWithProblems(CompetitionResponse):
    problems: List[ProblemResponse] = []
