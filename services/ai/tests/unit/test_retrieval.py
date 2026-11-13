from __future__ import annotations

from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.db.models.document_chunk import DocumentChunk
from app.retrieval.hybrid import HybridRetriever, RetrievalResult, rrf_fuse


class _Result:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return self.rows


class _Session:
    def __init__(self, results=None) -> None:
        self.results = iter(results or [])
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return next(self.results)


class _QueryEmbeddingService:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def generate_query_embedding(self, query: str) -> tuple[float, ...]:
        self.queries.append(query)
        return (0.1,) * 384


def _chunk(*, text: str = "chunk text") -> DocumentChunk:
    return DocumentChunk(
        id=uuid4(),
        file_id=uuid4(),
        processing_run_id=uuid4(),
        chunk_ordinal=3,
        page_number=2,
        sheet_name="Summary",
        section_name="Overview",
        extracted_text=text,
        normalized_search_text=text,
    )


def _result(chunk: DocumentChunk, source: str, score: float) -> RetrievalResult:
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


def test_full_text_retrieval_maps_ranked_rows_and_active_filter() -> None:
    chunk = _chunk()
    session = _Session([_Result([(chunk, 0.75)])])
    retriever = HybridRetriever(_QueryEmbeddingService())

    results = retriever.full_text(session, "important terms", limit=5)

    assert results[0].chunk_id == chunk.id
    assert results[0].retrieval_sources == ("full_text",)
    assert results[0].page_number == 2
    statement = session.statements[0]
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert "file_processing_runs.status" in compiled
    assert statement._limit_clause is not None


def test_semantic_retrieval_uses_query_embedding_and_active_filter() -> None:
    chunk = _chunk()
    embedding_service = _QueryEmbeddingService()
    session = _Session([_Result([(chunk, 0.2)])])
    retriever = HybridRetriever(embedding_service)

    results = retriever.semantic(session, "semantic query", limit=4)

    assert embedding_service.queries == ["semantic query"]
    assert results[0].score == 0.8
    assert results[0].sheet_name == "Summary"
    compiled = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert "file_processing_runs.status" in compiled


def test_rrf_deduplicates_and_combines_sources() -> None:
    shared = _chunk(text="shared")
    keyword_only = _chunk(text="keyword")
    semantic_only = _chunk(text="semantic")

    results = rrf_fuse(
        [_result(shared, "full_text", 1.0), _result(keyword_only, "full_text", 0.5)],
        [_result(shared, "semantic", 0.9), _result(semantic_only, "semantic", 0.8)],
        constant=60,
    )

    assert [result.chunk_id for result in results].count(shared.id) == 1
    assert results[0].chunk_id == shared.id
    assert results[0].retrieval_sources == ("full_text", "semantic")
    assert results[0].fused_score == (1 / 61) + (1 / 61)


def test_empty_query_returns_no_results_without_database_or_model_calls() -> None:
    embedding_service = _QueryEmbeddingService()
    session = _Session()
    retriever = HybridRetriever(embedding_service)

    assert retriever.hybrid(session, "   ") == ()
    assert session.statements == []
    assert embedding_service.queries == []


def test_hybrid_handles_empty_result_from_either_retrieval_method() -> None:
    chunk = _chunk()
    embedding_service = _QueryEmbeddingService()
    session = _Session([_Result([]), _Result([(chunk, 0.1)])])
    retriever = HybridRetriever(embedding_service)

    results = retriever.hybrid(session, "query")

    assert len(results) == 1
    assert results[0].retrieval_sources == ("semantic",)
