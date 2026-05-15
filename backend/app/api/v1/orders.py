from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.order import OrderAftersaleContextOut
from app.services.order_context_service import get_order_aftersale_context

router=APIRouter(prefix="/orders",tags=["orders"])

@router.get("/{order_no}/aftersale-context",response_model=OrderAftersaleContextOut)
def get_aftersale_context(order_no: str, db: Session = Depends(get_db)):
    return get_order_aftersale_context(db=db, order_no=order_no)