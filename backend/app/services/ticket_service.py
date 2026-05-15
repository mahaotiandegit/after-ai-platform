from __future__ import annotations

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


TOKYO_TZ = ZoneInfo("Asia/Tokyo")


CATEGORY_RULES = [
    {
        "category": "refund_progress",
        "keywords": ["退款", "退钱", "钱没到", "到账", "拒收", "退货"],
        "title": "退款进度咨询",
        "summary_template": "用户咨询退款或退货后的处理进度，需要核实退款状态、退货入库状态和支付原路返回情况。",
        "priority": "high",
    },
    {
        "category": "logistics_delay",
        "keywords": ["物流延迟", "没更新", "三天没更新", "没到", "延迟", "催快递", "派送慢", "运输中"],
        "title": "物流延迟处理",
        "summary_template": "用户反馈物流长时间未更新或派送延迟，需要查询最新物流轨迹并判断是否满足补偿条件。",
        "priority": "high",
    },
    {
        "category": "logistics_exception",
        "keywords": ["地址不完整", "地址异常", "无法派送", "配送失败", "拦截", "改地址"],
        "title": "物流异常处理",
        "summary_template": "用户反馈配送异常，需要核实收货地址、承运商异常原因，并判断是否需要创建升级工单。",
        "priority": "high",
    },
    {
        "category": "product_damage",
        "keywords": ["破损", "坏了", "碎了", "裂了", "包装破", "商品损坏"],
        "title": "商品破损投诉",
        "summary_template": "用户反馈商品破损，需要收集外包装、破损位置和快递面单等凭证，并判断责任归属。",
        "priority": "high",
    },
    {
        "category": "product_quality",
        "keywords": ["质量", "不好用", "描述不一致", "假货", "瑕疵", "少件", "错发", "漏发"],
        "title": "商品质量问题",
        "summary_template": "用户反馈商品质量或履约问题，需要核实商品信息、订单 SKU、出库记录和用户凭证。",
        "priority": "medium",
    },
    {
        "category": "campaign_compensation",
        "keywords": ["活动", "大促", "补偿券", "优惠券", "承诺当天发货", "补偿"],
        "title": "活动补偿咨询",
        "summary_template": "用户咨询活动承诺或补偿规则，需要核实活动条件、订单时间和责任归属。",
        "priority": "medium",
    },
    {
        "category": "invoice",
        "keywords": ["发票", "抬头", "税号", "开票", "红冲"],
        "title": "发票问题处理",
        "summary_template": "用户咨询发票开具或修改问题，需要核实订单状态、发票类型、抬头和是否允许红冲重开。",
        "priority": "medium",
    },
    {
        "category": "service_complaint",
        "keywords": ["投诉客服", "客服太慢", "没人处理", "态度差", "投诉"],
        "title": "客服服务投诉",
        "summary_template": "用户投诉客服服务或处理时效，需要组长复核历史沟通记录和工单处理过程。",
        "priority": "high",
    },
]


DEFAULT_ASSIGNEE_BY_PRIORITY = {
    "high": "11111111-1111-1111-1111-111111111113",
    "medium": "11111111-1111-1111-1111-111111111112",
    "low": "11111111-1111-1111-1111-111111111111",
}


def _generate_ticket_no() -> str:
    now = datetime.now(TOKYO_TZ)
    suffix = uuid.uuid4().hex[:6].upper()
    return f"TICKET-{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"


def _find_order_by_no(db: Session, order_no: str | None) -> dict | None:
    if not order_no:
        return None

    row = db.execute(
        text(
            """
            SELECT id, order_no, status, total_amount_cents
            FROM orders
            WHERE order_no = :order_no
            """
        ),
        {"order_no": order_no},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="order not found")

    return dict(row)


def _classify_question(question: str) -> dict:
    # PHASE_LOGISTICS_DELAY_REFUND_START
    # 组合意图必须放在单一规则之前：
    # 物流/快递/包裹延迟 + 退款/补偿/赔偿 => logistics_delay_refund
    q = question.strip().lower()

    logistics_words = [
        "物流", "快递", "配送", "包裹", "运单",
        "三天没更新", "两天没更新", "没更新", "未更新",
        "延迟", "超时", "未到", "没到", "派送慢"
    ]
    refund_or_compensation_words = [
        "退款", "退钱", "退货退款", "补偿", "赔偿", "赔付", "补偿券"
    ]

    has_logistics_delay = any(word in q for word in logistics_words)
    has_refund_or_compensation = any(word in q for word in refund_or_compensation_words)

    if has_logistics_delay and has_refund_or_compensation:
        return {
            "category": "logistics_delay_refund",
            "priority": "high",
            "title": "物流延迟退款补偿处理",
            "summary": "用户反馈包裹长时间未更新，并咨询退款或补偿，需要同时核实物流异常、订单状态和退款/补偿规则。",
            "reason": "同时命中物流延迟与退款/补偿关键词，归类为 logistics_delay_refund。",
        }
    # PHASE_LOGISTICS_DELAY_REFUND_END
    text_for_match = question.lower()

    for rule in CATEGORY_RULES:
        for keyword in rule["keywords"]:
            if keyword.lower() in text_for_match:
                return {
                    "category": rule["category"],
                    "priority": rule["priority"],
                    "title": rule["title"],
                    "summary": rule["summary_template"],
                    "reason": f"命中关键词“{keyword}”，归类为 {rule['category']}。",
                }

    return {
        "category": "general_aftersale",
        "priority": "low",
        "title": "普通售后咨询",
        "summary": "用户提交普通售后问题，需要客服根据订单状态和知识库规则进一步判断。",
        "reason": "未命中明确规则，按普通售后咨询处理。",
    }


def _adjust_priority_by_order(order: dict | None, result: dict) -> dict:
    if order is None:
        return result

    amount = order["total_amount_cents"]
    status = order["status"]

    if amount >= 30000 and result["priority"] == "medium":
        result = dict(result)
        result["priority"] = "high"
        result["reason"] += " 订单金额较高，优先级提升为 high。"

    if status in {"refunding", "refunded"} and result["category"] in {"refund_progress", "general_aftersale"}:
        result = dict(result)
        result["priority"] = "high"
        result["reason"] += f" 当前订单状态为 {status}，退款相关问题优先处理。"

    return result


def _build_next_action(category: str, priority: str) -> str:
    if priority == "high":
        return "建议优先分配给客服组长或资深客服处理，并在工单列表中置顶关注。"

    if category in {"invoice", "campaign_compensation"}:
        return "建议客服先查询对应知识库规则，再根据规则回复用户。"

    return "建议客服按照标准售后 SOP 处理，并根据处理结果更新工单状态。"


def auto_create_ticket(
    db: Session,
    customer_question: str,
    order_no: str | None,
    created_by_id: uuid.UUID | None,
) -> dict:
    question = customer_question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="customer_question cannot be empty")

    order = _find_order_by_no(db=db, order_no=order_no)
    classification = _classify_question(question)
    classification = _adjust_priority_by_order(order=order, result=classification)

    assignee_id = DEFAULT_ASSIGNEE_BY_PRIORITY.get(classification["priority"])
    ticket_no = _generate_ticket_no()

    row = db.execute(
        text(
            """
            INSERT INTO tickets (
                ticket_no,
                order_id,
                customer_question,
                category,
                priority,
                title,
                summary,
                status,
                assignee_id,
                created_by_id
            )
            VALUES (
                :ticket_no,
                :order_id,
                :customer_question,
                :category,
                :priority,
                :title,
                :summary,
                'open',
                :assignee_id,
                :created_by_id
            )
            RETURNING
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
            """
        ),
        {
            "ticket_no": ticket_no,
            "order_id": order["id"] if order else None,
            "customer_question": question,
            "category": classification["category"],
            "priority": classification["priority"],
            "title": classification["title"],
            "summary": classification["summary"],
            "assignee_id": assignee_id,
            "created_by_id": str(created_by_id) if created_by_id else None,
        },
    ).mappings().first()

    db.commit()

    ticket = dict(row)

    return {
        "ticket": ticket,
        "classification_reason": classification["reason"],
        "next_action": _build_next_action(
            category=classification["category"],
            priority=classification["priority"],
        ),
    }


def list_tickets(
    db: Session,
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    where_clauses = []
    params = {
        "limit": limit,
        "offset": offset,
    }

    if status:
        where_clauses.append("status = :status")
        params["status"] = status

    if category:
        where_clauses.append("category = :category")
        params["category"] = category

    if priority:
        where_clauses.append("priority = :priority")
        params["priority"] = priority

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM tickets
        {where_sql}
    """

    list_sql = f"""
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
        {where_sql}
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                ELSE 3
            END,
            created_at DESC
        LIMIT :limit OFFSET :offset
    """

    total = db.execute(text(count_sql), params).scalar_one()
    rows = db.execute(text(list_sql), params).mappings().all()

    return {
        "total": int(total),
        "items": [dict(row) for row in rows],
    }


def get_ticket_by_no(db: Session, ticket_no: str) -> dict:
    row = db.execute(
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
            WHERE ticket_no = :ticket_no
            """
        ),
        {"ticket_no": ticket_no},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    return dict(row)

def _ticket_row_to_dict(row) -> dict:
    return dict(row)


def update_ticket_status(
    db: Session,
    ticket_no: str,
    new_status: str,
    operator_id: uuid.UUID | None = None,
    note: str | None = None,
) -> dict:
    current = db.execute(
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
            WHERE ticket_no = :ticket_no
            """
        ),
        {"ticket_no": ticket_no},
    ).mappings().first()

    if current is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    current_status = current["status"]

    allowed_transitions = {
        "open": {"processing", "closed"},
        "processing": {"resolved", "closed", "open"},
        "resolved": {"closed", "processing"},
        "closed": set(),
    }

    if new_status == current_status:
        return {
            "ticket": dict(current),
            "action": "status_unchanged",
            "message": f"工单已经是 {new_status} 状态，无需重复更新。",
        }

    if new_status not in allowed_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"invalid status transition: {current_status} -> {new_status}",
        )

    updated = db.execute(
        text(
            """
            UPDATE tickets
            SET status = :new_status,
                updated_at = NOW()
            WHERE ticket_no = :ticket_no
            RETURNING
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
            """
        ),
        {
            "ticket_no": ticket_no,
            "new_status": new_status,
        },
    ).mappings().first()

    db.commit()

    message = f"工单状态已从 {current_status} 更新为 {new_status}。"
    if note:
        message += f" 备注：{note}"

    return {
        "ticket": dict(updated),
        "action": "status_updated",
        "message": message,
    }


def escalate_ticket(
    db: Session,
    ticket_no: str,
    assignee_id: uuid.UUID | None,
    reason: str,
) -> dict:
    target_assignee_id = assignee_id or uuid.UUID("11111111-1111-1111-1111-111111111113")

    current = db.execute(
        text(
            """
            SELECT ticket_no, priority, status
            FROM tickets
            WHERE ticket_no = :ticket_no
            """
        ),
        {"ticket_no": ticket_no},
    ).mappings().first()

    if current is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    if current["status"] == "closed":
        raise HTTPException(status_code=400, detail="closed ticket cannot be escalated")

    updated = db.execute(
        text(
            """
            UPDATE tickets
            SET priority = 'high',
                assignee_id = :assignee_id,
                updated_at = NOW()
            WHERE ticket_no = :ticket_no
            RETURNING
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
            """
        ),
        {
            "ticket_no": ticket_no,
            "assignee_id": str(target_assignee_id),
        },
    ).mappings().first()

    db.commit()

    return {
        "ticket": dict(updated),
        "action": "ticket_escalated",
        "message": f"工单已升级为 high 优先级，并分配给组长/高级客服。升级原因：{reason}",
    }