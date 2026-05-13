"""CR-003/004 — Periodic corridor risk scoring Celery task.

score_all_corridors runs every hour via Celery Beat, scoring every corridor
in the database and saving the result.  The list endpoint (/corridors) then
serves the stored risk_level without rerunning spatial queries.

The detail endpoint (/corridors/{id}) always computes fresh — this task keeps
the list view up to date in the background.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="tasks.risk_tasks.score_all_corridors", bind=True, max_retries=3)  # type: ignore[misc]
def score_all_corridors(self: Any) -> dict[str, int]:  # type: ignore[misc]
    """Score all corridors and persist risk_level + risk_score to the DB.

    Scheduled every hour by Celery Beat (see celery_app.py).
    Calls corridor_risk.score_corridor (CR-002/003/004) for each corridor
    and writes the result via corridor_repository.save_corridor_risk.
    """

    async def _run() -> dict[str, int]:
        from database import async_session_factory
        from services.corridor_repository import get_all_corridors, save_corridor_risk
        from services.corridor_risk import score_corridor

        scored = 0
        errors = 0

        async with async_session_factory() as session:
            corridors = await get_all_corridors(session)

        for corridor in corridors:
            try:
                async with async_session_factory() as session:
                    risk_score, risk_level, _, _ = await score_corridor(session, corridor.id)
                    await save_corridor_risk(session, corridor.id, risk_score, risk_level)
                scored += 1
            except Exception as exc:
                logger.error("Failed to score corridor %s: %s", corridor.id, exc)
                errors += 1

        logger.info("Corridor risk scoring complete: %d scored, %d errors", scored, errors)
        return {"scored": scored, "errors": errors}

    return asyncio.run(_run())
