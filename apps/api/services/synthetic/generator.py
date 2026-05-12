"""SM-008 — Synthetic Street Manager data generator.

Produces realistic, schema-conformant StreetWork permit records for use as
test fixtures, demo data, and Phase 2 corridor risk scoring inputs.

Design decisions:
- numpy.random.default_rng(seed) for determinism (ADR-022)
- All sampling is weighted using reference data in refs/
- Geographic distribution mirrors real English authority work volumes
- Status distribution matches observed Street Manager data patterns
- Geometry is Gaussian-jittered around authority centres (70% Point, 30% LineString)

Usage:
    gen = SyntheticStreetManagerGenerator(seed=42)
    works = gen.generate(5000, date(2026, 1, 1), date(2026, 12, 31))
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from numpy.random import Generator

from schemas.domain import LineStringGeometry, PointGeometry
from schemas.works import StreetWorkBase, StreetWorkStatus

logger = logging.getLogger(__name__)

_REFS_DIR = Path(__file__).parent / "refs"

# Status distribution matching observed SM open data patterns
_STATUSES = [
    "granted",
    "completed",
    "in_progress",
    "submitted",
    "closed",
    "revoked",
    "refused",
    "permit_modification_request",
]
_STATUS_WEIGHTS = np.array([0.60, 0.20, 0.08, 0.05, 0.04, 0.02, 0.005, 0.005])
_STATUS_WEIGHTS /= _STATUS_WEIGHTS.sum()  # normalise to exactly 1.0

# UK bounding box — every generated coordinate must fall inside this
UK_BBOX = (-8.5, 49.5, 2.0, 60.5)  # (min_lng, min_lat, max_lng, max_lat)

# Corridor → authority name mapping for generate_corridor_cluster
_CORRIDOR_AUTHORITY: dict[str, str] = {
    "A38 Birmingham": "Birmingham City Council",
    "M42 Jn 3-4": "Birmingham City Council",
    "A1 Leeds North": "Leeds City Council",
    "A57 Manchester East": "Manchester City Council",
    "A13 London East": "Transport for London",
    "A316 Richmond": "Transport for London",
}

# Additional traffic management options (beyond work-type default)
_TRAFFIC_MGMT_OPTIONS = [
    "No traffic management",
    "Give and take",
    "Two-way signals",
    "Multi-way signals",
    "Stop and go boards",
    "Priority working",
    "Convoy working",
    "Lane closure",
    "Contra-flow",
    "Road closure",
    "Traffic free zone",
]
_RESTRICTION_OPTIONS = [
    "Lane closure",
    "Footway closure",
    "Carriageway restriction",
    "Road closure",
    "No restriction",
    "Multi-way signals",
]

# Street name syllables for synthetic street names
_STREET_PREFIXES = [
    "High", "Church", "Park", "Victoria", "King", "Queen", "Station", "Mill",
    "Grove", "Manor", "Castle", "Bridge", "Market", "New", "Old", "North",
    "South", "East", "West", "London", "Oxford", "Bath", "York",
]
_STREET_SUFFIXES = [
    "Street", "Road", "Lane", "Avenue", "Close", "Way", "Drive", "Place",
    "Terrace", "Crescent", "Gardens", "Row", "Hill", "Court", "Square",
]


class SyntheticStreetManagerGenerator:
    """Generate deterministic, schema-conformant synthetic Street Manager permits.

    Pass the same seed to produce byte-identical output across machines,
    as required by ADR-022 (synthetic data strategy).
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng: Generator = np.random.default_rng(seed)
        self._authorities: list[dict[str, Any]] = json.loads(
            (_REFS_DIR / "authorities.json").read_text()
        )
        self._promoters: list[dict[str, Any]] = json.loads(
            (_REFS_DIR / "promoters.json").read_text()
        )
        self._work_types: list[dict[str, Any]] = json.loads(
            (_REFS_DIR / "work-types.json").read_text()
        )
        # Pre-compute sampling probability arrays
        self._auth_weights = np.array(
            [a["relativeWorkVolumeWeight"] for a in self._authorities], dtype=float
        )
        self._auth_weights /= self._auth_weights.sum()

        self._wt_weights = np.array(
            [w["relativeFrequencyWeight"] for w in self._work_types], dtype=float
        )
        self._wt_weights /= self._wt_weights.sum()

        # Permit sequence counters: (licenceNumber, year) -> last_seq
        self._sequences: dict[tuple[str, int], int] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate(
        self,
        count: int,
        start_date: date,
        end_date: date,
    ) -> list[StreetWorkBase]:
        """Generate *count* permits whose proposed dates fall within the window."""
        if end_date <= start_date:
            raise ValueError("end_date must be after start_date")
        return [self._generate_one(start_date, end_date) for _ in range(count)]

    def generate_corridor_cluster(
        self,
        corridor_name: str,
        count: int,
        date_window: tuple[date, date],
    ) -> list[StreetWorkBase]:
        """Generate *count* concurrent permits centred on a named corridor.

        All permits have overlapping proposed-date windows that intersect
        *date_window*, creating the concurrent-works scenario needed for
        Phase 2 corridor risk scoring tests.
        """
        window_start, window_end = date_window
        if window_end <= window_start:
            raise ValueError("date_window end must be after start")

        # Resolve authority by corridor name; fall back to highest-volume authority
        auth_name = _CORRIDOR_AUTHORITY.get(corridor_name)
        if auth_name:
            auth_matches = [a for a in self._authorities if a["name"] == auth_name]
            auth = auth_matches[0] if auth_matches else self._authorities[0]
        else:
            auth = self._authorities[0]  # highest weight (TfL)

        works = []
        for _ in range(count):
            work = self._generate_one(window_start, window_end, forced_authority=auth)
            # Ensure the permit overlaps the date window:
            # proposed_start <= window_end AND proposed_end >= window_start
            works.append(work)
        return works

    def inject_edge_cases(
        self,
        works: list[StreetWorkBase],
        cases: list[str],
    ) -> list[StreetWorkBase]:
        """Inject deliberate edge cases into an existing list of works.

        Supported cases:
          "overrun"       — actualEndDate > proposedEndDate by 1–14 days
          "modified"      — status changed to permit_modification_request
          "cancelled"     — status changed to revoked
          "weekend_only"  — proposed dates shifted to start on a Saturday
          "school_term_peak" — dates shifted to September start
        """
        result = list(works)
        n = len(result)
        if n == 0:
            return result

        # Roughly inject edge cases into ~5% of the list per case type
        inject_n = max(1, n // 20)

        for case in cases:
            # Pick deterministic random indices for this case
            indices = self._rng.choice(n, size=min(inject_n, n), replace=False)

            if case == "overrun":
                result = self._inject_overrun(result, indices)
            elif case == "modified":
                result = self._inject_status(result, indices, "permit_modification_request")
            elif case == "cancelled":
                result = self._inject_status(result, indices, "revoked")
            elif case == "weekend_only":
                result = self._inject_weekend_only(result, indices)
            elif case == "school_term_peak":
                result = self._inject_school_term_peak(result, indices)
            else:
                logger.warning("Unknown edge case type '%s' — skipping", case)

        return result

    # ── Internal generation ────────────────────────────────────────────────────

    def _generate_one(
        self,
        start_date: date,
        end_date: date,
        forced_authority: dict[str, Any] | None = None,
    ) -> StreetWorkBase:
        rng = self._rng
        window_days = (end_date - start_date).days

        # Authority
        auth = forced_authority or self._sample_authority()

        # Work type
        wt = self._sample_work_type()

        # Promoter — biased towards types that match the work category
        promoter = self._sample_promoter(wt)

        # Dates — duration clamped so proposed_end fits within window
        min_days, max_days = wt["minDays"], wt["maxDays"]
        duration = int(rng.integers(min_days, max_days + 1))
        max_start_offset = max(1, window_days - duration)
        start_offset = int(rng.integers(0, max_start_offset))
        proposed_start = start_date + timedelta(days=start_offset)
        proposed_end = proposed_start + timedelta(days=duration)
        # Safety: clamp proposed_end to end_date; ensure at least 1 day gap
        if proposed_end > end_date:
            proposed_end = end_date
        if proposed_end <= proposed_start:
            proposed_end = proposed_start + timedelta(days=1)

        # Status
        status_str = str(rng.choice(_STATUSES, p=_STATUS_WEIGHTS))
        status = StreetWorkStatus(status_str)

        # Actual dates for completed / in_progress / closed
        actual_start: str | None = None
        actual_end: str | None = None
        if status in (
            StreetWorkStatus.completed,
            StreetWorkStatus.in_progress,
            StreetWorkStatus.closed,
        ):
            actual_start_date = proposed_start + timedelta(
                days=int(rng.integers(0, 2))
            )
            actual_start = actual_start_date.isoformat()
        if status in (StreetWorkStatus.completed, StreetWorkStatus.closed):
            overrun = int(rng.integers(0, 8))  # 0–7 day overrun (non-edge-case)
            actual_end_date = proposed_end + timedelta(days=overrun)
            actual_end = actual_end_date.isoformat()

        # Geometry
        geometry = self._generate_geometry(auth)

        # USRN — authority prefix + random 4-digit suffix
        usrn = self._generate_usrn(auth)

        # Street name
        street_name = self._generate_street_name()

        # Permit reference
        licence = promoter["licenceNumber"]
        year = proposed_start.year
        permit_ref = self._next_permit_ref(licence, year)

        # Traffic management & restriction (default from work type, occasionally varied)
        traffic_mgmt = wt["typicalTrafficManagement"]
        restriction = wt["typicalRestrictionType"]
        if rng.random() < 0.15:  # 15% chance of non-default traffic management
            traffic_mgmt = str(rng.choice(_TRAFFIC_MGMT_OPTIONS))
        if rng.random() < 0.15:
            restriction = str(rng.choice(_RESTRICTION_OPTIONS))

        return StreetWorkBase(
            permit_reference=permit_ref,
            usrn=usrn,
            street_name=street_name,
            authority=auth["name"],
            promoter=promoter["name"],
            promoter_licence_number=licence,
            work_type=wt["name"],
            traffic_management_type=traffic_mgmt,
            restriction_type=restriction,
            proposed_start_date=proposed_start.isoformat(),
            proposed_end_date=proposed_end.isoformat(),
            actual_start_date=actual_start,
            actual_end_date=actual_end,
            status=status,
            geometry=geometry,
        )

    # ── Sampling helpers ───────────────────────────────────────────────────────

    def _sample_authority(self) -> dict[str, Any]:
        idx = int(self._rng.choice(len(self._authorities), p=self._auth_weights))
        return self._authorities[idx]

    def _sample_work_type(self) -> dict[str, Any]:
        idx = int(self._rng.choice(len(self._work_types), p=self._wt_weights))
        return self._work_types[idx]

    def _sample_promoter(self, work_type: dict[str, Any]) -> dict[str, Any]:
        affinity: list[str] = work_type.get("promoterTypeAffinity", [])
        # Build weights: prefer affinity-matching promoters (3× boost)
        raw_weights = np.array(
            [
                p["relativeWorkVolumeWeight"] * (3.0 if p["type"] in affinity else 1.0)
                for p in self._promoters
            ],
            dtype=float,
        )
        raw_weights /= raw_weights.sum()
        idx = int(self._rng.choice(len(self._promoters), p=raw_weights))
        return self._promoters[idx]

    # ── Geometry ───────────────────────────────────────────────────────────────

    def _generate_geometry(
        self, auth: dict[str, Any]
    ) -> PointGeometry | LineStringGeometry:
        radius = float(auth.get("approxBboxRadius", 0.12))
        centre_lng, centre_lat = auth["approxBboxCentre"]
        use_linestring = self._rng.random() < 0.30  # 30% LineString, 70% Point

        if use_linestring:
            return self._generate_linestring(centre_lng, centre_lat, radius)
        return self._generate_point(centre_lng, centre_lat, radius)

    def _generate_point(
        self, centre_lng: float, centre_lat: float, radius: float
    ) -> PointGeometry:
        lng, lat = self._jitter(centre_lng, centre_lat, radius)
        return PointGeometry(type="Point", coordinates=(lng, lat))

    def _generate_linestring(
        self, centre_lng: float, centre_lat: float, radius: float
    ) -> LineStringGeometry:
        # 2–4 point linestring along a random bearing from centre
        n_points = int(self._rng.integers(2, 5))
        bearing_lng = float(self._rng.uniform(-0.001, 0.001))
        bearing_lat = float(self._rng.uniform(-0.001, 0.001))
        start_lng, start_lat = self._jitter(centre_lng, centre_lat, radius * 0.5)
        coords = []
        for i in range(n_points):
            step_lng = start_lng + bearing_lng * i
            step_lat = start_lat + bearing_lat * i
            step_lng = float(np.clip(step_lng, UK_BBOX[0], UK_BBOX[2]))
            step_lat = float(np.clip(step_lat, UK_BBOX[1], UK_BBOX[3]))
            coords.append((step_lng, step_lat))
        return LineStringGeometry(type="LineString", coordinates=coords)

    def _jitter(
        self, centre_lng: float, centre_lat: float, radius: float
    ) -> tuple[float, float]:
        sigma = radius * 0.4  # ~68% of points within 40% of radius
        lng = centre_lng + float(self._rng.normal(0.0, sigma))
        lat = centre_lat + float(self._rng.normal(0.0, sigma))
        lng = float(np.clip(lng, UK_BBOX[0], UK_BBOX[2]))
        lat = float(np.clip(lat, UK_BBOX[1], UK_BBOX[3]))
        return round(lng, 6), round(lat, 6)

    # ── USRN ───────────────────────────────────────────────────────────────────

    def _generate_usrn(self, auth: dict[str, Any]) -> str:
        prefix = str(auth.get("usrnPrefix", "9999"))[:4]
        suffix = int(self._rng.integers(1000, 9999))
        return f"{prefix}{suffix:04d}"

    # ── Permit reference ───────────────────────────────────────────────────────

    def _next_permit_ref(self, licence: str, year: int) -> str:
        key = (licence, year)
        self._sequences[key] = self._sequences.get(key, 0) + 1
        seq = self._sequences[key]
        return f"{licence}/{year}/{seq:05d}"

    # ── Street name ────────────────────────────────────────────────────────────

    def _generate_street_name(self) -> str:
        prefix = str(self._rng.choice(_STREET_PREFIXES))
        suffix = str(self._rng.choice(_STREET_SUFFIXES))
        return f"{prefix} {suffix}"

    # ── Edge case injectors ────────────────────────────────────────────────────

    def _inject_overrun(
        self,
        works: list[StreetWorkBase],
        indices: np.ndarray,
    ) -> list[StreetWorkBase]:
        result = list(works)
        for i in [int(j) for j in indices]:
            w = result[i]
            overrun_days = int(self._rng.integers(1, 15))
            actual_end = date.fromisoformat(w.proposed_end_date) + timedelta(
                days=overrun_days
            )
            actual_start = w.actual_start_date or w.proposed_start_date
            result[i] = w.model_copy(
                update={
                    "actual_start_date": actual_start,
                    "actual_end_date": actual_end.isoformat(),
                    "status": StreetWorkStatus.completed,
                }
            )
        return result

    def _inject_status(
        self,
        works: list[StreetWorkBase],
        indices: np.ndarray,
        new_status: str,
    ) -> list[StreetWorkBase]:
        result = list(works)
        for i in [int(j) for j in indices]:
            result[i] = result[i].model_copy(
                update={"status": StreetWorkStatus(new_status)}
            )
        return result

    def _inject_weekend_only(
        self,
        works: list[StreetWorkBase],
        indices: np.ndarray,
    ) -> list[StreetWorkBase]:
        result = list(works)
        for i in [int(j) for j in indices]:
            w = result[i]
            start = date.fromisoformat(w.proposed_start_date)
            # Advance to nearest Saturday (weekday 5)
            days_to_saturday = (5 - start.weekday()) % 7
            new_start = start + timedelta(days=days_to_saturday)
            new_end = new_start + timedelta(
                days=max(
                    1,
                    (date.fromisoformat(w.proposed_end_date) - start).days,
                )
            )
            result[i] = w.model_copy(
                update={
                    "proposed_start_date": new_start.isoformat(),
                    "proposed_end_date": new_end.isoformat(),
                }
            )
        return result

    def _inject_school_term_peak(
        self,
        works: list[StreetWorkBase],
        indices: np.ndarray,
    ) -> list[StreetWorkBase]:
        result = list(works)
        for i in [int(j) for j in indices]:
            w = result[i]
            original_year = date.fromisoformat(w.proposed_start_date).year
            # September start — peak school-term period
            new_start = date(original_year, 9, 1)
            duration = max(
                1,
                (
                    date.fromisoformat(w.proposed_end_date)
                    - date.fromisoformat(w.proposed_start_date)
                ).days,
            )
            new_end = new_start + timedelta(days=duration)
            result[i] = w.model_copy(
                update={
                    "proposed_start_date": new_start.isoformat(),
                    "proposed_end_date": new_end.isoformat(),
                }
            )
        return result
