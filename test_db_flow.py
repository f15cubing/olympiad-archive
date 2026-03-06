import asyncio
import sys
import os
os.chdir('.')  # Already in root

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def test_flow():
    async with AsyncSessionLocal() as session:
        # Create competition
        comp = models.Competition(name="Test IMO", country="International", description="Test Desc")
        session.add(comp)
        await session.flush()

        # Create problem
        problem = models.Problem(
            competition_id=comp.id,
            year=2024,
            problem_number=1,
            statement="Find x such that...",
            author="Test Author"
        )
        session.add(problem)
        await session.commit()

        print("✓ Created competition and problem")

        # Fetch and verify
        result = await session.execute(
            select(models.Competition).where(models.Competition.id == comp.id)
        )
        fetched_comp = result.scalars().first()
        print(f"✓ Retrieved competition: {fetched_comp.name}, description={fetched_comp.description}")

        result = await session.execute(
            select(models.Problem).where(models.Problem.id == problem.id)
        )
        fetched_prob = result.scalars().first()
        print(f"✓ Retrieved problem: Problem {fetched_prob.problem_number}, year {fetched_prob.year}")

asyncio.run(test_flow())
