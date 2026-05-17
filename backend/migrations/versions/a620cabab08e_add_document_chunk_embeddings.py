"""add document chunk embeddings

Revision ID: a620cabab08e
Revises: 20260516000100
Create Date: 2026-05-17 20:06:32.130160

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a620cabab08e'
down_revision: Union[str, Sequence[str], None] = '20260516000100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS embedding vector(384)
        """
    )

    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100)
        """
    )

    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS embedding_dimension INTEGER
        """
    )

    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS embedding_updated_at TIMESTAMP
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ready
        ON document_chunks (embedding_model)
        WHERE embedding IS NOT NULL
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
            ON document_chunks
            USING hnsw (embedding vector_cosine_ops);
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'skip hnsw index: %', SQLERRM;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ready")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_updated_at")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_dimension")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_model")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
