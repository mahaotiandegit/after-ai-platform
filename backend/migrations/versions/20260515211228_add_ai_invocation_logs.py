"""add ai invocation logs

Revision ID: 20260515211228
Revises: a672504e657e
Create Date: 2026-05-15T21:12:28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515211228"
down_revision = 'a672504e657e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_invocation_logs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("scene", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index(
        "idx_ai_invocation_logs_scene_created_at",
        "ai_invocation_logs",
        ["scene", "created_at"],
    )

    op.create_index(
        "idx_ai_invocation_logs_success_created_at",
        "ai_invocation_logs",
        ["success", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_ai_invocation_logs_success_created_at", table_name="ai_invocation_logs")
    op.drop_index("idx_ai_invocation_logs_scene_created_at", table_name="ai_invocation_logs")
    op.drop_table("ai_invocation_logs")
