from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.ai_quality_service import get_ai_quality_overview, get_ai_quality_trends, run_recent_ai_quality_evaluations, list_ai_quality_evaluations, get_ai_quality_evaluation_summary, create_bad_case_from_ai_quality_evaluation, auto_create_bad_cases_from_high_risk_evaluations

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

@router.post("/evaluations/run-recent")
def run_recent_evaluations(
    limit: int = Query(default=20, ge=1, le=100),
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return run_recent_ai_quality_evaluations(db, limit=limit, force=force)




@router.get("/evaluations/summary")
def evaluation_summary(
    recent_limit: int = Query(default=5, ge=1, le=20),
    top_issue_limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return get_ai_quality_evaluation_summary(
        db,
        recent_limit=recent_limit,
        top_issue_limit=top_issue_limit,
    )



@router.post("/evaluations/{evaluation_id}/to-bad-case")
def evaluation_to_bad_case(
    evaluation_id: str,
    db: Session = Depends(get_db),
):
    return create_bad_case_from_ai_quality_evaluation(db, evaluation_id=evaluation_id)


@router.post("/evaluations/auto-create-bad-cases")
def auto_create_bad_cases(
    score_lte: int = Query(default=60, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return auto_create_bad_cases_from_high_risk_evaluations(
        db,
        score_lte=score_lte,
        limit=limit,
    )

@router.get("/evaluations")
def evaluations(
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    scene: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return list_ai_quality_evaluations(db, limit=limit, status=status, scene=scene)
