from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.ticket_ai_classifier import classify_ticket_with_llm_gateway


router = APIRouter(tags=["ticket-ai-classifier"])


class TicketAICreateRequest(BaseModel):
    order_id: str | None = None
    customer_question: str = Field(..., min_length=1)
    created_by_id: str | None = None
    assignee_id: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, uuid.UUID):
        return str(value)

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


def _first_id(db: Session, table: str) -> str | None:
    if table not in {"users", "orders"}:
        return None

    bind = db.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table(table):
        return None

    try:
        value = db.execute(text(f"SELECT id FROM {table} LIMIT 1")).scalar_one_or_none()
        return str(value) if value is not None else None
    except Exception:
        db.rollback()
        return None


def _table_columns(db: Session, table: str) -> dict[str, dict[str, Any]]:
    bind = db.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table(table):
        raise HTTPException(
            status_code=500,
            detail=f"table not found: {table}",
        )

    return {column["name"]: column for column in inspector.get_columns(table)}


def _fill_required_missing_values(
    values: dict[str, Any],
    columns: dict[str, dict[str, Any]],
    *,
    user_id: str | None,
    order_id: str | None,
    result: Any,
    customer_question: str,
) -> None:
    for name, column in columns.items():
        if name in values:
            continue

        nullable = bool(column.get("nullable", True))
        default = column.get("default")
        server_default = column.get("server_default")
        autoincrement = column.get("autoincrement")

        if nullable or default is not None or server_default is not None or autoincrement is True:
            continue

        lower_name = name.lower()
        type_name = str(column.get("type", "")).lower()

        if lower_name == "id" and "uuid" in type_name:
            values[name] = str(uuid.uuid4())

        elif lower_name.endswith("_at"):
            values[name] = _now()

        elif lower_name in {"created_by_id", "updated_by_id", "assignee_id", "user_id"} and user_id:
            values[name] = user_id

        elif lower_name == "order_id" and order_id:
            values[name] = order_id

        elif "question" in lower_name:
            values[name] = customer_question

        elif lower_name == "category":
            values[name] = result.category

        elif lower_name == "priority":
            values[name] = result.priority

        elif lower_name == "title":
            values[name] = result.title

        elif lower_name == "summary":
            values[name] = result.summary

        elif lower_name == "status":
            values[name] = "open"

        elif "bool" in type_name:
            values[name] = False

        elif any(token in type_name for token in ["int", "numeric", "decimal", "float", "double"]):
            values[name] = 0

        else:
            values[name] = ""


@router.post("/tickets/ai-create")
def create_ticket_with_ai_classifier(
    payload: TicketAICreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = classify_ticket_with_llm_gateway(
        customer_question=payload.customer_question,
        context={
            "order_id": payload.order_id,
        },
    )

    columns = _table_columns(db, "tickets")

    order_id = payload.order_id or _first_id(db, "orders")
    user_id = payload.created_by_id or _first_id(db, "users")
    assignee_id = payload.assignee_id or user_id

    values: dict[str, Any] = {}

    if "id" in columns and "uuid" in str(columns["id"].get("type", "")).lower():
        values["id"] = str(uuid.uuid4())

    if "ticket_no" in columns:
        values["ticket_no"] = (
            f"TICKET-{datetime.now().strftime('%Y%m%d-%H%M%S')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

    if "order_id" in columns and order_id:
        values["order_id"] = order_id

    if "customer_question" in columns:
        values["customer_question"] = payload.customer_question
    elif "question" in columns:
        values["question"] = payload.customer_question

    base_values = {
        "category": result.category,
        "priority": result.priority,
        "title": result.title,
        "summary": result.summary,
        "status": "open",
        "created_by_id": user_id,
        "assignee_id": assignee_id,
        "created_at": _now(),
        "updated_at": _now(),
    }

    for name, value in base_values.items():
        if name in columns and value is not None:
            values[name] = value

    _fill_required_missing_values(
        values,
        columns,
        user_id=user_id,
        order_id=order_id,
        result=result,
        customer_question=payload.customer_question,
    )

    if not values:
        raise HTTPException(
            status_code=500,
            detail="no insertable columns resolved for tickets",
        )

    column_sql = ", ".join(values.keys())
    bind_sql = ", ".join(f":{key}" for key in values.keys())

    try:
        row = db.execute(
            text(f"INSERT INTO tickets ({column_sql}) VALUES ({bind_sql}) RETURNING *"),
            values,
        ).mappings().first()

        db.commit()

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"create ticket failed: {type(exc).__name__}: {exc}",
        ) from exc

    ticket = {
        key: _jsonable(value)
        for key, value in dict(row or {}).items()
    }

    return {
        **ticket,
        "category": ticket.get("category", result.category),
        "priority": ticket.get("priority", result.priority),
        "title": ticket.get("title", result.title),
        "summary": ticket.get("summary", result.summary),
        "llm_provider": result.llm_provider,
        "llm_model": result.llm_model,
        "used_llm": result.used_llm,
        "classification_source": result.classification_source,
        "recommended_action": result.recommended_action,
    }