from __future__ import annotations

import hashlib
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models.document_chunk import DocumentChunk
from app.db.models.file_processing_run import FileProcessingRun, ProcessingRunStatus
from app.documents.chunking import chunk_document
from app.documents.extraction import extract_document
from app.embeddings.service import EmbeddingService
from app.embeddings.workflow import embed_persist_and_activate


class DocumentIngestionError(RuntimeError):
    """Raised when document ingestion cannot be completed."""


def ingest_document(
    session_factory: Callable[[], Session] | sessionmaker,
    *,
    file_id: UUID,
    filename: str,
    content: bytes,
    embedding_service: EmbeddingService,
    expected_checksum: str | None = None,
) -> dict[str, object]:
    """Extract, chunk, embed, and activate one uploaded document version."""

    if not content:
        raise DocumentIngestionError("Uploaded file is empty.")

    checksum = hashlib.sha256(content).hexdigest()
    if expected_checksum and checksum.lower() != expected_checksum.lower():
        raise DocumentIngestionError("Uploaded file checksum does not match.")

    extracted_document = extract_document(content, filename)
    chunks = chunk_document(extracted_document)

    if not chunks:
        raise DocumentIngestionError("No searchable text was extracted.")

    processing_run_id = None

    try:
        with session_factory() as session:
            with session.begin():
                processing_run = FileProcessingRun(
                    file_id=file_id,
                    source_checksum=checksum,
                    status=ProcessingRunStatus.PROCESSING,
                    processing_config={
                        "embedding_model": embedding_service.model_name,
                        "embedding_model_version": embedding_service.model_version,
                        "chunk_count": len(chunks),
                    },
                )
                session.add(processing_run)
                session.flush()
                processing_run_id = processing_run.id

                document_chunks = [
                    DocumentChunk(
                        processing_run_id=processing_run_id,
                        file_id=file_id,
                        chunk_ordinal=chunk.chunk_ordinal,
                        page_number=chunk.page_number,
                        sheet_name=chunk.sheet_name,
                        section_name=chunk.section_name,
                        extracted_text=chunk.extracted_text,
                        normalized_search_text=chunk.normalized_search_text,
                        token_count=chunk.token_count,
                        character_count=chunk.character_count,
                    )
                    for chunk in chunks
                ]
                session.add_all(document_chunks)
                session.flush()

        with session_factory() as session:
            persisted_chunks = session.scalars(
                select(DocumentChunk)
                .where(
                    DocumentChunk.processing_run_id == processing_run_id,
                    DocumentChunk.file_id == file_id,
                )
                .order_by(DocumentChunk.chunk_ordinal)
            ).all()

        persisted_embeddings = embed_persist_and_activate(
            session_factory,
            file_id=file_id,
            processing_run_id=processing_run_id,
            chunks=persisted_chunks,
            embedding_service=embedding_service,
        )

        return {
            "file_id": str(file_id),
            "processing_run_id": str(processing_run_id),
            "status": "ACTIVE",
            "checksum": checksum,
            "chunk_count": len(chunks),
            "embedding_count": persisted_embeddings,
        }

    except Exception as error:
        if processing_run_id is not None:
            try:
                with session_factory() as session:
                    with session.begin():
                        failed_run = session.scalar(
                            select(FileProcessingRun).where(
                                FileProcessingRun.id == processing_run_id,
                                FileProcessingRun.file_id == file_id,
                            )
                        )
                        if (
                            failed_run is not None
                            and failed_run.status == ProcessingRunStatus.PROCESSING
                        ):
                            failed_run.status = ProcessingRunStatus.FAILED
                            failed_run.error_details = str(error)[:4000]
            except Exception as failure_error:
                raise DocumentIngestionError(
                    "Ingestion failed, and the processing run could not be "
                    "marked as FAILED."
                ) from failure_error

        raise DocumentIngestionError(f"Document ingestion failed: {error}") from error
