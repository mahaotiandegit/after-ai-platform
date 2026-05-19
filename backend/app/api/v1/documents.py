from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.document_ingest_service import (
    UnsupportedDocumentTypeError,
    create_document_index_task,
    get_document_index_task,
    list_document_index_tasks,
    retry_document_index_task,
    run_document_index_task,
    run_pending_document_index_tasks,
)

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    document_id: str
    task_id: str
    title: str
    file_name: str
    file_type: str
    storage_path: str
    status: str
    document_status: str
    task_status: str
    chunk_count: int
    total_chars: int

class DocumentIndexTaskResponse(BaseModel):
    task_id: str
    document_id: str
    title: str | None = None
    file_name: str | None = None
    file_type: str | None = None
    storage_path: str | None = None
    task_type: str | None = None
    task_status: str
    document_status: str | None = None
    attempt_count: int
    max_attempts: int
    error_message: str | None = None
    result_metadata: dict
    chunk_count: int
    total_chars: int | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None

def _to_http_error(exc: Exception, *, prefix: str) -> HTTPException:
    if isinstance(exc, UnsupportedDocumentTypeError):
        return HTTPException(status_code=400, detail=str(exc))

    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))

    return HTTPException(status_code=500, detail=f"{prefix}：{exc}")

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

        result = create_document_index_task(
            db,
            filename=file.filename,
            content=content,
            title=title,
            content_type=file.content_type,
        )

        return result

    except Exception as exc:
        raise _to_http_error(exc, prefix="文档上传创建索引任务失败") from exc

    finally:
        await file.close()

@router.get("/index-tasks")
def list_index_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    try:
        return {
            "items": list_document_index_tasks(
                db,
                limit=limit,
                offset=offset,
            )
        }

    except Exception as exc:
        raise _to_http_error(exc, prefix="查询文档索引任务列表失败") from exc
    
@router.post("/index-tasks/run-pending")
def run_pending_index_tasks(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    try:
        return run_pending_document_index_tasks(db, limit=limit)

    except Exception as exc:
        raise _to_http_error(exc, prefix="执行待处理文档索引任务失败") from exc
    

@router.get("/index-tasks/{task_id}", response_model=DocumentIndexTaskResponse)
def get_index_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    try:
        return get_document_index_task(db, task_id)

    except Exception as exc:
        raise _to_http_error(exc, prefix="查询文档索引任务失败") from exc
    
@router.post("/index-tasks/{task_id}/run", response_model=DocumentIndexTaskResponse)
def run_index_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    try:
        return run_document_index_task(db, task_id)

    except Exception as exc:
        raise _to_http_error(exc, prefix="执行文档索引任务失败") from exc
    
@router.post("/index-tasks/{task_id}/retry", response_model=DocumentIndexTaskResponse)
def retry_index_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    try:
        return retry_document_index_task(db, task_id)

    except Exception as exc:
        raise _to_http_error(exc, prefix="重试文档索引任务失败") from exc