"""UN-001-prep — NUAR Harmonised Data Model schema (ADR-023, ADR-024)

Creates four tables conforming to the NUAR Harmonised Data Model V2-1-3
(github.com/national-underground-asset-register/nuar-datamodel) and the
PostGIS helper function required by ADR-024.

ADR-024 divergence: canonical NUAR schema uses EPSG:27700 (British National
Grid). Our columns use EPSG:4326 (WGS84) so geometry is consistent with the
rest of the application stack. The transform_bng_to_wgs84() function is the
single authorised transformation point when ingesting live NUAR data.

ADR-007: nuar_underground_assets.geometry is populated by the synthetic data
generator (Track 2, UN-008) for Phase 4 development. Live NUAR geometry is
queried on demand and cached in-memory for 1 hour maximum — it is NEVER
written to this table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-13
"""
from __future__ import annotations

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE_COMMENT = "NUAR Harmonised Data Model — StreetSense AI implementation (EPSG:4326)"


def upgrade() -> None:
    # ── transform_bng_to_wgs84 ─────────────────────────────────────────────────
    # ADR-024: the ONLY place BNG (EPSG:27700) → WGS84 (EPSG:4326) conversion
    # is permitted. All NUAR live data must pass through this function at the
    # service layer boundary before any storage or processing.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION transform_bng_to_wgs84(geom geometry)
        RETURNS geometry AS $$
          SELECT ST_Transform(geom, 4326)
        $$ LANGUAGE sql IMMUTABLE STRICT;
        """
    )

    # ── nuar_asset_owners ──────────────────────────────────────────────────────
    op.create_table(
        "nuar_asset_owners",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(f"COMMENT ON TABLE nuar_asset_owners IS '{_TABLE_COMMENT}'")

    # ── nuar_asset_types ───────────────────────────────────────────────────────
    op.create_table(
        "nuar_asset_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("type_code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["nuar_asset_owners.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(f"COMMENT ON TABLE nuar_asset_types IS '{_TABLE_COMMENT}'")

    # ── nuar_underground_assets ────────────────────────────────────────────────
    # ADR-007: geometry column is populated ONLY by synthetic data (data_source='synthetic')
    # or sandbox data (data_source='sandbox') during Phase 4 development.
    # Live NUAR geometry (data_source='live') is NEVER written here per ADR-007.
    op.create_table(
        "nuar_underground_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("external_asset_id", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("asset_type_id", sa.UUID(), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="GEOMETRY",
                srid=4326,
                spatial_index=False,  # created explicitly below as GIST
            ),
            nullable=False,
        ),
        sa.Column("depth_metres", sa.Float(), nullable=True),
        sa.Column("pressure_tier", sa.Text(), nullable=True),
        sa.Column("voltage_level", sa.Text(), nullable=True),
        sa.Column("installation_date", sa.Date(), nullable=True),
        sa.Column("last_verified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_source", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["nuar_asset_owners.id"]),
        sa.ForeignKeyConstraint(["asset_type_id"], ["nuar_asset_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(f"COMMENT ON TABLE nuar_underground_assets IS '{_TABLE_COMMENT}'")

    op.create_index(
        "ix_nuar_underground_assets_geometry",
        "nuar_underground_assets",
        ["geometry"],
        postgresql_using="gist",
    )
    op.create_index("ix_nuar_underground_assets_owner", "nuar_underground_assets", ["owner_id"])
    op.create_index("ix_nuar_underground_assets_data_source", "nuar_underground_assets", ["data_source"])

    # ── nuar_strike_risks ──────────────────────────────────────────────────────
    # Derived scores only — no asset geometry stored here (ADR-007 compliant).
    # Linked to street_works via permit_reference (text FK, no hard constraint
    # to allow strike risk records to outlive individual work records).
    op.create_table(
        "nuar_strike_risks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("permit_reference", sa.Text(), nullable=False),
        sa.Column("overall_risk", sa.Text(), nullable=False),
        sa.Column("asset_count", sa.Integer(), nullable=False),
        sa.Column("assets_by_type", sa.JSON(), nullable=False),
        sa.Column("highest_risk_asset", sa.JSON(), nullable=True),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(f"COMMENT ON TABLE nuar_strike_risks IS '{_TABLE_COMMENT}'")

    op.create_index("ix_nuar_strike_risks_permit", "nuar_strike_risks", ["permit_reference"])
    op.create_index("ix_nuar_strike_risks_overall_risk", "nuar_strike_risks", ["overall_risk"])


def downgrade() -> None:
    op.drop_index("ix_nuar_strike_risks_overall_risk", table_name="nuar_strike_risks")
    op.drop_index("ix_nuar_strike_risks_permit", table_name="nuar_strike_risks")
    op.drop_table("nuar_strike_risks")

    op.drop_index("ix_nuar_underground_assets_data_source", table_name="nuar_underground_assets")
    op.drop_index("ix_nuar_underground_assets_owner", table_name="nuar_underground_assets")
    op.drop_index("ix_nuar_underground_assets_geometry", table_name="nuar_underground_assets")
    op.drop_table("nuar_underground_assets")

    op.drop_table("nuar_asset_types")
    op.drop_table("nuar_asset_owners")

    op.execute("DROP FUNCTION IF EXISTS transform_bng_to_wgs84(geometry)")
