from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.order_workbench_service import get_order_workbench

router = APIRouter(prefix="/order-workbench", tags=["order-workbench"])


@router.get("/{order_no}")
def read_order_workbench(order_no: str, db: Session = Depends(get_db)):
    data = get_order_workbench(db=db, order_no=order_no)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_no}")
    return data
