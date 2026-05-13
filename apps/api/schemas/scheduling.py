from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from schemas.domain import RiskLevel


class SchedulingConflict(BaseModel):
    """A detected scheduling conflict between two permits on the same corridor.

    Produced by AI-005: pairs of street works whose date ranges overlap and
    whose combined traffic management severity warrants attention.
    Mirrors the TypeScript SchedulingConflict interface in types/index.ts.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    corridor_id: str
    corridor_name: str
    permit_a: str
    permit_b: str
    street_name: str
    overlap_start: str   # ISO 8601 date
    overlap_end: str     # ISO 8601 date
    overlap_days: int
    severity: RiskLevel
    severity_score: float   # 0–100
    promoter_a: str
    promoter_b: str
    traffic_management_a: str
    traffic_management_b: str
    recommendation: str
