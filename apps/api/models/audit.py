from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class AIAuditLog(Base):
    """Persistent audit trail for every AI interaction (AI-007).

    Logged after each copilot response or permit summary completes.
    Never modified after creation — append-only.
    """

    __tablename__ = "ai_audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    interaction_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # 'copilot' | 'permit_summary'
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
