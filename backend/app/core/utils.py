"""
Shared utilities used across ALL agents.
Agent-specific logic that is NOT shared belongs in agents/<name>/utils.py.
"""

from __future__ import annotations

import os
from functools import lru_cache

import yaml


# ─── Prompt loading ──────────────────────────────────────────────────────────


@lru_cache(maxsize=64)
def load_prompt(agent_name: str) -> dict[str, str]:
    """
    Load and cache prompts.yaml for an agent.

    The file must live at  app/agents/<agent_name>/prompts.yaml
    and contain at minimum the keys ``system`` and ``user_template``.

    Args:
        agent_name: directory name under app/agents/, e.g. ``'classifier'``

    Returns:
        Mapping with keys ``system`` and ``user_template``.

    Raises:
        FileNotFoundError: if the prompts file does not exist.
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))  # → app/
    prompt_path = os.path.join(base_dir, "agents", agent_name, "prompts.yaml")

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(
            f"Prompt file not found for agent '{agent_name}': {prompt_path}"
        )

    with open(prompt_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    return {
        "system": data.get("system", ""),
        "user_template": data.get("user_template", ""),
    }


def format_prompt(template: str, **kwargs: object) -> str:
    """
    Substitute ``{key}`` placeholders in a prompt template.

    Args:
        template: String containing ``{key}`` placeholders.
        **kwargs: Substitution values.

    Returns:
        Fully substituted string.

    Raises:
        ValueError: if a required placeholder is missing.
    """
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        raise ValueError(f"Missing prompt variable: {exc}") from exc


# ─── Neo4j helpers (shared across graph_analyzer, searcher, …) ───────────────


def build_neo4j_hints(service: str, entities: list[str]) -> list[str]:
    """
    Build a list of Cypher query *hints* for a service and its related entities.

    These are informational strings passed to the LLM – they are **not**
    executed directly against the database.

    Args:
        service:  Primary service name (e.g. ``'checkout-service'``).
        entities: Additional entity names extracted from the incident query.

    Returns:
        List of Cypher query strings.
    """
    hints: list[str] = [
        f"MATCH (s:Service {{name: '{service}'}}) RETURN s",
        f"MATCH (s:Service {{name: '{service}'}})-[:DEPENDS_ON]->(dep) RETURN dep",
        (
            f"MATCH (d:Deployment)-[:DEPLOYED_IN]->(s:Service {{name: '{service}'}}) "
            f"RETURN d ORDER BY d.timestamp DESC LIMIT 5"
        ),
        f"MATCH (i:Incident)-[:AFFECTS]->(s:Service {{name: '{service}'}}) "
        f"RETURN i ORDER BY i.timestamp DESC LIMIT 5",
    ]
    for entity in entities:
        if entity != service:
            hints.append(f"MATCH (s:Service {{name: '{entity}'}}) RETURN s")
    return hints


def normalize_service_name(name: str) -> str:
    """
    Lowercase, strip whitespace, and replace spaces with hyphens.

    Args:
        name: Raw service name string.

    Returns:
        Normalised slug, e.g. ``'checkout-service'``.
    """
    return name.strip().lower().replace(" ", "-")
