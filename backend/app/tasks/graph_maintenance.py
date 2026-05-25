"""
Celery tasks that keep the Neo4j knowledge graph fresh.

Tasks:
  refresh_service_health       — queries DuckDuckGo status pages, updates graph
  sync_web_intelligence_to_graph — writes cached web-search findings to graph
  prune_stale_incidents        — removes old resolved incidents
"""

from __future__ import annotations

import asyncio

from app.agents.web_searcher.utils import web_search
from app.db.neo4j import neo4j_driver
from app.services.neo4j_service import Neo4jService
from app.tasks.celery_app import celery_app
from logger import logger

# Services to monitor for status-page health signals
_MONITORED_SERVICES = [
    "checkout-service",
    "payment-service",
    "inventory-service",
    "api-gateway",
    "user-service",
]


def _run(coro):
    """Execute an async coroutine from a synchronous Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    name="app.tasks.graph_maintenance.refresh_service_health", bind=True, max_retries=3
)
def refresh_service_health(self):
    """
    For each monitored service, search for current status signals.
    Updates the Neo4j Service node with the inferred status.
    """
    logger.info("[Task:refresh_service_health] Starting")

    async def _inner():
        async with neo4j_driver.session() as session:
            svc = Neo4jService(session)
            for service in _MONITORED_SERVICES:
                try:
                    results = web_search(f"{service} status outage incident", max_results=3)
                    # Simple heuristic: if any snippet contains "outage" or "down" → degraded
                    combined = " ".join(r.snippet.lower() for r in results)
                    if any(kw in combined for kw in ("outage", "down", "unavailable", "incident")):
                        status = "degraded"
                    else:
                        status = "healthy"
                    await svc.upsert_service_status(service, status)
                    logger.info(f"[Task:refresh_service_health] {service} → {status}")
                except Exception as exc:
                    logger.warning(f"[Task:refresh_service_health] Failed for {service}: {exc}")

    try:
        _run(_inner())
        logger.info("[Task:refresh_service_health] Complete")
    except Exception as exc:
        logger.error(f"[Task:refresh_service_health] Error: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    name="app.tasks.graph_maintenance.sync_web_intelligence_to_graph", bind=True, max_retries=3
)
def sync_web_intelligence_to_graph(self):
    """
    Run targeted web searches for each monitored service and write
    findings back into the Neo4j knowledge graph as WebKnowledge nodes.
    """
    logger.info("[Task:sync_web_intelligence] Starting")

    async def _inner():
        async with neo4j_driver.session() as session:
            svc = Neo4jService(session)
            for service in _MONITORED_SERVICES:
                try:
                    results = web_search(f"{service} CVE bug known issue", max_results=3)
                    for r in results:
                        if r.url and r.snippet:
                            await svc.write_web_intelligence(
                                service=service,
                                source_url=r.url,
                                summary=r.snippet[:500],
                                label="CVEOrBugReport",
                            )
                except Exception as exc:
                    logger.warning(f"[Task:sync_web_intelligence] Failed for {service}: {exc}")

    try:
        _run(_inner())
        logger.info("[Task:sync_web_intelligence] Complete")
    except Exception as exc:
        logger.error(f"[Task:sync_web_intelligence] Error: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(name="app.tasks.graph_maintenance.prune_stale_incidents", bind=True, max_retries=2)
def prune_stale_incidents(self, days_old: int = 90):
    """
    Remove resolved Incident nodes older than ``days_old`` days from Neo4j.
    Keeps the graph lean and relevant.
    """
    logger.info(f"[Task:prune_stale_incidents] Pruning incidents older than {days_old} days")

    async def _inner():
        async with neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (i:Incident) "
                "WHERE i.status = 'resolved' "
                "AND i.timestamp < datetime() - duration({days: $days}) "
                "WITH i LIMIT 500 "
                "DETACH DELETE i "
                "RETURN count(i) AS deleted",
                days=days_old,
            )
            record = await result.single()
            deleted = record["deleted"] if record else 0
            logger.info(f"[Task:prune_stale_incidents] Deleted {deleted} stale incidents")

    try:
        _run(_inner())
    except Exception as exc:
        logger.error(f"[Task:prune_stale_incidents] Error: {exc}")
        raise self.retry(exc=exc, countdown=300)
