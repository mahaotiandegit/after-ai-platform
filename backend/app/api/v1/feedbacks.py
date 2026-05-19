from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from uuid import UUID

from app.schemas.feedback import FeedbackCreateIn, FeedbackListOut, FeedbackOut, FeedbackStatusUpdateIn
from app.services.feedback_service import create_feedback, list_feedbacks, update_feedback_status

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


@router.patch("/{feedback_id}/status", response_model=FeedbackOut)
def change_feedback_status(
    feedback_id: UUID,
    payload: FeedbackStatusUpdateIn,
    db: Session = Depends(get_db),
):
    return update_feedback_status(
        db=db,
        feedback_id=feedback_id,
        status=payload.status,
    )