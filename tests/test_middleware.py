"""Session-per-update middleware — app/bot/middlewares.py.

The transaction model in CLAUDE.md rests on this class: one session per
update, rolled back on any exception — with one deliberate exception of its
own, a brand-new user committed before the handler runs so that log_ai_calls,
writing from its own session, does not hit a foreign key that isn't there yet.
"""

from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.bot.middlewares import DbSessionMiddleware
from app.db.models import Base, Event, User


@pytest_asyncio.fixture
async def maker(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    # The middleware imported the name directly, so patch it where it is used.
    monkeypatch.setattr("app.bot.middlewares.async_session_maker", factory)
    yield factory
    await engine.dispose()


def _message(tg_id: int = 77, username: str = "student", first_name: str = "Глеб"):
    """The slice of aiogram's Message the middleware touches."""
    return SimpleNamespace(
        from_user=SimpleNamespace(
            id=tg_id, username=username, first_name=first_name
        )
    )


async def _count(maker, model) -> int:
    async with maker() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


# ── the happy path ───────────────────────────────────────────────────────────


async def test_session_and_user_are_injected(maker):
    seen = {}

    async def handler(event, data):
        seen["session"] = data["session"]
        seen["user"] = data["user"]
        return "готово"

    result = await DbSessionMiddleware()(handler, _message(), {})

    assert result == "готово"
    assert seen["session"] is not None
    assert seen["user"].tg_id == 77


async def test_a_new_user_is_stored_with_their_telegram_details(maker):
    async def handler(event, data):
        return None

    await DbSessionMiddleware()(handler, _message(), {})

    async with maker() as session:
        user = (await session.execute(select(User))).scalar_one()
    assert (user.tg_id, user.username, user.first_name) == (77, "student", "Глеб")


async def test_registering_a_new_user_writes_an_event(maker):
    async def handler(event, data):
        return None

    await DbSessionMiddleware()(handler, _message(), {})

    async with maker() as session:
        event = (await session.execute(select(Event))).scalar_one()
    assert event.type == "user_registered"


async def test_a_known_user_is_reused(maker):
    async def handler(event, data):
        return data["user"].id

    first = await DbSessionMiddleware()(handler, _message(), {})
    second = await DbSessionMiddleware()(handler, _message(), {})

    assert first == second
    assert await _count(maker, User) == 1
    # user_registered is written once, on creation only.
    assert await _count(maker, Event) == 1


async def test_the_handler_commits_its_own_writes(maker):
    async def handler(event, data):
        data["session"].add(Event(user_id=data["user"].id, type="note_processed"))

    await DbSessionMiddleware()(handler, _message(), {})

    assert await _count(maker, Event) == 2  # user_registered + note_processed


# ── failure ──────────────────────────────────────────────────────────────────


async def test_an_exception_reaches_the_global_error_handler(maker):
    async def handler(event, data):
        raise RuntimeError("что-то сломалось")

    with pytest.raises(RuntimeError):
        await DbSessionMiddleware()(handler, _message(), {})


async def test_handler_writes_are_rolled_back_on_failure(maker):
    async def handler(event, data):
        data["session"].add(Event(user_id=data["user"].id, type="note_processed"))
        raise RuntimeError("после записи")

    with pytest.raises(RuntimeError):
        await DbSessionMiddleware()(handler, _message(), {})

    async with maker() as session:
        types = (await session.execute(select(Event.type))).scalars().all()
    assert types == ["user_registered"]


async def test_a_new_user_survives_a_failing_first_update(maker):
    """The early commit, stated as a behaviour rather than an implementation
    detail: someone whose very first message crashes the handler is still
    registered, because log_ai_calls may already have written a row pointing
    at them from a different session."""

    async def handler(event, data):
        raise RuntimeError("первое же сообщение упало")

    with pytest.raises(RuntimeError):
        await DbSessionMiddleware()(handler, _message(), {})

    assert await _count(maker, User) == 1
