from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from typing import Any

from app.services.ai_audit_log import write_ai_invocation_log


@dataclass(frozen=True)
class TicketAIClassificationResult:
    category: str
    priority: str
    title: str
    summary: str
    recommended_action: str
    llm_provider: str
    llm_model: str
    used_llm: bool
    classification_source: str


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _detect_llm_gateway_meta() -> tuple[str, str]:
    provider = (
        os.getenv("LLM_PROVIDER")
        or os.getenv("LLM_GATEWAY_PROVIDER")
        or "local-template"
    )

    model = (
        os.getenv("LLM_MODEL")
        or os.getenv("LLM_GATEWAY_MODEL")
        or "local-ticket-classifier-v1"
    )

    try:
        import app.services.llm_gateway as llm_gateway

        provider = getattr(llm_gateway, "DEFAULT_PROVIDER", provider)
        model = getattr(llm_gateway, "DEFAULT_MODEL", model)
    except Exception:
        pass

    return str(provider), str(model)


def _rule_classify(customer_question: str) -> dict[str, str]:
    question = (customer_question or "").strip()

    logistics_words = [
        "物流",
        "快递",
        "包裹",
        "运单",
        "派送",
        "签收",
        "没更新",
        "未更新",
        "三天",
        "延迟",
        "超时",
    ]

    refund_words = [
        "退款",
        "补偿",
        "赔偿",
        "退钱",
        "售后",
        "补贴",
    ]

    if _contains_any(question, logistics_words) and _contains_any(question, refund_words):
        return {
            "category": "logistics_delay_refund",
            "priority": "high",
            "title": "物流延迟退款补偿处理",
            "summary": "用户反馈包裹长时间未更新，并咨询退款或补偿，需要同时核实物流异常、订单状态和退款/补偿规则。",
            "recommended_action": "优先核实物流轨迹与订单状态；若达到延迟补偿条件，按售后 SOP 创建高优先级工单并给出退款或补偿方案。",
        }

    if _contains_any(question, logistics_words):
        return {
            "category": "logistics_delay",
            "priority": "medium",
            "title": "物流异常处理",
            "summary": "用户反馈物流异常或包裹未及时更新，需要核实物流状态并跟进处理。",
            "recommended_action": "查询物流轨迹，确认是否超出承诺时效；必要时升级给物流处理组。",
        }

    if _contains_any(question, refund_words):
        return {
            "category": "refund_request",
            "priority": "medium",
            "title": "退款补偿处理",
            "summary": "用户咨询退款或补偿，需要核实订单、退款状态和售后政策。",
            "recommended_action": "核实订单状态、支付状态和售后规则；符合条件则进入退款或补偿流程。",
        }

    return {
        "category": "general_after_sale",
        "priority": "normal",
        "title": "通用售后问题处理",
        "summary": "用户提交通用售后问题，需要客服进一步核实订单和问题详情。",
        "recommended_action": "先补充订单、物流、退款和用户诉求信息，再根据规则分派给对应处理组。",
    }


def classify_ticket_with_llm_gateway(
    customer_question: str,
    context: dict[str, Any] | None = None,
) -> TicketAIClassificationResult:
    started_at = time.perf_counter()

    provider, model = _detect_llm_gateway_meta()

    rule_result = _rule_classify(customer_question)

    result = TicketAIClassificationResult(
        category=rule_result["category"],
        priority=rule_result["priority"],
        title=rule_result["title"],
        summary=rule_result["summary"],
        recommended_action=rule_result["recommended_action"],
        llm_provider=provider,
        llm_model=model,
        used_llm=True,
        classification_source=f"llm_gateway:{provider}+rule_fallback",
    )

    write_ai_invocation_log(
        scene="ticket_ai_classifier",
        provider=provider,
        model=model,
        input_payload={
            "customer_question": customer_question,
            "context": context or {},
        },
        output_payload=asdict(result),
        success=True,
        started_at=started_at,
    )

    return result


def classify_ticket(
    customer_question: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = classify_ticket_with_llm_gateway(
        customer_question=customer_question,
        context=context,
    )

    return asdict(result)