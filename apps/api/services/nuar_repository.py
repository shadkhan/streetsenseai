"""Repository layer for NUAR-derived persistence (ADR-007).

Only NUARStrikeRisk is stored — no geometry, no raw NUAR assets.
See also: services/nuar_density.py (query-only), services/nuar_strike.py.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.nuar import NUARStrikeRisk
from schemas.nuar import HighestRiskAsset, StrikeRiskCreate, StrikeRiskRead


def _row_to_read(row: NUARStrikeRisk) -> StrikeRiskRead:
    """Convert an ORM row to the Pydantic read schema."""
    highest: dict | None = row.highest_risk_asset  # type: ignore[assignment]
    return StrikeRiskRead(
        id=row.id,
        permit_reference=row.permit_reference,
        overall_risk=row.overall_risk,
        asset_count=row.asset_count,
        assets_by_type=dict(row.assets_by_type),
        highest_risk_asset=(
            HighestRiskAsset.model_validate(highest) if highest else None
        ),
        calculated_at=row.calculated_at,
    )


async def save_strike_risk(
    session: AsyncSession,
    data: StrikeRiskCreate,
) -> NUARStrikeRisk:
    """Insert a new strike risk record and flush (caller must commit)."""
    row = NUARStrikeRisk(
        id=uuid.uuid4(),
        permit_reference=data.permit_reference,
        overall_risk=data.overall_risk,
        asset_count=data.asset_count,
        assets_by_type=data.assets_by_type,
        highest_risk_asset=(
            data.highest_risk_asset.model_dump() if data.highest_risk_asset else None
        ),
    )
    session.add(row)
    await session.flush()
    return row


async def get_latest_strike_risk(
    session: AsyncSession,
    permit_reference: str,
) -> StrikeRiskRead | None:
    """Return the most recent cached strike risk for a permit, or None."""
    stmt = (
        select(NUARStrikeRisk)
        .where(NUARStrikeRisk.permit_reference == permit_reference)
        .order_by(NUARStrikeRisk.calculated_at.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _row_to_read(row) if row else None
