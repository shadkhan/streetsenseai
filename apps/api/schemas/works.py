"""SM-008 — Canonical Pydantic v2 schemas for Street Manager permit data.

These schemas are the ground truth for validation. Every synthetic record
produced by services/synthetic/generator.py and every ingested record from
the live Street Manager API must pass StreetWorkBase without modification.

Geometry types are imported from schemas/domain.py (single definition).
WorksGeometry uses a discriminated union so Pydantic can parse GeoJSON dicts
directly without ambiguity between Point and LineString.
"""
from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from schemas.domain import LineStringGeometry, PointGeometry

# ── Geometry discriminated union ───────────────────────────────────────────────

WorksGeometry = Annotated[
    Union[PointGeometry, LineStringGeometry],
    Field(discriminator="type"),
]

# ── Status enum ────────────────────────────────────────────────────────────────


class StreetWorkStatus(str, Enum):
    """Mirrors the TypeScript StreetWorkStatus union type exactly."""

    submitted = "submitted"
    granted = "granted"
    permit_modification_request = "permit_modification_request"
    refused = "refused"
    revoked = "revoked"
    in_progress = "in_progress"
    completed = "completed"
    closed = "closed"


# ── Validation patterns ────────────────────────────────────────────────────────

_PERMIT_RE = re.compile(r"^[A-Z0-9]+/\d{4}/\d+$")
_USRN_RE = re.compile(r"^\d{8}$")


# ── Base schema ────────────────────────────────────────────────────────────────


class StreetWorkBase(BaseModel):
    """Canonical shape — mirrors the TypeScript StreetWork interface from CLAUDE.md §8.

    All datetime fields use ISO 8601 strings to mirror the TypeScript types.
    camelCase aliases are applied so API responses match the frontend types.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    permit_reference: str
    usrn: str
    street_name: str
    authority: str
    promoter: str
    promoter_licence_number: str
    work_type: str
    traffic_management_type: str
    restriction_type: str
    proposed_start_date: str  # ISO 8601 date string
    proposed_end_date: str  # ISO 8601 date string
    actual_start_date: str | None = None
    actual_end_date: str | None = None
    status: StreetWorkStatus
    geometry: WorksGeometry

    @field_validator("permit_reference")
    @classmethod
    def validate_permit_reference(cls, v: str) -> str:
        if not _PERMIT_RE.match(v):
            raise ValueError(
                f"Permit reference '{v}' must match LICENCE/YEAR/SEQUENCE "
                f"(e.g. WG1/2026/00001)"
            )
        return v

    @field_validator("usrn")
    @classmethod
    def validate_usrn(cls, v: str) -> str:
        if not _USRN_RE.match(v):
            raise ValueError(f"USRN '{v}' must be exactly 8 digits")
        return v

    @model_validator(mode="after")
    def validate_date_order(self) -> "StreetWorkBase":
        try:
            start = date.fromisoformat(self.proposed_start_date)
            end = date.fromisoformat(self.proposed_end_date)
        except ValueError:
            return self  # malformed dates — field-level parsing will raise
        if end <= start:
            raise ValueError(
                f"proposed_end_date ({self.proposed_end_date}) must be strictly "
                f"after proposed_start_date ({self.proposed_start_date})"
            )
        return self


class StreetWorkCreate(StreetWorkBase):
    """Schema for ingest — all base fields required, no derived fields added."""


class StreetWorkRead(StreetWorkBase):
    """Schema for API responses — extends base with server-computed fields."""

    risk_score: Literal["low", "medium", "high", "critical"] | None = None
