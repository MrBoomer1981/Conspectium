"""Application settings, read from the environment once at import time."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# (input, output) price in USD per million tokens.
# A model missing from this dict means unknown cost, not an error.
PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    "gemini-3.5-flash-lite": (0.30, 2.50),
    # Retired: closed to new accounts since September 2026, kept for the
    # ai_calls rows already written against it and for any key that still
    # has access.
    "gemini-2.5-flash-lite": (0.10, 0.40),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required: a missing one must crash at startup, not on the first request.
    BOT_TOKEN: str
    DATABASE_URL: str
    GEMINI_API_KEY: str
    WEBHOOK_URL: str
    WEBHOOK_SECRET: str

    AI_ENABLED: bool = True
    DAILY_PAGES_PER_USER: int = 30
    DAILY_COST_LIMIT_USD: float = 5
    VISION_RUNS: int = 3
    VISION_MODEL: str = "gemini-3.5-flash-lite"
    # Which prompt file vision.py loads at import. A variant can be tried on
    # the deployed bot by changing this one variable, and rolled back the same
    # way, without a code change in between.
    PROMPT_FILE: str = "prompts-v3.md"
    MIN_MARKDOWN_LEN: int = 40
    MAX_ALBUM_PAGES: int = 10
    LOG_LEVEL: str = "INFO"

    @field_validator("DATABASE_URL")
    @classmethod
    def _asyncpg_scheme(cls, v: str) -> str:
        """Railway's Postgres addon hands out `postgresql://`, SQLAlchemy with
        asyncpg needs `postgresql+asyncpg://`. The variable itself is managed by
        the addon and must stay untouched, so the scheme is fixed here."""
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("VISION_RUNS")
    @classmethod
    def _at_least_two_runs(cls, v: int) -> int:
        # Fewer than two runs leaves nothing to compare against.
        if v < 2:
            raise ValueError("VISION_RUNS must be >= 2")
        return v


settings = Settings()
