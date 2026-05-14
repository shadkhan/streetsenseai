"""AI-007 — Audit Trail endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.audit import AuditLogCreate, AuditLogRead
from services.audit_repository import get_recent_logs, save_log

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post(
    "/log",
    response_model=AuditLogRead,
    response_model_by_alias=True,
    status_code=201,
    summary="Log an AI interaction",
    description=(
        "AI-007: Appends one audit record after a copilot response or permit summary "
        "completes. Called by the frontend after each streaming response finishes."
    ),
)
async def create_log(
    entry: AuditLogCreate,
    session: AsyncSession = Depends(get_db),
) -> AuditLogRead:
    return await save_log(session, entry)


@router.get(
    "/logs",
    response_model=list[AuditLogRead],
    response_model_by_alias=True,
    summary="List recent AI audit logs",
    description=(
        "Returns the most recent AI interaction records, newest first. "
        "Optionally filter by interaction_type ('copilot' or 'permit_summary')."
    ),
)
async def list_logs(
    limit: int = 50,
    interaction_type: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[AuditLogRead]:
    return await get_recent_logs(session, limit=limit, interaction_type=interaction_type)
