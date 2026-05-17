from __future__ import annotations

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.embedding_service import embed_text, to_pgvector_literal


def _float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _hybrid_keyword_weight() -> float:
    return _float(os.getenv("HYBRID_KEYWORD_WEIGHT", "0.55"), 0.55)


def _hybrid_vector_weight() -> float:
    return _float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.45"), 0.45)


def _embedding_ready(db: Session) -> bool:
    has_column = db.execute(
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
        return False

    count = db.execute(
        text(
            """
            SELECT count(*)
            FROM document_chunks
            WHERE embedding IS NOT NULL
            """
        )
    ).scalar()

    return int(count or 0) > 0


def _row_to_hit(row: Any, score: float | None = None) -> dict[str, Any]:
    item = dict(row)

    return {
        "chunk_id": str(item.get("chunk_id")),
        "document_id": str(item.get("document_id")),
        "document_title": item.get("document_title") or "",
        "file_name": item.get("file_name") or "",
        "file_type": item.get("file_type") or "",
        "content": item.get("content") or "",
        "page_no": item.get("page_no"),
        "policy_code": item.get("policy_code"),
        "section": item.get("section"),
        "score": round(score if score is not None else _float(item.get("score")), 6),
    }


def _keyword_search(db: Session, query: str, limit: int) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []

    query_like = f"%{query}%"

    rows = db.execute(
        text(
            """
            SELECT
                c.id AS chunk_id,
                c.document_id AS document_id,
                d.title AS document_title,
                d.file_name AS file_name,
                d.file_type AS file_type,
                c.content AS content,
                c.page_no AS page_no,
                c.policy_code AS policy_code,
                c.section AS section,
                (
                    CASE WHEN c.content ILIKE :query_like THEN 2.0 ELSE 0 END
                    + CASE WHEN d.title ILIKE :query_like THEN 1.2 ELSE 0 END
                    + CASE WHEN c.section ILIKE :query_like THEN 0.8 ELSE 0 END
                    + CASE WHEN c.policy_code ILIKE :query_like THEN 1.0 ELSE 0 END
                ) AS score
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE
                c.content ILIKE :query_like
                OR d.title ILIKE :query_like
                OR c.section ILIKE :query_like
                OR c.policy_code ILIKE :query_like
            ORDER BY score DESC, c.id
            LIMIT :limit
            """
        ),
        {
            "query_like": query_like,
            "limit": max(limit, 1),
        },
    ).mappings().all()

    return [_row_to_hit(row) for row in rows]


def _vector_search(db: Session, query: str, limit: int) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []

    query_vector = to_pgvector_literal(embed_text(query))

    rows = db.execute(
        text(
            """
            SELECT
                c.id AS chunk_id,
                c.document_id AS document_id,
                d.title AS document_title,
                d.file_name AS file_name,
                d.file_type AS file_type,
                c.content AS content,
                c.page_no AS page_no,
                c.policy_code AS policy_code,
                c.section AS section,
                (1 - (c.embedding <=> CAST(:query_vector AS vector))) AS score
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:query_vector AS vector)
            LIMIT :limit
            """
        ),
        {
            "query_vector": query_vector,
            "limit": max(limit, 1),
        },
    ).mappings().all()

    hits: list[dict[str, Any]] = []
    for row in rows:
        raw_score = _float(row.get("score"))
        score = max(0.0, min(1.0, raw_score))
        hits.append(_row_to_hit(row, score=score))

    return hits


def _merge_hits(
    keyword_hits: list[dict[str, Any]],
    vector_hits: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    if not keyword_hits:
        return sorted(vector_hits, key=lambda x: x["score"], reverse=True)[:limit]

    if not vector_hits:
        return sorted(keyword_hits, key=lambda x: x["score"], reverse=True)[:limit]

    keyword_weight = _hybrid_keyword_weight()
    vector_weight = _hybrid_vector_weight()

    max_keyword_score = max([h["score"] for h in keyword_hits] or [1.0]) or 1.0

    merged: dict[str, dict[str, Any]] = {}

    for hit in keyword_hits:
        chunk_id = hit["chunk_id"]
        merged[chunk_id] = {
            **hit,
            "_keyword_score": hit["score"] / max_keyword_score,
            "_vector_score": 0.0,
        }

    for hit in vector_hits:
        chunk_id = hit["chunk_id"]
        if chunk_id not in merged:
            merged[chunk_id] = {
                **hit,
                "_keyword_score": 0.0,
                "_vector_score": hit["score"],
            }
        else:
            merged[chunk_id]["_vector_score"] = hit["score"]

    final_hits: list[dict[str, Any]] = []
    for item in merged.values():
        final_score = (
            keyword_weight * item["_keyword_score"]
            + vector_weight * item["_vector_score"]
        )

        item.pop("_keyword_score", None)
        item.pop("_vector_score", None)
        item["score"] = round(final_score, 6)
        final_hits.append(item)

    final_hits.sort(key=lambda x: x["score"], reverse=True)
    return final_hits[:limit]


def _build_answer_summary(query: str, hits: list[dict[str, Any]], retrieval_mode: str) -> str:
    if not hits:
        return f"未检索到与“{query}”相关的知识，请尝试换一个关键词，或上传相关规则文档。"

    first = hits[0]
    title = first.get("document_title") or "未知文档"
    section = first.get("section") or "相关片段"
    policy_code = first.get("policy_code")

    code_text = f"，规则编号为 {policy_code}" if policy_code else ""

    return (
        f"根据知识库{retrieval_mode}检索结果，问题“{query}”优先参考"
        f"《{title}》中的“{section}”部分{code_text}。"
        f"客服处理时应结合订单状态、物流状态、退款状态和用户历史售后记录综合判断。"
    )


def search_knowledge(db: Session, query: str, limit: int = 5) -> dict[str, Any]:
    limit = max(1, min(int(limit or 5), 20))
    query = (query or "").strip()

    candidate_limit = max(limit * 4, 10)

    keyword_hits = _keyword_search(db, query, candidate_limit)

    vector_ready = _embedding_ready(db)
    vector_hits: list[dict[str, Any]] = []

    retrieval_mode = "keyword"

    if vector_ready:
        try:
            vector_hits = _vector_search(db, query, candidate_limit)
            retrieval_mode = "hybrid" if keyword_hits else "vector"
        except Exception:
            vector_hits = []
            retrieval_mode = "keyword"

    hits = _merge_hits(keyword_hits, vector_hits, limit)

    return {
        "query": query,
        "answer_summary": _build_answer_summary(query, hits, retrieval_mode),
        "hits": hits,
        "retrieval_mode": retrieval_mode,
        "embedding_ready": vector_ready,
        "vector_candidate_count": len(vector_hits),
    }