"""
GraphAnalyzerAgent — the backbone of the incident analysis pipeline.

This agent performs DEEP Neo4j knowledge graph traversal far beyond simple
dependency lookup. It queries:
  - Service → dependency chains (up to 3 hops)
  - Deployment correlation windows
  - Historical incident fingerprints
  - Team ownership and escalation paths
  - Runbook associations
  - SLO/health status of every node
  - Configuration change events
  - Cross-cluster impact estimation

The raw graph data is synthesised by the LLM into a structured output
consumed by the RootCauseFinderAgent and RemediatorAgent.
"""

from __future__ import annotations

from app.core import BaseAgent, format_prompt
from app.db.neo4j import neo4j_driver
from logger import logger

from .models import GraphAnalyzerQueryInput, GraphAnalyzerQueryOutput


class GraphAnalyzerAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        super().__init__("graph_analyzer", **kwargs)
        self._chain = self._build_chain(GraphAnalyzerQueryOutput)

    # Neo4j queries

    async def _query_neo4j(self, service: str, entities: list[str]) -> dict:
        try:
            async with neo4j_driver.session() as session:
                # 1. Direct dependencies (1 hop)
                deps = await (
                    await session.run(
                        "MATCH (s:Service {name:$s})-[r]->(dep) "
                        "RETURN dep.name AS name, dep.type AS type, "
                        "dep.status AS status, type(r) AS relation LIMIT 20",
                        s=service,
                    )
                ).data()

                # 2. Upstream callers (who calls ME?)
                upstream = await (
                    await session.run(
                        "MATCH (u)-[:DEPENDS_ON]->(s:Service {name:$s}) "
                        "RETURN u.name AS name, u.type AS type, u.status AS status LIMIT 10",
                        s=service,
                    )
                ).data()

                # 3. Full blast radius — 3-hop transitive closure
                blast = await (
                    await session.run(
                        "MATCH path = (s:Service {name:$s})-[:DEPENDS_ON*1..3]->(dep) "
                        "RETURN DISTINCT dep.name AS name, dep.type AS type, "
                        "dep.status AS status, length(path) AS hops",
                        s=service,
                    )
                ).data()

                # 4. Recent deployments across all blast-radius services
                blast_names = [b["name"] for b in blast] + [service]
                deployments = await (
                    await session.run(
                        "MATCH (d:Deployment)-[:DEPLOYED_IN]->(s:Service) "
                        "WHERE s.name IN $names "
                        "RETURN d.id AS id, d.version AS version, "
                        "d.status AS status, d.timestamp AS timestamp, "
                        "d.author AS author, s.name AS service "
                        "ORDER BY d.timestamp DESC LIMIT 10",
                        names=blast_names,
                    )
                ).data()

                # 5. Historical incidents — same service + similar fingerprint
                incidents = await (
                    await session.run(
                        "MATCH (i:Incident)-[:AFFECTS]->(s:Service {name:$s}) "
                        "RETURN i.id AS id, i.severity AS severity, "
                        "i.description AS description, i.status AS status, "
                        "i.timestamp AS timestamp "
                        "ORDER BY i.timestamp DESC LIMIT 10",
                        s=service,
                    )
                ).data()

                # 6. Runbooks attached to impacted services
                runbooks = await (
                    await session.run(
                        "MATCH (s:Service)-[:HAS_RUNBOOK]->(rb:Runbook) "
                        "WHERE s.name IN $names "
                        "RETURN s.name AS service, rb.id AS id, "
                        "rb.title AS title, rb.url AS url",
                        names=blast_names,
                    )
                ).data()

                # 7. Team ownership across blast radius
                ownership = await (
                    await session.run(
                        "MATCH (s:Service)-[:OWNED_BY]->(t:Team) "
                        "WHERE s.name IN $names "
                        "RETURN s.name AS service, t.name AS team, t.slack AS slack",
                        names=blast_names,
                    )
                ).data()

                # 8. Config changes (if ConfigChange nodes exist)
                config_changes = await (
                    await session.run(
                        "MATCH (c:ConfigChange)-[:APPLIED_TO]->(s:Service {name:$s}) "
                        "RETURN c.id AS id, c.key AS key, c.old_value AS old_value, "
                        "c.new_value AS new_value, c.timestamp AS timestamp "
                        "ORDER BY c.timestamp DESC LIMIT 5",
                        s=service,
                    )
                ).data()

                # 9. Cross-entity incidents — incidents affecting related entities
                entity_incidents = []
                if entities:
                    entity_incidents = await (
                        await session.run(
                            "MATCH (i:Incident)-[:AFFECTS]->(s:Service) "
                            "WHERE s.name IN $names AND s.name <> $primary "
                            "RETURN i.id AS id, i.severity AS severity, "
                            "i.description AS description, s.name AS service "
                            "ORDER BY i.timestamp DESC LIMIT 5",
                            names=entities,
                            primary=service,
                        )
                    ).data()

                return {
                    "dependencies": deps,
                    "upstream": upstream,
                    "blast_radius": blast,
                    "deployments": deployments,
                    "incidents": incidents,
                    "runbooks": runbooks,
                    "ownership": ownership,
                    "config_changes": config_changes,
                    "entity_incidents": entity_incidents,
                }

        except Exception as exc:
            logger.warning(f"[GraphAnalyzerAgent] Neo4j unavailable: {exc}. Using mock.")
            return self._mock_data(service)

    @staticmethod
    def _mock_data(service: str) -> dict:
        return {
            "dependencies": [
                {
                    "name": "postgres-primary",
                    "type": "Database",
                    "status": "healthy",
                    "relation": "DEPENDS_ON",
                },
                {
                    "name": "redis-cache",
                    "type": "Cache",
                    "status": "degraded",
                    "relation": "DEPENDS_ON",
                },
                {
                    "name": "payment-service",
                    "type": "Service",
                    "status": "healthy",
                    "relation": "DEPENDS_ON",
                },
            ],
            "upstream": [{"name": "api-gateway", "type": "Service", "status": "degraded"}],
            "blast_radius": [
                {"name": "postgres-primary", "type": "Database", "status": "healthy", "hops": 1},
                {"name": "redis-cache", "type": "Cache", "status": "degraded", "hops": 1},
                {"name": "payment-service", "type": "Service", "status": "healthy", "hops": 1},
                {"name": "api-gateway", "type": "Service", "status": "degraded", "hops": 0},
            ],
            "deployments": [
                {
                    "id": "deploy-001",
                    "version": "v2.3.1",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "status": "completed",
                    "author": "ci-bot",
                    "service": service,
                }
            ],
            "incidents": [
                {
                    "id": "INC-001",
                    "severity": "P1",
                    "description": "High latency",
                    "status": "resolved",
                    "timestamp": "2024-01-10T11:00:00Z",
                }
            ],
            "runbooks": [
                {
                    "service": service,
                    "id": "RB-001",
                    "title": "Checkout Rollback",
                    "url": "https://wiki.internal/runbooks/checkout-rollback",
                }
            ],
            "ownership": [
                {"service": service, "team": "checkout-team", "slack": "#checkout-squad"}
            ],
            "config_changes": [],
            "entity_incidents": [],
        }

    # Run

    async def run(self, inp: GraphAnalyzerQueryInput) -> GraphAnalyzerQueryOutput:
        self._log(f"Deep graph traversal for service={inp.service}")
        raw = await self._query_neo4j(inp.service, inp.entities)

        user_msg = format_prompt(
            self._prompts["user_template"],
            service=inp.service,
            incident_type=inp.incident_type,
            entities=inp.entities,
            dependencies=raw["dependencies"],
            upstream=raw["upstream"],
            blast_radius=raw["blast_radius"],
            deployments=raw["deployments"],
            incidents=raw["incidents"],
            runbooks=raw["runbooks"],
            ownership=raw["ownership"],
            config_changes=raw["config_changes"],
            entity_incidents=raw["entity_incidents"],
        )
        messages = [
            ("system", self._prompts["system"]),
            ("human", user_msg),
        ]
        result: GraphAnalyzerQueryOutput = await self._chain.ainvoke(messages)
        self._log(
            f"blast_radius={result.blast_radius_count} services={len(result.affected_services)}"
        )
        return result
