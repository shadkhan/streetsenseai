"""AI-007 — Audit log repository: persist and retrieve AI interaction records."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AIAuditLog
from schemas.audit import AuditLogCreate, AuditLogRead


def _row_to_domain(row: AIAuditLog) -> AuditLogRead:
    return AuditLogRead(
        id=row.id,
        interaction_type=row.interaction_type,  # type: ignore[arg-type]
        query=row.query,
        response=row.response,
        citations=row.citations,
        session_id=row.session_id,
        created_at=row.created_at.isoformat(),
    )


async def save_log(session: AsyncSession, entry: AuditLogCreate) -> AuditLogRead:
    """Append one audit log entry. Called after each AI response completes."""
    row = AIAuditLog(
        id=str(uuid.uuid4()),
        interaction_type=entry.interaction_type,
        query=entry.query,
        response=entry.response,
        citations=entry.citations,
        session_id=entry.session_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _row_to_domain(row)


async def get_recent_logs(
    session: AsyncSession,
    limit: int = 50,
    interaction_type: str | None = None,
) -> list[AuditLogRead]:
    """Return the most recent audit entries, newest first."""
    stmt = select(AIAuditLog).order_by(AIAuditLog.created_at.desc()).limit(limit)
    if interaction_type is not None:
        stmt = stmt.where(AIAuditLog.interaction_type == interaction_type)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_domain(row) for row in rows]
