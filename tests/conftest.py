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
