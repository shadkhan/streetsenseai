"""Pydantic schemas for NUAR Harmonised Data Model (UN-001-prep).

Domain types mirror the TypeScript types defined in CLAUDE.md Section 8.

NUARAsset: in-memory only — geometry is NEVER serialised to JSON for storage.
StrikeRisk: the only NUAR-derived value that is persisted (nuar_strike_risks).
AssetDensityRead: re-exported from nuar_density for convenience.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ── Asset owner ────────────────────────────────────────────────────────────────

class NUARAssetOwnerBase(BaseModel):
    name: str
    asset_type: str  # 'gas' | 'electric' | 'water' | 'telecoms' | 'other'
    contact_email: str | None = None


class NUARAssetOwnerRead(NUARAssetOwnerBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Asset type ─────────────────────────────────────────────────────────────────

class NUARAssetTypeBase(BaseModel):
    owner_id: uuid.UUID
    type_code: str
    description: str


class NUARAssetTypeRead(NUARAssetTypeBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


# ── Underground asset (in-memory domain model — never serialised to DB) ────────

class NUARAssetRead(BaseModel):
    """In-memory NUAR asset — matches TypeScript NUARAsset from CLAUDE.md §8.

    ADR-007: This schema represents a queried/cached asset. It is NEVER used
    as a request body for database writes with live NUAR data.
    """

    asset_id: str
    asset_type: str  # 'gas' | 'electric' | 'water' | 'telecoms' | 'other'
    depth: float | None = None
    pressure_tier: str | None = None
    voltage_level: str | None = None
    operator_name: str
    geometry: dict[str, Any]  # GeoJSON geometry object — WGS84 (EPSG:4326)

    model_config = {"from_attributes": True}


# ── Strike risk (persisted) ────────────────────────────────────────────────────

class HighestRiskAsset(BaseModel):
    """The single highest-risk asset found near a permit works area."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    type: str       # 'gas' | 'electric' | 'water' | 'telecoms' | 'other'
    operator: str   # Utility owner name
    risk: str       # 'low' | 'medium' | 'high' | 'critical'


class StrikeRiskCreate(BaseModel):
    """Input schema for creating a new strike risk record.

    Uses camelCase aliases so FastAPI serialises to the TypeScript StrikeRisk
    shape in CLAUDE.md §8 when response_model_by_alias=True is set.
    populate_by_name=True preserves snake_case access from Python code.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    permit_reference: str
    overall_risk: str  # 'low' | 'medium' | 'high' | 'critical'
    asset_count: int = Field(ge=0)
    assets_by_type: dict[str, int]
    highest_risk_asset: HighestRiskAsset | None = None


class StrikeRiskRead(StrikeRiskCreate):
    """Response schema — matches TypeScript StrikeRisk from CLAUDE.md §8."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    id: uuid.UUID
    calculated_at: datetime
