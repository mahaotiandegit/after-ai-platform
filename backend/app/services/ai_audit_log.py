from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.db.session import SessionLocal


def _json_safe(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _ensure_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS ai_invocation_logs (
                id TEXT PRIMARY KEY,
                trace_id TEXT NULL,
                scene TEXT NOT NULL,
                provider TEXT NULL,
                model TEXT NULL,
                input_summary TEXT NULL,
                input_payload JSONB NULL,
                output_payload JSONB NULL,
                success BOOLEAN NOT NULL DEFAULT TRUE,
                error_message TEXT NULL,
                latency_ms INTEGER NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )

    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_invocation_logs_scene_created_at
            ON ai_invocation_logs(scene, created_at DESC)
            """
        )
    )

    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_invocation_logs_success_created_at
            ON ai_invocation_logs(success, created_at DESC)
            """
        )
    )


def write_ai_invocation_log(
    *,
    scene: str,
    provider: str | None,
    model: str | None,
    input_payload: dict[str, Any] | None = None,
    output_payload: dict[str, Any] | None = None,
    success: bool = True,
    error_message: str | None = None,
    trace_id: str | None = None,
    started_at: float | None = None,
    latency_ms: int | None = None,
) -> str | None:
    if started_at is not None and latency_ms is None:
        latency_ms = int((time.perf_counter() - started_at) * 1000)

    log_id = str(uuid.uuid4())

    safe_input = _json_safe(input_payload or {})
    safe_output = _json_safe(output_payload or {})

    input_summary = _json_dumps(safe_input)

    if len(input_summary) > 1000:
        input_summary = input_summary[:1000]

    db = SessionLocal()

    try:
        _ensure_table(db)

        db.execute(
            text(
                """
                INSERT INTO ai_invocation_logs (
                    id,
                    trace_id,
                    scene,
                    provider,
                    model,
                    input_summary,
                    input_payload,
                    output_payload,
                    success,
                    error_message,
                    latency_ms,
                    created_at
                )
                VALUES (
                    :id,
                    :trace_id,
                    :scene,
                    :provider,
                    :model,
                    :input_summary,
                    CAST(:input_payload AS JSONB),
                    CAST(:output_payload AS JSONB),
                    :success,
                    :error_message,
                    :latency_ms,
                    :created_at
                )
                """
            ),
            {
                "id": log_id,
                "trace_id": trace_id,
                "scene": scene,
                "provider": provider,
                "model": model,
                "input_summary": input_summary,
                "input_payload": _json_dumps(safe_input),
                "output_payload": _json_dumps(safe_output),
                "success": success,
                "error_message": error_message,
                "latency_ms": latency_ms,
                "created_at": datetime.now(timezone.utc),
            },
        )

        db.commit()

        return log_id

    except Exception:
        db.rollback()
        return None

    finally:
        db.close()
