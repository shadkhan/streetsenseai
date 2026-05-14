"""AI-007 — ai_audit_log table for AI interaction audit trail

Creates the ai_audit_log table that stores every copilot response and
permit summary lookup for accountability and review.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_audit_log",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("interaction_type", sa.String(32), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_audit_log_created_at", "ai_audit_log", ["created_at"])
    op.create_index("ix_ai_audit_log_type", "ai_audit_log", ["interaction_type"])


def downgrade() -> None:
    op.drop_index("ix_ai_audit_log_type", table_name="ai_audit_log")
    op.drop_index("ix_ai_audit_log_created_at", table_name="ai_audit_log")
    op.drop_table("ai_audit_log")
