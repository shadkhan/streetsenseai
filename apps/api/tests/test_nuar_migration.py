"""Tests for UN-001-prep: NUAR Harmonised Data Model schema migration.

Strategy: inspect the migration source file and ORM/Pydantic definitions
directly — no live database required, consistent with all other tests in
this project.

ADR references verified:
  ADR-023 — four-track NUAR strategy; Track 1 = schema conformance
  ADR-024 — EPSG:4326 throughout (not canonical EPSG:27700)
  ADR-007 — nuar_strike_risks is the only persisted NUAR output; no geometry
"""
from __future__ import annotations

import importlib
import inspect
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

# ── Migration source ───────────────────────────────────────────────────────────

_MIGRATION_PATH = (
    Path(__file__).parent.parent
    / "alembic" / "versions" / "0003_nuar_schema.py"
)
_MIGRATION_SRC = _MIGRATION_PATH.read_text(encoding="utf-8")


# ── test_nuar_tables_exist ─────────────────────────────────────────────────────

def test_nuar_tables_exist() -> None:
    """Migration must create all four NUAR tables."""
    expected_tables = [
        "nuar_asset_owners",
        "nuar_asset_types",
        "nuar_underground_assets",
        "nuar_strike_risks",
    ]
    for table in expected_tables:
        assert f'"{table}"' in _MIGRATION_SRC or f"'{table}'" in _MIGRATION_SRC, (
            f"Migration does not create table '{table}'"
        )


# ── test_nuar_geometry_srid ────────────────────────────────────────────────────

def test_nuar_geometry_srid() -> None:
    """Geometry column must use SRID 4326 (WGS84) — NOT 27700 (BNG). ADR-024."""
    assert "srid=4326" in _MIGRATION_SRC, "Expected srid=4326 in migration"
    # "27700" may appear in docstrings/comments explaining the ADR-024 divergence.
    # What must NOT appear is srid=27700 — that would mean a column was created wrong.
    assert "srid=27700" not in _MIGRATION_SRC, (
        "srid=27700 found in migration — geometry columns must use EPSG:4326 (ADR-024)"
    )


# ── test_transform_function_exists ────────────────────────────────────────────

def test_transform_function_exists() -> None:
    """Migration must create the transform_bng_to_wgs84 PostGIS function (ADR-024)."""
    assert "transform_bng_to_wgs84" in _MIGRATION_SRC, (
        "Migration must define the transform_bng_to_wgs84() function"
    )
    assert "ST_Transform" in _MIGRATION_SRC, (
        "transform_bng_to_wgs84 must use ST_Transform internally"
    )
    assert "CREATE OR REPLACE FUNCTION" in _MIGRATION_SRC


# ── test_nuar_asset_model ──────────────────────────────────────────────────────

def test_nuar_asset_model() -> None:
    """SQLAlchemy NUARAsset model instantiates correctly with required attributes."""
    from models.nuar import NUARAsset, NUARAssetOwner, NUARAssetType, NUARStrikeRisk

    owner = NUARAssetOwner(
        id=uuid.uuid4(),
        name="Cadent Gas",
        asset_type="gas",
        contact_email="data@cadent.co.uk",
    )
    assert owner.name == "Cadent Gas"
    assert owner.asset_type == "gas"
    assert owner.contact_email == "data@cadent.co.uk"

    asset_type = NUARAssetType(
        id=uuid.uuid4(),
        owner_id=owner.id,
        type_code="GAS_MAIN",
        description="Gas distribution main",
    )
    assert asset_type.type_code == "GAS_MAIN"

    asset_id = uuid.uuid4()
    asset = NUARAsset(
        id=asset_id,
        external_asset_id="NUAR-GAS-00001",
        owner_id=owner.id,
        asset_type_id=asset_type.id,
        geometry="SRID=4326;POINT(-1.9 52.5)",  # WKT placeholder
        depth_metres=1.2,
        pressure_tier="Medium",
        data_source="synthetic",
    )
    assert asset.external_asset_id == "NUAR-GAS-00001"
    assert asset.depth_metres == 1.2
    assert asset.data_source == "synthetic"

    strike = NUARStrikeRisk(
        id=uuid.uuid4(),
        permit_reference="WG7/2026/00001234",
        overall_risk="high",
        asset_count=3,
        assets_by_type={"gas": 2, "water": 1},
        highest_risk_asset={"type": "gas", "operator": "Cadent Gas", "risk": "high"},
    )
    assert strike.overall_risk == "high"
    assert strike.asset_count == 3


# ── test_strike_risk_schema ────────────────────────────────────────────────────

def test_strike_risk_schema() -> None:
    """Pydantic StrikeRiskRead validates correctly and matches CLAUDE.md §8 shape."""
    from schemas.nuar import StrikeRiskCreate, StrikeRiskRead, HighestRiskAsset

    payload = {
        "permit_reference": "WG7/2026/00001234",
        "overall_risk": "high",
        "asset_count": 3,
        "assets_by_type": {"gas": 2, "water": 1},
        "highest_risk_asset": {
            "type": "gas",
            "operator": "Cadent Gas",
            "risk": "high",
        },
    }
    create = StrikeRiskCreate.model_validate(payload)
    assert create.permit_reference == "WG7/2026/00001234"
    assert create.overall_risk == "high"
    assert create.asset_count == 3
    assert create.assets_by_type == {"gas": 2, "water": 1}
    assert create.highest_risk_asset is not None
    assert create.highest_risk_asset.operator == "Cadent Gas"

    read_payload = {
        **payload,
        "id": str(uuid.uuid4()),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
    read = StrikeRiskRead.model_validate(read_payload)
    assert isinstance(read.id, uuid.UUID)
    assert isinstance(read.calculated_at, datetime)

    # Null highest_risk_asset is valid
    null_payload = {**payload, "highest_risk_asset": None}
    null_risk = StrikeRiskCreate.model_validate(null_payload)
    assert null_risk.highest_risk_asset is None

    # asset_count must be non-negative
    with pytest.raises(Exception):
        StrikeRiskCreate.model_validate({**payload, "asset_count": -1})


# ── test_nuar_indexes ──────────────────────────────────────────────────────────

def test_nuar_indexes() -> None:
    """Migration must create a GIST spatial index on the geometry column."""
    assert 'postgresql_using="gist"' in _MIGRATION_SRC, (
        "Expected a GIST spatial index on nuar_underground_assets.geometry"
    )
    assert "ix_nuar_underground_assets_geometry" in _MIGRATION_SRC

    # Verify downgrade cleans up the index
    assert 'op.drop_index("ix_nuar_underground_assets_geometry"' in _MIGRATION_SRC


# ── test_migration_chain ───────────────────────────────────────────────────────

def test_migration_chain() -> None:
    """Migration must chain correctly: revision=0003, down_revision=0002."""
    assert 'revision: str = "0003"' in _MIGRATION_SRC
    assert 'down_revision: Union[str, None] = "0002"' in _MIGRATION_SRC


# ── test_adr007_compliance ─────────────────────────────────────────────────────

def test_adr007_compliance() -> None:
    """nuar_strike_risks must contain no geometry column (ADR-007)."""
    from models.nuar import NUARStrikeRisk
    from geoalchemy2 import Geometry

    for col in NUARStrikeRisk.__table__.columns:
        assert not isinstance(col.type, Geometry), (
            f"nuar_strike_risks.{col.name} is a geometry column — "
            "ADR-007 forbids storing NUAR geometry. "
            "Only derived risk scores are persisted."
        )
