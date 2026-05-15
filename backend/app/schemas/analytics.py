from pydantic import BaseModel


class CountItem(BaseModel):
    label: str
    count: int


class AnalyticsOverviewOut(BaseModel):
    orders_total: int
    tickets_total: int
    tickets_open: int
    tickets_high_priority: int
    refunds_pending: int
    documents_indexed: int
    avg_qa_latency_ms: float
    ticket_status_distribution: list[CountItem]
    ticket_category_distribution: list[CountItem]
    refund_status_distribution: list[CountItem]