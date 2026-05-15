from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.db.session import engine  # noqa: E402


USERS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "username": "agent01",
        "email": "agent01@example.com",
        "password_hash": "demo-password-hash",
        "role": "agent",
    },
    {
        "id": "11111111-1111-1111-1111-111111111112",
        "username": "agent02",
        "email": "agent02@example.com",
        "password_hash": "demo-password-hash",
        "role": "agent",
    },
    {
        "id": "11111111-1111-1111-1111-111111111113",
        "username": "leader01",
        "email": "leader01@example.com",
        "password_hash": "demo-password-hash",
        "role": "leader",
    },
    {
        "id": "11111111-1111-1111-1111-111111111114",
        "username": "ops01",
        "email": "ops01@example.com",
        "password_hash": "demo-password-hash",
        "role": "operator",
    },
    {
        "id": "11111111-1111-1111-1111-111111111115",
        "username": "admin01",
        "email": "admin01@example.com",
        "password_hash": "demo-password-hash",
        "role": "admin",
    },
]


ORDERS = [
    {
        "id": "22222222-2222-2222-2222-222222222201",
        "order_no": "ORDER-20260515-0001",
        "customer_name": "张三",
        "customer_phone": "13800000001",
        "status": "paid",
        "total_amount_cents": 19900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222202",
        "order_no": "ORDER-20260515-0002",
        "customer_name": "李四",
        "customer_phone": "13800000002",
        "status": "shipped",
        "total_amount_cents": 32900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222203",
        "order_no": "ORDER-20260515-0003",
        "customer_name": "王五",
        "customer_phone": "13800000003",
        "status": "delivered",
        "total_amount_cents": 9900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222204",
        "order_no": "ORDER-20260515-0004",
        "customer_name": "赵六",
        "customer_phone": "13800000004",
        "status": "paid",
        "total_amount_cents": 45900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222205",
        "order_no": "ORDER-20260515-0005",
        "customer_name": "孙七",
        "customer_phone": "13800000005",
        "status": "refunding",
        "total_amount_cents": 15900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222206",
        "order_no": "ORDER-20260515-0006",
        "customer_name": "周八",
        "customer_phone": "13800000006",
        "status": "delivered",
        "total_amount_cents": 25900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222207",
        "order_no": "ORDER-20260515-0007",
        "customer_name": "吴九",
        "customer_phone": "13800000007",
        "status": "cancelled",
        "total_amount_cents": 8900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222208",
        "order_no": "ORDER-20260515-0008",
        "customer_name": "郑十",
        "customer_phone": "13800000008",
        "status": "paid",
        "total_amount_cents": 69900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222209",
        "order_no": "ORDER-20260515-0009",
        "customer_name": "陈一",
        "customer_phone": "13800000009",
        "status": "shipped",
        "total_amount_cents": 12900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222210",
        "order_no": "ORDER-20260515-0010",
        "customer_name": "刘二",
        "customer_phone": "13800000010",
        "status": "delivered",
        "total_amount_cents": 21900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222211",
        "order_no": "ORDER-20260515-0011",
        "customer_name": "林三",
        "customer_phone": "13800000011",
        "status": "refunded",
        "total_amount_cents": 39900,
    },
    {
        "id": "22222222-2222-2222-2222-222222222212",
        "order_no": "ORDER-20260515-0012",
        "customer_name": "黄四",
        "customer_phone": "13800000012",
        "status": "paid",
        "total_amount_cents": 5600,
    },
]


LOGISTICS = [
    {
        "id": "33333333-3333-3333-3333-333333333301",
        "order_id": "22222222-2222-2222-2222-222222222201",
        "carrier": "SF Express",
        "tracking_no": "SF1234567801",
        "status": "delayed",
        "latest_event": "包裹已到达东京中转仓，预计延迟 1-2 天派送",
    },
    {
        "id": "33333333-3333-3333-3333-333333333302",
        "order_id": "22222222-2222-2222-2222-222222222202",
        "carrier": "Yamato",
        "tracking_no": "YA1234567802",
        "status": "in_transit",
        "latest_event": "包裹已离开发货仓，正在运输中",
    },
    {
        "id": "33333333-3333-3333-3333-333333333303",
        "order_id": "22222222-2222-2222-2222-222222222203",
        "carrier": "Japan Post",
        "tracking_no": "JP1234567803",
        "status": "delivered",
        "latest_event": "包裹已签收",
    },
    {
        "id": "33333333-3333-3333-3333-333333333304",
        "order_id": "22222222-2222-2222-2222-222222222204",
        "carrier": "SF Express",
        "tracking_no": "SF1234567804",
        "status": "exception",
        "latest_event": "收件地址疑似不完整，等待客服确认",
    },
    {
        "id": "33333333-3333-3333-3333-333333333305",
        "order_id": "22222222-2222-2222-2222-222222222205",
        "carrier": "Yamato",
        "tracking_no": "YA1234567805",
        "status": "returned",
        "latest_event": "用户拒收，包裹已退回仓库",
    },
    {
        "id": "33333333-3333-3333-3333-333333333306",
        "order_id": "22222222-2222-2222-2222-222222222206",
        "carrier": "Japan Post",
        "tracking_no": "JP1234567806",
        "status": "delivered",
        "latest_event": "包裹已签收，用户反馈商品破损",
    },
    {
        "id": "33333333-3333-3333-3333-333333333307",
        "order_id": "22222222-2222-2222-2222-222222222207",
        "carrier": "SF Express",
        "tracking_no": "SF1234567807",
        "status": "cancelled",
        "latest_event": "订单取消，物流未发出",
    },
    {
        "id": "33333333-3333-3333-3333-333333333308",
        "order_id": "22222222-2222-2222-2222-222222222208",
        "carrier": "Yamato",
        "tracking_no": "YA1234567808",
        "status": "delayed",
        "latest_event": "大促期间仓库爆仓，预计延迟 2 天",
    },
    {
        "id": "33333333-3333-3333-3333-333333333309",
        "order_id": "22222222-2222-2222-2222-222222222209",
        "carrier": "Japan Post",
        "tracking_no": "JP1234567809",
        "status": "in_transit",
        "latest_event": "包裹正在派送站分拣",
    },
    {
        "id": "33333333-3333-3333-3333-333333333310",
        "order_id": "22222222-2222-2222-2222-222222222210",
        "carrier": "SF Express",
        "tracking_no": "SF1234567810",
        "status": "delivered",
        "latest_event": "包裹已签收",
    },
    {
        "id": "33333333-3333-3333-3333-333333333311",
        "order_id": "22222222-2222-2222-2222-222222222211",
        "carrier": "Yamato",
        "tracking_no": "YA1234567811",
        "status": "returned",
        "latest_event": "退货已入库，等待退款完成",
    },
    {
        "id": "33333333-3333-3333-3333-333333333312",
        "order_id": "22222222-2222-2222-2222-222222222212",
        "carrier": "Japan Post",
        "tracking_no": "JP1234567812",
        "status": "in_transit",
        "latest_event": "包裹已揽收",
    },
]


REFUNDS = [
    {
        "id": "44444444-4444-4444-4444-444444444401",
        "order_id": "22222222-2222-2222-2222-222222222201",
        "refund_no": "REFUND-20260515-0001",
        "reason": "物流延迟申请补偿",
        "amount_cents": 3000,
        "status": "pending",
    },
    {
        "id": "44444444-4444-4444-4444-444444444402",
        "order_id": "22222222-2222-2222-2222-222222222205",
        "refund_no": "REFUND-20260515-0002",
        "reason": "用户拒收后申请退款",
        "amount_cents": 15900,
        "status": "processing",
    },
    {
        "id": "44444444-4444-4444-4444-444444444403",
        "order_id": "22222222-2222-2222-2222-222222222206",
        "refund_no": "REFUND-20260515-0003",
        "reason": "商品破损申请部分退款",
        "amount_cents": 5000,
        "status": "pending",
    },
    {
        "id": "44444444-4444-4444-4444-444444444404",
        "order_id": "22222222-2222-2222-2222-222222222207",
        "refund_no": "REFUND-20260515-0004",
        "reason": "订单取消自动退款",
        "amount_cents": 8900,
        "status": "succeeded",
    },
    {
        "id": "44444444-4444-4444-4444-444444444405",
        "order_id": "22222222-2222-2222-2222-222222222208",
        "refund_no": "REFUND-20260515-0005",
        "reason": "大促承诺时效未达成",
        "amount_cents": 6000,
        "status": "pending",
    },
    {
        "id": "44444444-4444-4444-4444-444444444406",
        "order_id": "22222222-2222-2222-2222-222222222210",
        "refund_no": "REFUND-20260515-0006",
        "reason": "发票信息错误补偿",
        "amount_cents": 1000,
        "status": "rejected",
    },
    {
        "id": "44444444-4444-4444-4444-444444444407",
        "order_id": "22222222-2222-2222-2222-222222222211",
        "refund_no": "REFUND-20260515-0007",
        "reason": "退货入库后整单退款",
        "amount_cents": 39900,
        "status": "succeeded",
    },
    {
        "id": "44444444-4444-4444-4444-444444444408",
        "order_id": "22222222-2222-2222-2222-222222222204",
        "refund_no": "REFUND-20260515-0008",
        "reason": "地址异常导致配送失败补偿",
        "amount_cents": 2000,
        "status": "pending",
    },
]


TICKETS = [
    {
        "id": "55555555-5555-5555-5555-555555555501",
        "ticket_no": "TICKET-20260515-0001",
        "order_id": "22222222-2222-2222-2222-222222222201",
        "customer_question": "我的包裹已经三天没更新了，能不能退款或者补偿？",
        "category": "logistics_delay",
        "priority": "high",
        "title": "物流延迟补偿咨询",
        "summary": "用户反馈包裹三天未更新，希望确认物流状态并申请补偿。",
        "status": "open",
        "assignee_id": "11111111-1111-1111-1111-111111111111",
        "created_by_id": "11111111-1111-1111-1111-111111111111",
    },
    {
        "id": "55555555-5555-5555-5555-555555555502",
        "ticket_no": "TICKET-20260515-0002",
        "order_id": "22222222-2222-2222-2222-222222222202",
        "customer_question": "物流显示运输中，但我想改地址。",
        "category": "address_change",
        "priority": "medium",
        "title": "运输中订单改地址",
        "summary": "用户希望修改收货地址，需要确认物流节点是否支持拦截。",
        "status": "open",
        "assignee_id": "11111111-1111-1111-1111-111111111112",
        "created_by_id": "11111111-1111-1111-1111-111111111112",
    },
    {
        "id": "55555555-5555-5555-5555-555555555503",
        "ticket_no": "TICKET-20260515-0003",
        "order_id": "22222222-2222-2222-2222-222222222203",
        "customer_question": "商品已经收到，但感觉和页面描述不一致。",
        "category": "product_quality",
        "priority": "medium",
        "title": "商品描述不一致投诉",
        "summary": "用户反馈商品与页面描述不一致，需要售后核实商品信息。",
        "status": "processing",
        "assignee_id": "11111111-1111-1111-1111-111111111111",
        "created_by_id": "11111111-1111-1111-1111-111111111111",
    },
    {
        "id": "55555555-5555-5555-5555-555555555504",
        "ticket_no": "TICKET-20260515-0004",
        "order_id": "22222222-2222-2222-2222-222222222204",
        "customer_question": "快递说地址不完整，但我下单时填的是完整地址。",
        "category": "logistics_exception",
        "priority": "high",
        "title": "地址异常导致配送失败",
        "summary": "物流提示地址异常，需要客服核实订单地址并联系承运商。",
        "status": "open",
        "assignee_id": "11111111-1111-1111-1111-111111111113",
        "created_by_id": "11111111-1111-1111-1111-111111111112",
    },
    {
        "id": "55555555-5555-5555-5555-555555555505",
        "ticket_no": "TICKET-20260515-0005",
        "order_id": "22222222-2222-2222-2222-222222222205",
        "customer_question": "我已经拒收了，什么时候退款？",
        "category": "refund_progress",
        "priority": "high",
        "title": "拒收后退款进度咨询",
        "summary": "用户已拒收包裹，咨询退款到账时间。",
        "status": "processing",
        "assignee_id": "11111111-1111-1111-1111-111111111111",
        "created_by_id": "11111111-1111-1111-1111-111111111111",
    },
    {
        "id": "55555555-5555-5555-5555-555555555506",
        "ticket_no": "TICKET-20260515-0006",
        "order_id": "22222222-2222-2222-2222-222222222206",
        "customer_question": "商品收到是破的，我要赔偿。",
        "category": "product_damage",
        "priority": "high",
        "title": "商品破损赔偿申请",
        "summary": "用户反馈商品破损，需要上传凭证并进入补偿审核。",
        "status": "open",
        "assignee_id": "11111111-1111-1111-1111-111111111112",
        "created_by_id": "11111111-1111-1111-1111-111111111112",
    },
    {
        "id": "55555555-5555-5555-5555-555555555507",
        "ticket_no": "TICKET-20260515-0007",
        "order_id": "22222222-2222-2222-2222-222222222207",
        "customer_question": "我取消订单了，钱还没回来。",
        "category": "refund_progress",
        "priority": "medium",
        "title": "取消订单退款到账咨询",
        "summary": "用户咨询取消订单后退款到账时间。",
        "status": "closed",
        "assignee_id": "11111111-1111-1111-1111-111111111111",
        "created_by_id": "11111111-1111-1111-1111-111111111111",
    },
    {
        "id": "55555555-5555-5555-5555-555555555508",
        "ticket_no": "TICKET-20260515-0008",
        "order_id": "22222222-2222-2222-2222-222222222208",
        "customer_question": "大促说当天发货，为什么现在还没到？",
        "category": "campaign_compensation",
        "priority": "high",
        "title": "大促时效未达成补偿",
        "summary": "用户因大促承诺时效未达成申请补偿。",
        "status": "open",
        "assignee_id": "11111111-1111-1111-1111-111111111113",
        "created_by_id": "11111111-1111-1111-1111-111111111112",
    },
    {
        "id": "55555555-5555-5555-5555-555555555509",
        "ticket_no": "TICKET-20260515-0009",
        "order_id": "22222222-2222-2222-2222-222222222209",
        "customer_question": "发票怎么开？",
        "category": "invoice",
        "priority": "low",
        "title": "发票开具咨询",
        "summary": "用户咨询发票开具流程。",
        "status": "open",
        "assignee_id": "11111111-1111-1111-1111-111111111112",
        "created_by_id": "11111111-1111-1111-1111-111111111112",
    },
    {
        "id": "55555555-5555-5555-5555-555555555510",
        "ticket_no": "TICKET-20260515-0010",
        "order_id": "22222222-2222-2222-2222-222222222210",
        "customer_question": "发票抬头写错了，能重新开吗？",
        "category": "invoice",
        "priority": "medium",
        "title": "发票抬头修改",
        "summary": "用户申请修改发票抬头，需要判断是否已开票。",
        "status": "processing",
        "assignee_id": "11111111-1111-1111-1111-111111111111",
        "created_by_id": "11111111-1111-1111-1111-111111111111",
    },
    {
        "id": "55555555-5555-5555-5555-555555555511",
        "ticket_no": "TICKET-20260515-0011",
        "order_id": "22222222-2222-2222-2222-222222222211",
        "customer_question": "退货已经到了仓库，为什么还没退款？",
        "category": "refund_progress",
        "priority": "high",
        "title": "退货入库后退款延迟",
        "summary": "用户反馈退货已入库但退款未到账，需要核实退款状态。",
        "status": "closed",
        "assignee_id": "11111111-1111-1111-1111-111111111113",
        "created_by_id": "11111111-1111-1111-1111-111111111112",
    },
    {
        "id": "55555555-5555-5555-5555-555555555512",
        "ticket_no": "TICKET-20260515-0012",
        "order_id": "22222222-2222-2222-2222-222222222212",
        "customer_question": "能不能催一下快递？",
        "category": "logistics_followup",
        "priority": "low",
        "title": "普通物流催促",
        "summary": "用户希望客服协助催促物流。",
        "status": "open",
        "assignee_id": "11111111-1111-1111-1111-111111111111",
        "created_by_id": "11111111-1111-1111-1111-111111111111",
    },
    {
        "id": "55555555-5555-5555-5555-555555555513",
        "ticket_no": "TICKET-20260515-0013",
        "order_id": None,
        "customer_question": "活动补偿券什么时候发？",
        "category": "campaign_compensation",
        "priority": "medium",
        "title": "活动补偿券发放咨询",
        "summary": "用户咨询活动补偿券发放时间，暂未提供订单号。",
        "status": "open",
        "assignee_id": "11111111-1111-1111-1111-111111111112",
        "created_by_id": "11111111-1111-1111-1111-111111111112",
    },
    {
        "id": "55555555-5555-5555-5555-555555555514",
        "ticket_no": "TICKET-20260515-0014",
        "order_id": None,
        "customer_question": "我想投诉客服处理太慢。",
        "category": "service_complaint",
        "priority": "high",
        "title": "客服处理时效投诉",
        "summary": "用户投诉客服响应慢，需要组长复核处理记录。",
        "status": "open",
        "assignee_id": "11111111-1111-1111-1111-111111111113",
        "created_by_id": "11111111-1111-1111-1111-111111111112",
    },
]


DOCUMENTS = [
    {
        "id": "66666666-6666-6666-6666-666666666601",
        "title": "售后退款规则 SOP",
        "file_name": "refund_sop.md",
        "file_type": "markdown",
        "storage_path": "/demo/docs/refund_sop.md",
        "status": "indexed",
        "uploaded_by_id": "11111111-1111-1111-1111-111111111114",
    },
    {
        "id": "66666666-6666-6666-6666-666666666602",
        "title": "物流异常处理规范",
        "file_name": "logistics_exception_policy.pdf",
        "file_type": "pdf",
        "storage_path": "/demo/docs/logistics_exception_policy.pdf",
        "status": "indexed",
        "uploaded_by_id": "11111111-1111-1111-1111-111111111114",
    },
    {
        "id": "66666666-6666-6666-6666-666666666603",
        "title": "大促活动补偿标准",
        "file_name": "campaign_compensation.xlsx",
        "file_type": "excel",
        "storage_path": "/demo/docs/campaign_compensation.xlsx",
        "status": "indexed",
        "uploaded_by_id": "11111111-1111-1111-1111-111111111114",
    },
    {
        "id": "66666666-6666-6666-6666-666666666604",
        "title": "商品质量投诉处理手册",
        "file_name": "product_quality_manual.pdf",
        "file_type": "pdf",
        "storage_path": "/demo/docs/product_quality_manual.pdf",
        "status": "indexed",
        "uploaded_by_id": "11111111-1111-1111-1111-111111111114",
    },
    {
        "id": "66666666-6666-6666-6666-666666666605",
        "title": "发票与开票问题处理规范",
        "file_name": "invoice_policy.md",
        "file_type": "markdown",
        "storage_path": "/demo/docs/invoice_policy.md",
        "status": "indexed",
        "uploaded_by_id": "11111111-1111-1111-1111-111111111114",
    },
]


DOCUMENT_CHUNKS = [
    {
        "id": "77777777-7777-7777-7777-777777777701",
        "document_id": "66666666-6666-6666-6666-666666666601",
        "chunk_index": 1,
        "content": "用户申请退款时，客服必须先确认订单状态、支付状态、物流状态和是否已签收。未发货订单可优先走取消退款流程。",
        "page_no": 1,
        "token_count": 52,
        "metadata": {"section": "退款前置校验", "policy_code": "REFUND-SOP-001"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777702",
        "document_id": "66666666-6666-6666-6666-666666666601",
        "chunk_index": 2,
        "content": "已签收订单申请退款时，需要区分七天无理由、商品质量问题、错发漏发和用户主观不满意。不同原因对应不同审核材料。",
        "page_no": 2,
        "token_count": 58,
        "metadata": {"section": "退款原因分类", "policy_code": "REFUND-SOP-002"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777703",
        "document_id": "66666666-6666-6666-6666-666666666601",
        "chunk_index": 3,
        "content": "退款金额不得超过订单实付金额。存在优惠券、积分、平台补贴时，应按照实付金额和活动规则计算可退金额。",
        "page_no": 3,
        "token_count": 49,
        "metadata": {"section": "退款金额计算", "policy_code": "REFUND-SOP-003"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777704",
        "document_id": "66666666-6666-6666-6666-666666666602",
        "chunk_index": 1,
        "content": "物流超过承诺时效 48 小时未更新时，客服应先查询最新轨迹，确认是否存在揽收异常、中转异常、派送异常或地址异常。",
        "page_no": 1,
        "token_count": 60,
        "metadata": {"section": "物流延迟判断", "policy_code": "LOGISTICS-001"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777705",
        "document_id": "66666666-6666-6666-6666-666666666602",
        "chunk_index": 2,
        "content": "物流延迟属实时，客服可以先安抚用户，并根据订单金额、延迟天数和用户等级判断是否发放补偿券。",
        "page_no": 2,
        "token_count": 51,
        "metadata": {"section": "物流延迟补偿", "policy_code": "LOGISTICS-002"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777706",
        "document_id": "66666666-6666-6666-6666-666666666602",
        "chunk_index": 3,
        "content": "地址异常订单需要客服联系用户确认地址。若承运商支持拦截改址，应优先改址；若不支持，应创建物流异常工单。",
        "page_no": 3,
        "token_count": 56,
        "metadata": {"section": "地址异常处理", "policy_code": "LOGISTICS-003"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777707",
        "document_id": "66666666-6666-6666-6666-666666666603",
        "chunk_index": 1,
        "content": "大促期间承诺当天发货但实际未发货的订单，可根据活动规则发放 5 元至 20 元补偿券。",
        "page_no": 1,
        "token_count": 44,
        "metadata": {"section": "大促发货承诺", "policy_code": "CAMPAIGN-001"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777708",
        "document_id": "66666666-6666-6666-6666-666666666603",
        "chunk_index": 2,
        "content": "大促物流延迟补偿需要排除不可抗力、用户地址错误、用户主动改约派送等非平台责任场景。",
        "page_no": 2,
        "token_count": 43,
        "metadata": {"section": "补偿排除条件", "policy_code": "CAMPAIGN-002"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777709",
        "document_id": "66666666-6666-6666-6666-666666666603",
        "chunk_index": 3,
        "content": "补偿券发放后应在工单中记录补偿金额、发放原因、审批人和用户反馈，便于后续复盘。",
        "page_no": 3,
        "token_count": 41,
        "metadata": {"section": "补偿记录", "policy_code": "CAMPAIGN-003"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777710",
        "document_id": "66666666-6666-6666-6666-666666666604",
        "chunk_index": 1,
        "content": "商品破损投诉必须要求用户上传外包装、商品破损位置和快递面单照片，用于判断是运输破损还是商品本身质量问题。",
        "page_no": 1,
        "token_count": 57,
        "metadata": {"section": "破损凭证要求", "policy_code": "QUALITY-001"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777711",
        "document_id": "66666666-6666-6666-6666-666666666604",
        "chunk_index": 2,
        "content": "若商品存在明显质量问题，客服可创建质量投诉工单，并根据商品金额判断是否需要组长复核。",
        "page_no": 2,
        "token_count": 45,
        "metadata": {"section": "质量投诉升级", "policy_code": "QUALITY-002"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777712",
        "document_id": "66666666-6666-6666-6666-666666666604",
        "chunk_index": 3,
        "content": "错发、漏发问题应优先核对仓库出库记录和订单 SKU。确认属实后，可安排补发或退款。",
        "page_no": 3,
        "token_count": 43,
        "metadata": {"section": "错发漏发处理", "policy_code": "QUALITY-003"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777713",
        "document_id": "66666666-6666-6666-6666-666666666605",
        "chunk_index": 1,
        "content": "用户申请开票时，客服需要确认订单是否已完成、发票类型、发票抬头、税号和接收邮箱。",
        "page_no": 1,
        "token_count": 43,
        "metadata": {"section": "开票信息校验", "policy_code": "INVOICE-001"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777714",
        "document_id": "66666666-6666-6666-6666-666666666605",
        "chunk_index": 2,
        "content": "发票已开具后，若用户要求修改抬头，应先判断是否允许红冲重开，并记录修改原因。",
        "page_no": 2,
        "token_count": 39,
        "metadata": {"section": "发票修改", "policy_code": "INVOICE-002"},
    },
    {
        "id": "77777777-7777-7777-7777-777777777715",
        "document_id": "66666666-6666-6666-6666-666666666605",
        "chunk_index": 3,
        "content": "发票问题不建议直接承诺现金补偿，除非存在平台明确责任且经过组长审批。",
        "page_no": 3,
        "token_count": 34,
        "metadata": {"section": "发票问题补偿限制", "policy_code": "INVOICE-003"},
    },
]


QA_LOGS = [
    {
        "id": "88888888-8888-8888-8888-888888888801",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "question": "物流超过 48 小时没更新可以补偿吗？",
        "answer": "可以先核实物流轨迹，若确认超过承诺时效且属于平台或物流责任，可根据订单金额和延迟天数判断是否发放补偿券。",
        "citations": [
            {"document": "物流异常处理规范", "page_no": 2, "policy_code": "LOGISTICS-002"}
        ],
        "latency_ms": 820,
    },
    {
        "id": "88888888-8888-8888-8888-888888888802",
        "user_id": "11111111-1111-1111-1111-111111111112",
        "question": "用户拒收后什么时候退款？",
        "answer": "需要确认包裹是否退回入库。退货入库后进入退款审核流程，若状态正常可提示用户等待原路退回。",
        "citations": [
            {"document": "售后退款规则 SOP", "page_no": 1, "policy_code": "REFUND-SOP-001"}
        ],
        "latency_ms": 940,
    },
    {
        "id": "88888888-8888-8888-8888-888888888803",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "question": "商品破损需要用户提供什么材料？",
        "answer": "需要用户提供外包装、破损位置和快递面单照片，用于判断责任归属。",
        "citations": [
            {"document": "商品质量投诉处理手册", "page_no": 1, "policy_code": "QUALITY-001"}
        ],
        "latency_ms": 760,
    },
    {
        "id": "88888888-8888-8888-8888-888888888804",
        "user_id": "11111111-1111-1111-1111-111111111113",
        "question": "大促发货延迟怎么补偿？",
        "answer": "可根据活动规则发放 5 元至 20 元补偿券，但需要排除不可抗力、用户地址错误等非平台责任场景。",
        "citations": [
            {"document": "大促活动补偿标准", "page_no": 1, "policy_code": "CAMPAIGN-001"},
            {"document": "大促活动补偿标准", "page_no": 2, "policy_code": "CAMPAIGN-002"},
        ],
        "latency_ms": 1120,
    },
    {
        "id": "88888888-8888-8888-8888-888888888805",
        "user_id": "11111111-1111-1111-1111-111111111112",
        "question": "发票抬头错了能改吗？",
        "answer": "需要先确认是否已经开票。已开票场景下需要判断是否允许红冲重开，并记录修改原因。",
        "citations": [
            {"document": "发票与开票问题处理规范", "page_no": 2, "policy_code": "INVOICE-002"}
        ],
        "latency_ms": 690,
    },
    {
        "id": "88888888-8888-8888-8888-888888888806",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "question": "退款金额能超过订单实付吗？",
        "answer": "不能。退款金额不得超过订单实付金额，涉及优惠券、积分、平台补贴时需要按实付和活动规则计算。",
        "citations": [
            {"document": "售后退款规则 SOP", "page_no": 3, "policy_code": "REFUND-SOP-003"}
        ],
        "latency_ms": 710,
    },
]


FEEDBACKS = [
    {
        "id": "99999999-9999-9999-9999-999999999901",
        "qa_log_id": "88888888-8888-8888-8888-888888888801",
        "ticket_id": "55555555-5555-5555-5555-555555555501",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "rating": 5,
        "comment": "回答准确，引用规则清楚。",
        "status": "resolved",
    },
    {
        "id": "99999999-9999-9999-9999-999999999902",
        "qa_log_id": "88888888-8888-8888-8888-888888888802",
        "ticket_id": "55555555-5555-5555-5555-555555555505",
        "user_id": "11111111-1111-1111-1111-111111111112",
        "rating": 4,
        "comment": "退款流程解释清楚，但缺少预计到账时间。",
        "status": "reviewed",
    },
    {
        "id": "99999999-9999-9999-9999-999999999903",
        "qa_log_id": "88888888-8888-8888-8888-888888888803",
        "ticket_id": "55555555-5555-5555-5555-555555555506",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "rating": 5,
        "comment": "材料要求完整。",
        "status": "resolved",
    },
    {
        "id": "99999999-9999-9999-9999-999999999904",
        "qa_log_id": "88888888-8888-8888-8888-888888888804",
        "ticket_id": "55555555-5555-5555-5555-555555555508",
        "user_id": "11111111-1111-1111-1111-111111111113",
        "rating": 3,
        "comment": "补偿标准给了，但需要更明确的金额判断规则。",
        "status": "new",
    },
    {
        "id": "99999999-9999-9999-9999-999999999905",
        "qa_log_id": "88888888-8888-8888-8888-888888888805",
        "ticket_id": "55555555-5555-5555-5555-555555555510",
        "user_id": "11111111-1111-1111-1111-111111111112",
        "rating": 4,
        "comment": "能解决问题，但可以补充红冲流程。",
        "status": "reviewed",
    },
]


def execute_many(conn, sql: str, rows: list[dict]) -> None:
    stmt = text(sql)
    for row in rows:
        conn.execute(stmt, row)


def seed_users(conn) -> None:
    execute_many(
        conn,
        """
        INSERT INTO users (id, username, email, password_hash, role, is_active)
        VALUES (:id, :username, :email, :password_hash, :role, true)
        ON CONFLICT (id) DO NOTHING
        """,
        USERS,
    )


def seed_orders(conn) -> None:
    execute_many(
        conn,
        """
        INSERT INTO orders (id, order_no, customer_name, customer_phone, status, total_amount_cents)
        VALUES (:id, :order_no, :customer_name, :customer_phone, :status, :total_amount_cents)
        ON CONFLICT (id) DO NOTHING
        """,
        ORDERS,
    )


def seed_logistics(conn) -> None:
    execute_many(
        conn,
        """
        INSERT INTO logistics (id, order_id, carrier, tracking_no, status, latest_event)
        VALUES (:id, :order_id, :carrier, :tracking_no, :status, :latest_event)
        ON CONFLICT (id) DO NOTHING
        """,
        LOGISTICS,
    )


def seed_refunds(conn) -> None:
    execute_many(
        conn,
        """
        INSERT INTO refunds (id, order_id, refund_no, reason, amount_cents, status)
        VALUES (:id, :order_id, :refund_no, :reason, :amount_cents, :status)
        ON CONFLICT (id) DO NOTHING
        """,
        REFUNDS,
    )


def seed_tickets(conn) -> None:
    execute_many(
        conn,
        """
        INSERT INTO tickets (
            id, ticket_no, order_id, customer_question, category,
            priority, title, summary, status, assignee_id, created_by_id
        )
        VALUES (
            :id, :ticket_no, :order_id, :customer_question, :category,
            :priority, :title, :summary, :status, :assignee_id, :created_by_id
        )
        ON CONFLICT (id) DO NOTHING
        """,
        TICKETS,
    )


def seed_documents(conn) -> None:
    execute_many(
        conn,
        """
        INSERT INTO documents (
            id, title, file_name, file_type, storage_path, status, uploaded_by_id
        )
        VALUES (
            :id, :title, :file_name, :file_type, :storage_path, :status, :uploaded_by_id
        )
        ON CONFLICT (id) DO NOTHING
        """,
        DOCUMENTS,
    )


def seed_document_chunks(conn) -> None:
    rows = []
    for item in DOCUMENT_CHUNKS:
        row = dict(item)
        row["metadata_json"] = json.dumps(row.pop("metadata"), ensure_ascii=False)
        rows.append(row)

    execute_many(
        conn,
        """
        INSERT INTO document_chunks (
            id, document_id, chunk_index, content, page_no, token_count, metadata
        )
        VALUES (
            :id, :document_id, :chunk_index, :content, :page_no, :token_count,
            CAST(:metadata_json AS jsonb)
        )
        ON CONFLICT (id) DO NOTHING
        """,
        rows,
    )


def seed_qa_logs(conn) -> None:
    rows = []
    for item in QA_LOGS:
        row = dict(item)
        row["citations_json"] = json.dumps(row.pop("citations"), ensure_ascii=False)
        rows.append(row)

    execute_many(
        conn,
        """
        INSERT INTO qa_logs (
            id, user_id, question, answer, citations, latency_ms
        )
        VALUES (
            :id, :user_id, :question, :answer, CAST(:citations_json AS jsonb), :latency_ms
        )
        ON CONFLICT (id) DO NOTHING
        """,
        rows,
    )


def seed_feedbacks(conn) -> None:
    execute_many(
        conn,
        """
        INSERT INTO feedbacks (
            id, qa_log_id, ticket_id, user_id, rating, comment, status
        )
        VALUES (
            :id, :qa_log_id, :ticket_id, :user_id, :rating, :comment, :status
        )
        ON CONFLICT (id) DO NOTHING
        """,
        FEEDBACKS,
    )


def print_counts(conn) -> None:
    tables = [
        "users",
        "orders",
        "logistics",
        "refunds",
        "tickets",
        "documents",
        "document_chunks",
        "qa_logs",
        "feedbacks",
    ]

    print("\nSeed result:")
    for table in tables:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        print(f"- {table}: {count}")


def main() -> None:
    with engine.begin() as conn:
        seed_users(conn)
        seed_orders(conn)
        seed_logistics(conn)
        seed_refunds(conn)
        seed_tickets(conn)
        seed_documents(conn)
        seed_document_chunks(conn)
        seed_qa_logs(conn)
        seed_feedbacks(conn)
        print_counts(conn)

    print("\nDemo data seeded successfully.")


if __name__ == "__main__":
    main()