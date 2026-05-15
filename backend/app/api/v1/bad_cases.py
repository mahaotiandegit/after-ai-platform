from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.bad_case_service import (
    create_bad_case_from_ai_log,
    list_bad_cases,
    update_bad_case_status,
)


router = APIRouter(prefix="/bad-cases", tags=["bad-cases"])


class BadCaseFromAILogIn(BaseModel):
    ai_log_id: str = Field(..., min_length=1)
    correction: str | None = None
    root_cause: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    tags: list[str] = Field(default_factory=list)


class BadCaseStatusUpdateIn(BaseModel):
    status: Literal["open", "reviewing", "fixed", "ignored", "closed"]
    root_cause: str | None = None
    correction: str | None = None


@router.post("/from-ai-log")
def create_from_ai_log(
    payload: BadCaseFromAILogIn,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return create_bad_case_from_ai_log(
        db=db,
        ai_log_id=payload.ai_log_id,
        correction=payload.correction,
        root_cause=payload.root_cause,
        priority=payload.priority,
        tags=payload.tags,
    )


@router.get("")
def get_bad_cases(
    status: str | None = Query(default=None),
    scene: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return list_bad_cases(
        db=db,
        status=status,
        scene=scene,
        priority=priority,
        limit=limit,
        offset=offset,
    )


@router.patch("/{bad_case_id}/status")
def change_bad_case_status(
    bad_case_id: str,
    payload: BadCaseStatusUpdateIn,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return update_bad_case_status(
        db=db,
        bad_case_id=bad_case_id,
        status=payload.status,
        root_cause=payload.root_cause,
        correction=payload.correction,
    )
