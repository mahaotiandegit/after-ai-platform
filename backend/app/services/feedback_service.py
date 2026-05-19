from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


def _find_ticket_id_by_no(db: Session, ticket_no: str | None) -> uuid.UUID | None:
    if not ticket_no:
        return None

    row = db.execute(
        text(
            """
            SELECT id
            FROM tickets
            WHERE ticket_no = :ticket_no
            """
        ),
        {"ticket_no": ticket_no},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    return row["id"]


def create_feedback(
    db: Session,
    qa_log_id: uuid.UUID | None,
    ticket_no: str | None,
    user_id: uuid.UUID | None,
    rating: int,
    comment: str | None,
) -> dict:
    ticket_id = _find_ticket_id_by_no(db=db, ticket_no=ticket_no)

    row = db.execute(
        text(
            """
            INSERT INTO feedbacks (
                qa_log_id,
                ticket_id,
                user_id,
                rating,
                comment,
                status
            )
            VALUES (
                :qa_log_id,
                :ticket_id,
                :user_id,
                :rating,
                :comment,
                'new'
            )
            RETURNING
                id,
                qa_log_id,
                ticket_id,
                user_id,
                rating,
                comment,
                status,
                created_at
            """
        ),
        {
            "qa_log_id": str(qa_log_id) if qa_log_id else None,
            "ticket_id": str(ticket_id) if ticket_id else None,
            "user_id": str(user_id) if user_id else None,
            "rating": rating,
            "comment": comment,
        },
    ).mappings().first()

    db.commit()
    return dict(row)


def list_feedbacks(
    db: Session,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    where_clauses = []
    params = {
        "limit": limit,
        "offset": offset,
    }

    if status:
        where_clauses.append("f.status = :status")
        params["status"] = status

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    total = db.execute(
        text(
            f"""
            SELECT COUNT(*) AS total
            FROM feedbacks f
            {where_sql}
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            f"""
            SELECT
                f.id,
                f.qa_log_id,
                f.ticket_id,
                f.user_id,
                f.rating,
                f.comment,
                f.status,
                f.created_at,
                q.question,
                q.answer
            FROM feedbacks f
            LEFT JOIN qa_logs q ON q.id = f.qa_log_id
            {where_sql}
            ORDER BY f.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return {
        "total": int(total),
        "items": [dict(row) for row in rows],
    }

def update_feedback_status(
    db: Session,
    feedback_id: uuid.UUID,
    status: str,
) -> dict:
    allowed_status = {
        "new",
        "reviewing",
        "converted",
        "ignored",
        "resolved",
    }

    if status not in allowed_status:
        raise HTTPException(status_code=400, detail="invalid feedback status")

    row = db.execute(
        text(
            """
            UPDATE feedbacks
            SET status = :status
            WHERE id = :id
            RETURNING
                id,
                qa_log_id,
                ticket_id,
                user_id,
                rating,
                comment,
                status,
                created_at
            """
        ),
        {
            "id": str(feedback_id),
            "status": status,
        },
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="feedback not found")

    db.commit()
    return dict(row)