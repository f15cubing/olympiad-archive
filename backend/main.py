import asyncio
from database import engine
from models import Base
from fastapi import FastAPI
from database import engine
from models import Base
from routers import problems, competitions, solutions, tags
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Olympiad Archive API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Your Vite port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(problems.router)
app.include_router(competitions.router)
app.include_router(solutions.router)
app.include_router(tags.router)

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
