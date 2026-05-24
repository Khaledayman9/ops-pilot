from neo4j import AsyncSession


class Neo4jService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_service_dependencies(self, service: str) -> list[dict]:
        result = await self._session.run(
            "MATCH (s:Service {name:$s})-[:DEPENDS_ON]->(dep) "
            "RETURN dep.name AS name, dep.type AS type, dep.status AS status",
            s=service,
        )
        return await result.data()

    async def get_upstream_services(self, service: str) -> list[dict]:
        result = await self._session.run(
            "MATCH (u)-[:DEPENDS_ON]->(s:Service {name:$s}) "
            "RETURN u.name AS name, u.type AS type",
            s=service,
        )
        return await result.data()

    async def get_recent_deployments(self, service: str, limit: int = 5) -> list[dict]:
        result = await self._session.run(
            "MATCH (d:Deployment)-[:DEPLOYED_IN]->(s:Service {name:$s}) "
            "RETURN d.id AS id, d.version AS version, d.status AS status, d.timestamp AS timestamp "
            "ORDER BY d.timestamp DESC LIMIT $limit",
            s=service, limit=limit,
        )
        return await result.data()

    async def get_related_incidents(self, service: str, limit: int = 5) -> list[dict]:
        result = await self._session.run(
            "MATCH (i:Incident)-[:AFFECTS]->(s:Service {name:$s}) "
            "RETURN i.id AS id, i.severity AS severity, i.description AS description "
            "ORDER BY i.timestamp DESC LIMIT $limit",
            s=service, limit=limit,
        )
        return await result.data()

    async def compute_blast_radius(self, service: str) -> int:
        result = await self._session.run(
            "MATCH (s:Service {name:$s})-[:DEPENDS_ON*1..3]->(dep) "
            "RETURN count(DISTINCT dep) AS count",
            s=service,
        )
        record = await result.single()
        return record["count"] if record else 0