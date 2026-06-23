"""Application settings, loaded from environment variables.

Mirrors the variable table in IMPLEMENTATION_PLAN.md §6.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- DB / model ---
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/ticket_db"
    MODEL_NAME: str = "distilbert-base-uncased-finetuned-sst-2-english"
    HF_HOME: str = "/opt/hf-cache"
    TRANSFORMERS_OFFLINE: int = 1

    # --- API surface ---
    # Empty string disables CORS (frontend is reached via same-origin nginx
    # reverse proxy; this is a fallback per IMPLEMENTATION_PLAN Decision #4).
    CORS_ALLOWED_ORIGINS: str = ""
    LOG_LEVEL: str = "info"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    @field_validator("TRANSFORMERS_OFFLINE")
    @classmethod
    def _coerce_offline_flag(cls, v: int | str) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return 1 if str(v).lower() in {"1", "true", "yes", "on"} else 0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
