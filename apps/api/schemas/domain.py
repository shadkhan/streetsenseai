"""Python mirrors of the TypeScript domain types in apps/web/types/index.ts.

Keep in sync: any change here must be reflected in types/index.ts and vice versa.
"""
from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# ── Geometry primitives ────────────────────────────────────────────────────────
# Mirrors: Position, PointGeometry, LineStringGeometry, WorksGeometry, CorridorGeometry

Position = tuple[float, float]  # [lng, lat]


class PointGeometry(BaseModel):
    type: Literal["Point"]
    coordinates: Position


class LineStringGeometry(BaseModel):
    type: Literal["LineString"]
    coordinates: list[Position]


WorksGeometry = Union[PointGeometry, LineStringGeometry]
CorridorGeometry = LineStringGeometry  # corridors are always linear

# ── Risk ───────────────────────────────────────────────────────────────────────
RiskLevel = Literal["low", "medium", "high", "critical"]

# ── Status ─────────────────────────────────────────────────────────────────────
StreetWorkStatus = Literal[
    "submitted",
    "granted",
    "permit_modification_request",
    "refused",
    "revoked",
    "in_progress",
    "completed",
    "closed",
]

# ── Street Work ────────────────────────────────────────────────────────────────


# ── Road Info (SM-004) ────────────────────────────────────────────────────────


class RoadInfo(BaseModel):
    """OS Open Roads classification for a road link.

    Sourced from the OS Features API (OpenRoads_RoadLink collection).
    Cached in Redis by USRN for 24 hours — road classifications change rarely.
    Used by Phase 2 corridor risk scoring to weight works by road type.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    road_classification: str           # "A Road", "B Road", "Motorway", "Unclassified"
    road_function: str | None = None   # "A Road", "Local Road", "Motorway", …
    road_name: str | None = None       # "A38", "B4140", etc.
    form_of_way: str | None = None     # "Single Carriageway", "Dual Carriageway", …
    is_primary_route: bool = False     # True for Motorway or A Road


# ── USRN Info (SM-003) ─────────────────────────────────────────────────────────


class USRNInfo(BaseModel):
    """Resolved metadata for a Unique Street Reference Number.

    Sourced from the OS National Street Gazetteer. Cached indefinitely
    in Redis — USRNs are stable identifiers that never change once assigned.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    usrn: str
    street_name: str
    locality: str | None = None
    town: str | None = None
    authority: str | None = None
    road_classification: str | None = None  # A, B, C, U, unclassified


# ── Street Work ────────────────────────────────────────────────────────────────


class StreetWork(BaseModel):
    """Python mirror of the TypeScript StreetWork interface.

    Uses camelCase aliases for JSON serialisation so the API responses
    match the TypeScript type exactly. Python code uses snake_case attributes.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    permit_reference: str
    usrn: str
    street_name: str
    authority: str
    promoter: str
    promoter_licence_number: str
    work_type: str
    traffic_management_type: str
    restriction_type: str
    proposed_start_date: str  # ISO 8601
    proposed_end_date: str  # ISO 8601
    actual_start_date: str | None = None
    actual_end_date: str | None = None
    status: StreetWorkStatus
    geometry: PointGeometry | LineStringGeometry
    risk_score: RiskLevel | None = None
