from pathlib import Path

MIGRATION = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "20261113_0001_initial_ai_schema.py"
)
ALEMBIC_ENV = Path(__file__).parents[2] / "alembic" / "env.py"


def test_initial_migration_is_ai_owned_only() -> None:
    migration = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE SCHEMA IF NOT EXISTS ai" in migration
    assert 'schema="ai"' in migration
    assert 'schema="app"' not in migration
    assert migration.count("op.create_table(") == 4
    assert "CREATE EXTENSION" not in migration
    assert "DROP SCHEMA" not in migration
    assert "app." not in migration
    assert migration.count('op.drop_table("') == 4
    assert 'sa.Enum(name="processing_run_status", schema="ai").drop' in migration


def test_initial_migration_contains_lifecycle_and_vector_rules() -> None:
    migration = MIGRATION.read_text(encoding="utf-8")

    assert "uq_file_processing_runs_active_file" in migration
    assert "processing_run_status" in migration
    for status in (
        "QUEUED",
        "PROCESSING",
        "ACTIVE",
        "SUPERSEDED",
        "FAILED",
        "CANCELLED",
    ):
        assert f'"{status}"' in migration
    assert "Vector()" in migration
    assert "fk_document_chunks_processing_run_file" in migration
    assert "'QUEUED'::ai.processing_run_status" in migration
    assert (
        'sa.Column("model_version", sa.String(length=128), nullable=False)' in migration
    )


def test_alembic_filter_is_ai_schema_only() -> None:
    alembic_env = ALEMBIC_ENV.read_text(encoding="utf-8")

    assert "def _object_schema(object_)" in alembic_env
    assert 'return name == "ai"' in alembic_env
    assert 'return _object_schema(object_) == "ai"' in alembic_env


def test_retrieval_index_migration_is_ai_owned() -> None:
    migration = (MIGRATION.parent / "20261113_0002_retrieval_indexes.py").read_text(
        encoding="utf-8"
    )

    assert "ai.document_chunks" in migration
    assert "to_tsvector('simple', normalized_search_text)" in migration
    assert "DROP SCHEMA" not in migration
    assert "app." not in migration
