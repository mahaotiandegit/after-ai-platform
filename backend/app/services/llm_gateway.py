from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _clip(text: str, max_chars: int = 1200) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _normalize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for index, chunk in enumerate(chunks, start=1):
        content = (
            chunk.get("content")
            or chunk.get("text")
            or chunk.get("chunk_text")
            or ""
        )

        normalized.append(
            {
                "index": index,
                "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                "document_title": chunk.get("document_title") or chunk.get("title") or "未知文档",
                "content": _clip(str(content), 1000),
            }
        )

    return normalized


class LLMGateway:
    def __init__(self) -> None:
        self.provider = _env("LLM_PROVIDER", "local").lower()
        self.api_key = _env("LLM_API_KEY", "")
        self.model = _env("LLM_MODEL", "local-template")
        self.base_url = _env("LLM_BASE_URL", "")

        if self.provider == "deepseek" and not self.base_url:
            self.base_url = "https://api.deepseek.com/v1"

        if self.provider == "openai" and not self.base_url:
            self.base_url = "https://api.openai.com/v1"

    def generate_rag_answer(
        self,
        question: str,
        chunks: list[dict[str, Any]],
        fallback_answer: str = "",
    ) -> dict[str, Any]:
        normalized_chunks = _normalize_chunks(chunks)

        if self.provider in {"openai", "deepseek", "openai-compatible"} and self.api_key:
            try:
                answer = self._generate_with_openai_compatible(
                    question=question,
                    chunks=normalized_chunks,
                )
                return {
                    "answer": answer,
                    "provider": self.provider,
                    "model": self.model,
                    "used_llm": True,
                    "fallback_reason": "",
                }
            except Exception as exc:
                local = self._generate_local_answer(
                    question=question,
                    chunks=normalized_chunks,
                    fallback_answer=fallback_answer,
                )
                local["fallback_reason"] = f"{type(exc).__name__}: {exc}"
                return local

        return self._generate_local_answer(
            question=question,
            chunks=normalized_chunks,
            fallback_answer=fallback_answer,
        )

    def classify_ticket(self, question: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "used_llm": False,
            "category": "unknown",
            "priority": "medium",
            "title": "",
            "summary": "",
            "reason": "LLM Gateway v1 placeholder. Ticket classification will be wired in next phase.",
        }

    def extract_analytics_intent(self, question: str) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "used_llm": False,
            "intent": "unknown",
            "reason": "LLM Gateway v1 placeholder. Analytics intent extraction will be wired in next phase.",
        }

    def _generate_local_answer(
        self,
        question: str,
        chunks: list[dict[str, Any]],
        fallback_answer: str = "",
    ) -> dict[str, Any]:
        if not chunks:
            answer = fallback_answer or "当前知识库没有检索到足够依据，建议补充相关售后规则文档后再回答。"
        else:
            first = chunks[0]
            answer = (
                f"根据知识库命中内容，问题“{question}”可优先按以下规则处理："
                f"{first['content']} "
                f"请以引用文档为准，涉及退款、补偿或升级处理时需要结合订单状态、物流状态和售后记录复核。"
            )

        return {
            "answer": answer,
            "provider": "local",
            "model": "local-template",
            "used_llm": False,
            "fallback_reason": "",
        }

    def _generate_with_openai_compatible(
        self,
        question: str,
        chunks: list[dict[str, Any]],
    ) -> str:
        if not self.base_url:
            raise RuntimeError("LLM_BASE_URL is empty")

        context_text = "\n\n".join(
            [
                f"[{chunk['index']}] 文档：{chunk['document_title']}\n内容：{chunk['content']}"
                for chunk in chunks
            ]
        )

        system_prompt = (
            "你是电商售后知识助手。必须只基于给定知识片段回答。"
            "如果知识片段不足，明确说明依据不足。"
            "回答要给客服可执行建议，不要编造规则。"
        )

        user_prompt = (
            f"用户问题：{question}\n\n"
            f"知识片段：\n{context_text}\n\n"
            "请输出面向客服的中文回答。"
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "temperature": 0.2,
        }

        url = self.base_url.rstrip("/") + "/chat/completions"

        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc

        data = json.loads(raw)
        return data["choices"][0]["message"]["content"]


def get_llm_gateway() -> LLMGateway:
    return LLMGateway()


def generate_rag_answer(
    question: str,
    chunks: list[dict[str, Any]],
    fallback_answer: str = "",
) -> dict[str, Any]:
    return get_llm_gateway().generate_rag_answer(
        question=question,
        chunks=chunks,
        fallback_answer=fallback_answer,
    )
