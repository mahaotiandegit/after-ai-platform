from typing import Any

from pydantic import BaseModel, Field


class AnalyticsAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)


class AnalyticsAskResponse(BaseModel):
    question: str
    intent: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    summary: str

class AnalyticsOverviewOut(BaseModel):
    class Config:
        extra = "allow"
