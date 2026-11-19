from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.routes import verify_ai_service_key
from app.db.base import session_factory
from app.documents.ingestion import DocumentIngestionError, ingest_document
from app.embeddings.service import EmbeddingService

router = APIRouter(
    prefix="/api/v1/files",
    tags=["file-ingestion"],
    dependencies=[Depends(verify_ai_service_key)],
)

MAX_FILE_SIZE = 25 * 1024 * 1024


def get_embedding_service() -> EmbeddingService:
    from app.main import embedding_service

    return embedding_service


@router.post("/ingest")
async def ingest_file(
    file_id: UUID = Form(...),  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
) -> dict[str, object]:
    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Maximum upload size is 25 MB.",
        )

    try:
        return ingest_document(
            session_factory,
            file_id=file_id,
            filename=file.filename or "",
            content=content,
            embedding_service=get_embedding_service(),
        )
    except DocumentIngestionError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
