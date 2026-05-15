from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OrderOut(BaseModel):
    id: UUID
    order_no: str
    customer_name: str
    customer_phone: str
    status: str
    total_amount_cents: int
    created_at: datetime
    updated_at: datetime


class LogisticsOut(BaseModel):
    id: UUID
    order_id: UUID
    carrier: str
    tracking_no: str
    status: str
    latest_event: str | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime


class RefundOut(BaseModel):
    id: UUID
    order_id: UUID
    refund_no: str
    reason: str
    amount_cents: int
    status: str
    created_at: datetime
    updated_at: datetime


class TicketOut(BaseModel):
    id: UUID
    ticket_no: str
    order_id: UUID | None = None
    customer_question: str
    category: str
    priority: str
    title: str
    summary: str
    status: str
    assignee_id: UUID | None = None
    created_by_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class OrderRecommendation(BaseModel):
    issue_type: str
    priority: str
    suggested_action: str
    reason: str


class OrderAftersaleContextOut(BaseModel):
    order: OrderOut
    logistics: list[LogisticsOut]
    refunds: list[RefundOut]
    tickets: list[TicketOut]
    recommendation: OrderRecommendation