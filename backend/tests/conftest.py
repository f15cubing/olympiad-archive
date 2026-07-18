import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base
from database import get_db
from main import app

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_engine():
    # Fresh in-memory database per test so committed rows can't leak across tests.
    # StaticPool keeps a single connection alive so the :memory: DB persists for the test.
    from sqlalchemy.pool import StaticPool
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", echo=False, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def async_session(async_engine):
    async_session_maker = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
        # Ensure we roll back after each test to keep them isolated
        await session.rollback()

@pytest.fixture
async def client(async_session):
    # Fixed the dependency override to yield the existing session
    async def _override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = _override_get_db

    # Use ASGITransport for HTTPX 0.28+ compatibility
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clear overrides after the test finishes
    app.dependency_overrides.clear()
