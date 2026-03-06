from database import engine
from models import Base
from fastapi import FastAPI
from database import engine
from routers import problems, competitions, solutions, tags, tagging
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Olympiad Archive API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(competitions.router)
app.include_router(problems.router)
app.include_router(solutions.router)
app.include_router(tags.router)
app.include_router(tagging.router)

@app.get("/")
def read_root():
    return {"message": "Olympiad Archive API is live"}
