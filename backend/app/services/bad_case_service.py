from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            _json_safe(item)
            for item in value
        ]

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _json_loads(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except Exception:
        return value


def ensure_bad_cases_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS bad_cases (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                scene TEXT NULL,
                question TEXT NULL,
                ai_output JSONB NULL,
                correction TEXT NULL,
                root_cause TEXT NULL,
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'open',
                tags JSONB NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )

    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_bad_cases_status_created_at
            ON bad_cases(status, created_at DESC)
            """
        )
    )

    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_bad_cases_scene_created_at
            ON bad_cases(scene, created_at DESC)
            """
        )
    )


def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)

    for key in ["ai_output", "tags"]:
        result[key] = _json_loads(result.get(key))

    for key in ["created_at", "updated_at"]:
        value = result.get(key)

        if hasattr(value, "isoformat"):
            result[key] = value.isoformat()

    return result


def _extract_question(input_payload: Any) -> str | None:
    payload = _json_loads(input_payload)

    if not isinstance(payload, dict):
        return None

    body = payload.get("body")

    if isinstance(body, dict):
        question = body.get("question") or body.get("customer_question")

        if question:
            return str(question)

    question = payload.get("question") or payload.get("customer_question")

    if question:
        return str(question)

    return None


def _extract_output(output_payload: Any) -> dict[str, Any]:
    payload = _json_loads(output_payload)

    if isinstance(payload, dict):
        body = payload.get("body")

        if isinstance(body, dict):
            return body

        return payload

    return {
        "raw": payload,
    }


def create_bad_case_from_ai_log(
    *,
    db: Session,
    ai_log_id: str,
    correction: str | None = None,
    root_cause: str | None = None,
    priority: str = "medium",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    ensure_bad_cases_table(db)

    ai_log = db.execute(
        text(
            """
            SELECT
                id,
                scene,
                input_payload,
                output_payload
            FROM ai_invocation_logs
            WHERE id = :id
            """
        ),
        {
            "id": ai_log_id,
        },
    ).mappings().first()

    if ai_log is None:
        raise HTTPException(
            status_code=404,
            detail=f"ai invocation log not found: {ai_log_id}",
        )

    bad_case_id = str(uuid.uuid4())
    question = _extract_question(ai_log["input_payload"])
    ai_output = _extract_output(ai_log["output_payload"])

    row = db.execute(
        text(
            """
            INSERT INTO bad_cases (
                id,
                source_type,
                source_id,
                scene,
                question,
                ai_output,
                correction,
                root_cause,
                priority,
                status,
                tags,
                created_at,
                updated_at
            )
            VALUES (
                :id,
                :source_type,
                :source_id,
                :scene,
                :question,
                CAST(:ai_output AS JSONB),
                :correction,
                :root_cause,
                :priority,
                :status,
                CAST(:tags AS JSONB),
                :created_at,
                :updated_at
            )
            RETURNING
                id,
                source_type,
                source_id,
                scene,
                question,
                ai_output,
                correction,
                root_cause,
                priority,
                status,
                tags,
                created_at,
                updated_at
            """
        ),
        {
            "id": bad_case_id,
            "source_type": "ai_invocation_log",
            "source_id": ai_log_id,
            "scene": ai_log["scene"],
            "question": question,
            "ai_output": _json_dumps(ai_output),
            "correction": correction,
            "root_cause": root_cause,
            "priority": priority,
            "status": "open",
            "tags": _json_dumps(tags or []),
            "created_at": _now(),
            "updated_at": _now(),
        },
    ).mappings().first()

    db.commit()

    return _row_to_dict(dict(row))

def create_bad_case_from_feedback(
    *,
    db: Session,
    feedback_id: str,
    correction: str | None = None,
    root_cause: str | None = None,
    priority: str = "medium",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    ensure_bad_cases_table(db)

    existing = db.execute(
        text(
            """
            SELECT
                id,
                source_type,
                source_id,
                scene,
                question,
                ai_output,
                correction,
                root_cause,
                priority,
                status,
                tags,
                created_at,
                updated_at
            FROM bad_cases
            WHERE source_type = 'feedback'
              AND source_id = :feedback_id
            LIMIT 1
            """
        ),
        {
            "feedback_id": feedback_id,
        },
    ).mappings().first()

    if existing is not None:
        return _row_to_dict(dict(existing))

    feedback = db.execute(
        text(
            """
            SELECT
                f.id,
                f.qa_log_id,
                f.rating,
                f.comment,
                f.status,
                q.question,
                q.answer,
                q.citations
            FROM feedbacks f
            LEFT JOIN qa_logs q ON q.id = f.qa_log_id
            WHERE f.id = :feedback_id
            """
        ),
        {
            "feedback_id": feedback_id,
        },
    ).mappings().first()

    if feedback is None:
        raise HTTPException(
            status_code=404,
            detail=f"feedback not found: {feedback_id}",
        )

    rating = int(feedback["rating"] or 0)
    auto_tags = ["feedback", f"rating_{rating}"]

    if rating <= 2:
        auto_tags.append("low_rating")

    if tags:
        auto_tags.extend(tags)

    question = feedback["question"] or feedback["comment"] or "未关联 QA 日志的反馈"

    ai_output = {
        "answer": feedback["answer"],
        "citations": _json_loads(feedback["citations"]),
        "rating": rating,
        "comment": feedback["comment"],
        "qa_log_id": str(feedback["qa_log_id"]) if feedback["qa_log_id"] else None,
    }

    bad_case_id = str(uuid.uuid4())

    row = db.execute(
        text(
            """
            INSERT INTO bad_cases (
                id,
                source_type,
                source_id,
                scene,
                question,
                ai_output,
                correction,
                root_cause,
                priority,
                status,
                tags,
                created_at,
                updated_at
            )
            VALUES (
                :id,
                :source_type,
                :source_id,
                :scene,
                :question,
                CAST(:ai_output AS JSONB),
                :correction,
                :root_cause,
                :priority,
                :status,
                CAST(:tags AS JSONB),
                :created_at,
                :updated_at
            )
            RETURNING
                id,
                source_type,
                source_id,
                scene,
                question,
                ai_output,
                correction,
                root_cause,
                priority,
                status,
                tags,
                created_at,
                updated_at
            """
        ),
        {
            "id": bad_case_id,
            "source_type": "feedback",
            "source_id": feedback_id,
            "scene": "knowledge_feedback",
            "question": question,
            "ai_output": _json_dumps(ai_output),
            "correction": correction,
            "root_cause": root_cause,
            "priority": priority,
            "status": "open",
            "tags": _json_dumps(auto_tags),
            "created_at": _now(),
            "updated_at": _now(),
        },
    ).mappings().first()

    db.execute(
        text(
            """
            UPDATE feedbacks
            SET status = 'converted'
            WHERE id = :feedback_id
            """
        ),
        {
            "feedback_id": feedback_id,
        },
    )

    db.commit()

    return _row_to_dict(dict(row))


def list_bad_cases(
    *,
    db: Session,
    status: str | None = None,
    scene: str | None = None,
    priority: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    ensure_bad_cases_table(db)

    where_clauses: list[str] = []
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }

    if status:
        where_clauses.append("status = :status")
        params["status"] = status

    if scene:
        where_clauses.append("scene = :scene")
        params["scene"] = scene

    if priority:
        where_clauses.append("priority = :priority")
        params["priority"] = priority

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    total = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM bad_cases
            {where_sql}
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            f"""
            SELECT
                id,
                source_type,
                source_id,
                scene,
                question,
                ai_output,
                correction,
                root_cause,
                priority,
                status,
                tags,
                created_at,
                updated_at
            FROM bad_cases
            {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            _row_to_dict(dict(row))
            for row in rows
        ],
    }


def update_bad_case_status(
    *,
    db: Session,
    bad_case_id: str,
    status: str,
    root_cause: str | None = None,
    correction: str | None = None,
) -> dict[str, Any]:
    ensure_bad_cases_table(db)

    allowed_status = {
        "open",
        "reviewing",
        "fixed",
        "ignored",
        "closed",
    }

    if status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail=f"invalid status: {status}",
        )

    row = db.execute(
        text(
            """
            UPDATE bad_cases
            SET
                status = :status,
                root_cause = COALESCE(:root_cause, root_cause),
                correction = COALESCE(:correction, correction),
                updated_at = :updated_at
            WHERE id = :id
            RETURNING
                id,
                source_type,
                source_id,
                scene,
                question,
                ai_output,
                correction,
                root_cause,
                priority,
                status,
                tags,
                created_at,
                updated_at
            """
        ),
        {
            "id": bad_case_id,
            "status": status,
            "root_cause": root_cause,
            "correction": correction,
            "updated_at": _now(),
        },
    ).mappings().first()

    if row is None:
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail=f"bad case not found: {bad_case_id}",
        )

    db.commit()

    return _row_to_dict(dict(row))
