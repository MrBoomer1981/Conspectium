"""Application settings, read from the environment once at import time."""

from datetime import date

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
    #
    # The Standard tier, which is what a plain call is billed at. It stood at
    # 0.375 / 1.875 from 2026-09-23 to 09-25 — the Batch and Flex row of the
    # price page, which this bot never asks for — so every row of those days
    # is half its real price, and DAILY_COST_LIMIT_USD let through twice its
    # own figure.
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    # Retired: closed to new accounts since September 2026, kept for the
    # ai_calls rows already written against it and for any key that still
    # has access.
    "gemini-2.5-flash-lite": (0.10, 0.40),
}

# A price the page has already announced a change to, with the day it takes
# effect (UTC). Gemini 3.8 Flash doubles on 2027-01-01; left to memory, the cap
# would quietly start letting through twice its figure that morning.
PRICE_CHANGES: dict[str, tuple[date, tuple[float, float]]] = {
    "gemini-3.8-flash": (date(2027, 1, 1), (1.50, 7.50)),
}


def price_per_mtok(model: str, day: date) -> tuple[float, float] | None:
    """What a model's tokens cost on `day`, or None when it is not priced."""
    change = PRICE_CHANGES.get(model)
    if change is not None and day >= change[0]:
        return change[1]
    return PRICE_PER_MTOK.get(model)


# The settings whose model has to be priced for DAILY_COST_LIMIT_USD to mean
# anything. Both of them: half the spend going out unpriced breaks the cap just
# as quietly as all of it. One list, because the validator below refuses to
# start on it and the startup log warns about it, and two loops that have to
# agree is how they came to disagree — the warning looked at VISION_MODEL alone
# while the validator looked at both.
PRICED_MODEL_SETTINGS = ("VISION_MODEL", "COMPOSE_MODEL", "EXPLAIN_MODEL")

# Google Search grounding on a Gemini 3 model is billed per search query the
# model runs — $14 per 1,000 — not per call: $35 per 1,000 grounded prompts,
# which stood here until 2026-09-25, is the Gemini 2.5 price. A call can run
# several queries, so the count comes from the call's own grounding metadata
# (explain._search_queries). The first 5,000 queries a month are free and are
# not subtracted: the key's free allowance is shared with everything else on
# it, and counting them is the safe side of a cap to err on.
GROUNDING_USD_PER_QUERY = 0.014


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required: a missing one must crash at startup, not on the first request.
    BOT_TOKEN: str
    DATABASE_URL: str
    GEMINI_API_KEY: str
    WEBHOOK_URL: str
    WEBHOOK_SECRET: str

    AI_ENABLED: bool = True
    # A person's pages a day: 12 since 2026-10-06, the CEO's (task 72).
    DAILY_PAGES_PER_USER: int = 12
    # A group's pages a day, everyone in it together: 20 since 2026-10-07,
    # the CEO's (task 41). Pages rather than dollars, so a group is told
    # exactly what is left; DAILY_COST_LIMIT_USD stays the breaker over all.
    DAILY_PAGES_PER_GROUP: int = 20
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
    # A sketch drawn again from its page (task 101): three more calls on
    # VISION_MODEL for a page that describes a drawing, reading where each
    # is and what its labels say, and the pen's lines traced off the photo.
    # Off by default for the reason the stages are: what goes into the
    # group's document is a decision, not a deploy.
    SKETCHES_ENABLED: bool = False
    # Stage two: the trusted transcription, formatted. Off by default — it is
    # an experiment behind a switch, like PROMPT_FILE, and turning it on is a
    # decision rather than something that happens on a deploy.
    COMPOSE_ENABLED: bool = False
    COMPOSE_MODEL: str = "gemini-3.5-flash-lite"
    COMPOSE_PROMPT_FILE: str = "prompts-compose-v1.md"
    # Stage two is one call over the whole record; VISION_CALL_TIMEOUT_S is the
    # ceiling of one call over one page. They scale with different things, so
    # they cannot be the same number — and for a while they were. Measured on
    # gemini-3.8-flash: three pages compose in about 43 s, four pages ran past
    # 90 s and the album's markup was thrown away (ai_calls id 361).
    COMPOSE_CALL_TIMEOUT_S: int = 240
    # How long the composing call may think. Measured on record 45's text on
    # 2026-09-25: "low" composed it with the same ten headings and two frames
    # as the model's own default, differing in two lines — a bullet where the
    # default wrote "$\cdot$" — at $0.015 against $0.033 and in 9 s against
    # 24. Thinking was 85% of what this call produced. "unset" sends nothing,
    # the model's own default; the values are VISION_THINKING_LEVEL's.
    COMPOSE_THINKING_LEVEL: str = "low"
    # Stage three: hard places explained, with the sources Google Search gave
    # for them, and the record summed up — the bot's own words, printed as the
    # bot's. Off by default for the reason stage two is: turning on a stage
    # that adds text to the group's document is a decision, not a deploy.
    EXPLAIN_ENABLED: bool = False
    EXPLAIN_MODEL: str = "gemini-3.5-flash-lite"
    EXPLAIN_PROMPT_FILE: str = "prompts-explain-v1.md"
    # One call over the whole record, searching as it goes: sized like the
    # composing stage's ceiling, and for the same reasons.
    EXPLAIN_CALL_TIMEOUT_S: int = 240
    # How long a search for an explanation's source may think. The call only
    # has to find a page and quote a sentence of it, and at the model's
    # default it thought nine tokens for every one it wrote. Measured on
    # record 45's five explanations on 2026-09-25: "low" found a source for
    # all five, as the default did, with 8 searches against 14, for $0.115
    # against $0.268, in 4-7 s against 16-32. The writing call keeps the
    # default: finding what is hard on a page is the part that needs it.
    SOURCE_THINKING_LEVEL: str = "low"
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
    # The pages one send may hold: the albums of ten Telegram cuts a send of
    # more into are read as one (task 81), and an album past this begins a
    # send of its own. Production's value since 2026-10-08; at Telegram's ten
    # no album would ever join another.
    MAX_ALBUM_PAGES: int = 30
    # A whole notebook sent at once in a private chat (task 63, the CEO's of
    # 2026-10-12): a send of more pages than MAX_ALBUM_PAGES, or one whose
    # caption says «тетрадь», cut into its lectures — up to this many pages,
    # one notebook a person a day beyond their DAILY_PAGES_PER_USER. Read
    # with a prompt of its own, PROMPT_FILE's with where each lecture begins.
    NOTEBOOK_MAX_PAGES: int = 100
    NOTEBOOK_PROMPT_FILE: str = "prompts-v12.md"
    LOG_LEVEL: str = "INFO"
    # The chat every «Плохо» under a document and every reader's account of
    # an error is sent to at once, with the document (task 70) — the CEO's
    # own chat with the bot. Unset, the feedback is only stored.
    FEEDBACK_CHAT_ID: int | None = None

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

    @field_validator("FEEDBACK_CHAT_ID", mode="before")
    @classmethod
    def _empty_is_unset(cls, v: object) -> object:
        # A variable left empty on Railway means "nobody", not a number that
        # failed to parse: feedback is stored either way, and the bot must
        # not refuse to start over where its copies go.
        return None if isinstance(v, str) and not v.strip() else v

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

    @field_validator(
        "VISION_THINKING_LEVEL", "COMPOSE_THINKING_LEVEL", "SOURCE_THINKING_LEVEL"
    )
    @classmethod
    def _known_thinking_level(cls, v: str, info) -> str:
        # "minimal" is a level the SDK knows and gemini-3.8-flash refuses with
        # a 400; which levels a model takes is the model's to say, not this.
        allowed = {"unset", "minimal", "low", "medium", "high"}
        if v not in allowed:
            raise ValueError(
                f"{info.field_name} must be one of {sorted(allowed)}"
            )
        return v

    @field_validator("COMPOSE_CALL_TIMEOUT_S")
    @classmethod
    def _compose_timeout_is_workable(cls, v: int) -> int:
        """Under 30 s the stage refuses itself by construction: the shortest
        composition ever measured on a model strong enough to compose took
        41 s. Over 600 s the wait outlives what it runs in — an update is a
        background task that any deploy cancels, and a record whose formatting
        was cancelled goes out unformatted anyway."""
        if not 30 <= v <= 600:
            raise ValueError(
                "COMPOSE_CALL_TIMEOUT_S must be between 30 and 600"
            )
        return v

    @field_validator("EXPLAIN_CALL_TIMEOUT_S")
    @classmethod
    def _explain_timeout_is_workable(cls, v: int) -> int:
        """The composing stage's bounds, for the composing stage's reasons: a
        call over the whole record, in a background task a deploy cancels."""
        if not 30 <= v <= 600:
            raise ValueError("EXPLAIN_CALL_TIMEOUT_S must be between 30 and 600")
        return v

    @model_validator(mode="after")
    def _a_notebook_holds_a_send(self) -> "Settings":
        """A notebook is a send of more pages than MAX_ALBUM_PAGES: a smaller
        notebook would be no send the bot ever reads whole."""
        if self.NOTEBOOK_MAX_PAGES < self.MAX_ALBUM_PAGES:
            raise ValueError("NOTEBOOK_MAX_PAGES must be >= MAX_ALBUM_PAGES")
        return self

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
