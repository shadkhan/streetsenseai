"""AI-005 — Scheduling Advisor endpoints."""
from __future__ import annotations

from datetime import date as DateType

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.scheduling import SchedulingConflict
from services.scheduling import find_scheduling_conflicts

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


@router.get(
    "/conflicts",
    response_model=list[SchedulingConflict],
    response_model_by_alias=True,
    summary="Detect scheduling conflicts",
    description=(
        "AI-005: Returns pairs of concurrent street works whose proposed date ranges "
        "overlap on the same corridor, sorted by severity descending. "
        "Optionally filter by corridor_id and/or a date window."
    ),
)
async def get_conflicts(
    start_date: DateType | None = None,
    end_date: DateType | None = None,
    corridor_id: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[SchedulingConflict]:
    return await find_scheduling_conflicts(
        session,
        window_start=start_date,
        window_end=end_date,
        corridor_id=corridor_id,
    )
