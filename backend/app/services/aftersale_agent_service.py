from __future__ import annotations

import time
from typing import Any, Callable
from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.services.agent_tool_service import (
    call_analytics_tool,
    call_knowledge_rag_tool,
    call_order_context_tool,
    call_ticket_auto_create_tool,
)


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)

def _should_call_analytics(question: str, include_analytics: bool) -> bool:
    if include_analytics:
        return True

    analytics_words = [
        "统计",
        "趋势",
        "多少",
        "几条",
        "分布",
        "占比",
        "排行",
        "最近7天",
        "最近 7 天",
        "最近30天",
        "最近 30 天",
        "退款率",
        "物流异常数量",
        "投诉数量",
    ]

    return _contains_any(question, analytics_words)

def _detect_base_intents(
    *,
    question: str,
    order_no: str | None,
    auto_create_ticket: bool,
    include_analytics: bool,
) -> list[str]:
    intents = ["knowledge_rag"]

    if order_no:
        intents.append("order_context")

    if auto_create_ticket:
        intents.append("ticket_auto_create")

    if _should_call_analytics(question, include_analytics):
        intents.append("analytics_nl2sql")

    return intents

def _execute_tool(
    *,
    tool_name: str,
    purpose: str,
    func: Callable[[], Any],
) -> dict[str, Any]:
    started = time.perf_counter()

    try:
        data = func()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "tool_name": tool_name,
            "purpose": purpose,
            "success": True,
            "latency_ms": latency_ms,
            "data": jsonable_encoder(data),
            "error": None,
        }
    except HTTPException as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "tool_name": tool_name,
            "purpose": purpose,
            "success": False,
            "latency_ms": latency_ms,
            "data": None,
            "error": f"HTTPException {exc.status_code}: {exc.detail}",
        }
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "tool_name": tool_name,
            "purpose": purpose,
            "success": False,
            "latency_ms": latency_ms,
            "data": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

def _get_tool_data(tool_calls: list[dict[str, Any]], tool_name: str) -> dict[str, Any] | None:
    for call in tool_calls:
        if call["tool_name"] == tool_name and call["success"]:
            data = call.get("data")
            if isinstance(data, dict):
                return data
    return None

def _build_risk_flags(
    *,
    question: str,
    order_context: dict[str, Any] | None,
) -> list[str]:
    flags: list[str] = []
    q = question.strip()

    if _contains_any(q, ["三天没更新", "72小时", "72 小时", "物流延迟", "没更新", "未更新"]):
        flags.append("物流长时间未更新，存在投诉升级风险")

    if _contains_any(q, ["退款", "退钱", "赔偿", "补偿", "投诉"]):
        flags.append("涉及退款/补偿/投诉，需要保留规则依据和处理记录")

    if _contains_any(q, ["破损", "坏了", "少件", "错发", "质量"]):
        flags.append("涉及商品质量或履约问题，需要收集凭证")

    if order_context:
        order = order_context.get("order") or {}
        amount = int(order.get("total_amount_cents") or 0)

        if amount >= 30000:
            flags.append("高金额订单，建议组长复核")

        logistics = order_context.get("logistics") or []
        if any(item.get("status") in {"delayed", "exception"} for item in logistics):
            flags.append("订单存在物流延迟或异常状态")

        refunds = order_context.get("refunds") or []
        if any(item.get("status") in {"pending", "processing"} for item in refunds):
            flags.append("订单存在待处理或处理中的退款")

        tickets = order_context.get("tickets") or []
        if any(item.get("status") in {"open", "processing"} for item in tickets):
            flags.append("订单存在未关闭售后工单")

    return list(dict.fromkeys(flags))

def _build_action_plan(
    *,
    question: str,
    knowledge: dict[str, Any] | None,
    order_context: dict[str, Any] | None,
    ticket_result: dict[str, Any] | None,
    analytics: dict[str, Any] | None,
    auto_create_ticket: bool,
) -> list[str]:
    steps: list[str] = []

    if order_context:
        recommendation = order_context.get("recommendation") or {}
        suggested_action = recommendation.get("suggested_action")
        if suggested_action:
            steps.append(suggested_action)

    if knowledge:
        citations = knowledge.get("citations") or knowledge.get("hits") or []
        if citations:
            first = citations[0]
            title = first.get("document_title") or "知识库命中文档"
            section = first.get("section") or "相关章节"
            steps.append(f"回复用户前先引用《{title}》中的“{section}”规则，避免无依据承诺。")
        else:
            steps.append("知识库依据不足，建议转人工复核或补充政策文档。")

    if ticket_result:
        ticket = ticket_result.get("ticket") or {}
        ticket_no = ticket.get("ticket_no")
        if ticket_no:
            steps.append(f"已创建工单 {ticket_no}，后续在工单中心跟踪处理。")
    elif auto_create_ticket:
        steps.append("已尝试创建工单，但创建失败，请查看 tool_calls 中的错误信息。")
    else:
        if _contains_any(question, ["投诉", "退款", "补偿", "破损", "质量", "没更新", "物流延迟"]):
            steps.append("如用户继续追问或情绪升级，可开启 auto_create_ticket 创建工单。")

    if analytics:
        summary = analytics.get("summary")
        if summary:
            steps.append(f"运营侧参考：{summary}")

    if not steps:
        steps.append("建议客服按标准售后 SOP 处理，并记录用户问题、订单状态和处理结论。")

    return steps

def _build_final_answer(
    *,
    question: str,
    knowledge: dict[str, Any] | None,
    order_context: dict[str, Any] | None,
    ticket_result: dict[str, Any] | None,
    analytics: dict[str, Any] | None,
    risk_flags: list[str],
    action_plan: list[str],
) -> str:
    lines: list[str] = []

    lines.append(f"针对用户问题“{question}”，系统已完成售后处理编排。")

    if knowledge:
        answer = knowledge.get("answer")
        if answer:
            lines.append("")
            lines.append("【知识库建议】")
            lines.append(str(answer))

    if order_context:
        recommendation = order_context.get("recommendation") or {}
        lines.append("")
        lines.append("【订单处理建议】")
        lines.append(str(recommendation.get("suggested_action") or "已查询订单上下文，但暂无明确推荐动作。"))
        if recommendation.get("reason"):
            lines.append(f"原因：{recommendation['reason']}")

    if risk_flags:
        lines.append("")
        lines.append("【风险提示】")
        for item in risk_flags:
            lines.append(f"- {item}")

    if action_plan:
        lines.append("")
        lines.append("【下一步动作】")
        for index, item in enumerate(action_plan, start=1):
            lines.append(f"{index}. {item}")

    if ticket_result:
        ticket = ticket_result.get("ticket") or {}
        ticket_no = ticket.get("ticket_no")
        if ticket_no:
            lines.append("")
            lines.append(f"【工单结果】已创建工单：{ticket_no}")

    if analytics:
        lines.append("")
        lines.append("【数据分析】")
        lines.append(str(analytics.get("summary") or "已完成运营问数。"))

    return "\n".join(lines)


def run_aftersale_agent(
    db: Session,
    *,
    question: str,
    order_no: str | None = None,
    top_k: int = 5,
    auto_create_ticket: bool = False,
    include_analytics: bool = False,
    created_by_id: UUID | None = None,
) -> dict[str, Any]:
    question = question.strip()
    order_no = order_no.strip() if order_no else None

    route_intents = _detect_base_intents(
        question=question,
        order_no=order_no,
        auto_create_ticket=auto_create_ticket,
        include_analytics=include_analytics,
    )
    tool_calls: list[dict[str, Any]] = []

    tool_calls.append(
        _execute_tool(
            tool_name="knowledge_rag",
            purpose="检索售后规则并生成有引用依据的客服回答",
            func=lambda: call_knowledge_rag_tool(
                db=db,
                question=question,
                top_k=top_k,
            ),
        )
    )

    if order_no:
        tool_calls.append(
            _execute_tool(
                tool_name="order_context",
                purpose="查询订单、物流、退款和历史售后上下文",
                func=lambda: call_order_context_tool(
                    db=db,
                    order_no=order_no,
                ),
            )
        )
    if _should_call_analytics(question, include_analytics):
        tool_calls.append(
            _execute_tool(
                tool_name="analytics_nl2sql",
                purpose="根据运营问题生成安全 SQL 并返回统计结果",
                func=lambda: call_analytics_tool(
                    db=db,
                    question=question,
                    limit=20,
                ),
            )
        )

    if auto_create_ticket:
        tool_calls.append(
            _execute_tool(
                tool_name="ticket_auto_create",
                purpose="根据用户问题和订单号自动创建售后工单",
                func=lambda: call_ticket_auto_create_tool(
                    db=db,
                    customer_question=question,
                    order_no=order_no,
                    created_by_id=created_by_id,
                ),
            )
        )
    knowledge = _get_tool_data(tool_calls, "knowledge_rag")
    order_context = _get_tool_data(tool_calls, "order_context")
    ticket_result = _get_tool_data(tool_calls, "ticket_auto_create")
    analytics = _get_tool_data(tool_calls, "analytics_nl2sql")

    risk_flags = _build_risk_flags(
        question=question,
        order_context=order_context,
    )

    action_plan = _build_action_plan(
        question=question,
        knowledge=knowledge,
        order_context=order_context,
        ticket_result=ticket_result,
        analytics=analytics,
        auto_create_ticket=auto_create_ticket,
    )

    final_answer = _build_final_answer(
        question=question,
        knowledge=knowledge,
        order_context=order_context,
        ticket_result=ticket_result,
        analytics=analytics,
        risk_flags=risk_flags,
        action_plan=action_plan,
    )
    created_ticket_no = None
    if ticket_result:
        ticket = ticket_result.get("ticket") or {}
        created_ticket_no = ticket.get("ticket_no")

    provider = "local"
    model = "local-template"
    used_llm = False

    if knowledge:
        provider = knowledge.get("provider") or provider
        model = knowledge.get("model") or model
        used_llm = bool(knowledge.get("used_llm", False))

    return {
        "question": question,
        "order_no": order_no,
        "route_intents": route_intents,
        "final_answer": final_answer,
        "action_plan": action_plan,
        "risk_flags": risk_flags,
        "tool_calls": tool_calls,
        "created_ticket_no": created_ticket_no,
        "used_llm": used_llm,
        "provider": provider,
        "model": model,
    }