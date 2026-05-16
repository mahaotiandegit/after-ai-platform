from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def _jsonable_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: _jsonable_value(value) for key, value in dict(row).items()}


def _rows_to_list(rows: list[Any]) -> list[dict[str, Any]]:
    return [_row_to_dict(row) for row in rows]


def _amount_yuan(amount_cents: int | None) -> float:
    return round((amount_cents or 0) / 100, 2)


def _build_recommendation(
    order: dict[str, Any],
    logistics: list[dict[str, Any]],
    refunds: list[dict[str, Any]],
    tickets: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_logistics = logistics[0] if logistics else None
    active_tickets = [
        item for item in tickets
        if item.get("status") in {"open", "processing"}
    ]
    pending_refunds = [
        item for item in refunds
        if item.get("status") in {"pending", "processing"}
    ]

    risk_flags: list[str] = []
    issue_type = "general_after_sale"
    priority = "low"
    suggested_action = "先核对订单、物流、退款和历史工单信息，再根据用户诉求选择售后处理动作。"
    next_steps = [
        "核对订单状态和用户诉求是否一致",
        "检查是否已有未关闭工单，避免重复建单",
        "必要时补充客服备注并转人工复核",
    ]

    if latest_logistics and latest_logistics.get("status") == "delayed":
        issue_type = "logistics_delay"
        priority = "high" if pending_refunds or active_tickets else "medium"
        risk_flags.append("物流延迟")
        suggested_action = (
            "当前订单存在物流延迟，应先安抚用户并核实最新物流节点；"
            "如果延迟属实，再结合订单金额、延迟天数、退款状态和历史工单判断是否补偿。"
        )
        next_steps = [
            "确认物流是否仍处于 delayed 状态",
            "检查是否已有退款或补偿申请",
            "参考物流延迟补偿规则判断是否发放补偿券",
            "如用户强烈投诉或已有退款申请，优先升级高优先级工单",
        ]

    if pending_refunds:
        risk_flags.append("存在处理中退款")
        if priority == "low":
            priority = "medium"

    if active_tickets:
        risk_flags.append("存在未关闭工单")

    if order.get("total_amount_cents", 0) >= 30000:
        risk_flags.append("订单金额较高")
        if priority == "low":
            priority = "medium"

    can_create_ticket = len(active_tickets) == 0

    if not can_create_ticket:
        next_steps.append("当前已有未关闭工单，建议先进入历史工单继续处理，不要重复建单。")
    else:
        next_steps.append("如果用户问题无法直接解决，可以一键创建工单进入流转。")

    return {
        "issue_type": issue_type,
        "priority": priority,
        "suggested_action": suggested_action,
        "risk_flags": risk_flags,
        "can_create_ticket": can_create_ticket,
        "next_steps": next_steps,
    }


def get_order_workbench(db: Session, order_no: str) -> dict[str, Any] | None:
    order_row = db.execute(
        text(
            """
            SELECT
                id,
                order_no,
                customer_name,
                customer_phone,
                status,
                total_amount_cents,
                created_at,
                updated_at
            FROM orders
            WHERE order_no = :order_no
            LIMIT 1
            """
        ),
        {"order_no": order_no},
    ).mappings().first()

    order = _row_to_dict(order_row)
    if order is None:
        return None

    order_id = order["id"]

    logistics = _rows_to_list(
        db.execute(
            text(
                """
                SELECT
                    id,
                    order_id,
                    carrier,
                    tracking_no,
                    status,
                    latest_event,
                    shipped_at,
                    delivered_at,
                    created_at
                FROM logistics
                WHERE order_id = :order_id
                ORDER BY created_at DESC
                """
            ),
            {"order_id": order_id},
        ).mappings().all()
    )

    refunds = _rows_to_list(
        db.execute(
            text(
                """
                SELECT
                    id,
                    order_id,
                    refund_no,
                    reason,
                    amount_cents,
                    status,
                    created_at,
                    updated_at
                FROM refunds
                WHERE order_id = :order_id
                ORDER BY created_at DESC
                """
            ),
            {"order_id": order_id},
        ).mappings().all()
    )

    tickets = _rows_to_list(
        db.execute(
            text(
                """
                SELECT
                    id,
                    ticket_no,
                    order_id,
                    customer_question,
                    category,
                    priority,
                    title,
                    summary,
                    status,
                    assignee_id,
                    created_by_id,
                    created_at,
                    updated_at
                FROM tickets
                WHERE order_id = :order_id
                ORDER BY created_at DESC
                """
            ),
            {"order_id": order_id},
        ).mappings().all()
    )

    order["total_amount_yuan"] = _amount_yuan(order.get("total_amount_cents"))

    for refund in refunds:
        refund["amount_yuan"] = _amount_yuan(refund.get("amount_cents"))

    return {
        "order_no": order_no,
        "order": order,
        "logistics": logistics,
        "refunds": refunds,
        "tickets": tickets,
        "recommendation": _build_recommendation(order, logistics, refunds, tickets),
    }
