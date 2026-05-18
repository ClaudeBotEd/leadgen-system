"""Typed configuration loaded from environment / .env files.

All settings are namespaced with `LLM_COUNCIL_*` except OPENROUTER_API_KEY,
which keeps its canonical name so it can be shared with other tooling.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings — fail fast on import if required values are missing."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Secrets ---
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")

    # --- Server ---
    host: str = Field(default="0.0.0.0", alias="LLM_COUNCIL_HOST")
    port: int = Field(default=8001, alias="LLM_COUNCIL_PORT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", alias="LLM_COUNCIL_LOG_LEVEL"
    )
    env: Literal["development", "production", "test"] = Field(
        default="development", alias="LLM_COUNCIL_ENV"
    )

    # --- CORS ---
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
        ],
        alias="LLM_COUNCIL_CORS_ORIGINS",
    )

    # --- Storage ---
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/llm_council.db",
        alias="LLM_COUNCIL_DATABASE_URL",
    )

    # --- Models ---
    council_models: List[str] = Field(
        default_factory=lambda: [
            "openai/gpt-4.1-mini",
            "google/gemini-2.5-flash",
            "anthropic/claude-3.5-haiku",
        ],
        alias="LLM_COUNCIL_MODELS",
    )
    chairman_model: str = Field(
        default="openai/gpt-4.1", alias="LLM_COUNCIL_CHAIRMAN_MODEL"
    )
    title_model: str = Field(
        default="google/gemini-2.5-flash", alias="LLM_COUNCIL_TITLE_MODEL"
    )

    # --- HTTP / API ---
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"
    request_timeout_seconds: float = Field(
        default=120.0, alias="LLM_COUNCIL_REQUEST_TIMEOUT_SECONDS"
    )
    rate_limit_per_minute: int = Field(
        default=60, alias="LLM_COUNCIL_RATE_LIMIT_PER_MINUTE"
    )

    # --- Optional bearer-token gate for n8n / CRM ---
    api_token: str = Field(default="", alias="LLM_COUNCIL_API_TOKEN")

    @field_validator("cors_origins", "council_models", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def assert_runtime_ready(self) -> None:
        """Verify minimal runtime config. Call before serving requests, not at import."""
        if not self.openrouter_api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env.local "
                "and fill in your key from https://openrouter.ai/keys"
            )
        if not self.council_models:
            raise RuntimeError("At least one council model must be configured.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — call from anywhere."""
    return Settings()
