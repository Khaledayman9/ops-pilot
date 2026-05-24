import asyncio

from app.db.models import Base  # noqa: F401
from app.db.postgres import engine
from logger import logger


async def run_migrations() -> None:
    logger.info("Running database migrations...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Migrations complete.")


if __name__ == "__main__":
    asyncio.run(run_migrations())