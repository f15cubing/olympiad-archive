import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, engine
import models

async def seed_data():
    async with AsyncSessionLocal() as db:
        # 1. Create a Competition
        imo = models.Competition(name="IMO", country="International")
        db.add(imo)
        await db.flush() # Get the ID

        # 2. Create a Tag
        algebra = models.Tag(name="Algebra")
        db.add(algebra)
        await db.flush()

        # 3. Create a Problem
        prob1 = models.Problem(
            competition_id=imo.id,
            year=2024,
            problem_number=1,
            statement="Let $a, b, c$ be real numbers. Prove that $a^2 + b^2 + c^2 \\ge ab + bc + ca$.",
            difficulty=2
        )
        prob1.tags.append(algebra)
        db.add(prob1)
        await db.flush()

        # 4. Create a Solution
        sol = models.Solution(
            problem_id=prob1.id,
            content="This is a classic application of the Rearrangement Inequality or simply expanding $(a-b)^2 + (b-c)^2 + (c-a)^2 \\ge 0$.",
            author="Felipe"
        )
        db.add(sol)

        await db.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
