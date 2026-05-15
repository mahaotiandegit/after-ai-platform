from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.ai_quality_service import get_ai_quality_overview, get_ai_quality_trends

router = APIRouter()


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return get_ai_quality_overview(db)

@router.get("/trends")
def trends(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    return get_ai_quality_trends(db, days=days)
