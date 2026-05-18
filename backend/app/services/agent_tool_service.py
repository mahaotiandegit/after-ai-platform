from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.services.analytics_nl2sql import ask_analytics_question
from app.services.knowledge_search_service import search_knowledge
from app.services.llm_gateway import generate_rag_answer
from app.services.order_context_service import get_order_aftersale_context
from app.services.ticket_service import auto_create_ticket

def _build_fallback_answer(question:str,hits:list[dict[str, Any]])->str:
    if not hits:
        return (
            f"知识库中暂未检索到与“{question}”直接相关的规则。"
            "建议客服转人工复核，或补充售后政策文档后重新查询。"
        )
    
    first=hits[0]
    document_title = first.get("document_title") or "相关知识文档"
    section = first.get("section") or "相关章节"
    policy_code = first.get("policy_code") or "暂无规则编号"
    content = first.get("content") or ""

    return (
        f"针对“{question}”，建议优先参考《{document_title}》"
        f"中的“{section}”部分，规则编号为 {policy_code}。"
        f"根据命中文档内容：{content}"
        "客服处理时需要结合订单状态、物流状态、退款状态和用户历史售后记录综合判断。"
    )

def call_knowledge_rag_tool(
    db: Session,
    *,
    question: str,
    top_k: int = 5,
) -> dict[str, Any]:
    search_result = search_knowledge(
        db=db,
        query=question,
        limit=top_k,
    )

    hits = search_result.get("hits", [])
    fallback_answer = _build_fallback_answer(question, hits)

    llm_result = generate_rag_answer(
        question=question,
        chunks=hits,
        fallback_answer=fallback_answer,
    )

    return jsonable_encoder(
        {
            "query": search_result.get("query", question),
            "answer": llm_result.get("answer", fallback_answer),
            "answer_summary": search_result.get("answer_summary"),
            "citations": hits,
            "hits": hits,
            "retrieval_mode": search_result.get("retrieval_mode", "keyword"),
            "embedding_ready": bool(search_result.get("embedding_ready", False)),
            "provider": llm_result.get("provider", "local"),
            "model": llm_result.get("model", "local-template"),
            "used_llm": bool(llm_result.get("used_llm", False)),
            "fallback_reason": llm_result.get("fallback_reason", ""),
        }
    )

def call_order_context_tool(
    db: Session,
    *,
    order_no: str,
) -> dict[str, Any]:
    result = get_order_aftersale_context(db=db, order_no=order_no)
    return jsonable_encoder(result)


def call_ticket_auto_create_tool(
    db: Session,
    *,
    customer_question: str,
    order_no: str | None,
    created_by_id: UUID | None,
) -> dict[str, Any]:
    result = auto_create_ticket(
        db=db,
        customer_question=customer_question,
        order_no=order_no,
        created_by_id=created_by_id,
    )
    return jsonable_encoder(result)


def call_analytics_tool(
    db: Session,
    *,
    question: str,
    limit: int = 20,
) -> dict[str, Any]:
    result = ask_analytics_question(
        db=db,
        question=question,
        limit=limit,
    )
    return jsonable_encoder(result)