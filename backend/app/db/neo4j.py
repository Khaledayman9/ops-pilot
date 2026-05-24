from neo4j import AsyncGraphDatabase, AsyncDriver
from settings import settings


neo4j_driver: AsyncDriver = AsyncGraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
)


async def get_neo4j_session():
    async with neo4j_driver.session() as session:
        yield session