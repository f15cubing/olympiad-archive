import asyncio
from backend import models
from backend.database import engine

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)
        await conn.run_sync(models.Base.metadata.create_all)
        print("tables dropped and recreated")

if __name__ == "__main__":
    asyncio.run(main())
