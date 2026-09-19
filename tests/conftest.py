"""Dummy environment so importing app.* succeeds during collection.

app.core.config.settings is built at import time and needs the five required
variables; app.services.vision also constructs a Gemini client at import. The
unit tests in this suite don't make network or database calls, so placeholder
values are enough.
"""

import os

os.environ.setdefault("BOT_TOKEN", "test-bot-token")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test"
)
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("WEBHOOK_URL", "https://example.test")
os.environ.setdefault("WEBHOOK_SECRET", "test-secret")


# Event.payload and the JSONB columns of Note are PostgreSQL types that the
# SQLite dialect cannot render, which is why the older tests create only the
# JSONB-free tables. Teaching the SQLite compiler to emit JSON for JSONB is a
# test-side adapter: it registers a compilation rule for the sqlite dialect
# only and leaves the PostgreSQL behaviour, and app/db/models.py, untouched.
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")
def _render_jsonb_as_json_on_sqlite(type_, compiler, **kw) -> str:
    return "JSON"
