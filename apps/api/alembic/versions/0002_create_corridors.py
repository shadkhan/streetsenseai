"""Create corridors table with PostGIS LineString geometry

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-13
"""
from __future__ import annotations

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "corridors",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("road_classification", sa.String(), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="LINESTRING",
                srid=4326,
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("last_calculated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="synthetic"),
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
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_corridors_road_classification", "corridors", ["road_classification"])
    op.create_index("ix_corridors_risk_level", "corridors", ["risk_level"])

    op.create_index(
        "ix_corridors_geometry",
        "corridors",
        ["geometry"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_corridors_geometry", table_name="corridors")
    op.drop_index("ix_corridors_risk_level", table_name="corridors")
    op.drop_index("ix_corridors_road_classification", table_name="corridors")
    op.drop_table("corridors")
