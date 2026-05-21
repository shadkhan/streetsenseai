"""DT-005 — Embeddable widget API endpoints.

Lightweight corridor summary designed for embedding via <iframe> in
CausewayOne or any third-party portal.

Endpoints:
  GET /embed/corridor/{id}   minimal risk summary for embeddable widget
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.corridor_repository import get_corridor_with_risk

router = APIRouter(prefix="/embed", tags=["embed"])


class EmbedCorridorSummary(BaseModel):
    corridorId: str
    name: str
    roadClassification: str
    riskLevel: str | None
    riskScore: float | None
    activeWorksCount: int
    plannedWorksCount: int
    lastCalculated: str | None
    embedUrl: str


@router.get(
    "/corridor/{corridor_id}",
    response_model=EmbedCorridorSummary,
    summary="DT-005 — Lightweight corridor summary for embeddable widget",
)
async def get_embed_corridor(
    corridor_id: str,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> EmbedCorridorSummary:
    # Allow cross-origin embedding — needed for CausewayOne <iframe>
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["X-Frame-Options"] = "ALLOWALL"

    corridor = await get_corridor_with_risk(session, corridor_id, None, None)
    if not corridor:
        raise HTTPException(status_code=404, detail=f"Corridor '{corridor_id}' not found")

    return EmbedCorridorSummary(
        corridorId=corridor.id,
        name=corridor.name,
        roadClassification=corridor.roadClassification,
        riskLevel=corridor.riskLevel,
        riskScore=corridor.riskScore,
        activeWorksCount=corridor.activeWorksCount,
        plannedWorksCount=corridor.plannedWorksCount,
        lastCalculated=corridor.lastCalculated,
        embedUrl=f"/embed/corridor/{corridor_id}",
    )
