"""UN-008 — Synthetic NUAR underground asset generator.

Generates realistic synthetic utility assets for the 5 Birmingham corridors,
following the NUAR Harmonised Data Model V2-1-3 schema created in UN-001-prep.

Design goals (mirrors SM-008):
  - Deterministic: SEED=42 → same output every run
  - Idempotent: re-running returns the existing count, no duplicates
  - ADR-007 compliant: data_source='synthetic' — live geometry never stored
  - ADR-024 compliant: all geometry in EPSG:4326 (WGS84)

Output: 6 asset owners · 15 asset types · ~405 underground assets
"""
from __future__ import annotations

import random
import uuid
from datetime import date
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.nuar import NUARAsset, NUARAssetOwner, NUARAssetType

SEED = 42

# ── Corridor anchor points ─────────────────────────────────────────────────────
# Derived from: SELECT id, ST_AsText(ST_Centroid(geometry)) FROM corridors
# half_extent in degrees: NS corridors vary latitude, EW corridors vary longitude
_CORRIDORS: list[dict[str, Any]] = [
    {"id": "a38-bristol-road",       "center": (-1.905665, 52.473497), "axis": "NS", "half_extent": 0.009},
    {"id": "a38-corporation-street", "center": (-1.895750, 52.485750), "axis": "EW", "half_extent": 0.006},
    {"id": "broad-street",           "center": (-1.904000, 52.479500), "axis": "EW", "half_extent": 0.005},
    {"id": "bull-street",            "center": (-1.895978, 52.485063), "axis": "EW", "half_extent": 0.003},
    {"id": "new-street",             "center": (-1.896000, 52.479250), "axis": "EW", "half_extent": 0.004},
]

# ── Asset owner seed data (UK utility companies operating in Birmingham) ────────
_OWNER_SEEDS: list[dict[str, Any]] = [
    {"name": "Cadent Gas Ltd",                    "asset_type": "gas",      "contact_email": "streetworks@cadentgas.com"},
    {"name": "National Grid Electricity Dist.",   "asset_type": "electric", "contact_email": "streetworks@nationalgrid.com"},
    {"name": "Severn Trent Water",                "asset_type": "water",    "contact_email": "streetworks@severntrent.co.uk"},
    {"name": "BT Openreach",                      "asset_type": "telecoms", "contact_email": "streetworks@openreach.com"},
    {"name": "Virgin Media O2",                   "asset_type": "telecoms", "contact_email": "streetworks@virginmedia.com"},
    {"name": "Severn Trent Drainage",             "asset_type": "other",    "contact_email": "drainage@severntrent.co.uk"},
]

# ── Asset type seed data — keyed by owner name ─────────────────────────────────
_TYPE_SEEDS: dict[str, list[dict[str, str]]] = {
    "Cadent Gas Ltd": [
        {"type_code": "GAS_DIST_MAIN_HP", "description": "High-pressure gas distribution main"},
        {"type_code": "GAS_DIST_MAIN_MP", "description": "Medium-pressure gas distribution main"},
        {"type_code": "GAS_SERVICE_PIPE", "description": "Gas service pipe (property connection)"},
    ],
    "National Grid Electricity Dist.": [
        {"type_code": "ELEC_HV_CABLE",  "description": "High-voltage underground cable (11kV+)"},
        {"type_code": "ELEC_LV_CABLE",  "description": "Low-voltage distribution cable (400V)"},
        {"type_code": "ELEC_SERVICE",   "description": "Electricity service cable (230V)"},
    ],
    "Severn Trent Water": [
        {"type_code": "WATER_TRUNK_MAIN", "description": "Trunk water main (> 300 mm diameter)"},
        {"type_code": "WATER_DIST_MAIN",  "description": "Distribution water main (≤ 300 mm diameter)"},
        {"type_code": "WATER_SERVICE",    "description": "Water service pipe (property connection)"},
    ],
    "BT Openreach": [
        {"type_code": "TELE_DUCT_SPINE", "description": "Spine telecoms duct (multi-way)"},
        {"type_code": "TELE_DUCT_DIST",  "description": "Distribution telecoms duct"},
    ],
    "Virgin Media O2": [
        {"type_code": "CABLE_COAX_TRUNK",  "description": "Coaxial trunk cable"},
        {"type_code": "CABLE_FIBRE_DIST",  "description": "Fibre-optic distribution cable"},
    ],
    "Severn Trent Drainage": [
        {"type_code": "DRAIN_SEWER_FOUL",  "description": "Foul water sewer"},
        {"type_code": "DRAIN_SEWER_STORM", "description": "Stormwater surface drain"},
    ],
}

# ── Physical attributes per type code ─────────────────────────────────────────
# depth_metres range, pressure_tier, voltage_level
_ATTRS: dict[str, dict[str, Any]] = {
    "GAS_DIST_MAIN_HP":  {"depth": (0.9, 1.4), "pressure": "High",   "voltage": None},
    "GAS_DIST_MAIN_MP":  {"depth": (0.7, 1.1), "pressure": "Medium", "voltage": None},
    "GAS_SERVICE_PIPE":  {"depth": (0.5, 0.8), "pressure": "Low",    "voltage": None},
    "ELEC_HV_CABLE":     {"depth": (0.9, 1.5), "pressure": None,     "voltage": "11kV"},
    "ELEC_LV_CABLE":     {"depth": (0.6, 0.9), "pressure": None,     "voltage": "400V"},
    "ELEC_SERVICE":      {"depth": (0.45, 0.7),"pressure": None,     "voltage": "230V"},
    "WATER_TRUNK_MAIN":  {"depth": (1.2, 2.0), "pressure": None,     "voltage": None},
    "WATER_DIST_MAIN":   {"depth": (0.9, 1.4), "pressure": None,     "voltage": None},
    "WATER_SERVICE":     {"depth": (0.6, 1.0), "pressure": None,     "voltage": None},
    "TELE_DUCT_SPINE":   {"depth": (0.5, 0.9), "pressure": None,     "voltage": None},
    "TELE_DUCT_DIST":    {"depth": (0.35, 0.6),"pressure": None,     "voltage": None},
    "CABLE_COAX_TRUNK":  {"depth": (0.45, 0.7),"pressure": None,     "voltage": None},
    "CABLE_FIBRE_DIST":  {"depth": (0.35, 0.6),"pressure": None,     "voltage": None},
    "DRAIN_SEWER_FOUL":  {"depth": (1.5, 4.0), "pressure": None,     "voltage": None},
    "DRAIN_SEWER_STORM": {"depth": (0.9, 2.5), "pressure": None,     "voltage": None},
}

# ── Asset density per corridor: (linestring_count, point_count) ───────────────
# ~80 assets per corridor × 5 corridors = ~405 total
_DENSITY: dict[str, tuple[int, int]] = {
    "GAS_DIST_MAIN_HP":  (1, 0),
    "GAS_DIST_MAIN_MP":  (2, 0),
    "GAS_SERVICE_PIPE":  (0, 20),
    "ELEC_HV_CABLE":     (1, 0),
    "ELEC_LV_CABLE":     (2, 0),
    "ELEC_SERVICE":      (0, 18),
    "WATER_TRUNK_MAIN":  (1, 0),
    "WATER_DIST_MAIN":   (1, 0),
    "WATER_SERVICE":     (0, 18),
    "TELE_DUCT_SPINE":   (1, 0),
    "TELE_DUCT_DIST":    (2, 0),
    "CABLE_COAX_TRUNK":  (1, 0),
    "CABLE_FIBRE_DIST":  (1, 0),
    "DRAIN_SEWER_FOUL":  (1, 4),
    "DRAIN_SEWER_STORM": (1, 4),
}

# Maximum lateral offset from corridor centreline (≈ 15m at latitude 52.5°)
# Keeps all assets within the 100 m PostGIS buffer used by the density scorer
_LATERAL_DEG = 0.00013


# ── Geometry helpers ───────────────────────────────────────────────────────────

def _rand_date(rng: random.Random) -> date:
    start = date(1975, 1, 1).toordinal()
    end = date(2022, 12, 31).toordinal()
    return date.fromordinal(rng.randint(start, end))


def _linestring_wkt(rng: random.Random, corridor: dict[str, Any]) -> str:
    """Generate a WGS84 LineString running roughly parallel to a corridor segment."""
    cx, cy = corridor["center"]
    half = corridor["half_extent"]
    axis = corridor["axis"]

    lng_off = rng.uniform(-_LATERAL_DEG, _LATERAL_DEG)
    lat_off = rng.uniform(-_LATERAL_DEG, _LATERAL_DEG)

    # Segment spans 20–70% of the corridor half-extent
    frac = rng.uniform(0.2, 0.7)
    start_frac = rng.uniform(-1.0 + frac, 0.0)

    if axis == "NS":
        x = cx + lng_off
        y0 = cy + start_frac * half
        y1 = y0 + frac * half
        pts: list[tuple[float, float]] = [(x, y0), (x, y1)]
        if rng.random() > 0.45:
            ym = (y0 + y1) / 2 + rng.gauss(0, half * 0.015)
            pts = [(x, y0), (x + rng.gauss(0, 0.00003), ym), (x, y1)]
    else:
        y = cy + lat_off
        x0 = cx + start_frac * half
        x1 = x0 + frac * half
        pts = [(x0, y), (x1, y)]
        if rng.random() > 0.45:
            xm = (x0 + x1) / 2 + rng.gauss(0, half * 0.015)
            pts = [(x0, y), (xm, y + rng.gauss(0, 0.00003)), (x1, y)]

    coords = ", ".join(f"{p[0]:.7f} {p[1]:.7f}" for p in pts)
    return f"LINESTRING({coords})"


def _point_wkt(rng: random.Random, corridor: dict[str, Any]) -> str:
    """Generate a WGS84 Point near a corridor (service connection location)."""
    cx, cy = corridor["center"]
    half = corridor["half_extent"]
    axis = corridor["axis"]

    if axis == "NS":
        x = cx + rng.uniform(-_LATERAL_DEG, _LATERAL_DEG)
        y = cy + rng.uniform(-half, half)
    else:
        x = cx + rng.uniform(-half, half)
        y = cy + rng.uniform(-_LATERAL_DEG, _LATERAL_DEG)

    return f"POINT({x:.7f} {y:.7f})"


# ── Main generator ─────────────────────────────────────────────────────────────

async def generate_nuar_assets(session: AsyncSession) -> dict[str, Any]:
    """UN-008: Seed synthetic NUAR asset owners, types, and underground assets.

    Idempotent — returns immediately if synthetic assets already exist.
    Returns a summary dict with counts for logging / API response.
    """
    existing_count = await session.scalar(
        select(func.count()).select_from(NUARAsset)
        .where(NUARAsset.data_source == "synthetic")
    )
    if existing_count and existing_count > 0:
        return {"status": "already_seeded", "asset_count": int(existing_count)}

    rng = random.Random(SEED)

    # 1. Asset owners
    owner_id_map: dict[str, uuid.UUID] = {}
    for seed in _OWNER_SEEDS:
        owner = NUARAssetOwner(
            id=uuid.uuid4(),
            name=seed["name"],
            asset_type=seed["asset_type"],
            contact_email=seed["contact_email"],
        )
        session.add(owner)
        owner_id_map[seed["name"]] = owner.id

    await session.flush()

    # 2. Asset types
    type_id_map: dict[str, uuid.UUID] = {}   # type_code → NUARAssetType.id
    type_owner_map: dict[str, uuid.UUID] = {}  # type_code → NUARAssetOwner.id
    for owner_name, types in _TYPE_SEEDS.items():
        for t in types:
            row = NUARAssetType(
                id=uuid.uuid4(),
                owner_id=owner_id_map[owner_name],
                type_code=t["type_code"],
                description=t["description"],
            )
            session.add(row)
            type_id_map[t["type_code"]] = row.id
            type_owner_map[t["type_code"]] = owner_id_map[owner_name]

    await session.flush()

    # 3. Underground assets — one pass per corridor × type code
    asset_count = 0
    for corridor in _CORRIDORS:
        abbrev = corridor["id"].replace("-", "")[:8].upper()
        seq = 0

        for type_code, (ls_n, pt_n) in _DENSITY.items():
            attrs = _ATTRS[type_code]
            type_id = type_id_map[type_code]
            owner_id = type_owner_map[type_code]

            for _ in range(ls_n):
                seq += 1
                session.add(NUARAsset(
                    id=uuid.uuid4(),
                    external_asset_id=f"SYN-{type_code[:8]}-{abbrev}-{seq:04d}",
                    owner_id=owner_id,
                    asset_type_id=type_id,
                    geometry=WKTElement(_linestring_wkt(rng, corridor), srid=4326),
                    depth_metres=round(rng.uniform(*attrs["depth"]), 2),
                    pressure_tier=attrs["pressure"],
                    voltage_level=attrs["voltage"],
                    installation_date=_rand_date(rng),
                    data_source="synthetic",
                ))
                asset_count += 1

            for _ in range(pt_n):
                seq += 1
                session.add(NUARAsset(
                    id=uuid.uuid4(),
                    external_asset_id=f"SYN-{type_code[:8]}-{abbrev}-{seq:04d}",
                    owner_id=owner_id,
                    asset_type_id=type_id,
                    geometry=WKTElement(_point_wkt(rng, corridor), srid=4326),
                    depth_metres=round(rng.uniform(*attrs["depth"]), 2),
                    pressure_tier=attrs["pressure"],
                    voltage_level=attrs["voltage"],
                    installation_date=_rand_date(rng),
                    data_source="synthetic",
                ))
                asset_count += 1

    await session.commit()
    return {
        "status": "seeded",
        "owner_count": len(_OWNER_SEEDS),
        "type_count": sum(len(v) for v in _TYPE_SEEDS.values()),
        "asset_count": asset_count,
    }


def expected_total_asset_count() -> int:
    """Return the deterministic expected asset count (used in tests)."""
    per_corridor = sum(ls + pt for ls, pt in _DENSITY.values())
    return per_corridor * len(_CORRIDORS)
