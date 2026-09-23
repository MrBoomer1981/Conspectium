"""Application settings, read from the environment once at import time."""

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# (input, output) price in USD per million tokens.
# A model missing from this dict means unknown cost, not an error.
PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    # The output rate is what the day's spend actually turns on: this model
    # thinks about four times as long as it speaks, measured at 15778 thinking
    # tokens against 4029 of answer over one three-page album, and thinking is
    # billed as output. Roughly two thirds of an album's price is the part
    # nobody could see until ai_calls.tokens_thought existed.
    "gemini-3.8-flash": (0.375, 1.875),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    # Retired: closed to new accounts since September 2026, kept for the
    # ai_calls rows already written against it and for any key that still
    # has access.
    "gemini-2.5-flash-lite": (0.10, 0.40),
}

# The settings whose model has to be priced for DAILY_COST_LIMIT_USD to mean
# anything. Both of them: half the spend going out unpriced breaks the cap just
# as quietly as all of it. One list, because the validator below refuses to
# start on it and the startup log warns about it, and two loops that have to
# agree is how they came to disagree — the warning looked at VISION_MODEL alone
# while the validator looked at both.
PRICED_MODEL_SETTINGS = ("VISION_MODEL", "COMPOSE_MODEL")


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
    # How long one model call may take. The only one of the three timeouts
    # that is a setting: 30 s was tuned for a model answering in ~6 s, and a
    # slower one has to move the consensus and album ceilings with it, so
    # those are computed from this rather than written down beside it.
    VISION_CALL_TIMEOUT_S: int = 30
    # Two knobs on the model call that have never been set, so neither has
    # ever been measured. "unset" means the field is not sent at all, which
    # is bit-for-bit what the call did before they existed.
    VISION_MEDIA_RESOLUTION: str = "unset"
    VISION_THINKING_LEVEL: str = "unset"
    # Stage two: the trusted transcription, formatted. Off by default — it is
    # an experiment behind a switch, like PROMPT_FILE, and turning it on is a
    # decision rather than something that happens on a deploy.
    COMPOSE_ENABLED: bool = False
    COMPOSE_MODEL: str = "gemini-3.5-flash-lite"
    COMPOSE_PROMPT_FILE: str = "prompts-compose-v1.md"
    # Which prompt file vision.py loads at import. A variant can be tried on
    # the deployed bot by changing this one variable, and rolled back the same
    # way, without a code change in between.
    PROMPT_FILE: str = "prompts-v3.md"
    # Compression before the model sees the page. 1500 px and quality 85 are
    # what rule 2 of CLAUDE.md fixed, on evidence from a model that has since
    # been retired; these are here so a larger page can be measured against
    # the same album rather than argued about.
    IMAGE_MAX_SIDE: int = 1500
    IMAGE_QUALITY: int = 85
    # Run a model that has no price anyway. Deliberate and recorded: the daily
    # cost cap cannot be enforced against calls nobody can price, and that is
    # a thing to decide rather than to discover.
    ALLOW_UNPRICED_MODEL: bool = False
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

    def unpriced_models(self) -> list[tuple[str, str]]:
        """The (variable, model) pairs whose price is unknown, in order.

        Read twice for the same reason: the validator below refuses to start on
        this list, and under ALLOW_UNPRICED_MODEL the startup log warns about
        it instead. One list rather than two so they cannot drift apart.
        """
        return [
            (name, getattr(self, name))
            for name in PRICED_MODEL_SETTINGS
            if getattr(self, name) not in PRICE_PER_MTOK
        ]

    @model_validator(mode="after")
    def _model_is_priced_or_deliberately_not(self) -> "Settings":
        """A model missing from PRICE_PER_MTOK makes every ai_calls row cost
        NULL, and SUM skips NULL — so DAILY_COST_LIMIT_USD quietly stops being
        a limit while everything else keeps working. Refuse to start, unless
        that is the decision: trying a model before its price is published is
        a real thing to want, and the page cap still stands."""
        if self.ALLOW_UNPRICED_MODEL:
            return self
        for name, model in self.unpriced_models():
            raise ValueError(
                f"{name}={model} has no price in PRICE_PER_MTOK "
                "(app/core/config.py). Add its cost per million tokens as "
                "(input, output), or set ALLOW_UNPRICED_MODEL=true to run "
                "with DAILY_COST_LIMIT_USD not enforced."
            )
        return self

    @field_validator("VISION_RUNS")
    @classmethod
    def _at_least_two_runs(cls, v: int) -> int:
        # Fewer than two runs leaves nothing to compare against.
        if v < 2:
            raise ValueError("VISION_RUNS must be >= 2")
        return v

    @field_validator("VISION_MEDIA_RESOLUTION")
    @classmethod
    def _known_media_resolution(cls, v: str) -> str:
        # Refused at startup rather than at the first photo, and refused
        # rather than ignored: a knob that silently does nothing is how an
        # experiment comes to compare a setting against itself.
        allowed = {"unset", "low", "medium", "high"}
        if v not in allowed:
            raise ValueError(
                f"VISION_MEDIA_RESOLUTION must be one of {sorted(allowed)}"
            )
        return v

    @field_validator("VISION_THINKING_LEVEL")
    @classmethod
    def _known_thinking_level(cls, v: str) -> str:
        allowed = {"unset", "minimal", "low", "medium", "high"}
        if v not in allowed:
            raise ValueError(
                f"VISION_THINKING_LEVEL must be one of {sorted(allowed)}"
            )
        return v

    @field_validator("VISION_CALL_TIMEOUT_S")
    @classmethod
    def _call_timeout_is_workable(cls, v: int) -> int:
        """Both ends are the album ceiling, which is derived from this.

        Under 5 s no model answers at all and every call is a timeout; over
        180 s the derived ceiling passes half an hour, and an update is a
        background task that any deploy cancels."""
        if not 5 <= v <= 180:
            raise ValueError("VISION_CALL_TIMEOUT_S must be between 5 and 180")
        return v


settings = Settings()
