from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "File Recommendation AI Service"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    ai_service_api_key: str | None = None
    model_cache_dir: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
