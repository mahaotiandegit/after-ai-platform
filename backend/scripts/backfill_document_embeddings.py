from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_DIR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND_DIR))

from app.services.embedding_service import (  # noqa: E402
    embed_text,
    embedding_dimension,
    embedding_model_name,
    to_pgvector_literal,
)

def database_url()->str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://after_ai:after_ai_password@localhost:5432/after_ai_platform",
    )

def parse_args():
    parser = argparse.ArgumentParser(description="Backfill embeddings for document_chunks")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()

def ensure_embedding_columns(conn) -> None:
    has_column = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'document_chunks'
                  AND column_name = 'embedding'
            )
            """
        )
    ).scalar()

    if not has_column:
        raise RuntimeError(
            "document_chunks.embedding 不存在，请先执行 alembic upgrade head"
        )


def fetch_rows(conn, limit: int, force: bool):
    if force:
        sql = """
            SELECT id, content
            FROM document_chunks
            WHERE content IS NOT NULL
              AND length(content) > 0
            ORDER BY id
            LIMIT :limit
        """
        return conn.execute(text(sql), {"limit": limit}).mappings().all()

    sql = """
        SELECT id, content
        FROM document_chunks
        WHERE content IS NOT NULL
          AND length(content) > 0
          AND embedding IS NULL
        ORDER BY id
        LIMIT :limit
    """
    return conn.execute(text(sql), {"limit": limit}).mappings().all()


def update_embedding(conn, chunk_id: str, content: str) -> None:
    dim = embedding_dimension()
    model = embedding_model_name()
    vector = embed_text(content, dim)
    vector_literal = to_pgvector_literal(vector)

    conn.execute(
        text(
            """
            UPDATE document_chunks
            SET
                embedding = CAST(:embedding AS vector),
                embedding_model = :embedding_model,
                embedding_dimension = :embedding_dimension,
                embedding_updated_at = now()
            WHERE id = :id
            """
        ),
        {
            "id": chunk_id,
            "embedding": vector_literal,
            "embedding_model": model,
            "embedding_dimension": dim,
        },
    )


def main() -> None:
    args = parse_args()

    engine = create_engine(database_url())

    total = 0

    with engine.begin() as conn:
        ensure_embedding_columns(conn)

        rows = fetch_rows(conn, args.limit, args.force)

        print(f"[INFO] selected chunks={len(rows)}")
        print(f"[INFO] embedding_model={embedding_model_name()}")
        print(f"[INFO] embedding_dimension={embedding_dimension()}")

        for row in rows:
            update_embedding(conn, str(row["id"]), row["content"])
            total += 1

            if total % args.batch_size == 0:
                print(f"[INFO] embedded={total}")

    print(f"[PASS] backfill document embeddings done, total={total}")


if __name__ == "__main__":
    main()