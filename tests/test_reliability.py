"""The three money-critical mechanisms from PLAN.md -> Contracts -> Testing
boundaries: retry, album batch ownership, spend independence. Nothing else is
covered here on purpose.
"""

import asyncio
import os
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from google.genai import errors as genai_errors
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.bot import albums
from app.db.models import AiCall, Base, Event, User
from app.services import vision


def _api_error(code: int) -> genai_errors.APIError:
    """A Gemini APIError with a chosen HTTP status, built without the SDK
    constructor (its signature shifts between versions)."""
    err = genai_errors.APIError.__new__(genai_errors.APIError)
    err.code = code
    err.message = "test"
    err.details = None
    return err


@pytest_asyncio.fixture
async def sqlite_maker():
    """A shared in-memory SQLite bound to one connection. check_limits' tables
    only — no JSONB is involved in these tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[User.__table__, AiCall.__table__],
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


# 1. Retry — a transient failure then success gives two CallStats and two rows.


async def test_retry_then_success(monkeypatch, sqlite_maker):
    # Classification: the full table from PLAN.md task 10.
    assert vision._should_retry(_api_error(429)) is True
    assert vision._should_retry(_api_error(408)) is True
    assert vision._should_retry(_api_error(500)) is True
    assert vision._should_retry(_api_error(503)) is True
    assert vision._should_retry(_api_error(400)) is False
    assert vision._should_retry(_api_error(401)) is False
    assert vision._should_retry(_api_error(403)) is False
    assert vision._should_retry(_api_error(404)) is False
    assert vision._should_retry(httpx.ConnectError("refused")) is True
    assert vision._should_retry(TimeoutError()) is True
    assert vision._should_retry(ValueError("logical")) is False

    monkeypatch.setattr(vision, "_RETRY_PAUSES_S", (0, 0))  # no real waiting

    calls: list[dict] = []
    good = SimpleNamespace(
        text='{"markdown": "# Note\\n\\nEnough body text to pass the length gate."}',
        usage_metadata=SimpleNamespace(
            prompt_token_count=10, candidates_token_count=20
        ),
    )

    async def fake_generate_content(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise httpx.ConnectError("connection refused")
        return good

    # Replace the whole client: patching a method on _client.aio.models would
    # break if the SDK ever gives that object __slots__.
    fake_client = SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_content=fake_generate_content)
        )
    )
    monkeypatch.setattr(vision, "_client", fake_client)

    result, stats = await vision.transcribe(b"image-bytes", "gemini-3.5-flash-lite")

    assert result is not None
    assert len(calls) == 2
    assert len(stats) == 2
    assert stats[0].success is False and stats[0].cost_usd is None
    assert stats[1].success is True

    monkeypatch.setattr(vision, "async_session_maker", sqlite_maker)
    await vision.log_ai_calls(1, stats)

    async with sqlite_maker() as session:
        rows = (
            await session.execute(select(func.count()).select_from(AiCall))
        ).scalar_one()
    assert rows == 2


# 2. Batch ownership — concurrent handlers for one media_group_id run once.


async def test_album_batch_has_one_owner(monkeypatch):
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.05)
    albums.reset()

    async def handler(message_id: int):
        albums.add_page(
            "grp",
            albums.PageInput(
                data=b"x",
                message_id=message_id,
                chat_id=1,
                media_group_id="grp",
                bytes_before=1,
                bytes_after=1,
                width=1,
                height=1,
            ),
        )
        return await albums.collect("grp")

    results = await asyncio.gather(handler(1), handler(2), handler(3))

    owners = [r for r in results if r is not None]
    assert len(owners) == 1
    assert len(owners[0]) == 3
    assert albums._buffer == {}


# 3. Independence of spend — a rollback of the main session keeps committed
#    ai_calls. Needs a real Postgres (separate transactions); skipped otherwise.

_TEST_DB = os.environ.get("TEST_DATABASE_URL")


@pytest.mark.skipif(
    not _TEST_DB, reason="TEST_DATABASE_URL not set (needs real Postgres)"
)
async def test_spend_survives_main_rollback(monkeypatch):
    engine = create_async_engine(_TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(vision, "async_session_maker", maker)

    async with maker() as setup:
        setup.add(User(tg_id=999_999))
        await setup.commit()
    async with maker() as reader:
        user_id = (
            await reader.execute(select(User.id).where(User.tg_id == 999_999))
        ).scalar_one()

    async with maker() as main:
        main.add(Event(user_id=user_id, type="note_captured", payload={}))
        await main.flush()
        await vision.log_ai_calls(
            user_id, [vision.CallStats(
                    "transcribe", "gemini-3.5-flash-lite", 1, 1, 0.001, 10,
                    True, None,
                )]
        )
        await main.rollback()

    async with maker() as check:
        events = (
            await check.execute(select(func.count()).select_from(Event))
        ).scalar_one()
        calls = (
            await check.execute(select(func.count()).select_from(AiCall))
        ).scalar_one()
    assert events == 0  # the main session's write is gone
    assert calls == 1  # the spend, committed in its own session, is not

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# 4. Attribution — the row names the model that was actually called.


async def test_a_row_names_its_own_kind_and_model(monkeypatch, sqlite_maker):
    """log_ai_calls used to write "transcribe" and settings.VISION_MODEL on
    every row it made. A second stage on another model would have been
    recorded and priced as the first one, and rule 4 would have stopped
    holding with nothing failing to show it."""
    monkeypatch.setattr(vision, "async_session_maker", sqlite_maker)

    await vision.log_ai_calls(
        1,
        [
            vision.CallStats("transcribe", "model-a", 1, 1, 0.001, 10, True, None),
            vision.CallStats("compose", "model-b", 2, 2, 0.002, 20, True, None),
        ],
    )

    async with sqlite_maker() as session:
        rows = (
            await session.execute(
                select(AiCall.kind, AiCall.model).order_by(AiCall.id)
            )
        ).all()

    assert [tuple(row) for row in rows] == [
        ("transcribe", "model-a"),
        ("compose", "model-b"),
    ]
    # Neither row carries the configured model, so neither could have come
    # from settings rather than from the stats.
    assert vision.settings.VISION_MODEL not in {model for _, model in rows}
