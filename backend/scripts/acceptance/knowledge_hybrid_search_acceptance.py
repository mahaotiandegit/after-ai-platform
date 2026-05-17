#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from sqlalchemy import create_engine, text
import os


def database_url() -> str:
    return os.getenv("DATABASE_URL") or "postgresql://after_ai:after_ai_password@localhost:5432/after_ai_platform"


BACKEND_DIR=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.embedding_service import embed_text, to_pgvector_literal  # noqa: E402


BASE_URL = os.getenv("ACCEPTANCE_BASE_URL", "http://127.0.0.1:8000")

def fail(message: str):
    print(f"[FAIL] {message}")
    sys.exit(1)


def ok(message: str):
    print(f"[PASS] {message}")

def request_json(method:str,path:str,body=None):
    data=None
    headers={"Content-Type":"application/json"}

    if body is not None:
        data=json.dumps(body,ensure_ascii=False).encode("utf-8")

    req=urllib.request.Request(
        url=BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req,timeout=45)as resp:
            text_body=resp.read().decode("utf-8")
            return resp.status,json.loads(text_body) if text_body else None
    except urllib.error.HTTPError as e:
        text_body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(text_body)
        except Exception:
            return e.code, text_body
    except Exception as e:
        return 0, str(e)
    
def test_healthz():
    status,body=request_json("GET", "/healthz")
    if status != 200:
        fail(f"/healthz failed, status={status}, body={body}")
    ok("/healthz")

def test_pgvector_and_embeddings():
    engine=create_engine(database_url())
    with engine.begin() as conn:
        ext=conn.execute(
            text("select count(*) from pg_extension where extname='vector'")
        ).scalar()

        if int(ext or 0) <= 0:
            fail("pgvector extension not installed")

        has_column = conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'document_chunks'
                      AND column_name = 'embedding'
                )
                """
            )
        ).scalar()

        if not has_column:
            fail("document_chunks.embedding column not found")

        count = conn.execute(
            text(
                """
                SELECT count(*)
                FROM document_chunks
                WHERE embedding IS NOT NULL
                """
            )
        ).scalar()

        if int(count or 0) <= 0:
            fail("no document_chunks embeddings found, run backfill first")

        query_vector = to_pgvector_literal(embed_text("物流延迟补偿"))

        rows = conn.execute(
            text(
                """
                SELECT id, embedding <=> CAST(:query_vector AS vector) AS distance
                FROM document_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_vector AS vector)
                LIMIT 3
                """
            ),
            {"query_vector": query_vector},
        ).mappings().all()

        if not rows:
            fail("vector similarity query returned empty result")

    ok(f"pgvector + embeddings ready, embedded_chunks={count}")

def test_knowledge_search():
    query = urllib.parse.quote("物流延迟补偿")
    status, body = request_json("GET", f"/api/v1/knowledge/search?q={query}&limit=5")

    if status != 200:
        fail(f"/api/v1/knowledge/search failed, status={status}, body={body}")

    if "hits" not in body:
        fail(f"search response missing hits: {body}")

    if not body["hits"]:
        fail(f"search hits empty: {body}")

    retrieval_mode = body.get("retrieval_mode", "unknown")
    embedding_ready = body.get("embedding_ready", False)

    if retrieval_mode not in {"hybrid", "vector", "keyword", "unknown"}:
        fail(f"invalid retrieval_mode={retrieval_mode}")

    ok(
        "knowledge search ok, "
        f"hits={len(body['hits'])}, "
        f"retrieval_mode={retrieval_mode}, "
        f"embedding_ready={embedding_ready}"
    )

def test_knowledge_ask():
    status, body = request_json(
        "POST",
        "/api/v1/knowledge/ask",
        {
            "question": "物流超过三天没有更新，客服应该怎么补偿？",
            "top_k": 5,
        },
    )

    if status != 200:
        fail(f"/api/v1/knowledge/ask failed, status={status}, body={body}")

    required = ["answer", "citations", "provider", "model", "used_llm", "qa_log_id"]
    for field in required:
        if field not in body:
            fail(f"ask response missing {field}: {body}")

    if not body["answer"]:
        fail(f"answer empty: {body}")

    if not body["citations"]:
        fail(f"citations empty: {body}")

    if body["provider"] != "deepseek":
        fail(f"provider not deepseek: {body.get('provider')}")

    if body["used_llm"] is not True:
        fail(f"used_llm is not true, fallback_reason={body.get('fallback_reason')}")

    ok(
        "knowledge ask ok, "
        f"provider={body['provider']}, "
        f"citations={len(body['citations'])}, "
        f"qa_log_id={body['qa_log_id']}, "
        f"retrieval_mode={body.get('retrieval_mode', 'unknown')}"
    )

def main():
    print("========== v0.7.0 hybrid search acceptance ==========")
    test_healthz()
    test_pgvector_and_embeddings()
    test_knowledge_search()
    test_knowledge_ask()
    print("========== v0.7.0 验收通过 ==========")


if __name__ == "__main__":
    main()