from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TicketAutoCreateIn(BaseModel):
    order_no: str | None = Field(default=None, description="订单号，可为空")
    customer_question: str = Field(..., min_length=2, description="用户原始问题")
    created_by_id: UUID | None = Field(default=None, description="创建人 ID，可为空")


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


class TicketAutoCreateOut(BaseModel):
    ticket: TicketOut
    classification_reason: str
    next_action: str


class TicketListOut(BaseModel):
    total: int
    items: list[TicketOut]


class TicketStatusUpdateIn(BaseModel):
    status: Literal["open", "processing", "resolved", "closed"]
    operator_id: UUID | None = None
    note: str | None = None


class TicketEscalateIn(BaseModel):
    assignee_id: UUID | None = None
    reason: str = Field(..., min_length=2)


class TicketActionOut(BaseModel):
    ticket: TicketOut
    action: str
    message: str