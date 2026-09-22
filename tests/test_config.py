"""Settings validators — app/core/config.py.

Both validators guard a production-only failure. The scheme rewrite is what
lets the app talk to Railway's Postgres at all, and it is invisible in local
development because a hand-written .env usually already says +asyncpg.
"""

import pytest
from pydantic import ValidationError

from app.core.config import PRICE_PER_MTOK, Settings
from app.services import vision

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


def test_the_current_model_is_priced_correctly():
    # Gemini 3.5 Flash-Lite, paid tier: $0.30 in / $2.50 out per Mtok. Output
    # is over six times what the retired 2.5 cost, so a page is now worth
    # roughly $0.009 across three runs rather than $0.002.
    assert PRICE_PER_MTOK["gemini-3.5-flash-lite"] == (0.30, 2.50)


def test_the_retired_model_keeps_its_price():
    # ai_calls rows already reference it; dropping the entry would turn their
    # cost into NULL on any recomputation.
    assert PRICE_PER_MTOK["gemini-2.5-flash-lite"] == (0.10, 0.40)


# ── VISION_MODEL has to be priced ────────────────────────────────────────────


def test_a_model_with_no_price_stops_the_process():
    # The failure this replaces was silent: cost_usd NULL, SUM skipping NULL,
    # and DAILY_COST_LIMIT_USD no longer a limit with nothing to show for it.
    with pytest.raises(ValidationError) as caught:
        _settings(VISION_MODEL="gemini-9.9-imaginary")
    assert "PRICE_PER_MTOK" in str(caught.value)
    assert "ALLOW_UNPRICED_MODEL" in str(caught.value)


def test_an_unpriced_model_runs_when_that_is_the_decision():
    # Trying a model before its price is published is a real thing to want.
    s = _settings(VISION_MODEL="gemini-9.9-imaginary", ALLOW_UNPRICED_MODEL=True)
    assert s.VISION_MODEL == "gemini-9.9-imaginary"


def test_the_escape_hatch_is_off_by_default():
    assert _settings().ALLOW_UNPRICED_MODEL is False


def test_every_priced_model_is_accepted():
    for model in PRICE_PER_MTOK:
        assert _settings(VISION_MODEL=model).VISION_MODEL == model


def test_the_default_model_is_priced():
    assert _settings().VISION_MODEL in PRICE_PER_MTOK


# ── PROMPT_FILE: the switch the prompt experiment runs on ────────────────────


def test_the_prompt_file_defaults_to_the_one_in_the_repo():
    from app.core.config import settings

    assert settings.PROMPT_FILE == "prompts-v3.md"


def test_image_compression_defaults_to_what_rule_two_fixed():
    # 1500 px and quality 85 are the rule; the settings exist so a larger page
    # can be measured against the same album, not so the default drifts.
    from app.core.config import settings

    assert (settings.IMAGE_MAX_SIDE, settings.IMAGE_QUALITY) == (1500, 85)


def test_the_prompt_loaded_is_the_one_the_environment_names(tmp_path):
    """Both prompts ship, so the switch has to be proved rather than assumed.

    Reading the name from settings and hardcoding it straight back would look
    identical in every other test, the default being that very name — which is
    how an experiment comes to compare a variant against itself.

    A subprocess, because PROMPT_FILE is read once at import: reloading the
    module in place rebinds vision's dataclasses and every test holding the
    old Transcription class starts failing on identity.
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", "from app.services import vision;"
         " print(vision.PROMPT_WORDS)"],
        capture_output=True,
        text=True,
        cwd=root,
        env={**os.environ, "PROMPT_FILE": "prompts-v4.md"},
    )

    assert result.returncode == 0, result.stderr
    assert int(result.stdout.strip()) == len(
        vision.load_prompt("prompts-v4.md").split()
    )


def test_a_prompt_file_that_is_not_there_stops_the_process():
    # The same bargain as a missing required variable: fail on the deploy,
    # never on somebody's first photo.
    with pytest.raises(FileNotFoundError):
        vision.load_prompt("prompts-v99.md")


def test_every_prompt_that_ships_loads_and_carries_a_prompt():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    names = sorted(path.name for path in root.glob("prompts-v*.md"))

    assert len(names) >= 3
    for name in names:
        assert len(vision.load_prompt(name).split()) > 100, name


def test_the_prompts_that_ship_are_different_files():
    loaded = {
        name: vision.load_prompt(name)
        for name in ("prompts-v3.md", "prompts-v4.md", "prompts-v5.md")
    }
    assert len(set(loaded.values())) == 3


def test_the_extraction_prompt_stays_the_shortest_one():
    # prompts-v5 exists to carry nothing but reading: every rule about how the
    # page should look was taken out of it. If it stops being the shortest,
    # formatting has crept back in and the measurement it was made for is gone.
    words = {
        name: len(vision.load_prompt(name).split())
        for name in ("prompts-v3.md", "prompts-v4.md", "prompts-v5.md")
    }
    assert words["prompts-v5.md"] == min(words.values())
