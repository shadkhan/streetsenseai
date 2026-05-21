"""DT-008 — Synthetic D-TRO Traffic Regulation Order generator.

Generates realistic synthetic D-TRO records conforming to the v4.0.0 JSON schema
published at: github.com/department-for-transport-public/D-TRO

Design goals (mirrors SM-008 and UN-008):
  - Deterministic: SEED=42 → same output every run
  - Idempotent: re-running returns existing count, no duplicates
  - Schema-conformant: v4.0.0 field names and types throughout
  - ADR-024 compliant: all geometry in EPSG:4326 (WGS84)

Output: 500 permanent TROs + 200 TTROs across 41 authorities
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.dtro import DTROOrder, DTROProvision

SEED = 42

_REFS_DIR = Path(__file__).parent / "refs"

# ── Authority data ─────────────────────────────────────────────────────────────

def _load_authorities() -> list[dict[str, Any]]:
    with (_REFS_DIR / "authorities.json").open() as f:
        return json.load(f)  # type: ignore[no-any-return]


# ── TRO type definitions ───────────────────────────────────────────────────────

_TRO_TYPE_WEIGHTS: list[tuple[str, float]] = [
    ("speedLimit",          0.35),
    ("parkingRestriction",  0.25),
    ("roadClosure",         0.10),
    ("busLane",             0.08),
    ("cycleLane",           0.07),
    ("weightRestriction",   0.06),
    ("oneWay",              0.04),
    ("turningProhibition",  0.03),
    ("pedestrianZone",      0.02),
]

_SPEED_VALUES = [20, 30, 40, 50, 60, 70]
_SPEED_WEIGHTS = [0.18, 0.45, 0.15, 0.10, 0.07, 0.05]

_PARKING_RESTRICTION_TYPES = [
    "noWaiting",
    "loadingBay",
    "residentPermit",
    "payAndDisplay",
    "disabledBay",
    "taxiRank",
]

_WEIGHT_LIMITS = [3500, 7500, 10000, 18000, 26000, 40000]  # kg
_WEIGHT_LIMIT_LABELS = ["3.5t", "7.5t", "10t", "18t", "26t", "40t"]

_VEHICLE_TYPES = ["motorVehicle", "goodsVehicle", "bus", "motorcycle", "pedal_cycle"]

_DESCRIPTIONS: dict[str, list[str]] = {
    "speedLimit": [
        "20 mph speed limit",
        "30 mph speed limit",
        "40 mph speed limit",
        "Variable speed limit scheme",
        "School zone 20 mph limit",
    ],
    "parkingRestriction": [
        "Prohibition of waiting — at any time",
        "Loading bay restriction",
        "Residents' parking zone",
        "Pay and display parking zone",
        "Disabled parking bay",
    ],
    "roadClosure": [
        "Road closure — maintenance works",
        "Emergency road closure",
        "Temporary road closure — event",
        "TTRO road closure — utility works",
    ],
    "busLane": [
        "Bus and cycle lane — peak hours",
        "24-hour bus lane",
        "Bus lane — Mon-Sat 7am-7pm",
    ],
    "cycleLane": [
        "Mandatory cycle lane",
        "Advisory cycle lane",
        "Protected cycle lane",
    ],
    "weightRestriction": [
        "Weight limit — bridge",
        "Gross weight restriction",
        "Axle weight restriction — historic bridge",
    ],
    "oneWay": [
        "One-way traffic order",
        "One-way system — town centre",
    ],
    "turningProhibition": [
        "No right turn",
        "No left turn",
        "No U-turn",
        "Banned turning movement",
    ],
    "pedestrianZone": [
        "Pedestrian zone — at all times",
        "Pedestrian zone — retail hours",
        "Shared space — pedestrian priority",
    ],
}


# ── Geometry helpers ───────────────────────────────────────────────────────────

def _linestring_wkt(
    rng: random.Random,
    cx: float,
    cy: float,
    radius: float,
    length_deg: float,
) -> str:
    """Generate a WGS84 LineString of given approximate length near (cx, cy)."""
    bearing = rng.uniform(0, 360)
    import math
    rad = math.radians(bearing)
    # Start point offset from centre
    dx = rng.uniform(-radius * 0.5, radius * 0.5)
    dy = rng.uniform(-radius * 0.5, radius * 0.5)
    x0 = cx + dx
    y0 = cy + dy
    # End point in the bearing direction
    x1 = x0 + length_deg * math.sin(rad)
    y1 = y0 + length_deg * math.cos(rad)
    # Add 1-2 intermediate vertices for realism
    n_mid = rng.choice([0, 1, 2])
    pts: list[tuple[float, float]] = [(x0, y0)]
    for i in range(1, n_mid + 1):
        t = i / (n_mid + 1)
        pts.append((
            x0 + t * (x1 - x0) + rng.gauss(0, length_deg * 0.05),
            y0 + t * (y1 - y0) + rng.gauss(0, length_deg * 0.05),
        ))
    pts.append((x1, y1))
    coords = ", ".join(f"{p[0]:.6f} {p[1]:.6f}" for p in pts)
    return f"LINESTRING({coords})"


def _polygon_wkt(
    rng: random.Random,
    cx: float,
    cy: float,
    radius: float,
) -> str:
    """Generate a rough rectangular WGS84 Polygon (for zone-type TROs)."""
    import math
    half_w = rng.uniform(0.001, 0.005)
    half_h = rng.uniform(0.001, 0.005)
    angle = math.radians(rng.uniform(0, 45))
    ca, sa = math.cos(angle), math.sin(angle)
    cx += rng.uniform(-radius * 0.3, radius * 0.3)
    cy += rng.uniform(-radius * 0.3, radius * 0.3)
    corners = [
        (-half_w, -half_h), (half_w, -half_h),
        (half_w, half_h), (-half_w, half_h), (-half_w, -half_h),
    ]
    pts = [(cx + ca * dx - sa * dy, cy + sa * dx + ca * dy) for dx, dy in corners]
    coords = ", ".join(f"{p[0]:.6f} {p[1]:.6f}" for p in pts)
    return f"POLYGON(({coords}))"


def _geometry_wkt(rng: random.Random, tro_type: str, cx: float, cy: float, radius: float) -> str:
    """Return appropriate geometry for a given TRO type."""
    zone_types = {"parkingRestriction", "pedestrianZone", "busLane", "cycleLane"}
    if tro_type in zone_types:
        return _polygon_wkt(rng, cx, cy, radius)
    # Road-linear types get a LineString
    length = rng.uniform(0.002, 0.015)   # ~200m – 1.5km in degrees at UK lat
    return _linestring_wkt(rng, cx, cy, radius, length)


# ── Document builders ──────────────────────────────────────────────────────────

def _build_restriction(rng: random.Random, tro_type: str) -> dict[str, Any]:
    if tro_type == "speedLimit":
        speed = rng.choices(_SPEED_VALUES, weights=_SPEED_WEIGHTS)[0]
        return {
            "speedInMph": speed,
            "vehicleCharacteristics": {"vehicleType": "motorVehicle"},
            "conditions": [],
            "exceptions": ["emergencyVehicles"],
        }
    if tro_type == "weightRestriction":
        idx = rng.randrange(len(_WEIGHT_LIMITS))
        return {
            "maxWeightKg": _WEIGHT_LIMITS[idx],
            "maxWeightLabel": _WEIGHT_LIMIT_LABELS[idx],
            "vehicleCharacteristics": {"vehicleType": "goodsVehicle"},
            "conditions": [],
            "exceptions": ["vehiclesServingPremises"],
        }
    if tro_type == "parkingRestriction":
        r_type = rng.choice(_PARKING_RESTRICTION_TYPES)
        hours = rng.choice(["atAnyTime", "7am-7pm", "8am-6pm", "9am-5pm"])
        return {
            "restrictionType": r_type,
            "hours": hours,
            "conditions": [],
            "exceptions": ["disabledBadgeHolders"],
        }
    if tro_type in {"busLane", "cycleLane"}:
        hours = rng.choice(["atAllTimes", "7am-10am-4pm-7pm", "7am-7pm"])
        permitted = ["bus", "taxi"] if tro_type == "busLane" else ["pedalCycle"]
        return {"permittedVehicles": permitted, "hours": hours, "conditions": []}
    if tro_type == "roadClosure":
        return {
            "reason": rng.choice(["maintenance", "emergency", "event", "utilityWorks"]),
            "alternativeRoute": f"Via {rng.choice(['A38', 'A45', 'A34', 'B4100'])}",
            "conditions": [],
        }
    return {"conditions": []}


def _build_document(
    rng: random.Random,
    tro_id: str,
    authority: dict[str, Any],
    tro_type: str,
    is_temporary: bool,
    valid_from: date,
    valid_to: date | None,
    seq: int,
) -> dict[str, Any]:
    description = rng.choice(_DESCRIPTIONS[tro_type])
    ref_number = (
        f"TTRO/{authority['regionCode']}/{valid_from.year}/{seq:04d}"
        if is_temporary
        else f"TRO/{authority['regionCode']}/{valid_from.year}/{seq:04d}"
    )
    cx, cy = authority["approxBboxCentre"]
    radius = authority["approxBboxRadius"]

    geom_wkt = _geometry_wkt(rng, tro_type, cx, cy, radius)

    restriction = _build_restriction(rng, tro_type)
    speed_mph: int | None = restriction.get("speedInMph")

    provision_id = str(uuid.UUID(int=rng.getrandbits(128)))
    doc: dict[str, Any] = {
        "id": tro_id,
        "schemaVersion": "4.0.0",
        "header": {
            "notice": "Traffic Regulation Order",
            "source": {
                "reference": ref_number,
                "publisher": authority["name"],
                "provenance": "synthetic",
                "timestamp": f"{valid_from.isoformat()}T00:00:00Z",
            },
        },
        "body": {
            "tro": {
                "referenceNumber": ref_number,
                "type": tro_type,
                "description": description,
                "authority": authority["name"],
                "isTemporary": is_temporary,
                "validFrom": valid_from.isoformat(),
                "validTo": valid_to.isoformat() if valid_to else None,
                "externalReference": f"SYN-{seq:06d}",
            },
            "provisions": [
                {
                    "id": provision_id,
                    "referenceNumber": f"{ref_number}-P001",
                    "type": tro_type,
                    "geometry": _wkt_to_geojson(geom_wkt),
                    "restriction": restriction,
                },
            ],
        },
    }
    return doc, geom_wkt, speed_mph, restriction.get("restrictionType")  # type: ignore[return-value]


def _wkt_to_geojson(wkt: str) -> dict[str, Any]:
    """Convert a simple WKT string to a GeoJSON geometry dict."""
    if wkt.startswith("LINESTRING("):
        coords_str = wkt[len("LINESTRING("):-1]
        coords = [[float(v) for v in pair.split()] for pair in coords_str.split(", ")]
        return {"type": "LineString", "coordinates": coords}
    if wkt.startswith("POLYGON(("):
        coords_str = wkt[len("POLYGON(("):-2]
        coords = [[float(v) for v in pair.split()] for pair in coords_str.split(", ")]
        return {"type": "Polygon", "coordinates": [coords]}
    return {"type": "Point", "coordinates": [0, 0]}


def _rand_date_past(rng: random.Random, years_back: int = 10) -> date:
    today = date(2026, 5, 20)
    start = (today - timedelta(days=365 * years_back)).toordinal()
    end = today.toordinal()
    return date.fromordinal(rng.randint(start, end))


def _rand_ttro_dates(rng: random.Random) -> tuple[date, date]:
    """Return start/end dates for a TTRO — duration 1 day to 6 months."""
    today = date(2026, 5, 20)
    # TTROs can be in the past or future (for demos)
    offset = rng.randint(-180, 180)
    start = today + timedelta(days=offset)
    duration = rng.randint(1, 180)
    end = start + timedelta(days=duration)
    return start, end


# ── Main generator ─────────────────────────────────────────────────────────────

_PERMANENT_COUNT = 500
_TEMPORARY_COUNT = 200


async def generate_dtro_orders(session: AsyncSession) -> dict[str, Any]:
    """DT-008: Seed synthetic D-TRO orders and provisions.

    Idempotent — returns immediately if synthetic orders already exist.
    """
    existing = await session.scalar(
        select(func.count()).select_from(DTROOrder)
        .where(DTROOrder.data_source == "synthetic")
    )
    if existing and existing > 0:
        provision_count = await session.scalar(
            select(func.count()).select_from(DTROProvision)
        )
        return {
            "status": "already_seeded",
            "orderCount": int(existing),
            "provisionCount": int(provision_count or 0),
            "authorities": [],
        }

    rng = random.Random(SEED)
    authorities = _load_authorities()
    # Use all 41 authorities
    tro_types = [t for t, _ in _TRO_TYPE_WEIGHTS]
    type_weights = [w for _, w in _TRO_TYPE_WEIGHTS]

    order_count = 0
    provision_count = 0
    authority_names: set[str] = set()
    seq = 0

    for is_temporary, total in [(False, _PERMANENT_COUNT), (True, _TEMPORARY_COUNT)]:
        for _ in range(total):
            seq += 1
            authority = rng.choice(authorities)
            tro_type = rng.choices(tro_types, weights=type_weights)[0]

            if is_temporary:
                valid_from, valid_to = _rand_ttro_dates(rng)
            else:
                valid_from = _rand_date_past(rng, years_back=15)
                valid_to = None

            tro_id = str(uuid.uuid4())
            doc, geom_wkt, speed_mph, restriction_type = _build_document(
                rng, tro_id, authority, tro_type, is_temporary, valid_from, valid_to, seq
            )

            order = DTROOrder(
                id=uuid.uuid4(),
                dtro_id=tro_id,
                schema_version="4.0.0",
                reference_number=doc["body"]["tro"]["referenceNumber"],
                tro_type=tro_type,
                description=doc["body"]["tro"]["description"],
                authority=authority["name"],
                is_temporary=is_temporary,
                valid_from=valid_from,
                valid_to=valid_to,
                data_source="synthetic",
                raw_json=doc,
            )
            session.add(order)
            await session.flush()

            provision = DTROProvision(
                id=uuid.uuid4(),
                order_id=order.id,
                provision_type=tro_type,
                geometry=WKTElement(geom_wkt, srid=4326),
                speed_mph=speed_mph,
                restriction_type=restriction_type,
                conditions=doc["body"]["provisions"][0]["restriction"],
            )
            session.add(provision)
            order_count += 1
            provision_count += 1
            authority_names.add(authority["name"])

    await session.commit()
    return {
        "status": "seeded",
        "orderCount": order_count,
        "provisionCount": provision_count,
        "authorities": sorted(authority_names),
    }


def expected_order_count() -> int:
    return _PERMANENT_COUNT + _TEMPORARY_COUNT


def expected_temporary_count() -> int:
    return _TEMPORARY_COUNT


def expected_permanent_count() -> int:
    return _PERMANENT_COUNT
