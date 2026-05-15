from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackCreateIn(BaseModel):
    qa_log_id: UUID | None = None
    ticket_no: str | None = None
    user_id: UUID | None = None
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


class FeedbackOut(BaseModel):
    id: UUID
    qa_log_id: UUID | None = None
    ticket_id: UUID | None = None
    user_id: UUID | None = None
    rating: int
    comment: str | None = None
    status: str
    created_at: datetime


class FeedbackListOut(BaseModel):
    total: int
    items: list[FeedbackOut]