"""NC-001 — Pydantic schemas for Non-Compliance Analytics endpoints."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PromoterComplianceRead(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    promoter_licence_number: str
    promoter_name: str
    total_works: int
    overrun_rate: float           # 0–1
    late_start_rate: float        # 0–1
    missing_reinstatement_rate: float  # 0–1
    compliance_score: float       # 0–100, higher is better
    trend: Literal["improving", "stable", "deteriorating"]
    region: str
    last_updated: str             # ISO 8601


class FPNOpportunity(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    permit_reference: str
    promoter: str
    promoter_licence_number: str
    street_name: str
    authority: str
    proposed_end_date: str        # ISO date
    actual_end_date: str          # ISO date
    overrun_days: int


class ComplianceSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    total_promoters: int
    avg_compliance_score: float
    worst_offender: PromoterComplianceRead | None
    best_performer: PromoterComplianceRead | None
    total_fpn_opportunities: int
    calculated_at: str            # ISO 8601


class MonthlyTrend(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    month: str                    # "2026-01"
    compliance_score: float       # 0–100
    total_works: int
    overruns: int
