"""
Application settings — loaded from .env via Pydantic Settings.
All other modules import `settings` from here.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── App ────────────────────────────────────────────────────
    APP_NAME: str = "BlissyCRM"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # ── Database ───────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT (used in Module 2 — Auth) ──────────────────────────
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ───────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Rate Limiting ──────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Accept either a JSON array string or a real list."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


# Single shared instance — import this everywhere
settings = Settings()
