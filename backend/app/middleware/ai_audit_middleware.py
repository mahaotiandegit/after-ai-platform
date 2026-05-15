from __future__ import annotations

import json
import time
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.ai_audit_log import write_ai_invocation_log


AUDITED_PATHS = {
    "/api/v1/knowledge/ask-llm": {
        "scene": "rag_ask_llm",
        "default_provider": "local-template",
        "default_model": "local-rag-template-v1",
    },
    "/api/v1/analytics/ask": {
        "scene": "analytics_nl2sql",
        "default_provider": "local-nl2sql",
        "default_model": "analytics-nl2sql-v1",
    },
}


def _safe_json_loads(raw: bytes) -> Any:
    if not raw:
        return {}

    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {
            "_raw": raw.decode("utf-8", errors="replace")[:2000],
        }


def _jsonable(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            _jsonable(item)
            for item in value
        ]

    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def _extract_provider_model(
    *,
    path_config: dict[str, str],
    output_payload: Any,
) -> tuple[str | None, str | None]:
    provider = path_config.get("default_provider")
    model = path_config.get("default_model")

    if isinstance(output_payload, dict):
        provider = (
            output_payload.get("provider")
            or output_payload.get("llm_provider")
            or provider
        )

        model = (
            output_payload.get("model")
            or output_payload.get("llm_model")
            or model
        )

    return provider, model


def _extract_error_message(
    *,
    status_code: int,
    output_payload: Any,
) -> str | None:
    if status_code < 400:
        return None

    if isinstance(output_payload, dict):
        detail = output_payload.get("detail") or output_payload.get("message") or output_payload.get("error")
        return str(detail) if detail is not None else f"HTTP {status_code}"

    return f"HTTP {status_code}"


class AIAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path_config = AUDITED_PATHS.get(request.url.path)

        if path_config is None:
            return await call_next(request)

        started_at = time.perf_counter()

        request_body = await request.body()

        async def receive():
            return {
                "type": "http.request",
                "body": request_body,
                "more_body": False,
            }

        request._receive = receive  # noqa: SLF001

        response = await call_next(request)

        response_chunks = []

        async for chunk in response.body_iterator:
            response_chunks.append(chunk)

        response_body = b"".join(response_chunks)

        input_payload = _safe_json_loads(request_body)
        output_payload = _safe_json_loads(response_body)

        provider, model = _extract_provider_model(
            path_config=path_config,
            output_payload=output_payload,
        )

        success = response.status_code < 400
        error_message = _extract_error_message(
            status_code=response.status_code,
            output_payload=output_payload,
        )

        write_ai_invocation_log(
            scene=path_config["scene"],
            provider=provider,
            model=model,
            input_payload={
                "method": request.method,
                "path": request.url.path,
                "body": _jsonable(input_payload),
            },
            output_payload={
                "status_code": response.status_code,
                "body": _jsonable(output_payload),
            },
            success=success,
            error_message=error_message,
            started_at=started_at,
        )

        headers = dict(response.headers)
        headers.pop("content-length", None)

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
            background=response.background,
        )
