"""D-TRO endpoints — Phase 6 (DT-001 through DT-002, ADR-027).

Endpoints:
  POST /dtros/admin/seed                DT-008 — synthetic seed
  GET  /dtros/admin/stats               DT-001 — record counts
  GET  /dtros                           DT-001 — list all D-TROs (paginated)
  GET  /dtros/{dtro_id}                 DT-001 — single D-TRO
  GET  /dtros/geojson                   DT-003 — GeoJSON for map layer
  GET  /corridors/{id}/conflicts        DT-002 — permit+TRO conflicts
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.dtro import DTROOrder, DTROProvision
from schemas.dtro import (
    CorridorConflictsResponse,
    DTROOrderResponse,
    DTROProvisionResponse,
    DTROSeedResponse,
    DTROStatsResponse,
    TROConflict,
)
from services.conflict_detector import ConflictDetector
from services.corridor_repository import get_corridor_with_risk
from services.synthetic.dtro_generator import generate_dtro_orders

router = APIRouter(tags=["dtro"])


# ── DT-008: Synthetic seed ─────────────────────────────────────────────────────

@router.post(
    "/dtros/admin/seed",
    status_code=200,
    summary="DT-008 — Seed synthetic D-TRO orders and provisions",
    description=(
        "Generates 700 deterministic synthetic D-TRO records (500 permanent + 200 TTROs) "
        "conforming to the D-TRO v4.0.0 schema. Idempotent. ADR-027."
    ),
)
async def seed_dtro_orders(
    session: AsyncSession = Depends(get_db),
) -> DTROSeedResponse:
    result = await generate_dtro_orders(session)
    return DTROSeedResponse(**result)


@router.get(
    "/dtros/admin/stats",
    summary="DT-001 — D-TRO record counts",
)
async def get_dtro_stats(
    session: AsyncSession = Depends(get_db),
) -> DTROStatsResponse:
    total = await session.scalar(select(func.count()).select_from(DTROOrder)) or 0
    temp = await session.scalar(
        select(func.count()).select_from(DTROOrder).where(DTROOrder.is_temporary.is_(True))
    ) or 0

    type_rows = (
        await session.execute(
            select(DTROOrder.tro_type, func.count().label("n"))
            .group_by(DTROOrder.tro_type)
            .order_by(func.count().desc())
        )
    ).all()

    auth_rows = (
        await session.execute(
            select(DTROOrder.authority, func.count().label("n"))
            .group_by(DTROOrder.authority)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()

    source_row = await session.scalar(
        select(DTROOrder.data_source).limit(1)
    ) or "unknown"

    return DTROStatsResponse(
        totalOrders=int(total),
        temporaryOrders=int(temp),
        permanentOrders=int(total) - int(temp),
        byType={row.tro_type: row.n for row in type_rows},
        byAuthority={row.authority: row.n for row in auth_rows},
        dataSource=source_row,
    )


# ── DT-001: Query endpoints ────────────────────────────────────────────────────

@router.get(
    "/dtros",
    response_model=list[DTROOrderResponse],
    response_model_by_alias=True,
    summary="DT-001 — List D-TRO orders (paginated)",
)
async def list_dtros(
    page: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tro_type: str | None = Query(None, alias="type"),
    authority: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[DTROOrderResponse]:
    q = select(DTROOrder).order_by(DTROOrder.valid_from.desc())
    if tro_type:
        q = q.where(DTROOrder.tro_type == tro_type)
    if authority:
        q = q.where(DTROOrder.authority.ilike(f"%{authority}%"))
    q = q.offset(page * limit).limit(limit)

    rows = (await session.execute(q)).scalars().all()
    return [
        DTROOrderResponse(
            id=row.id,
            dtro_id=row.dtro_id,
            schema_version=row.schema_version,
            reference_number=row.reference_number,
            tro_type=row.tro_type,
            description=row.description,
            authority=row.authority,
            is_temporary=row.is_temporary,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
            data_source=row.data_source,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get(
    "/dtros/geojson",
    summary="DT-003 — GeoJSON FeatureCollection of D-TRO provisions for map layer",
)
async def get_dtros_geojson(
    min_lng: float = Query(-2.1, alias="minLng"),
    min_lat: float = Query(52.3, alias="minLat"),
    max_lng: float = Query(-1.7, alias="maxLng"),
    max_lat: float = Query(52.7, alias="maxLat"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    bbox_wkt = f"POLYGON(({min_lng} {min_lat},{max_lng} {min_lat},{max_lng} {max_lat},{min_lng} {max_lat},{min_lng} {min_lat}))"
    rows = (
        await session.execute(
            text(
                """
                SELECT p.id, p.provision_type, p.speed_mph, p.restriction_type,
                       o.reference_number, o.tro_type, o.authority, o.is_temporary,
                       o.valid_from, o.valid_to, o.dtro_id,
                       ST_AsGeoJSON(p.geometry)::text AS geojson_geom
                FROM dtro_provisions p
                JOIN dtro_orders o ON o.id = p.order_id
                WHERE ST_Intersects(p.geometry, ST_GeomFromText(:bbox, 4326))
                LIMIT 500
                """
            ),
            {"bbox": bbox_wkt},
        )
    ).fetchall()

    features = []
    for row in rows:
        import json as _json
        geom = _json.loads(row.geojson_geom)
        features.append({
            "type": "Feature",
            "id": str(row.id),
            "properties": {
                "dtroId": row.dtro_id,
                "troType": row.tro_type,
                "provisionType": row.provision_type,
                "speedMph": row.speed_mph,
                "restrictionType": row.restriction_type,
                "referenceNumber": row.reference_number,
                "authority": row.authority,
                "isTemporary": row.is_temporary,
                "validFrom": row.valid_from.isoformat() if row.valid_from else None,
                "validTo": row.valid_to.isoformat() if row.valid_to else None,
            },
            "geometry": geom,
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {"count": len(features), "bbox": [min_lng, min_lat, max_lng, max_lat]},
    }


@router.get(
    "/dtros/{dtro_id}",
    response_model=DTROOrderResponse,
    response_model_by_alias=True,
    summary="DT-001 — Single D-TRO by ID",
)
async def get_dtro(
    dtro_id: str,
    session: AsyncSession = Depends(get_db),
) -> DTROOrderResponse:
    row = (
        await session.execute(
            select(DTROOrder).where(DTROOrder.dtro_id == dtro_id)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail=f"D-TRO '{dtro_id}' not found")
    return DTROOrderResponse(
        id=row.id,
        dtro_id=row.dtro_id,
        schema_version=row.schema_version,
        reference_number=row.reference_number,
        tro_type=row.tro_type,
        description=row.description,
        authority=row.authority,
        is_temporary=row.is_temporary,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        data_source=row.data_source,
        created_at=row.created_at,
    )


# ── DT-002: Conflict detection ─────────────────────────────────────────────────

@router.get(
    "/corridors/{corridor_id}/conflicts",
    response_model=CorridorConflictsResponse,
    summary="DT-002 — List permit+TRO conflicts for works on this corridor",
)
async def get_corridor_conflicts(
    corridor_id: str,
    session: AsyncSession = Depends(get_db),
) -> CorridorConflictsResponse:
    # Load corridor + its works
    corridor = await get_corridor_with_risk(session, corridor_id, None, None)
    if not corridor:
        raise HTTPException(status_code=404, detail=f"Corridor '{corridor_id}' not found")

    # Load active D-TRO orders for the area (all synthetic/live — no spatial pre-filter needed
    # since the conflict detector does bbox intersection)
    dtro_rows = (
        await session.execute(
            select(DTROOrder).where(DTROOrder.data_source.in_(["synthetic", "integration", "production"]))
        )
    ).scalars().all()
    dtro_docs = [row.raw_json for row in dtro_rows]

    detector = ConflictDetector()
    results = detector.detect_corridor_conflicts(corridor.concurrentWorks, dtro_docs)

    conflicts = [
        TROConflict(
            permitReference=c.permit_reference,
            dtroId=c.dtro_id,
            troType=c.tro_type,
            conflictType=c.conflict_type,
            severity=c.severity,
            description=c.description,
            authority=c.authority,
            troReferenceNumber=c.tro_reference_number,
            troValidFrom=c.tro_valid_from,
            troValidTo=c.tro_valid_to,
        )
        for c in results
    ]

    return CorridorConflictsResponse(
        corridorId=corridor_id,
        conflictCount=len(conflicts),
        conflicts=conflicts,
        calculatedAt=datetime.now(timezone.utc).isoformat(),
    )
