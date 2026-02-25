import asyncio
from database import engine
from models import Base
from fastapi import FastAPI
from database import engine
from models import Base
from routers import problems, competitions

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(problems.router)
app.include_router(competitions.router)

@app.get("/")
def read_root():
    return {"message": "Olympiad Archive API is live"}

@app.get("/problems/test")
def get_test_problem():
    return {
        "id": 1,
        "competition": "IMO",
        "year": 2024,
        "statement": "Let $P(x)$ be a polynomial...",
        "tags": ["Algebra", "Polynomials"]
    }
