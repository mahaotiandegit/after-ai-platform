"""add ai quality evaluations

Revision ID: 20260516000100
Revises: 20260515212417
Create Date: 2026-05-16 00:01:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260516000100"
down_revision = "20260515212417"
branch_labels = None
depends_on = None


def _ai_log_id_type():
    bind = op.get_bind()
    row = bind.execute(sa.text("""
        SELECT data_type, udt_name, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'ai_invocation_logs'
          AND column_name = 'id'
    """)).mappings().first()

    if not row:
        return sa.String(length=64)

    data_type = row["data_type"]
    udt_name = row["udt_name"]
    max_len = row["character_maximum_length"]

    if data_type == "uuid" or udt_name == "uuid":
        return postgresql.UUID(as_uuid=True)

    if data_type == "integer" or udt_name == "int4":
        return sa.Integer()

    if data_type == "bigint" or udt_name == "int8":
        return sa.BigInteger()

    if data_type == "text":
        return sa.Text()

    if data_type == "character varying":
        return sa.String(length=max_len or 64)

    return sa.String(length=64)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "ai_quality_evaluations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ai_log_id", _ai_log_id_type(), nullable=False),
        sa.Column("scene", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="warn"),
        sa.Column("issues", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("suggestions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("ai_log_id", name="uq_ai_quality_evaluations_ai_log_id"),
    )

    op.create_index("ix_ai_quality_evaluations_scene", "ai_quality_evaluations", ["scene"])
    op.create_index("ix_ai_quality_evaluations_status", "ai_quality_evaluations", ["status"])
    op.create_index("ix_ai_quality_evaluations_created_at", "ai_quality_evaluations", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_quality_evaluations_created_at", table_name="ai_quality_evaluations")
    op.drop_index("ix_ai_quality_evaluations_status", table_name="ai_quality_evaluations")
    op.drop_index("ix_ai_quality_evaluations_scene", table_name="ai_quality_evaluations")
    op.drop_table("ai_quality_evaluations")
