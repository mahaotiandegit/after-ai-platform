from sqlalchemy import text
from sqlalchemy.orm import Session

def _build_summary(query:str,hits:list[dict])->str:
    if not hits:
        return "未检索到相关知识，请尝试换一个关键词，或联系运营管理员补充知识库。"
    top=hits[0]
    title=top["document_title"]
    section = top.get("section") or "相关规则"
    policy_code = top.get("policy_code") or "未标注规则编号"

    return (
        f"根据知识库命中结果，问题“{query}”优先参考《{title}》中的"
        f"“{section}”部分，规则编号为 {policy_code}。"
        f"客服处理时应结合订单状态、物流状态、退款状态进行判断。"
    )

def search_knowledge(db: Session, query: str, limit: int = 5) -> dict:
    normalized_query = query.strip()
    if not normalized_query:
        return {
            "query": query,
            "answer_summary": "查询内容不能为空。",
            "hits": [],
        }

    rows = db.execute(
        text(
            """
            SELECT
                c.id::text AS chunk_id,
                d.id::text AS document_id,
                d.title AS document_title,
                d.file_name,
                d.file_type,
                c.content,
                c.page_no,
                c.metadata ->> 'policy_code' AS policy_code,
                c.metadata ->> 'section' AS section,
                (
                    COALESCE(
                        ts_rank(
                            to_tsvector('simple', c.content),
                            plainto_tsquery('simple', :query)
                        ),
                        0
                    )
                    +
                    CASE WHEN c.content ILIKE :like_query THEN 1.0 ELSE 0 END
                    +
                    CASE WHEN d.title ILIKE :like_query THEN 0.8 ELSE 0 END
                    +
                    CASE WHEN c.metadata ->> 'section' ILIKE :like_query THEN 0.6 ELSE 0 END
                    +
                    CASE WHEN c.metadata ->> 'policy_code' ILIKE :like_query THEN 0.4 ELSE 0 END
                ) AS score
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE
                to_tsvector('simple', c.content) @@ plainto_tsquery('simple', :query)
                OR c.content ILIKE :like_query
                OR d.title ILIKE :like_query
                OR c.metadata ->> 'policy_code' ILIKE :like_query
                OR c.metadata ->> 'section' ILIKE :like_query
            ORDER BY
                score DESC,
                c.created_at DESC
            LIMIT :limit
            """
        ),
        {
            "query": normalized_query,
            "like_query": f"%{normalized_query}%",
            "limit": limit,
        },
    ).mappings().all()

    hits = []
    for row in rows:
        item = dict(row)
        item["score"] = float(item["score"] or 0)
        hits.append(item)

    return {
        "query": normalized_query,
        "answer_summary": _build_summary(normalized_query, hits),
        "hits": hits,
    }