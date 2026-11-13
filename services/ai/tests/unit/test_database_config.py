from app.config.settings import settings
from app.db.base import Base, engine, session_factory


def test_database_url_is_configured_without_credentials_in_source() -> None:
    assert settings.ai_database_url.startswith("postgresql+psycopg://")
    assert "localhost:5434/agentic_files" in settings.ai_database_url


def test_database_engine_and_session_factory_are_configured() -> None:
    assert engine.url.drivername == "postgresql+psycopg"
    assert session_factory.kw["expire_on_commit"] is False
    assert Base.metadata.schema == "ai"


def test_embedding_configuration_uses_local_cpu_defaults() -> None:
    assert settings.embedding_model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.embedding_batch_size > 0
    assert settings.embedding_device == "cpu"
