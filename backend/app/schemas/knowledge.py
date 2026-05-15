from pydantic import BaseModel


class KnowledgeHit(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    file_name: str
    file_type: str
    content: str
    page_no: int | None = None
    policy_code: str | None = None
    section: str | None = None
    score: float


class KnowledgeSearchOut(BaseModel):
    query: str
    answer_summary: str
    hits: list[KnowledgeHit]