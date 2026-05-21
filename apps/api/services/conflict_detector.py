"""DT-002 — Permit + TRO conflict detector.

Detects conflicts between active street works permits and D-TRO restrictions
on the same corridor. A conflict exists when:
  - Spatial: permit geometry intersects TRO provision geometry (ST_Intersects)
  - Temporal: permit date window overlaps TRO validity window

Conflict severity mapping:
  roadClosure       + in_progress/granted works  → critical
  weightRestriction + works                       → high
  busLane           + works                       → medium
  parkingRestriction + works                      → medium
  speedLimit        + works                       → low   (awareness only)
  others            + works                       → low
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from schemas.domain import RiskLevel, StreetWork


# ── Severity mapping ───────────────────────────────────────────────────────────

_SEVERITY_MAP: dict[str, RiskLevel] = {
    "roadClosure":         "critical",
    "weightRestriction":   "high",
    "busLane":             "medium",
    "cycleLane":           "medium",
    "parkingRestriction":  "medium",
    "oneWay":              "medium",
    "turningProhibition":  "low",
    "speedLimit":          "low",
    "pedestrianZone":      "low",
}


@dataclass
class ConflictResult:
    permit_reference: str
    dtro_id: str
    tro_type: str
    conflict_type: str      # "spatial_overlap" | "temporal_overlap" | "both"
    severity: RiskLevel
    description: str
    authority: str
    tro_reference_number: str
    tro_valid_from: str     # ISO date
    tro_valid_to: str | None


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None


def _dates_overlap(
    a_start: date | None,
    a_end: date | None,
    b_start: date | None,
    b_end: date | None,
) -> bool:
    """Return True if two date windows overlap. None end = open-ended."""
    if a_start is None or b_start is None:
        return False
    effective_a_end = a_end or date(9999, 12, 31)
    effective_b_end = b_end or date(9999, 12, 31)
    return a_start <= effective_b_end and effective_a_end >= b_start


def _plain_english_description(
    tro_type: str,
    permit: StreetWork,
    conflict_type: str,
    tro_ref: str,
) -> str:
    """Generate a concise plain-English conflict description without calling the LLM.

    The LLM (Claude Haiku) can be swapped in when an API key is available — for
    now a deterministic template provides the same information density.
    """
    action_map: dict[str, str] = {
        "roadClosure": "a road closure",
        "weightRestriction": "a weight restriction",
        "busLane": "a bus lane restriction",
        "cycleLane": "a cycle lane designation",
        "parkingRestriction": "a parking restriction",
        "speedLimit": "a speed limit zone",
        "oneWay": "a one-way traffic order",
        "turningProhibition": "a turning prohibition",
        "pedestrianZone": "a pedestrian zone",
    }
    tro_label = action_map.get(tro_type, f"a {tro_type} restriction")
    permit_ref = permit.permit_reference
    street = permit.street_name

    if conflict_type == "both":
        return (
            f"Permit {permit_ref} on {street} overlaps spatially and temporally "
            f"with {tro_label} ({tro_ref}). Review works programme to ensure compliance."
        )
    if conflict_type == "spatial_overlap":
        return (
            f"Permit {permit_ref} on {street} is located within {tro_label} ({tro_ref}). "
            f"Verify that works timing avoids the restriction window."
        )
    return (
        f"Permit {permit_ref} on {street} is active during {tro_label} ({tro_ref}). "
        f"Confirm spatial separation from the restriction boundary."
    )


class ConflictDetector:
    """Detects permit+TRO conflicts — spatial and temporal dimensions."""

    def detect_permit_tro_conflicts(
        self,
        permit: StreetWork,
        dtro_orders: list[dict],
    ) -> list[ConflictResult]:
        """Return all TRO conflicts for a single permit.

        dtro_orders: list of dicts from DTROOrder.raw_json (D-TRO v4.0.0 documents).
        Spatial intersection is approximated here using bounding-box overlap between
        the permit geometry and TRO provision geometry — the authoritative spatial
        check is done in the corridor endpoint via PostGIS ST_Intersects.
        """
        results: list[ConflictResult] = []

        permit_start = _parse_date(permit.proposed_start_date)
        permit_end = _parse_date(permit.proposed_end_date or permit.actual_end_date)

        for doc in dtro_orders:
            body = doc.get("body", {})
            tro_info = body.get("tro", {})
            tro_type = tro_info.get("type", "unknown")
            tro_ref = tro_info.get("referenceNumber", "")
            tro_id = doc.get("id", "")
            authority = tro_info.get("authority", "")
            tro_valid_from = _parse_date(tro_info.get("validFrom"))
            tro_valid_to = _parse_date(tro_info.get("validTo"))

            temporal_overlap = _dates_overlap(permit_start, permit_end, tro_valid_from, tro_valid_to)

            # Spatial check: compare permit lat/lng against TRO provision geometry bbox
            # (PostGIS ST_Intersects does the authoritative check in the corridor endpoint)
            spatial_overlap = _geometry_approx_intersects(permit, body.get("provisions", []))

            if not temporal_overlap and not spatial_overlap:
                continue

            conflict_type = (
                "both" if temporal_overlap and spatial_overlap
                else "temporal_overlap" if temporal_overlap
                else "spatial_overlap"
            )
            severity = _SEVERITY_MAP.get(tro_type, "low")
            description = _plain_english_description(tro_type, permit, conflict_type, tro_ref)

            results.append(ConflictResult(
                permit_reference=permit.permit_reference,
                dtro_id=tro_id,
                tro_type=tro_type,
                conflict_type=conflict_type,
                severity=severity,
                description=description,
                authority=authority,
                tro_reference_number=tro_ref,
                tro_valid_from=tro_info.get("validFrom", ""),
                tro_valid_to=tro_info.get("validTo"),
            ))

        return results

    def detect_corridor_conflicts(
        self,
        corridor_works: list[StreetWork],
        dtro_orders: list[dict],
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ConflictResult]:
        """Return all permit+TRO conflicts for a set of corridor works."""
        all_conflicts: list[ConflictResult] = []
        seen: set[str] = set()

        for permit in corridor_works:
            conflicts = self.detect_permit_tro_conflicts(permit, dtro_orders)
            for c in conflicts:
                key = f"{c.permit_reference}:{c.dtro_id}"
                if key not in seen:
                    seen.add(key)
                    all_conflicts.append(c)

        # Sort: critical first, then by permit reference
        _severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_conflicts.sort(key=lambda c: (_severity_order.get(c.severity, 9), c.permit_reference))
        return all_conflicts


def _geometry_approx_intersects(permit: StreetWork, provisions: list[dict]) -> bool:
    """Approximate spatial intersection using WGS84 bounding boxes.

    Returns True if the permit geometry centre is within any provision's
    bounding box (expanded by 0.005° ≈ 500m buffer). Errs on the side of
    false positives — the PostGIS query filters precisely later.
    """
    if not provisions:
        return False

    # Permit centre
    geom = permit.geometry
    if geom.type == "Point":
        plng, plat = geom.coordinates[0], geom.coordinates[1]
    else:
        coords = geom.coordinates
        plng = sum(c[0] for c in coords) / len(coords)
        plat = sum(c[1] for c in coords) / len(coords)

    buffer = 0.01   # ~1 km buffer

    for provision in provisions:
        geo = provision.get("geometry", {})
        geo_type = geo.get("type", "")
        coords_raw = geo.get("coordinates", [])

        if geo_type == "LineString":
            lngs = [c[0] for c in coords_raw]
            lats = [c[1] for c in coords_raw]
        elif geo_type == "Polygon":
            ring = coords_raw[0] if coords_raw else []
            lngs = [c[0] for c in ring]
            lats = [c[1] for c in ring]
        else:
            continue

        if not lngs or not lats:
            continue

        min_lng, max_lng = min(lngs) - buffer, max(lngs) + buffer
        min_lat, max_lat = min(lats) - buffer, max(lats) + buffer

        if min_lng <= plng <= max_lng and min_lat <= plat <= max_lat:
            return True

    return False
