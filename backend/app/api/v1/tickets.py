from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.ticket import (
    TicketActionOut,
    TicketAutoCreateIn,
    TicketAutoCreateOut,
    TicketEscalateIn,
    TicketListOut,
    TicketOut,
    TicketStatusUpdateIn,
)
from app.services.ticket_service import (
    auto_create_ticket,
    escalate_ticket,
    get_ticket_by_no,
    list_tickets,
    update_ticket_status,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("/auto-create", response_model=TicketAutoCreateOut)
def create_ticket_by_ai_rule(
    payload: TicketAutoCreateIn,
    db: Session = Depends(get_db),
):
    return auto_create_ticket(
        db=db,
        customer_question=payload.customer_question,
        order_no=payload.order_no,
        created_by_id=payload.created_by_id,
    )


@router.get("", response_model=TicketListOut)
def get_tickets(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_tickets(
        db=db,
        status=status,
        category=category,
        priority=priority,
        limit=limit,
        offset=offset,
    )


@router.get("/{ticket_no}", response_model=TicketOut)
def get_ticket_detail(
    ticket_no: str,
    db: Session = Depends(get_db),
):
    return get_ticket_by_no(db=db, ticket_no=ticket_no)


@router.patch("/{ticket_no}/status", response_model=TicketActionOut)
def change_ticket_status(
    ticket_no: str,
    payload: TicketStatusUpdateIn,
    db: Session = Depends(get_db),
):
    return update_ticket_status(
        db=db,
        ticket_no=ticket_no,
        new_status=payload.status,
        operator_id=payload.operator_id,
        note=payload.note,
    )


@router.post("/{ticket_no}/escalate", response_model=TicketActionOut)
def escalate(
    ticket_no: str,
    payload: TicketEscalateIn,
    db: Session = Depends(get_db),
):
    return escalate_ticket(
        db=db,
        ticket_no=ticket_no,
        assignee_id=payload.assignee_id,
        reason=payload.reason,
    )