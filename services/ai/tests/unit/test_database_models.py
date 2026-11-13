from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.db.models import (
    AgentExecutionTrace,
    ChunkEmbedding,
    DocumentChunk,
    FileProcessingRun,
)
from app.db.models.file_processing_run import ProcessingRunStatus


def test_ai_models_use_only_ai_schema() -> None:
    assert set(Base.metadata.tables) == {
        "ai.file_processing_runs",
        "ai.document_chunks",
        "ai.chunk_embeddings",
        "ai.agent_execution_traces",
    }
    assert all(table.schema == "ai" for table in Base.metadata.tables.values())


def test_processing_run_has_one_active_file_index() -> None:
    table = FileProcessingRun.__table__

    active_indexes = [
        index
        for index in table.indexes
        if index.name == "uq_file_processing_runs_active_file"
    ]

    assert len(active_indexes) == 1
    assert active_indexes[0].unique is True
    predicate = active_indexes[0].dialect_options["postgresql"]["where"]
    compiled = str(
        predicate.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert compiled == "ai.file_processing_runs.status = 'ACTIVE'"
    assert {status.value for status in ProcessingRunStatus} == {
        "QUEUED",
        "PROCESSING",
        "ACTIVE",
        "SUPERSEDED",
        "FAILED",
        "CANCELLED",
    }
    assert (
        FileProcessingRun.__table__.c.status.default.arg is ProcessingRunStatus.QUEUED
    )
    assert (
        str(FileProcessingRun.__table__.c.status.server_default.arg)
        == "'QUEUED'::ai.processing_run_status"
    )


def test_chunk_relationship_preserves_file_id_consistency() -> None:
    constraints = DocumentChunk.__table__.constraints

    composite_foreign_keys = [
        constraint
        for constraint in constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(composite_foreign_keys) == 1
    assert [column.name for column in composite_foreign_keys[0].columns] == [
        "processing_run_id",
        "file_id",
    ]
    target_columns = [
        element.target_fullname for element in composite_foreign_keys[0].elements
    ]
    assert target_columns == [
        "ai.file_processing_runs.id",
        "ai.file_processing_runs.file_id",
    ]


def test_embedding_has_no_fixed_vector_dimension() -> None:
    embedding_column = ChunkEmbedding.__table__.c.embedding

    assert embedding_column.type.dim is None
    assert ChunkEmbedding.__table__.c.model_version.nullable is False


def test_trace_keeps_query_reference_logical() -> None:
    assert "search_query_id" in AgentExecutionTrace.__table__.c
    assert not AgentExecutionTrace.__table__.c.search_query_id.foreign_keys
