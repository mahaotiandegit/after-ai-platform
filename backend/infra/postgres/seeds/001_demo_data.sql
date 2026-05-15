INSERT INTO users (
    id, username, email, password_hash, role, is_active
)
VALUES
(
    '11111111-1111-1111-1111-111111111111',
    'agent01',
    'agent01@example.com',
    'demo-password-hash',
    'agent',
    true
),
(
    '11111111-1111-1111-1111-111111111112',
    'leader01',
    'leader01@example.com',
    'demo-password-hash',
    'leader',
    true
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO orders (
    id, order_no, customer_name, customer_phone, status, total_amount_cents
)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    'ORDER-20260515-0001',
    '张三',
    '13800000001',
    'paid',
    19900
)
ON CONFLICT (order_no) DO NOTHING;

INSERT INTO logistics (
    id, order_id, carrier, tracking_no, status, latest_event, shipped_at
)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '22222222-2222-2222-2222-222222222222',
    'SF Express',
    'SF1234567890',
    'delayed',
    '包裹已到达东京中转仓，预计延迟 1-2 天派送',
    NOW() - INTERVAL '3 days'
)
ON CONFLICT DO NOTHING;

INSERT INTO refunds (
    id, order_id, refund_no, reason, amount_cents, status
)
VALUES (
    '44444444-4444-4444-4444-444444444444',
    '22222222-2222-2222-2222-222222222222',
    'REFUND-20260515-0001',
    '物流延迟申请补偿',
    3000,
    'pending'
)
ON CONFLICT (refund_no) DO NOTHING;

INSERT INTO tickets (
    id, ticket_no, order_id, customer_question, category, priority, title, summary, status, assignee_id, created_by_id
)
VALUES (
    '55555555-5555-5555-5555-555555555555',
    'TICKET-20260515-0001',
    '22222222-2222-2222-2222-222222222222',
    '我的包裹已经三天没更新了，能不能退款或者补偿？',
    'logistics_delay',
    'high',
    '物流延迟补偿咨询',
    '用户反馈包裹三天未更新，希望确认物流状态并申请补偿。',
    'open',
    '11111111-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111'
)
ON CONFLICT (ticket_no) DO NOTHING;
