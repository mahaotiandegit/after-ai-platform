from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session


UPLOAD_ROOT = Path("uploads/documents")

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".json",
    ".log",
}


class UnsupportedDocumentTypeError(ValueError):
    pass


def _safe_filename(filename: str | None) -> str:
    raw = Path(filename or "uploaded.txt").name
    cleaned = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]", "_", raw).strip("._")
    return cleaned[:180] or "uploaded.txt"


def _file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return (suffix or "txt")[:32]


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("文件编码无法识别，请先转成 UTF-8 文本后再上传。")


def _extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise UnsupportedDocumentTypeError(
            f"当前 MVP 先支持纯文本类文件：{supported}。PDF/Word 后续单独接解析器。"
        )

    content = _decode_text(data)

    if suffix == ".json":
        try:
            obj = json.loads(content)
            content = json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            pass

    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _split_text(content: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    clean = content.strip()
    if not clean:
        return []

    if len(clean) <= max_chars:
        return [clean]

    chunks: list[str] = []
    start = 0

    while start < len(clean):
        end = min(start + max_chars, len(clean))

        if end < len(clean):
            split_candidates = [
                clean.rfind("\n\n", start, end),
                clean.rfind("\n", start, end),
                clean.rfind("。", start, end),
                clean.rfind(".", start, end),
                clean.rfind("；", start, end),
                clean.rfind(";", start, end),
            ]
            split_at = max(split_candidates)
            if split_at > start + max_chars * 0.5:
                end = split_at + 1

        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(clean):
            break

        start = max(end - overlap, start + 1)

    return chunks


def ingest_document_bytes(
    db: Session,
    *,
    filename: str,
    content: bytes,
    title: str | None = None,
    content_type: str | None = None,
) -> dict:
    if not content:
        raise ValueError("上传文件为空。")

    safe_filename = _safe_filename(filename)
    file_type = _file_type(safe_filename)
    extracted_text = _extract_text(safe_filename, content)
    chunks = _split_text(extracted_text)

    if not chunks:
        raise ValueError("文件没有解析出有效文本。")

    document_id = str(uuid.uuid4())
    document_title = (title or Path(safe_filename).stem).strip()[:255] or safe_filename

    storage_dir = UPLOAD_ROOT / document_id
    storage_dir.mkdir(parents=True, exist_ok=True)

    storage_path = storage_dir / safe_filename
    storage_path.write_bytes(content)

    try:
        db.execute(
            text(
                """
                INSERT INTO documents (
                    id,
                    title,
                    file_name,
                    file_type,
                    storage_path,
                    status,
                    uploaded_by_id,
                    created_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :title,
                    :file_name,
                    :file_type,
                    :storage_path,
                    'processing',
                    NULL,
                    now(),
                    now()
                )
                """
            ),
            {
                "id": document_id,
                "title": document_title,
                "file_name": safe_filename,
                "file_type": file_type,
                "storage_path": str(storage_path),
            },
        )

        for index, chunk in enumerate(chunks):
            chunk_metadata = {
                "source": "uploaded",
                "section": document_title,
                "policy_code": f"UPLOAD-{index + 1:03d}",
                "original_file_name": safe_filename,
                "content_type": content_type,
            }

            db.execute(
                text(
                    """
                    INSERT INTO document_chunks (
                        id,
                        document_id,
                        chunk_index,
                        content,
                        page_no,
                        token_count,
                        metadata,
                        created_at
                    )
                    VALUES (
                        :id,
                        :document_id,
                        :chunk_index,
                        :content,
                        NULL,
                        :token_count,
                        CAST(:metadata_json AS jsonb),
                        now()
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "chunk_index": index,
                    "content": chunk,
                    "token_count": max(1, len(chunk) // 2),
                    "metadata_json": json.dumps(chunk_metadata, ensure_ascii=False),
                },
            )

        db.execute(
            text(
                """
                UPDATE documents
                SET status = 'indexed',
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": document_id},
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "document_id": document_id,
        "title": document_title,
        "file_name": safe_filename,
        "file_type": file_type,
        "storage_path": str(storage_path),
        "status": "indexed",
        "chunk_count": len(chunks),
        "total_chars": len(extracted_text),
    }