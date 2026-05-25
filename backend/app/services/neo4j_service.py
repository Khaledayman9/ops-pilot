"""
Neo4jService — rich knowledge graph query service.

Used by:
  - GraphAnalyzerAgent (direct queries)
  - Celery tasks (graph maintenance jobs)
  - Background enrichment (web-search → graph write-back)
"""

from __future__ import annotations

from neo4j import AsyncSession

from logger import logger


class Neo4jService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # Read queries

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
            "RETURN u.name AS name, u.type AS type, u.status AS status",
            s=service,
        )
        return await result.data()

    async def get_full_blast_radius(self, service: str, max_hops: int = 3) -> list[dict]:
        result = await self._session.run(
            "MATCH path = (s:Service {name:$s})-[:DEPENDS_ON*1..$hops]->(dep) "
            "RETURN DISTINCT dep.name AS name, dep.type AS type, "
            "dep.status AS status, length(path) AS hops",
            s=service,
            hops=max_hops,
        )
        return await result.data()

    async def get_recent_deployments(self, service: str, limit: int = 5) -> list[dict]:
        result = await self._session.run(
            "MATCH (d:Deployment)-[:DEPLOYED_IN]->(s:Service {name:$s}) "
            "RETURN d.id AS id, d.version AS version, "
            "d.status AS status, d.timestamp AS timestamp, d.author AS author "
            "ORDER BY d.timestamp DESC LIMIT $limit",
            s=service,
            limit=limit,
        )
        return await result.data()

    async def get_related_incidents(self, service: str, limit: int = 5) -> list[dict]:
        result = await self._session.run(
            "MATCH (i:Incident)-[:AFFECTS]->(s:Service {name:$s}) "
            "RETURN i.id AS id, i.severity AS severity, "
            "i.description AS description, i.status AS status, i.timestamp AS timestamp "
            "ORDER BY i.timestamp DESC LIMIT $limit",
            s=service,
            limit=limit,
        )
        return await result.data()

    async def get_runbooks(self, service: str) -> list[dict]:
        result = await self._session.run(
            "MATCH (s:Service {name:$s})-[:HAS_RUNBOOK]->(rb:Runbook) "
            "RETURN rb.id AS id, rb.title AS title, rb.url AS url",
            s=service,
        )
        return await result.data()

    async def get_team_ownership(self, services: list[str]) -> list[dict]:
        result = await self._session.run(
            "MATCH (s:Service)-[:OWNED_BY]->(t:Team) "
            "WHERE s.name IN $names "
            "RETURN s.name AS service, t.name AS team, t.slack AS slack",
            names=services,
        )
        return await result.data()

    async def compute_blast_radius_count(self, service: str) -> int:
        result = await self._session.run(
            "MATCH (s:Service {name:$s})-[:DEPENDS_ON*1..3]->(dep) "
            "RETURN count(DISTINCT dep) AS count",
            s=service,
        )
        record = await result.single()
        return record["count"] if record else 0

    # Write queries (used by Celery tasks)

    async def upsert_service_status(self, name: str, status: str) -> None:
        """Update or create a Service node's status field."""
        await self._session.run(
            "MERGE (s:Service {name:$name}) SET s.status = $status, s.last_updated = datetime()",
            name=name,
            status=status,
        )
        logger.info(f"[Neo4jService] Upserted {name} status={status}")

    async def record_incident(
        self,
        incident_id: str,
        service: str,
        severity: str,
        description: str,
    ) -> None:
        """Write a new Incident node and link it to the affected service."""
        await self._session.run(
            "MERGE (i:Incident {id:$id}) "
            "SET i.severity=$severity, i.description=$description, i.timestamp=datetime(), i.status='open' "
            "WITH i "
            "MATCH (s:Service {name:$service}) "
            "MERGE (i)-[:AFFECTS]->(s)",
            id=incident_id,
            service=service,
            severity=severity,
            description=description,
        )
        logger.info(f"[Neo4jService] Recorded incident {incident_id} → {service}")

    async def close_incident(self, incident_id: str) -> None:
        await self._session.run(
            "MATCH (i:Incident {id:$id}) SET i.status='resolved', i.resolved_at=datetime()",
            id=incident_id,
        )

    async def record_deployment(
        self,
        deploy_id: str,
        service: str,
        version: str,
        author: str = "ci-bot",
    ) -> None:
        """Write a new Deployment node and link it to its service."""
        await self._session.run(
            "MERGE (d:Deployment {id:$id}) "
            "SET d.version=$version, d.author=$author, "
            "d.timestamp=datetime(), d.status='completed' "
            "WITH d "
            "MATCH (s:Service {name:$service}) "
            "MERGE (d)-[:DEPLOYED_IN]->(s)",
            id=deploy_id,
            service=service,
            version=version,
            author=author,
        )
        logger.info(f"[Neo4jService] Recorded deployment {deploy_id} on {service}")

    async def write_web_intelligence(
        self,
        service: str,
        source_url: str,
        summary: str,
        label: str = "WebKnowledge",
    ) -> None:
        """
        Persist web search findings back into the knowledge graph.

        Creates a WebKnowledge node and links it to the relevant Service.
        This makes future graph queries aware of externally discovered facts.
        """
        await self._session.run(
            "MERGE (w:WebKnowledge {url:$url}) "
            "SET w.summary=$summary, w.label=$label, w.fetched_at=datetime() "
            "WITH w "
            "MATCH (s:Service {name:$service}) "
            "MERGE (s)-[:HAS_INTELLIGENCE]->(w)",
            url=source_url,
            summary=summary,
            label=label,
            service=service,
        )
        logger.info(f"[Neo4jService] Web intelligence written for {service}: {source_url}")
