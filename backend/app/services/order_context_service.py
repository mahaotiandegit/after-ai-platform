from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

def _build_recommendation(
        logistics:list[dict],
        refunds:list[dict],
        tickets: list[dict],
)->dict:
    has_delayed_logistics =any(item["status"]=="delayed" for item in logistics)
    has_exception_logistics = any(item["status"] == "exception" for item in logistics)
    has_returned_logistics = any(item["status"] == "returned" for item in logistics)

    has_pending_refund = any(item["status"] == "pending" for item in refunds)
    has_processing_refund = any(item["status"] == "processing" for item in refunds)

    has_high_ticket = any(item["priority"] == "high" for item in tickets)
    has_open_ticket = any(item["status"] == "open" for item in tickets)

    if has_delayed_logistics and has_pending_refund:
        return {
            "issue_type": "logistics_delay_refund",
            "priority": "high",
            "suggested_action": "建议客服优先核实物流轨迹。若延迟属实，可进入补偿或退款审核流程。",
            "reason": "当前订单存在物流延迟，同时已有待处理退款申请，存在投诉升级风险。",
        }

    if has_exception_logistics:
        return {
            "issue_type": "logistics_exception",
            "priority": "high",
            "suggested_action": "建议客服立即核实收货地址和承运商异常原因，必要时创建物流异常升级工单。",
            "reason": "当前订单物流状态异常，可能导致无法正常派送。",
        }

    if has_returned_logistics and has_processing_refund:
        return {
            "issue_type": "return_refund_progress",
            "priority": "high",
            "suggested_action": "建议客服确认退货是否已入库，并同步退款审核进度。",
            "reason": "当前订单已退回，且退款正在处理中，用户通常会关注到账时间。",
        }

    if has_delayed_logistics:
        return {
            "issue_type": "logistics_delay",
            "priority": "medium",
            "suggested_action": "建议客服先安抚用户，并同步最新物流状态；若超过承诺时效，再判断是否补偿。",
            "reason": "当前订单物流延迟，但暂未发现待处理退款申请。",
        }

    if has_high_ticket and has_open_ticket:
        return {
            "issue_type": "high_priority_ticket",
            "priority": "high",
            "suggested_action": "建议客服组长介入复核，优先处理高优先级未关闭工单。",
            "reason": "当前订单存在高优先级未关闭工单，可能影响用户满意度。",
        }

    return {
        "issue_type": "normal_aftersale",
        "priority": "low",
        "suggested_action": "建议客服按照标准售后 SOP 处理。",
        "reason": "当前订单未发现明显物流、退款或高优先级投诉风险。",
    }


def get_order_aftersale_context(db: Session, order_no: str) -> dict:
    order = db.execute(
        text(
            """
            SELECT id, order_no, customer_name, customer_phone, status,
                   total_amount_cents, created_at, updated_at
            FROM orders
            WHERE order_no = :order_no
            """
        ),
        {"order_no": order_no},
    ).mappings().first()

    if order is None:
        raise HTTPException(status_code=404, detail="order not found")

    order_dict = dict(order)

    logistics = [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT id, order_id, carrier, tracking_no, status, latest_event,
                       shipped_at, delivered_at, created_at
                FROM logistics
                WHERE order_id = :order_id
                ORDER BY created_at DESC
                """
            ),
            {"order_id": order_dict["id"]},
        ).mappings().all()
    ]

    refunds = [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT id, order_id, refund_no, reason, amount_cents, status,
                       created_at, updated_at
                FROM refunds
                WHERE order_id = :order_id
                ORDER BY created_at DESC
                """
            ),
            {"order_id": order_dict["id"]},
        ).mappings().all()
    ]

    tickets = [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT id, ticket_no, order_id, customer_question, category,
                       priority, title, summary, status, assignee_id,
                       created_by_id, created_at, updated_at
                FROM tickets
                WHERE order_id = :order_id
                ORDER BY created_at DESC
                """
            ),
            {"order_id": order_dict["id"]},
        ).mappings().all()
    ]

    return {
        "order": order_dict,
        "logistics": logistics,
        "refunds": refunds,
        "tickets": tickets,
        "recommendation": _build_recommendation(
            logistics=logistics,
            refunds=refunds,
            tickets=tickets,
        ),
    }