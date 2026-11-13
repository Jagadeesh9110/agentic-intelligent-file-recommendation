from __future__ import annotations

import math
from contextlib import AbstractContextManager
from uuid import uuid4

import pytest

from app.db.models.chunk_embedding import ChunkEmbedding
from app.db.models.document_chunk import DocumentChunk
from app.db.models.file_processing_run import FileProcessingRun, ProcessingRunStatus
from app.embeddings.service import (
    EMBEDDING_DIMENSION,
    EmbeddingGenerationError,
    EmbeddingService,
)
from app.embeddings.workflow import (
    EmbeddingPersistenceError,
    embed_persist_and_activate,
    persist_embeddings,
)


class _FakeModel:
    def __init__(self, vector_size: int = EMBEDDING_DIMENSION) -> None:
        self.vector_size = vector_size
        self.calls: list[tuple[list[str], int]] = []

    def encode(self, sentences: list[str], **kwargs):
        self.calls.append((sentences, kwargs["batch_size"]))
        return [[0.25] * self.vector_size for _ in sentences]


def _chunk(file_id, processing_run_id, text: str = "chunk text") -> DocumentChunk:
    return DocumentChunk(
        id=uuid4(),
        file_id=file_id,
        processing_run_id=processing_run_id,
        chunk_ordinal=0,
        extracted_text=text,
        normalized_search_text=text,
    )


def _run(file_id, status=ProcessingRunStatus.PROCESSING) -> FileProcessingRun:
    return FileProcessingRun(
        id=uuid4(),
        file_id=file_id,
        source_checksum="checksum",
        status=status,
    )


def test_embedding_generation_returns_valid_vectors_in_batches() -> None:
    model = _FakeModel()
    service = EmbeddingService(model=model, batch_size=2)
    file_id = uuid4()
    run_id = uuid4()
    chunks = [_chunk(file_id, run_id, f"text {index}") for index in range(3)]

    generated = service.generate(chunks)

    assert len(generated) == 3
    assert all(len(item.vector) == EMBEDDING_DIMENSION for item in generated)
    assert [item.chunk for item in generated] == chunks
    assert model.calls == [(["text 0", "text 1", "text 2"], 2)]


def test_embedding_model_is_loaded_once_per_service() -> None:
    model = _FakeModel()
    service = EmbeddingService(model=model)
    file_id = uuid4()
    run_id = uuid4()
    chunk = _chunk(file_id, run_id)

    service.generate([chunk])
    service.generate([chunk])

    assert model.calls == [(["chunk text"], 32), (["chunk text"], 32)]


@pytest.mark.parametrize(
    "vector_size",
    [EMBEDDING_DIMENSION - 1, EMBEDDING_DIMENSION + 1],
)
def test_embedding_generation_rejects_wrong_dimensions(vector_size: int) -> None:
    service = EmbeddingService(model=_FakeModel(vector_size))
    chunk = _chunk(uuid4(), uuid4())

    with pytest.raises(EmbeddingGenerationError, match="exactly 384"):
        service.generate([chunk])


def test_embedding_generation_rejects_non_finite_values() -> None:
    class NonFiniteModel(_FakeModel):
        def encode(self, sentences: list[str], **kwargs):
            return [[math.nan] * EMBEDDING_DIMENSION for _ in sentences]

    service = EmbeddingService(model=NonFiniteModel())

    with pytest.raises(EmbeddingGenerationError, match="non-finite"):
        service.generate([_chunk(uuid4(), uuid4())])


def test_embedding_generation_rejects_empty_text_and_allows_empty_input() -> None:
    service = EmbeddingService(model=_FakeModel())

    assert service.generate([]) == ()
    with pytest.raises(EmbeddingGenerationError, match="no text"):
        service.generate([_chunk(uuid4(), uuid4(), " \n\t ")])


class _Transaction(AbstractContextManager[None]):
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    def __enter__(self) -> None:
        return None

    def __exit__(self, exception_type, exception, traceback) -> bool:
        if exception_type is not None:
            self.session.rollback()
        return False


class _FakeSession:
    def __init__(
        self,
        scalar_results: list[object | None],
        *,
        fail_on_flush: bool = False,
    ) -> None:
        self.scalar_results = iter(scalar_results)
        self.fail_on_flush = fail_on_flush
        self.added: list[ChunkEmbedding] = []
        self.rollback_count = 0

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, exception_type, exception, traceback) -> None:
        return None

    def begin(self) -> _Transaction:
        return _Transaction(self)

    def scalar(self, statement):
        return next(self.scalar_results)

    def add(self, value: ChunkEmbedding) -> None:
        self.added.append(value)

    def flush(self) -> None:
        if self.fail_on_flush:
            raise RuntimeError("persistence failure")

    def rollback(self) -> None:
        self.rollback_count += 1
        self.added.clear()


def test_persistence_is_transactional_and_stores_embedding() -> None:
    file_id = uuid4()
    run = _run(file_id)
    chunk = _chunk(file_id, run.id)
    generated = EmbeddingService(model=_FakeModel()).generate([chunk])
    session = _FakeSession([run, chunk, None])

    persisted = persist_embeddings(
        session,
        file_id=file_id,
        processing_run_id=run.id,
        embeddings=generated,
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_version="1",
    )

    assert persisted == 1
    assert session.added[0].chunk_id == chunk.id
    assert session.added[0].model_version == "1"


def test_persistence_skips_existing_embedding() -> None:
    file_id = uuid4()
    run = _run(file_id)
    chunk = _chunk(file_id, run.id)
    generated = EmbeddingService(model=_FakeModel()).generate([chunk])
    existing = ChunkEmbedding(
        id=uuid4(),
        chunk_id=chunk.id,
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_version="1",
        embedding=[0.1] * EMBEDDING_DIMENSION,
    )
    session = _FakeSession([run, chunk, existing])

    persisted = persist_embeddings(
        session,
        file_id=file_id,
        processing_run_id=run.id,
        embeddings=generated,
        model_name=existing.model_name,
        model_version=existing.model_version,
    )

    assert persisted == 0
    assert session.added == []


def test_persistence_rejects_chunk_from_another_processing_run() -> None:
    file_id = uuid4()
    run = _run(file_id)
    chunk = _chunk(file_id, uuid4())
    generated = EmbeddingService(model=_FakeModel()).generate([chunk])
    session = _FakeSession([run, None])

    with pytest.raises(EmbeddingPersistenceError, match="does not belong"):
        persist_embeddings(
            session,
            file_id=file_id,
            processing_run_id=run.id,
            embeddings=generated,
            model_name="model",
            model_version="1",
        )


def test_persistence_rolls_back_on_flush_failure() -> None:
    file_id = uuid4()
    run = _run(file_id)
    chunk = _chunk(file_id, run.id)
    generated = EmbeddingService(model=_FakeModel()).generate([chunk])
    session = _FakeSession([run, chunk, None], fail_on_flush=True)

    with pytest.raises(RuntimeError, match="persistence failure"):
        persist_embeddings(
            session,
            file_id=file_id,
            processing_run_id=run.id,
            embeddings=generated,
            model_name="model",
            model_version="1",
        )

    assert session.rollback_count == 1
    assert session.added == []


def test_persistence_rejects_non_processing_run() -> None:
    file_id = uuid4()
    run = _run(file_id, ProcessingRunStatus.ACTIVE)
    session = _FakeSession([run])

    with pytest.raises(EmbeddingPersistenceError, match="PROCESSING"):
        persist_embeddings(
            session,
            file_id=file_id,
            processing_run_id=run.id,
            embeddings=(),
            model_name="model",
            model_version="1",
        )


def test_workflow_activates_only_after_persistence(monkeypatch) -> None:
    file_id = uuid4()
    run = _run(file_id)
    chunk = _chunk(file_id, run.id)
    service = EmbeddingService(model=_FakeModel())
    sessions = [_FakeSession([run, chunk, None]), _FakeSession([])]
    activation_calls = []

    def fake_activate(session, **kwargs):
        activation_calls.append(kwargs)

    monkeypatch.setattr(
        "app.embeddings.workflow.activate_processing_run", fake_activate
    )
    persisted = embed_persist_and_activate(
        lambda: sessions.pop(0),
        file_id=file_id,
        processing_run_id=run.id,
        chunks=[chunk],
        embedding_service=service,
    )

    assert persisted == 1
    assert activation_calls == [{"file_id": file_id, "processing_run_id": run.id}]
