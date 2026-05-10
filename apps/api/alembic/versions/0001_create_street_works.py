"""Create street_works table with PostGIS geometry

Revision ID: 0001
Revises:
Create Date: 2026-05-10
"""
from __future__ import annotations

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "street_works",
        sa.Column("permit_reference", sa.String(), nullable=False),
        sa.Column("usrn", sa.String(), nullable=False),
        sa.Column("street_name", sa.String(), nullable=False, server_default=""),
        sa.Column("authority", sa.String(), nullable=False, server_default=""),
        sa.Column("promoter", sa.String(), nullable=False, server_default=""),
        sa.Column("promoter_licence_number", sa.String(), nullable=False, server_default=""),
        sa.Column("work_type", sa.String(), nullable=False, server_default=""),
        sa.Column("traffic_management_type", sa.String(), nullable=False, server_default=""),
        sa.Column("restriction_type", sa.String(), nullable=False, server_default=""),
        sa.Column("proposed_start_date", sa.Date(), nullable=False),
        sa.Column("proposed_end_date", sa.Date(), nullable=False),
        sa.Column("actual_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("risk_score", sa.String(), nullable=True),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="GEOMETRY",
                srid=4326,
                spatial_index=False,  # created explicitly below as GIST
            ),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("permit_reference"),
    )

    # Regular B-tree indexes
    op.create_index("ix_street_works_usrn", "street_works", ["usrn"])
    op.create_index("ix_street_works_status", "street_works", ["status"])
    op.create_index("ix_street_works_authority", "street_works", ["authority"])
    op.create_index(
        "ix_street_works_dates",
        "street_works",
        ["proposed_start_date", "proposed_end_date"],
    )

    # PostGIS GIST spatial index — required for ST_Intersects bbox queries
    op.create_index(
        "ix_street_works_geometry",
        "street_works",
        ["geometry"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_street_works_geometry", table_name="street_works")
    op.drop_index("ix_street_works_dates", table_name="street_works")
    op.drop_index("ix_street_works_authority", table_name="street_works")
    op.drop_index("ix_street_works_status", table_name="street_works")
    op.drop_index("ix_street_works_usrn", table_name="street_works")
    op.drop_table("street_works")
