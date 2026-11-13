from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "File Recommendation AI Service"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    ai_service_api_key: str | None = None
    model_cache_dir: str | None = None
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    embedding_device: str = "cpu"
    ai_database_url: str = "postgresql+psycopg://localhost:5434/agentic_files"
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_batch_size: int = 16
    reranker_candidate_limit: int = 50
    workflow_max_tool_calls: int = 6
    workflow_timeout_seconds: float = 10.0
    workflow_max_refinements: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
