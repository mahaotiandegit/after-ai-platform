from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.ai_quality_service import get_ai_quality_overview

router = APIRouter()


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return get_ai_quality_overview(db)
