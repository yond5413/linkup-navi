"""Configuration and settings for the backend."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:0.5b"

    llm_provider: str = "openrouter"
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "arcee-ai/trinity-large-preview:free"

    linkup_api_key: Optional[str] = None
    linkup_api_url: str = "https://api.linkup.com/v1"

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    database_path: str = "backend.db"
    uploads_dir: str = "uploads"

    @property
    def db_path(self) -> Path:
        return Path(self.database_path)

    @property
    def uploads_path(self) -> Path:
        path = Path(self.uploads_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_file = ".env", ".env.local"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
