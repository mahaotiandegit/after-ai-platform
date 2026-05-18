"""change document_chunks embedding dimension to 384

Revision ID: 20260517190000
Revises: 20260516000100
Create Date: 2026-05-17 19:00:00
"""

from alembic import op


revision = "20260517190000"
down_revision = "20260516000100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        ALTER TABLE document_chunks
        ALTER COLUMN embedding TYPE vector(384)
        USING NULL::vector(384)
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE document_chunks
        ALTER COLUMN embedding TYPE vector(1536)
        USING NULL::vector(1536)
    """)
