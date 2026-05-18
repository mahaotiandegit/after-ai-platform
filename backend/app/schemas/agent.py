from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

class AftersaleAgentRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    order_no: str | None = Field(default=None, max_length=80)
    top_k: int = Field(default=5, ge=1, le=20)
    auto_create_ticket: bool = Field(default=False)
    include_analytics: bool = Field(default=False)
    created_by_id: UUID | None = None


class AgentToolCall(BaseModel):
    tool_name: str
    purpose: str
    success: bool
    latency_ms: int
    data: Any | None = None
    error: str | None = None


class AftersaleAgentResponse(BaseModel):
    question: str
    order_no: str | None = None
    route_intents: list[str]
    final_answer: str
    action_plan: list[str]
    risk_flags: list[str]
    tool_calls: list[AgentToolCall]

    created_ticket_no: str | None = None
    used_llm: bool = False
    provider: str = "local"
    model: str = "local-template"