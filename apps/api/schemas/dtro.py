"""Pydantic schemas for D-TRO v4.0.0 API (DT-001, ADR-027).

Conforms to: github.com/department-for-transport-public/D-TRO v4.0.0
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── D-TRO v4.0.0 type constants ───────────────────────────────────────────────

TRO_TYPES = {
    "speedLimit",
    "parkingRestriction",
    "roadClosure",
    "busLane",
    "cycleLane",
    "weightRestriction",
    "oneWay",
    "turningProhibition",
    "pedestrianZone",
}


# ── v4.0.0 raw JSON sub-schemas ───────────────────────────────────────────────

class DTROSource(BaseModel):
    reference: str
    publisher: str
    provenance: str
    timestamp: str


class DTROHeader(BaseModel):
    notice: str = "Traffic Regulation Order"
    source: DTROSource


class DTROOrderBody(BaseModel):
    referenceNumber: str
    type: str
    description: str
    authority: str
    isTemporary: bool = False
    validFrom: str        # ISO date string
    validTo: str | None = None
    externalReference: str | None = None


class DTROProvisionRestriction(BaseModel):
    speedInMph: int | None = None
    vehicleCharacteristics: dict[str, Any] = Field(default_factory=dict)
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    exceptions: list[dict[str, Any]] = Field(default_factory=list)


class DTROProvisionBody(BaseModel):
    id: str
    referenceNumber: str
    type: str
    geometry: dict[str, Any]
    restriction: DTROProvisionRestriction = Field(default_factory=DTROProvisionRestriction)


class DTROBody(BaseModel):
    tro: DTROOrderBody
    provisions: list[DTROProvisionBody]


class DTRODocument(BaseModel):
    """Full D-TRO v4.0.0 JSON document."""
    id: str
    schemaVersion: str = "4.0.0"
    header: DTROHeader
    body: DTROBody


# ── API response schemas ───────────────────────────────────────────────────────

class DTROProvisionResponse(BaseModel):
    id: UUID
    orderId: UUID = Field(alias="order_id")
    provisionType: str = Field(alias="provision_type")
    speedMph: int | None = Field(alias="speed_mph")
    restrictionType: str | None = Field(alias="restriction_type")
    conditions: dict[str, Any]

    model_config = {"populate_by_name": True}


class DTROOrderResponse(BaseModel):
    id: UUID
    dtroId: str = Field(alias="dtro_id")
    schemaVersion: str = Field(alias="schema_version")
    referenceNumber: str = Field(alias="reference_number")
    troType: str = Field(alias="tro_type")
    description: str
    authority: str
    isTemporary: bool = Field(alias="is_temporary")
    validFrom: date = Field(alias="valid_from")
    validTo: date | None = Field(alias="valid_to")
    dataSource: str = Field(alias="data_source")
    provisions: list[DTROProvisionResponse] = []
    createdAt: datetime = Field(alias="created_at")

    model_config = {"populate_by_name": True}


class DTROSeedResponse(BaseModel):
    status: str
    orderCount: int
    provisionCount: int
    authorities: list[str]


class DTROStatsResponse(BaseModel):
    totalOrders: int
    temporaryOrders: int
    permanentOrders: int
    byType: dict[str, int]
    byAuthority: dict[str, int]
    dataSource: str


# ── Conflict schemas (DT-002) ─────────────────────────────────────────────────

class TROConflict(BaseModel):
    permitReference: str
    dtroId: str
    troType: str
    conflictType: str   # "spatial_overlap" | "temporal_overlap" | "both"
    severity: str       # RiskLevel
    description: str
    authority: str
    troReferenceNumber: str
    troValidFrom: str
    troValidTo: str | None


class CorridorConflictsResponse(BaseModel):
    corridorId: str
    conflictCount: int
    conflicts: list[TROConflict]
    calculatedAt: str
