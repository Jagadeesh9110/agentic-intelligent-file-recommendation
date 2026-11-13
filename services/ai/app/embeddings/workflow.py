from __future__ import annotations

from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models.chunk_embedding import ChunkEmbedding
from app.db.models.document_chunk import DocumentChunk
from app.db.models.file_processing_run import FileProcessingRun, ProcessingRunStatus
from app.db.processing_runs import activate_processing_run
from app.embeddings.service import EmbeddingService, GeneratedEmbedding


class EmbeddingPersistenceError(ValueError):
    """Raised when embeddings cannot be safely persisted."""


def persist_embeddings(
    session: Session,
    *,
    file_id: UUID,
    processing_run_id: UUID,
    embeddings: Sequence[GeneratedEmbedding],
    model_name: str,
    model_version: str,
) -> int:
    """Persist embeddings in an owned transaction for one processing run."""
    with session.begin():
        processing_run = session.scalar(
            select(FileProcessingRun).where(
                FileProcessingRun.id == processing_run_id,
                FileProcessingRun.file_id == file_id,
            )
        )
        if processing_run is None:
            raise EmbeddingPersistenceError(
                "The processing run does not belong to the supplied file."
            )
        if processing_run.status is not ProcessingRunStatus.PROCESSING:
            raise EmbeddingPersistenceError(
                "Embeddings can only be persisted for a PROCESSING run."
            )

        persisted = 0
        seen_chunk_ids: set[UUID] = set()
        for generated in embeddings:
            chunk_id = generated.chunk.id
            if chunk_id is None or chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            chunk = session.scalar(
                select(DocumentChunk).where(
                    DocumentChunk.id == chunk_id,
                    DocumentChunk.processing_run_id == processing_run_id,
                    DocumentChunk.file_id == file_id,
                )
            )
            if chunk is None:
                raise EmbeddingPersistenceError(
                    f"Chunk {chunk_id} does not belong to the processing run."
                )
            existing = session.scalar(
                select(ChunkEmbedding).where(
                    ChunkEmbedding.chunk_id == chunk_id,
                    ChunkEmbedding.model_name == model_name,
                    ChunkEmbedding.model_version == model_version,
                )
            )
            if existing is None:
                session.add(
                    ChunkEmbedding(
                        chunk_id=chunk_id,
                        model_name=model_name,
                        model_version=model_version,
                        embedding=list(generated.vector),
                    )
                )
                persisted += 1
        session.flush()
        return persisted


def embed_persist_and_activate(
    session_factory: Callable[[], Session] | sessionmaker,
    *,
    file_id: UUID,
    processing_run_id: UUID,
    chunks: Sequence[DocumentChunk],
    embedding_service: EmbeddingService,
) -> int:
    """Generate, persist, and activate a completed processing run.

    Persistence and activation use separate fresh sessions because
    ``activate_processing_run`` owns its transaction.
    """
    embeddings = embedding_service.generate(tuple(chunks))
    with session_factory() as persistence_session:
        persisted = persist_embeddings(
            persistence_session,
            file_id=file_id,
            processing_run_id=processing_run_id,
            embeddings=embeddings,
            model_name=embedding_service.model_name,
            model_version=embedding_service.model_version,
        )
    with session_factory() as activation_session:
        activate_processing_run(
            activation_session,
            file_id=file_id,
            processing_run_id=processing_run_id,
        )
    return persisted
