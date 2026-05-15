from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.analytics import (
    AnalyticsAskRequest,
    AnalyticsAskResponse,
    AnalyticsOverviewOut,
)
from app.services.analytics_service import get_analytics_overview
from app.services.analytics_nl2sql import ask_analytics_question

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewOut)
def overview(db: Session = Depends(get_db)):
    return get_analytics_overview(db=db)

@router.post("/ask", response_model=AnalyticsAskResponse)
def ask_analytics(
    payload: AnalyticsAskRequest,
    db: Session = Depends(get_db),
):
    return ask_analytics_question(
        db=db,
        question=payload.question,
        limit=payload.limit,
    )