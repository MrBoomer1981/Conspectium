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
from app.db.models import Base, Event, Group, User


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


# ── a group chat ─────────────────────────────────────────────────────────────
# Once the bot can see a course chat it sees every message in it, and nearly
# all of them are classmates talking to each other. The middleware is where
# those stop, before a session is opened or a user row made.

from datetime import datetime, timezone  # noqa: E402

from aiogram.types import Chat, Document, Message, PhotoSize  # noqa: E402
from aiogram.types import User as TgUser  # noqa: E402

from app.bot import middlewares  # noqa: E402

_PHOTO = [PhotoSize(file_id="f", file_unique_id="u", width=60, height=40)]
_DOCX = Document(file_id="d", file_unique_id="v", file_name="лекция.docx")


def _in_chat(chat_id: int = -100500, chat_type: str = "supergroup",
             title: str = "Матан, 2 курс", **fields) -> Message:
    """A real aiogram Message, because what a group lets through is decided by
    the fields Telegram actually sends."""
    return Message(
        message_id=fields.pop("message_id", 1),
        date=datetime.now(timezone.utc),
        chat=Chat(id=chat_id, type=chat_type, title=title),
        from_user=TgUser(id=77, is_bot=False, first_name="Глеб", username="student"),
        **fields,
    )


def test_everything_in_a_private_chat_is_heard():
    assert middlewares.heard(_in_chat(77, "private", None, text="привет"))


def test_chatter_in_a_group_is_not():
    for message in (
        _in_chat(text="привет, кто был на паре?"),
        _in_chat(text="#дз на завтра: §5"),
        _in_chat(photo=_PHOTO),
        _in_chat(photo=_PHOTO, caption="смешно"),
        _in_chat(document=_DOCX, caption="вот методичка"),
    ):
        assert not middlewares.heard(message), message


def test_what_the_bot_acts_on_in_a_group_is_heard():
    for message in (
        _in_chat(text="/stats"),
        _in_chat(text="#матан"),
        _in_chat(photo=_PHOTO, caption="Лекция 5 #матан"),
        _in_chat(document=_DOCX, caption="#матан"),
        # An album is judged whole: its caption is on one page only.
        _in_chat(photo=_PHOTO, media_group_id="alb"),
        # The notice that moves the group to its new id.
        _in_chat(migrate_from_chat_id=-100),
    ):
        assert middlewares.heard(message), message


async def test_chatter_opens_no_session_and_makes_no_user(maker):
    called = []

    async def handler(event, data):
        called.append(event)

    result = await DbSessionMiddleware()(handler, _in_chat(text="привет"), {})

    assert result is None and called == []
    assert await _count(maker, User) == 0


async def test_a_group_is_registered_on_first_sight_and_reused(maker):
    async def handler(event, data):
        return data["group"].id

    first = await DbSessionMiddleware()(handler, _in_chat(text="/stats"), {})
    second = await DbSessionMiddleware()(handler, _in_chat(text="#матан"), {})

    assert first == second
    async with maker() as session:
        group = (await session.execute(select(Group))).scalar_one()
    assert (group.tg_chat_id, group.title) == (-100500, "Матан, 2 курс")


async def test_a_renamed_group_keeps_its_row(maker):
    async def handler(event, data):
        return data["group"].id

    first = await DbSessionMiddleware()(handler, _in_chat(text="/stats"), {})
    second = await DbSessionMiddleware()(
        handler, _in_chat(text="/stats", title="Матан, 3 курс"), {}
    )

    assert first == second
    async with maker() as session:
        group = (await session.execute(select(Group))).scalar_one()
    assert group.title == "Матан, 3 курс"


async def test_a_private_chat_has_no_group(maker):
    async def handler(event, data):
        return data["group"]

    assert await DbSessionMiddleware()(handler, _message(), {}) is None
    assert await _count(maker, Group) == 0


async def _group_id_after(maker, *messages) -> list[int]:
    async def handler(event, data):
        return data["group"].id

    return [await DbSessionMiddleware()(handler, m, {}) for m in messages]


async def test_a_group_that_became_a_supergroup_keeps_its_records(maker):
    """Telegram gives the supergroup a new chat id. The records point at our
    own id, so moving the row is what keeps every one of them findable."""
    before, after = await _group_id_after(
        maker,
        _in_chat(-100, "group", text="/stats"),
        _in_chat(-1001, "supergroup", migrate_from_chat_id=-100),
    )

    assert before == after
    async with maker() as session:
        group = (await session.execute(select(Group))).scalar_one()
    assert group.tg_chat_id == -1001


async def test_both_halves_of_the_notice_move_the_group_once(maker):
    # Telegram announces the move in the old chat and in the new one.
    ids = await _group_id_after(
        maker,
        _in_chat(-100, "group", text="/stats"),
        _in_chat(-100, "group", migrate_to_chat_id=-1001),
        _in_chat(-1001, "supergroup", migrate_from_chat_id=-100),
        _in_chat(-1001, "supergroup", text="#матан"),
    )

    assert len(set(ids)) == 1
    assert await _count(maker, Group) == 1


async def test_a_row_another_update_just_inserted_is_fetched_not_duplicated(maker):
    """The pages of an album are handled at once, and in a group an album is
    a likely first message from someone the bot has never seen: every page
    tries to register them, and all but one lose the race on the unique index.
    Losing it must cost nothing — not the page, and not an error in the chat."""
    async with maker() as session:
        session.add(User(tg_id=5, first_name="первая страница"))
        await session.commit()

    async with maker() as session:
        row = await middlewares._insert_or_fetch(
            session, User(tg_id=5), select(User).where(User.tg_id == 5)
        )
        assert row.first_name == "первая страница"
        # The failed insert left the session usable.
        await session.commit()

    assert await _count(maker, User) == 1
