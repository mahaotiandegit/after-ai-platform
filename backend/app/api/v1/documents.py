from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.document_ingest_service import (
    UnsupportedDocumentTypeError,
    ingest_document_bytes,
)


router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    document_id: str
    title: str
    file_name: str
    file_type: str
    storage_path: str
    status: str
    chunk_count: int
    total_chars: int


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名。")

    try:
        content = await file.read()

        result = ingest_document_bytes(
            db,
            filename=file.filename,
            content=content,
            title=title,
            content_type=file.content_type,
        )

        return result

    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文档上传解析失败：{exc}") from exc

    finally:
        await file.close()