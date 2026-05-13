"""Pydantic schemas for corridor definitions (CR-001).

Mirrors the TypeScript Corridor interface in apps/web/types/index.ts.
Keep in sync: any change here must be reflected in types/index.ts.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from schemas.domain import LineStringGeometry, RiskFactor, RiskLevel, StreetWork

RoadClassification = Literal["A", "B", "C", "unclassified"]


class CorridorBase(BaseModel):
    """Core corridor fields — written by seed_corridors and the OS/synthetic generators."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    name: str
    road_classification: RoadClassification
    geometry: LineStringGeometry
    source: str = "synthetic"  # "os_open_roads" | "synthetic"


class CorridorRead(CorridorBase):
    """Full corridor read response — risk fields populated by CR-003/CR-004."""

    risk_level: RiskLevel | None = None
    risk_score: float | None = None          # 0-100
    risk_factors: list[RiskFactor] = []
    concurrent_works: list[StreetWork] = []
    active_works_count: int = 0
    planned_works_count: int = 0
    last_calculated: str | None = None       # ISO 8601
