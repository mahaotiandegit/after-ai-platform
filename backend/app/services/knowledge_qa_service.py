from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _safe_get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _normalize_hits(search_result: Any) -> list[dict[str, Any]]:
    if isinstance(search_result, dict):
        raw_hits = search_result.get("hits") or search_result.get("items") or []
    elif isinstance(search_result, list):
        raw_hits = search_result
    else:
        raw_hits = []

    hits: list[dict[str, Any]] = []

    for item in raw_hits:
        chunk_id = _safe_get(item, "chunk_id") or _safe_get(item, "id")
        document_id = _safe_get(item, "document_id")
        document_title = (
            _safe_get(item, "document_title")
            or _safe_get(item, "title")
            or _safe_get(item, "document_name")
        )

        hits.append(
            {
                "chunk_id": str(chunk_id) if chunk_id is not None else None,
                "document_id": str(document_id) if document_id is not None else None,
                "document_title": document_title,
                "file_name": _safe_get(item, "file_name"),
                "file_type": _safe_get(item, "file_type"),
                "page_no": _safe_get(item, "page_no"),
                "policy_code": _safe_get(item, "policy_code"),
                "section": _safe_get(item, "section"),
                "score": _safe_get(item, "score"),
                "content": (
                    _safe_get(item, "content")
                    or _safe_get(item, "chunk_text")
                    or _safe_get(item, "text")
                    or ""
                ),
            }
        )

    return hits


def _build_answer(question: str, hits: list[dict[str, Any]]) -> str:
    if not hits:
        return (
            f"没有在知识库中检索到与“{question}”直接相关的规则。"
            "建议客服先核实订单状态、物流状态和退款状态，并提交工单给组长复核。"
        )

    first = hits[0]
    title = first.get("document_title") or "相关知识文档"
    section = first.get("section")
    policy_code = first.get("policy_code")
    content = (first.get("content") or "").strip()

    if len(content) > 260:
        content = content[:260] + "..."

    refs = []
    if policy_code:
        refs.append(f"规则编号：{policy_code}")
    if section:
        refs.append(f"章节：{section}")

    ref_text = "，".join(refs)

    return (
        f"针对“{question}”，优先参考《{title}》"
        f"{'（' + ref_text + '）' if ref_text else ''}。"
        f"{content}"
        " 客服处理时应结合订单状态、物流状态、退款状态和用户历史反馈判断；"
        "涉及补偿或退款承诺时，应保留处理记录，并按工单流程流转。"
    )


def write_qa_log(
    db: Session,
    *,
    question: str,
    answer: str,
    citations: list[dict[str, Any]],
    latency_ms: int,
) -> str:
    qa_log_id = str(uuid.uuid4())

    db.execute(
        text(
            """
            insert into qa_logs (
                id,
                question,
                answer,
                citations,
                latency_ms,
                created_at
            )
            values (
                :id,
                :question,
                :answer,
                cast(:citations as jsonb),
                :latency_ms,
                now()
            )
            """
        ),
        {
            "id": qa_log_id,
            "question": question,
            "answer": answer,
            "citations": json.dumps(citations, ensure_ascii=False),
            "latency_ms": latency_ms,
        },
    )
    db.commit()
    return qa_log_id


def ask_knowledge(
    db: Session,
    *,
    question: str,
    search_result: Any,
) -> dict[str, Any]:
    started = time.perf_counter()

    hits = _normalize_hits(search_result)
    citations = [
        {
            "chunk_id": h.get("chunk_id"),
            "document_id": h.get("document_id"),
            "document_title": h.get("document_title"),
            "file_name": h.get("file_name"),
            "file_type": h.get("file_type"),
            "page_no": h.get("page_no"),
            "policy_code": h.get("policy_code"),
            "section": h.get("section"),
            "score": h.get("score"),
            "content": h.get("content"),
        }
        for h in hits
    ]

    answer = _build_answer(question, hits)
    latency_ms = int((time.perf_counter() - started) * 1000)

    qa_log_id = write_qa_log(
        db,
        question=question,
        answer=answer,
        citations=citations,
        latency_ms=latency_ms,
    )

    return {
        "qa_log_id": qa_log_id,
        "question": question,
        "answer": answer,
        "citations": citations,
        "latency_ms": latency_ms,
    }
