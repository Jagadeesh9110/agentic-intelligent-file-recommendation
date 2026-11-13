"""Create the AI-owned schema and tables."""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261113_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS ai"))

    processing_status = postgresql.ENUM(
        "QUEUED",
        "PROCESSING",
        "ACTIVE",
        "SUPERSEDED",
        "FAILED",
        "CANCELLED",
        name="processing_run_status",
        schema="ai",
        create_type=False,
    )
    processing_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "file_processing_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_checksum", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            processing_status,
            server_default=sa.text("'QUEUED'::ai.processing_run_status"),
            nullable=False,
        ),
        sa.Column("processing_config", postgresql.JSONB(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "file_id", name="uq_file_processing_runs_id_file_id"),
        schema="ai",
    )
    op.create_index(
        "uq_file_processing_runs_active_file",
        "file_processing_runs",
        ["file_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        schema="ai",
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_ordinal", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        sa.Column("section_name", sa.String(length=255), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("normalized_search_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("character_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id", "file_id"],
            ["ai.file_processing_runs.id", "ai.file_processing_runs.file_id"],
            name="fk_document_chunks_processing_run_file",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processing_run_id",
            "chunk_ordinal",
            name="uq_document_chunks_processing_run_ordinal",
        ),
        schema="ai",
    )

    op.create_table(
        "chunk_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["ai.document_chunks.id"],
            name="fk_chunk_embeddings_chunk",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chunk_id",
            "model_name",
            "model_version",
            name="uq_chunk_embeddings_chunk_model",
        ),
        schema="ai",
    )

    op.create_table(
        "agent_execution_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_query_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("normalized_query", sa.Text(), nullable=True),
        sa.Column("filters", postgresql.JSONB(), nullable=True),
        sa.Column("selected_strategy", sa.String(length=32), nullable=True),
        sa.Column("attempts", postgresql.JSONB(), nullable=True),
        sa.Column("tool_decisions", postgresql.JSONB(), nullable=True),
        sa.Column("result_counts", postgresql.JSONB(), nullable=True),
        sa.Column("timings", postgresql.JSONB(), nullable=True),
        sa.Column("model_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("termination_reason", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="ai",
    )


def downgrade() -> None:
    op.drop_table("agent_execution_traces", schema="ai")
    op.drop_table("chunk_embeddings", schema="ai")
    op.drop_table("document_chunks", schema="ai")
    op.drop_index(
        "uq_file_processing_runs_active_file",
        table_name="file_processing_runs",
        schema="ai",
    )
    op.drop_table("file_processing_runs", schema="ai")
    sa.Enum(name="processing_run_status", schema="ai").drop(
        op.get_bind(), checkfirst=True
    )
