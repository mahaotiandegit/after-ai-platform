"""add document index tasks

Revision ID: 20260519090000
Revises: 479ee826d3b5
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260519090000"
down_revision = "479ee826d3b5"
branch_labels = None
depends_on = None

def upgrade()->None:
    op.create_table(
        "document_index_tasks",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True,nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id",ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_type", sa.String(length=64), nullable=False, server_default="index_document"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "result_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index(
        "ix_document_index_tasks_document_id",
        "document_index_tasks",
        ["document_id"],
    )

    op.create_index(
        "ix_document_index_tasks_status_created_at",
        "document_index_tasks",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_index_tasks_status_created_at", table_name="document_index_tasks")
    op.drop_index("ix_document_index_tasks_document_id", table_name="document_index_tasks")
    op.drop_table("document_index_tasks")