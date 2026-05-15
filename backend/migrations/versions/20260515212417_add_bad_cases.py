"""add bad cases

Revision ID: 20260515212417
Revises: 20260515211228
Create Date: 2026-05-15T21:24:17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515212417"
down_revision = '20260515211228'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bad_cases",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("scene", sa.String(length=80), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("ai_output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correction", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index(
        "idx_bad_cases_status_created_at",
        "bad_cases",
        ["status", "created_at"],
    )

    op.create_index(
        "idx_bad_cases_scene_created_at",
        "bad_cases",
        ["scene", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_bad_cases_scene_created_at", table_name="bad_cases")
    op.drop_index("idx_bad_cases_status_created_at", table_name="bad_cases")
    op.drop_table("bad_cases")
