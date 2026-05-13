"""CR-001 — Synthetic corridor geometry generator.

Generates realistic LineString geometries for 40 pre-defined UK road
corridors from corridors.json. Used as the fallback when the OS Open
Roads API is unavailable.

Same deterministic pattern as SM-008: same seed -> same output.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from numpy.random import Generator

from schemas.corridor import CorridorBase, RoadClassification
from schemas.domain import LineStringGeometry

_REFS_DIR = Path(__file__).parent / "refs"
_KM_PER_DEG_LAT = 110.574
_NUM_POINTS = 6  # intermediate vertices per corridor LineString


def _km_per_deg_lng(lat: float) -> float:
    return 111.32 * math.cos(math.radians(lat))


def _build_linestring(
    centre_lng: float,
    centre_lat: float,
    bearing_deg: float,
    length_km: float,
    rng: Generator,
    num_points: int = _NUM_POINTS,
) -> list[tuple[float, float]]:
    """Generate a corridor LineString from bearing/length parameters.

    Uses compass bearing (0=N, 90=E). Applies small perpendicular jitter
    to each intermediate vertex so the road is not perfectly straight.
    """
    bearing_rad = math.radians(bearing_deg)
    kdl = _km_per_deg_lng(centre_lat)

    half_lng = (length_km / 2) * math.sin(bearing_rad) / kdl
    half_lat = (length_km / 2) * math.cos(bearing_rad) / _KM_PER_DEG_LAT

    start_lng = centre_lng - half_lng
    start_lat = centre_lat - half_lat
    end_lng = centre_lng + half_lng
    end_lat = centre_lat + half_lat

    # Perpendicular direction (bearing + 90 degrees)
    perp_rad = bearing_rad + math.pi / 2
    jitter_scale = length_km * 0.008 / kdl  # 0.8% of length as max jitter

    coords: list[tuple[float, float]] = []
    for i in range(num_points):
        t = i / (num_points - 1)
        lng = start_lng + t * (end_lng - start_lng)
        lat = start_lat + t * (end_lat - start_lat)

        # No jitter on endpoints to keep corridor anchored
        if 0 < i < num_points - 1:
            jitter = float(rng.normal(0.0, jitter_scale))
            lng += jitter * math.cos(perp_rad)
            lat += jitter * math.sin(perp_rad)

        coords.append((round(lng, 6), round(lat, 6)))

    return coords


class SyntheticCorridorGenerator:
    """Generate CorridorBase objects from the pre-defined corridors.json reference data.

    Usage:
        gen = SyntheticCorridorGenerator(seed=42)
        corridors = gen.generate_all()

    The 40 UK corridors cover Birmingham, Manchester, London, Leeds, Sheffield,
    Bristol, Liverpool, Newcastle, Norwich, Southampton, Devon and Cornwall.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng: Generator = np.random.default_rng(seed)
        self._definitions: list[dict[str, Any]] = json.loads(
            (_REFS_DIR / "corridors.json").read_text(encoding="utf-8")
        )

    def generate_all(self) -> list[CorridorBase]:
        """Return one CorridorBase per entry in corridors.json."""
        return [self._build_corridor(defn) for defn in self._definitions]

    def generate_by_id(self, corridor_id: str) -> CorridorBase | None:
        """Return a single corridor by its slug ID, or None if not found."""
        for defn in self._definitions:
            if defn["id"] == corridor_id:
                return self._build_corridor(defn)
        return None

    def _build_corridor(self, defn: dict[str, Any]) -> CorridorBase:
        coords = _build_linestring(
            centre_lng=float(defn["centre_lng"]),
            centre_lat=float(defn["centre_lat"]),
            bearing_deg=float(defn["bearing_degrees"]),
            length_km=float(defn["length_km"]),
            rng=self._rng,
        )
        classification = str(defn["road_classification"])
        if classification not in ("A", "B", "C", "unclassified"):
            classification = "A"

        return CorridorBase(
            id=str(defn["id"]),
            name=str(defn["name"]),
            road_classification=classification,  # type: ignore[arg-type]
            geometry=LineStringGeometry(type="LineString", coordinates=coords),
            source="synthetic",
        )
