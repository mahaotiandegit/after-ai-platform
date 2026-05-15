from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.llm_gateway import generate_rag_answer


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeAskLLMRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeAskLLMResponse(BaseModel):
    question: str
    answer: str
    citations: list[dict[str, Any]]
    hits: list[dict[str, Any]]
    provider: str
    model: str
    used_llm: bool
    fallback_reason: str = ""
    qa_log_id: str | None = None


def _table_columns(db: Session, table_name: str) -> dict[str, str]:
    rows = db.execute(
        text(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).mappings().all()

    return {row["column_name"]: row["data_type"] for row in rows}


def _pick(columns: dict[str, str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def _safe_identifier(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQL identifier: {name}")
    return name


def _rewrite_query(question: str) -> list[str]:
    queries = [question]

    if "物流" in question and ("延迟" in question or "补偿" in question or "退款" in question):
        queries.append("物流延迟补偿")

    if "退款" in question:
        queries.append("退款 售后 规则")

    if "发票" in question:
        queries.append("发票 售后 规则")

    deduped: list[str] = []
    for item in queries:
        if item not in deduped:
            deduped.append(item)

    return deduped


def _search_chunks(db: Session, question: str, top_k: int) -> list[dict[str, Any]]:
    chunk_columns = _table_columns(db, "document_chunks")
    document_columns = _table_columns(db, "documents")

    if not chunk_columns:
        return []

    text_col = _pick(chunk_columns, ["content", "chunk_text", "text", "body"])
    if not text_col:
        return []

    chunk_id_col = _pick(chunk_columns, ["id", "chunk_id"])
    document_id_col = _pick(chunk_columns, ["document_id", "doc_id"])

    text_col = _safe_identifier(text_col)
    chunk_id_select = _safe_identifier(chunk_id_col) if chunk_id_col else "NULL"

    join_sql = ""
    title_select = "'未知文档' AS document_title"

    if document_id_col and document_columns and "id" in document_columns:
        document_id_col = _safe_identifier(document_id_col)
        title_col = _pick(document_columns, ["title", "name", "file_name", "filename"])
        if title_col:
            title_col = _safe_identifier(title_col)
            title_select = f"COALESCE(d.{title_col}::text, '未知文档') AS document_title"
        join_sql = f"LEFT JOIN documents d ON c.{document_id_col} = d.id"

    sql = f"""
    SELECT
        c.{chunk_id_select}::text AS chunk_id,
        c.{text_col}::text AS content,
        {title_select}
    FROM document_chunks c
    {join_sql}
    WHERE c.{text_col} ILIKE :query
    LIMIT :limit
    """

    hits: list[dict[str, Any]] = []

    for query in _rewrite_query(question):
        rows = db.execute(
            text(sql),
            {
                "query": f"%{query}%",
                "limit": top_k,
            },
        ).mappings().all()

        for row in rows:
            item = {
                "chunk_id": row.get("chunk_id"),
                "document_title": row.get("document_title") or "未知文档",
                "content": row.get("content") or "",
            }

            if item not in hits:
                hits.append(item)

            if len(hits) >= top_k:
                return hits

    return hits


def _build_citations(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []

    for index, hit in enumerate(hits, start=1):
        citations.append(
            {
                "index": index,
                "chunk_id": hit.get("chunk_id"),
                "document_title": hit.get("document_title") or "未知文档",
                "snippet": (hit.get("content") or "")[:160],
            }
        )

    return citations


def _try_insert_qa_log(
    db: Session,
    question: str,
    answer: str,
    citations: list[dict[str, Any]],
) -> str | None:
    columns = _table_columns(db, "qa_logs")

    if not columns:
        return None

    if "question" not in columns or "answer" not in columns:
        return None

    qa_log_id = str(uuid.uuid4())

    insert_columns: list[str] = []
    value_exprs: list[str] = []
    params: dict[str, Any] = {}

    if "id" in columns:
        insert_columns.append("id")
        value_exprs.append(":id")
        params["id"] = qa_log_id

    insert_columns.append("question")
    value_exprs.append(":question")
    params["question"] = question

    insert_columns.append("answer")
    value_exprs.append(":answer")
    params["answer"] = answer

    if "citations" in columns:
        insert_columns.append("citations")
        if columns["citations"] in {"json", "jsonb"}:
            value_exprs.append("CAST(:citations AS jsonb)")
        else:
            value_exprs.append(":citations")
        params["citations"] = json.dumps(citations, ensure_ascii=False)

    if "created_at" in columns:
        insert_columns.append("created_at")
        value_exprs.append("NOW()")

    sql = f"""
    INSERT INTO qa_logs ({", ".join(insert_columns)})
    VALUES ({", ".join(value_exprs)})
    RETURNING id::text
    """

    try:
        result = db.execute(text(sql), params).scalar_one()
        db.commit()
        return result
    except Exception:
        db.rollback()
        return None


@router.post("/ask-llm", response_model=KnowledgeAskLLMResponse)
def ask_knowledge_with_llm(
    payload: KnowledgeAskLLMRequest,
    db: Session = Depends(get_db),
):
    hits = _search_chunks(
        db=db,
        question=payload.question,
        top_k=payload.top_k,
    )

    citations = _build_citations(hits)

    llm_result = generate_rag_answer(
        question=payload.question,
        chunks=hits,
        fallback_answer="",
    )

    answer = llm_result["answer"]

    qa_log_id = _try_insert_qa_log(
        db=db,
        question=payload.question,
        answer=answer,
        citations=citations,
    )

    return {
        "question": payload.question,
        "answer": answer,
        "citations": citations,
        "hits": hits,
        "provider": llm_result["provider"],
        "model": llm_result["model"],
        "used_llm": llm_result["used_llm"],
        "fallback_reason": llm_result.get("fallback_reason", ""),
        "qa_log_id": qa_log_id,
    }
