"""DT-001 — D-TRO v4.0.0 schema: dtro_orders + dtro_provisions tables (ADR-027)

Creates two tables for storing Traffic Regulation Orders (TROs) and Temporary
Traffic Regulation Orders (TTROs) from the D-TRO v4.0.0 schema.

Conforms to: github.com/department-for-transport-public/D-TRO
All geometry in EPSG:4326 (WGS84) per ADR-024.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dtro_orders",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dtro_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False, server_default="4.0.0"),
        sa.Column("reference_number", sa.Text(), nullable=False),
        sa.Column("tro_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("authority", sa.Text(), nullable=False),
        sa.Column("is_temporary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("data_source", sa.Text(), nullable=False),
        sa.Column("raw_json", sa.dialects.postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dtro_id"),
    )
    op.create_index("ix_dtro_orders_dtro_id", "dtro_orders", ["dtro_id"])
    op.create_index("ix_dtro_orders_authority", "dtro_orders", ["authority"])
    op.create_index("ix_dtro_orders_tro_type", "dtro_orders", ["tro_type"])
    op.create_index("ix_dtro_orders_data_source", "dtro_orders", ["data_source"])
    op.create_index("ix_dtro_orders_valid_from", "dtro_orders", ["valid_from"])

    op.create_table(
        "dtro_provisions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provision_type", sa.Text(), nullable=False),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=False),
        sa.Column("speed_mph", sa.Integer(), nullable=True),
        sa.Column("restriction_type", sa.Text(), nullable=True),
        sa.Column("conditions", sa.dialects.postgresql.JSON(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["order_id"], ["dtro_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dtro_provisions_geometry",
        "dtro_provisions",
        ["geometry"],
        postgresql_using="gist",
    )
    op.create_index("ix_dtro_provisions_order", "dtro_provisions", ["order_id"])
    op.create_index("ix_dtro_provisions_type", "dtro_provisions", ["provision_type"])


def downgrade() -> None:
    op.drop_index("ix_dtro_provisions_type", table_name="dtro_provisions")
    op.drop_index("ix_dtro_provisions_order", table_name="dtro_provisions")
    op.drop_index("ix_dtro_provisions_geometry", table_name="dtro_provisions")
    op.drop_table("dtro_provisions")

    op.drop_index("ix_dtro_orders_valid_from", table_name="dtro_orders")
    op.drop_index("ix_dtro_orders_data_source", table_name="dtro_orders")
    op.drop_index("ix_dtro_orders_tro_type", table_name="dtro_orders")
    op.drop_index("ix_dtro_orders_authority", table_name="dtro_orders")
    op.drop_index("ix_dtro_orders_dtro_id", table_name="dtro_orders")
    op.drop_table("dtro_orders")
