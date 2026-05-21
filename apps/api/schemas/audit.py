from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class AuditLogCreate(BaseModel):
    """Payload sent from the frontend after each AI interaction completes."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    interaction_type: Literal["copilot", "permit_summary"]
    query: str
    response: str
    citations: list[dict] | None = None
    session_id: str | None = None
    flagged: bool = False
    flag_reason: str | None = None


class AuditLogRead(AuditLogCreate):
    """Full audit log entry including server-assigned fields."""

    id: str
    created_at: str  # ISO 8601
