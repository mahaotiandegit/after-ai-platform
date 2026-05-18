from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.agent import AftersaleAgentRequest, AftersaleAgentResponse
from app.services.aftersale_agent_service import run_aftersale_agent

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/aftersale", response_model=AftersaleAgentResponse)
def run_aftersale_agent_api(
    payload: AftersaleAgentRequest,
    db: Session = Depends(get_db),
):
    return run_aftersale_agent(
        db=db,
        question=payload.question,
        order_no=payload.order_no,
        top_k=payload.top_k,
        auto_create_ticket=payload.auto_create_ticket,
        include_analytics=payload.include_analytics,
        created_by_id=payload.created_by_id,
    )