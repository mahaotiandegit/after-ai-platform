"""add analytics query logs

Revision ID: 479ee826d3b5
Revises: 3bb90eadf61d
Create Date: 2026-05-18
"""

from alembic import op


revision = "479ee826d3b5"
down_revision = "3bb90eadf61d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_query_logs (
            id UUID PRIMARY KEY,
            question TEXT NOT NULL,
            intent VARCHAR(100),
            generated_sql TEXT NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'success',
            blocked_reason TEXT,
            tables_used JSONB NOT NULL DEFAULT '[]'::jsonb,
            columns_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            row_count INTEGER NOT NULL DEFAULT 0,
            applied_limit INTEGER,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_analytics_query_logs_created_at
        ON analytics_query_logs (created_at DESC)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_analytics_query_logs_status
        ON analytics_query_logs (status)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_analytics_query_logs_intent
        ON analytics_query_logs (intent)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_analytics_query_logs_intent")
    op.execute("DROP INDEX IF EXISTS ix_analytics_query_logs_status")
    op.execute("DROP INDEX IF EXISTS ix_analytics_query_logs_created_at")
    op.execute("DROP TABLE IF EXISTS analytics_query_logs")