import asyncio
from backend.database import AsyncSessionLocal
from backend import models

async def seed():
    async with AsyncSessionLocal() as session:
        # Create test competitions
        comps = [
            models.Competition(name="IMO 2024", country="International", description="International Math Olympiad"),
            models.Competition(name="USA AMC 2024", country="USA", description="American Mathematics Competitions"),
            models.Competition(name="China TST 2024", country="China", description="Team Selection Test"),
        ]
        session.add_all(comps)
        await session.flush()

        # Create test problems
        problems = [
            models.Problem(
                competition_id=comps[0].id,
                year=2024,
                problem_number=1,
                statement="Let $ABC$ be an acute triangle with $AB < AC$.",
                author="Test Author"
            ),
            models.Problem(
                competition_id=comps[0].id,
                year=2024,
                problem_number=2,
                statement="Find all pairs of positive integers $(a, b)$.",
                author="Test Author"
            ),
            models.Problem(
                competition_id=comps[1].id,
                year=2024,
                problem_number=1,
                statement="Compute $2024^2 - 2023^2$.",
                author="Test Author"
            ),
        ]
        session.add_all(problems)
        await session.commit()

        print(f"✓ Created {len(comps)} competitions")
        print(f"✓ Created {len(problems)} problems")
        print("\nYou can now navigate to http://localhost:5173 and test:")
        print("1. Click on 'IMO 2024' or 'USA AMC 2024'")
        print("2. Click on the year (2024)")
        print("3. You'll see the existing problems and a '+ Add Problem' button")

asyncio.run(seed())
