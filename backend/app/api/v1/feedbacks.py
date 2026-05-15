from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.feedback import FeedbackCreateIn, FeedbackListOut, FeedbackOut
from app.services.feedback_service import create_feedback, list_feedbacks

router = APIRouter(prefix="/feedbacks", tags=["feedbacks"])


@router.post("", response_model=FeedbackOut)
def submit_feedback(
    payload: FeedbackCreateIn,
    db: Session = Depends(get_db),
):
    return create_feedback(
        db=db,
        qa_log_id=payload.qa_log_id,
        ticket_no=payload.ticket_no,
        user_id=payload.user_id,
        rating=payload.rating,
        comment=payload.comment,
    )


@router.get("", response_model=FeedbackListOut)
def get_feedbacks(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_feedbacks(
        db=db,
        status=status,
        limit=limit,
        offset=offset,
    )