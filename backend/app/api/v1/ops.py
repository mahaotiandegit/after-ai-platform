from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.deps import get_db

router = APIRouter(prefix="/ops", tags=["ops"])


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def _rows(rows) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        result.append({k: _jsonable(v) for k, v in row.items()})
    return result


@router.get("/documents")
def list_documents(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.execute(text("SELECT COUNT(*) FROM documents")).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT
                d.id,
                d.title,
                d.file_name,
                d.file_type,
                d.status,
                d.storage_path,
                d.uploaded_by_id,
                d.created_at,
                d.updated_at,
                COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN document_chunks c ON c.document_id = d.id
            GROUP BY d.id
            ORDER BY d.created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()

    return {
        "total": int(total or 0),
        "items": _rows(rows),
    }

@router.get("/documents/{document_id}/chunks")
def get_document_chunks(
    document_id: str,
    db: Session = Depends(get_db),
):
    document = db.execute(
        text(
            """
            SELECT
                d.id,
                d.title,
                d.file_name,
                d.file_type,
                d.status,
                d.storage_path,
                d.uploaded_by_id,
                d.created_at,
                d.updated_at,
                COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN document_chunks c ON c.document_id = d.id
            WHERE d.id = :document_id
            GROUP BY d.id
            """
        ),
        {"document_id": document_id},
    ).mappings().first()

    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在。")

    chunks = db.execute(
        text(
            """
            SELECT
                c.id,
                c.document_id,
                c.chunk_index,
                c.page_no,
                c.token_count,
                c.metadata ->> 'policy_code' AS policy_code,
                c.metadata ->> 'section' AS section,
                c.metadata ->> 'parser' AS parser,
                c.content,
                c.created_at
            FROM document_chunks c
            WHERE c.document_id = :document_id
            ORDER BY c.chunk_index ASC
            """
        ),
        {"document_id": document_id},
    ).mappings().all()

    return {
        "document": _rows([document])[0],
        "total": len(chunks),
        "items": _rows(chunks),
    }
@router.get("/bad-cases")
def list_bad_cases(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.execute(text("SELECT COUNT(*) FROM bad_cases")).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT *
            FROM bad_cases
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()

    return {
        "total": int(total or 0),
        "items": _rows(rows),
    }


@router.get("/monitor")
def monitor_overview(db: Session = Depends(get_db)):
    table_counts = db.execute(
        text(
            """
            SELECT 'orders' AS name, COUNT(*) AS count FROM orders
            UNION ALL SELECT 'tickets', COUNT(*) FROM tickets
            UNION ALL SELECT 'refunds', COUNT(*) FROM refunds
            UNION ALL SELECT 'documents', COUNT(*) FROM documents
            UNION ALL SELECT 'document_chunks', COUNT(*) FROM document_chunks
            UNION ALL SELECT 'qa_logs', COUNT(*) FROM qa_logs
            UNION ALL SELECT 'feedbacks', COUNT(*) FROM feedbacks
            UNION ALL SELECT 'bad_cases', COUNT(*) FROM bad_cases
            UNION ALL SELECT 'ai_invocation_logs', COUNT(*) FROM ai_invocation_logs
            UNION ALL SELECT 'ai_quality_evaluations', COUNT(*) FROM ai_quality_evaluations
            ORDER BY name
            """
        )
    ).mappings().all()

    recent_qa = db.execute(
        text(
            """
            SELECT
                id,
                question,
                latency_ms,
                created_at
            FROM qa_logs
            ORDER BY created_at DESC
            LIMIT 10
            """
        )
    ).mappings().all()

    recent_ai = db.execute(
        text(
            """
            SELECT
                id,
                scene,
                provider,
                model,
                success,
                latency_ms,
                created_at
            FROM ai_invocation_logs
            ORDER BY created_at DESC
            LIMIT 10
            """
        )
    ).mappings().all()

    return {
        "status": "ok",
        "table_counts": _rows(table_counts),
        "recent_qa_logs": _rows(recent_qa),
        "recent_ai_invocations": _rows(recent_ai),
    }
