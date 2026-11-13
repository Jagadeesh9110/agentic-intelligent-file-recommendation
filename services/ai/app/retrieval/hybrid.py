from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.chunk_embedding import ChunkEmbedding
from app.db.models.document_chunk import DocumentChunk
from app.db.models.file_processing_run import FileProcessingRun, ProcessingRunStatus
from app.embeddings.service import EmbeddingService

DEFAULT_RRF_CONSTANT = 60


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunk_id: UUID
    file_id: UUID
    text: str
    chunk_ordinal: int
    page_number: int | None
    sheet_name: str | None
    section_name: str | None
    score: float
    retrieval_sources: tuple[str, ...]
    fused_score: float | None = None


def rrf_fuse(
    full_text_results: list[RetrievalResult] | tuple[RetrievalResult, ...],
    semantic_results: list[RetrievalResult] | tuple[RetrievalResult, ...],
    *,
    constant: int = DEFAULT_RRF_CONSTANT,
    limit: int | None = None,
) -> tuple[RetrievalResult, ...]:
    """Fuse ranked result lists using Reciprocal Rank Fusion."""
    if constant <= 0:
        raise ValueError("RRF constant must be greater than zero.")
    if limit is not None and limit <= 0:
        raise ValueError("Retrieval limit must be greater than zero.")

    fused: dict[UUID, RetrievalResult] = {}
    scores: dict[UUID, float] = {}
    sources: dict[UUID, set[str]] = {}
    for source, results in (
        ("full_text", full_text_results),
        ("semantic", semantic_results),
    ):
        for rank, result in enumerate(results, start=1):
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + (
                1.0 / (constant + rank)
            )
            sources.setdefault(result.chunk_id, set()).add(source)
            fused.setdefault(result.chunk_id, result)

    ordered = sorted(
        fused.values(),
        key=lambda result: (-scores[result.chunk_id], str(result.chunk_id)),
    )
    fused_results = tuple(
        RetrievalResult(
            chunk_id=result.chunk_id,
            file_id=result.file_id,
            text=result.text,
            chunk_ordinal=result.chunk_ordinal,
            page_number=result.page_number,
            sheet_name=result.sheet_name,
            section_name=result.section_name,
            score=result.score,
            retrieval_sources=tuple(sorted(sources[result.chunk_id])),
            fused_score=scores[result.chunk_id],
        )
        for result in ordered
    )
    return fused_results[:limit] if limit is not None else fused_results


class HybridRetriever:
    """Retrieve active document chunks with keyword, semantic, and fused ranking."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        *,
        rrf_constant: int = DEFAULT_RRF_CONSTANT,
    ) -> None:
        if rrf_constant <= 0:
            raise ValueError("RRF constant must be greater than zero.")
        self.embedding_service = embedding_service
        self.rrf_constant = rrf_constant

    def full_text(
        self, session: Session, query: str, *, limit: int = 10
    ) -> tuple[RetrievalResult, ...]:
        if not query.strip():
            return ()
        _validate_limit(limit)
        ts_query = func.websearch_to_tsquery("simple", query.strip())
        ts_vector = func.to_tsvector("simple", DocumentChunk.normalized_search_text)
        rank = func.ts_rank_cd(ts_vector, ts_query).label("rank")
        statement = (
            select(DocumentChunk, rank)
            .join(
                FileProcessingRun,
                FileProcessingRun.id == DocumentChunk.processing_run_id,
            )
            .where(
                FileProcessingRun.file_id == DocumentChunk.file_id,
                FileProcessingRun.status == ProcessingRunStatus.ACTIVE,
                ts_vector.op("@@")(ts_query),
            )
            .order_by(rank.desc(), DocumentChunk.id)
            .limit(limit)
        )
        rows = session.execute(statement).all()
        return tuple(
            _result_from_row(chunk, float(rank_value), "full_text")
            for chunk, rank_value in rows
        )

    def semantic(
        self, session: Session, query: str, *, limit: int = 10
    ) -> tuple[RetrievalResult, ...]:
        if not query.strip():
            return ()
        _validate_limit(limit)
        query_vector = self.embedding_service.generate_query_embedding(query)
        distance = ChunkEmbedding.embedding.cosine_distance(query_vector).label(
            "distance"
        )
        statement = (
            select(DocumentChunk, distance)
            .join(
                ChunkEmbedding,
                ChunkEmbedding.chunk_id == DocumentChunk.id,
            )
            .join(
                FileProcessingRun,
                FileProcessingRun.id == DocumentChunk.processing_run_id,
            )
            .where(
                FileProcessingRun.file_id == DocumentChunk.file_id,
                FileProcessingRun.status == ProcessingRunStatus.ACTIVE,
            )
            .order_by(distance, DocumentChunk.id)
            .limit(limit)
        )
        rows = session.execute(statement).all()
        return tuple(
            _result_from_row(chunk, 1.0 - float(distance_value), "semantic")
            for chunk, distance_value in rows
        )

    def hybrid(
        self,
        session: Session,
        query: str,
        *,
        limit: int = 10,
        rrf_constant: int | None = None,
    ) -> tuple[RetrievalResult, ...]:
        if not query.strip():
            return ()
        _validate_limit(limit)
        full_text_results = self.full_text(session, query, limit=limit)
        semantic_results = self.semantic(session, query, limit=limit)
        return rrf_fuse(
            full_text_results,
            semantic_results,
            constant=rrf_constant or self.rrf_constant,
            limit=limit,
        )


def _validate_limit(limit: int) -> None:
    if limit <= 0:
        raise ValueError("Retrieval limit must be greater than zero.")


def _result_from_row(
    chunk: DocumentChunk,
    score: float,
    source: str,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk.id,
        file_id=chunk.file_id,
        text=chunk.extracted_text,
        chunk_ordinal=chunk.chunk_ordinal,
        page_number=chunk.page_number,
        sheet_name=chunk.sheet_name,
        section_name=chunk.section_name,
        score=score,
        retrieval_sources=(source,),
    )
