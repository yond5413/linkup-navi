"""Configuration and settings for the backend."""

from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, List

from pydantic import Field
from pydantic_settings import BaseSettings

AVAILABLE_MODELS = [
    {"id": "arcee-ai/trinity-large-preview:free", "name": "Arcee Trinity"},
    {"id": "stepfun/step-3.5-flash:free", "name": "Step-3.5 Flash"},
    {"id": "openai/gpt-oss-120b:free", "name": "GPT-OSS 120B"},
    {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B"},
]

DEFAULT_MODEL = "arcee-ai/trinity-large-preview:free"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:0.5b"

    llm_provider: str = "openrouter"
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "arcee-ai/trinity-large-preview:free"

    linkup_api_key: Optional[str] = None

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    database_path: str = "backend.db"
    uploads_dir: str = "uploads"
    memory_dir: str = "memory"

    cohere_api_key: Optional[str] = None

    @property
    def db_path(self) -> Path:
        return Path(self.database_path)

    @property
    def memory_path(self) -> Path:
        path = Path(self.memory_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def uploads_path(self) -> Path:
        path = Path(self.uploads_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def checkpoints_path(self) -> Path:
        path = Path(self.memory_dir) / "checkpoints"
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_file = ".env", ".env.local", "env.local"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
