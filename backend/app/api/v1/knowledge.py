import json
import time
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.knowledge import KnowledgeSearchOut
from app.services.knowledge_search_service import search_knowledge
from app.services.llm_gateway import generate_rag_answer

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeHit(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    file_name: str | None = None
    file_type: str | None = None
    content: str
    page_no: int | None = None
    policy_code: str | None = None
    section: str | None = None
    score: float = 0.0


class KnowledgeAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeAskResponse(BaseModel):
    question: str
    query: str
    answer: str
    answer_summary: str | None = None
    citations: list[KnowledgeHit] = Field(default_factory=list)
    hits: list[KnowledgeHit] = Field(default_factory=list)
    qa_log_id: str | None = None

    provider:str="local"
    model:str="local-template"
    used_llm:bool=False
    fallback_reason:str=""


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _build_candidate_queries(question: str) -> list[str]:
    q = question.strip()

    logistics_words = ["物流", "快递", "配送", "包裹", "运单", "三天没更新", "没更新", "未更新", "延迟", "超时", "未到", "没到"]
    refund_words = ["退款", "退钱", "补偿", "赔偿", "赔付", "补偿券"]

    has_logistics = any(word in q for word in logistics_words)
    has_refund_or_comp = any(word in q for word in refund_words)

    candidates = [q]

    if has_logistics and has_refund_or_comp:
        candidates.extend([
            "物流延迟补偿",
            "物流延迟 退款 补偿",
            "大促物流延迟补偿",
        ])

    compact = q
    for noise in ["应该", "怎么", "如何", "什么", "请问", "能不能", "可以", "是否", "需要", "规则", "处理", "吗", "呢", "？", "?", "。", "，", ","]:
        compact = compact.replace(noise, "")
    candidates.append(compact)

    terms: list[str] = []
    if has_logistics:
        terms.append("物流")
    if any(word in q for word in ["延迟", "超时", "三天", "没更新", "未更新", "未到", "没到"]):
        terms.append("延迟")
    if any(word in q for word in ["退款", "退钱"]):
        terms.append("退款")
    if any(word in q for word in ["补偿", "赔偿", "赔付", "补偿券"]):
        terms.append("补偿")

    if terms:
        candidates.append("".join(terms))
        candidates.append(" ".join(terms))

    return _unique(candidates)


def _build_answer(question: str, hits: list[dict]) -> str:
    if not hits:
        return (
            f"知识库中暂未检索到与“{question}”直接相关的规则。"
            "建议客服转人工复核，或补充售后政策文档后重新查询。"
        )

    first = hits[0]
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


def _write_qa_log(
    db: Session,
    *,
    question: str,
    answer: str,
    citations: list[dict],
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


@router.get("/search", response_model=KnowledgeSearchOut)
def search(
    q: str = Query(..., min_length=1, description="知识检索关键词"),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return search_knowledge(db=db, query=q, limit=limit)


@router.post("/ask", response_model=KnowledgeAskResponse)
def ask_knowledge_api(payload: KnowledgeAskRequest, db: Session = Depends(get_db)):
    started = time.perf_counter()

    used_query = payload.question
    search_result = {"hits": [], "answer_summary": None}

    for candidate_query in _build_candidate_queries(payload.question):
        current_result = search_knowledge(
            db=db,
            query=candidate_query,
            limit=payload.top_k,
        )
        if current_result.get("hits"):
            used_query = candidate_query
            search_result = current_result
            break
        search_result = current_result

    hits = search_result.get("hits", [])
    fallback_answer=_build_answer(payload.question,hits)
    llm_result = generate_rag_answer(
        question=payload.question,
        chunks=hits,
        fallback_answer=fallback_answer,
    )
    answer = _build_answer(payload.question, hits)
    latency_ms = int((time.perf_counter() - started) * 1000)

    qa_log_id = _write_qa_log(
        db,
        question=payload.question,
        answer=answer,
        citations=hits,
        latency_ms=latency_ms,
    )

    return {
        "question": payload.question,
        "query": used_query,
        "answer": answer,
        "answer_summary": search_result.get("answer_summary"),
        "citations": hits,
        "hits": hits,
        "qa_log_id": qa_log_id,
        "provider": llm_result["provider"],
        "model": llm_result["model"],
        "used_llm": llm_result["used_llm"],
        "fallback_reason": llm_result.get("fallback_reason", ""),
    }
