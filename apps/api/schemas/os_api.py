"""Pydantic schemas for OS Data Hub API responses (SM-003, SM-004).

OS NSG API: returns uppercase key names — models mirror that directly.
OS Features API (Open Roads): returns GeoJSON with camelCase property keys
  — models use alias_generator=to_camel so Python attributes are snake_case.
Both sets are only used inside their respective service modules.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class OSNSGStreetDescriptor(BaseModel):
    """OS NSG STREET_DESCRIPTOR record (uppercase keys from API)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    USRN: str | None = None
    STREET_DESCRIPTION: str | None = None
    LOCALITY_NAME: str | None = None
    TOWN_NAME: str | None = None
    ADMINISTRATIVE_AREA: str | None = None
    LANGUAGE: str | None = None


class OSNSGStreet(BaseModel):
    """OS NSG STREET record (uppercase keys from API)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    USRN: str | None = None
    RECORD_TYPE: int | None = None
    STATE: int | None = None
    SURFACE: int | None = None
    CLASSIFICATION: str | None = None  # A, B, C, U, etc.
    START_X: float | None = None  # easting BNG EPSG:27700
    START_Y: float | None = None  # northing BNG EPSG:27700
    END_X: float | None = None
    END_Y: float | None = None


class OSNSGResult(BaseModel):
    """Single result object in the OS NSG response."""

    model_config = ConfigDict(extra="ignore")

    STREET_DESCRIPTOR: OSNSGStreetDescriptor | None = None
    STREET: OSNSGStreet | None = None


class OSNSGResponse(BaseModel):
    """Top-level OS NSG API response envelope."""

    model_config = ConfigDict(extra="ignore")

    results: list[OSNSGResult] = []


# ── OS Open Roads (SM-004) — OGC Features API GeoJSON response ─────────────────


class OSOpenRoadsProperties(BaseModel):
    """Properties on a single OS Open Roads RoadLink GeoJSON feature.

    OS Features API returns camelCase keys; alias_generator maps them to
    snake_case Python attributes.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True, alias_generator=to_camel)

    identifier: str | None = None
    road_classification: str | None = None   # "A Road", "B Road", "Motorway", "Unclassified"
    road_function: str | None = None         # "A Road", "Local Road", "Motorway" …
    name1: str | None = None                 # road name/number, e.g. "A38", "B4140"
    form_of_way: str | None = None           # "Single Carriageway", "Dual Carriageway" …
    length: float | None = None              # metres


class OSOpenRoadsFeature(BaseModel):
    """A single GeoJSON Feature from the OS Open Roads collection."""

    model_config = ConfigDict(extra="ignore")

    type: str = "Feature"
    properties: OSOpenRoadsProperties | None = None


class OSOpenRoadsCollection(BaseModel):
    """GeoJSON FeatureCollection returned by the OS Features API."""

    model_config = ConfigDict(extra="ignore")

    type: str = "FeatureCollection"
    features: list[OSOpenRoadsFeature] = []
    number_returned: int = 0
