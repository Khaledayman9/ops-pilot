"""
Searcher-specific utilities — not shared across other agents.
Shared utilities live in app/core/utils.py.
"""

def build_neo4j_hints(service: str, entities: list[str]) -> list[str]:
    """Build Cypher query strings from extracted entity list."""
    hints = [
        f"MATCH (s:Service {{name: '{service}'}}) RETURN s",
        f"MATCH (s:Service {{name: '{service}'}})-[:DEPENDS_ON]->(dep) RETURN dep",
        f"MATCH (d:Deployment)-[:DEPLOYED_IN]->(s:Service {{name: '{service}'}}) "
        f"RETURN d ORDER BY d.timestamp DESC LIMIT 5",
    ]
    for entity in entities:
        if entity != service:
            hints.append(f"MATCH (s:Service {{name: '{entity}'}}) RETURN s")
    return hints


def normalize_service_name(name: str) -> str:
    """Lowercase and strip whitespace from a service name."""
    return name.strip().lower().replace(" ", "-")