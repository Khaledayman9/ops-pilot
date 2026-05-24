from app.core import format_prompt, llm, load_prompt
from app.db.neo4j import neo4j_driver
from logger import logger

from .models import GraphAnalyzerQueryInput, GraphAnalyzerQueryOutput

__all__ = ["GraphAgent"]


class GraphAnalyzerAgent:
    def __init__(self) -> None:
        self._llm = llm.with_structured_output(GraphAnalyzerQueryOutput)
        self._prompts = load_prompt("graph_agent")

    async def _query_neo4j(self, service: str) -> dict:
        try:
            async with neo4j_driver.session() as session:
                deps = await (
                    await session.run(
                        "MATCH (s:Service {name:$s})-[r]->(dep) RETURN dep LIMIT 20",
                        s=service,
                    )
                ).data()
                upstream = await (
                    await session.run(
                        "MATCH (u)-[:DEPENDS_ON]->(s:Service {name:$s}) "
                        "RETURN u.name AS name, u.type AS type LIMIT 10",
                        s=service,
                    )
                ).data()
                deployments = await (
                    await session.run(
                        "MATCH (d:Deployment)-[:DEPLOYED_IN]->(s:Service {name:$s}) "
                        "RETURN d ORDER BY d.timestamp DESC LIMIT 5",
                        s=service,
                    )
                ).data()
                incidents = await (
                    await session.run(
                        "MATCH (i:Incident)-[:AFFECTS]->(s:Service {name:$s}) "
                        "RETURN i ORDER BY i.timestamp DESC LIMIT 5",
                        s=service,
                    )
                ).data()
                return {
                    "dependencies": deps,
                    "upstream": upstream,
                    "deployments": deployments,
                    "incidents": incidents,
                }
        except Exception as exc:
            logger.warning(f"[GraphAgent] Neo4j unavailable: {exc}. Using mock.")
            return {
                "dependencies": [
                    {"dep": {"name": "postgres-primary", "type": "Database"}},
                    {"dep": {"name": "redis-cache", "type": "Cache"}},
                    {"dep": {"name": "payment-service", "type": "Service"}},
                ],
                "upstream": [
                    {"name": "api-gateway", "type": "Service"},
                    {"name": "mobile-bff", "type": "Service"},
                ],
                "deployments": [
                    {
                        "d": {
                            "version": "v2.3.1",
                            "timestamp": "2024-01-15T10:30:00Z",
                            "status": "completed",
                        }
                    }
                ],
                "incidents": [
                    {
                        "i": {
                            "id": "INC-001",
                            "severity": "P1",
                            "description": "High latency",
                        }
                    }
                ],
            }

    async def run(self, inp: GraphAnalyzerQueryInput) -> GraphAnalyzerQueryOutput:
        logger.info(f"[GraphAgent] Traversing graph for service={inp.service}")
        raw = await self._query_neo4j(inp.service)
        user_msg = format_prompt(
            self._prompts["user_template"],
            service=inp.service,
            dependencies=raw["dependencies"],
            upstream=raw["upstream"],
            deployments=raw["deployments"],
            incidents=raw["incidents"],
            incident_type=inp.incident_type,
            entities=inp.entities,
        )
        messages = [
            ("system", self._prompts["system"]),
            ("human", user_msg),
        ]
        result: GraphAnalyzerQueryOutput = await self._llm.ainvoke(messages)
        logger.info(f"[GraphAgent] blast_radius={result.blast_radius_count}")
        return result
