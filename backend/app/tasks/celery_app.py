"""
Celery application instance.

Workers are started separately from FastAPI:
    celery -A app.tasks.celery_app worker --loglevel=info
    celery -A app.tasks.celery_app beat   --loglevel=info
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from settings import settings

celery_app = Celery(
    "ops-pilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.graph_maintenance"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Periodic schedule (Celery Beat)
celery_app.conf.beat_schedule = {
    # Every 15 minutes: refresh service health from web sources → graph
    "refresh-service-health": {
        "task": "app.tasks.graph_maintenance.refresh_service_health",
        "schedule": crontab(minute="*/15"),
        "args": [],
    },
    # Every hour: sync any new web intelligence into Neo4j
    "sync-web-intelligence": {
        "task": "app.tasks.graph_maintenance.sync_web_intelligence_to_graph",
        "schedule": crontab(minute=0),
        "args": [],
    },
    # Daily at 2 AM: prune resolved incidents older than 90 days
    "prune-stale-incidents": {
        "task": "app.tasks.graph_maintenance.prune_stale_incidents",
        "schedule": crontab(hour=2, minute=0),
        "args": [90],
    },
}
