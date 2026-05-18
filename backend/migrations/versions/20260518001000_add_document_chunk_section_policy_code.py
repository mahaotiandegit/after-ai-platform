"""add section and policy_code to document_chunks

Revision ID: 20260518001000
Revises: 20260516000100
Create Date: 2026-05-18 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260518001000"
down_revision = "20260516000100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS section VARCHAR(255)
        """
    )

    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS policy_code VARCHAR(100)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_section
        ON document_chunks (section)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_policy_code
        ON document_chunks (policy_code)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_policy_code")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_section")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS policy_code")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS section")