"""AI-007 — Add flagged and flag_reason to ai_audit_log (Layer 4 output audit)

Adds two columns to support the AI guardrails output-audit layer:
  - flagged: bool  — true when checkOutput() detects a policy violation
  - flag_reason: varchar(64)  — machine-readable reason code

Migration is additive and non-destructive. Existing rows default flagged=false.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_audit_log",
        sa.Column(
            "flagged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "ai_audit_log",
        sa.Column("flag_reason", sa.String(64), nullable=True),
    )
    op.create_index("ix_ai_audit_log_flagged", "ai_audit_log", ["flagged"])


def downgrade() -> None:
    op.drop_index("ix_ai_audit_log_flagged", table_name="ai_audit_log")
    op.drop_column("ai_audit_log", "flag_reason")
    op.drop_column("ai_audit_log", "flagged")
