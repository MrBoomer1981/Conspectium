"""Settings validators — app/core/config.py.

Both validators guard a production-only failure. The scheme rewrite is what
lets the app talk to Railway's Postgres at all, and it is invisible in local
development because a hand-written .env usually already says +asyncpg.
"""

import pytest
from pydantic import ValidationError

from app.core.config import PRICE_PER_MTOK, Settings

_REQUIRED = {
    "BOT_TOKEN": "t",
    "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
    "GEMINI_API_KEY": "k",
    "WEBHOOK_URL": "https://example.test",
    "WEBHOOK_SECRET": "s",
}


def _settings(**overrides) -> Settings:
    return Settings(**{**_REQUIRED, **overrides})


# ── DATABASE_URL ─────────────────────────────────────────────────────────────


def test_railway_postgres_scheme_is_rewritten():
    # The addon hands out postgres://; asyncpg needs postgresql+asyncpg://.
    s = _settings(DATABASE_URL="postgres://u:p@host:5432/db")
    assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"


def test_plain_postgresql_scheme_is_rewritten():
    s = _settings(DATABASE_URL="postgresql://u:p@host:5432/db")
    assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"


def test_an_already_async_url_is_left_alone():
    url = "postgresql+asyncpg://u:p@host:5432/db"
    assert _settings(DATABASE_URL=url).DATABASE_URL == url


def test_only_the_scheme_is_touched():
    # "postgres" appearing in the password or host must survive untouched.
    s = _settings(DATABASE_URL="postgres://user:postgres@postgres-host/postgres")
    assert s.DATABASE_URL == (
        "postgresql+asyncpg://user:postgres@postgres-host/postgres"
    )


def test_a_non_postgres_url_is_passed_through():
    url = "sqlite+aiosqlite://"
    assert _settings(DATABASE_URL=url).DATABASE_URL == url


# ── VISION_RUNS ──────────────────────────────────────────────────────────────


def test_two_runs_is_the_minimum():
    assert _settings(VISION_RUNS=2).VISION_RUNS == 2


def test_fewer_than_two_runs_is_refused():
    # One run leaves nothing to compare against, and agreement between
    # independent runs is the only uncertainty signal that works.
    for runs in (1, 0, -1):
        with pytest.raises(ValidationError):
            _settings(VISION_RUNS=runs)


# ── required variables ───────────────────────────────────────────────────────


def test_a_missing_required_variable_is_a_startup_error(monkeypatch):
    # conftest.py puts the five variables into os.environ so that importing
    # app.* works at all, so the variable has to be removed from there too —
    # leaving it out of the kwargs alone proves nothing.
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    incomplete = dict(_REQUIRED)
    del incomplete["BOT_TOKEN"]
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **incomplete)


# ── price table ──────────────────────────────────────────────────────────────


def test_the_default_model_is_priced():
    # An unpriced VISION_MODEL yields cost_usd = NULL, and NULL rows are
    # skipped by the SUM behind DAILY_COST_LIMIT_USD — the cost circuit
    # breaker would go quiet without anything failing.
    assert _settings().VISION_MODEL in PRICE_PER_MTOK
