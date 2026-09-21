"""Handler-level behaviour that no other test reaches — app/bot/handlers.py.

Only the two pieces that stand on their own: splitting a long reply, and the
catch-all for messages the bot has no handler for. The photo and document
pipelines are deliberately not covered here.
"""

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.bot import handlers, texts
from app.db.models import Base, Event, User


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


class _Message:
    """The slice of aiogram's Message that handle_unsupported touches."""

    def __init__(self, content_type: str = "text"):
        self.content_type = content_type
        self.replies: list[str] = []

    async def answer(self, text: str) -> None:
        self.replies.append(text)


async def _user(session) -> User:
    user = User(tg_id=1)
    session.add(user)
    await session.flush()
    return user


# ── _split_message ───────────────────────────────────────────────────────────
# Telegram rejects messages over 4096 characters.


def test_short_text_is_not_split():
    assert texts.split_message("коротко") == ["коротко"]


def test_text_exactly_at_the_limit_is_not_split():
    text = "я" * 10
    assert texts.split_message(text, limit=10) == [text]


def test_split_happens_on_blank_lines():
    chunks = texts.split_message("аааа\n\nбббб\n\nвввв", limit=10)
    assert chunks == ["аааа\n\nбббб", "вввв"]


def test_a_paragraph_longer_than_the_limit_is_hard_cut():
    chunks = texts.split_message("я" * 25, limit=10)
    assert chunks == ["я" * 10, "я" * 10, "я" * 5]


def test_every_chunk_respects_the_limit():
    text = "\n\n".join("абзац номер %d" % i for i in range(50))
    assert all(len(chunk) <= 100 for chunk in texts.split_message(text, limit=100))


def test_nothing_is_lost_when_splitting():
    text = "\n\n".join("абзац %d" % i for i in range(30))
    assert "".join(texts.split_message(text, limit=40)).replace("\n", "") == (
        text.replace("\n", "")
    )


# ── handle_unsupported ───────────────────────────────────────────────────────


async def test_unsupported_message_gets_an_answer(session):
    user = await _user(session)
    message = _Message("text")

    await handlers.handle_unsupported(message, session, user)

    assert message.replies == [texts.UNSUPPORTED]


async def test_the_answer_invites_a_photo():
    # A note is created from a photo of a page; the .docx path is a side door
    # and must not be offered here as an equal way in.
    assert "фотограф" in texts.UNSUPPORTED.lower()
    assert ".docx" not in texts.UNSUPPORTED.lower()


async def test_unsupported_message_is_logged_with_its_content_type(session):
    user = await _user(session)

    await handlers.handle_unsupported(_Message("sticker"), session, user)

    event = (await session.execute(select(Event))).scalar_one()
    assert event.type == "unsupported_message"
    assert event.payload == {"content_type": "sticker"}
    assert event.user_id == user.id


async def test_every_unhandled_kind_is_answered(session):
    user = await _user(session)
    for content_type in ("text", "voice", "sticker", "video", "location"):
        message = _Message(content_type)
        await handlers.handle_unsupported(message, session, user)
        assert message.replies == [texts.UNSUPPORTED], content_type


# ── an album page is registered before it is fetched ─────────────────────────
# The line this covers is the whole of the album fix: announcing after the
# download would time the debounce from our own network speed again, and a
# four-page album would come back as four separate records. Removing the call
# left every other test green, which is why this one exists.

import asyncio  # noqa: E402
import io  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from PIL import Image  # noqa: E402

from app.bot import albums  # noqa: E402


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (60, 40), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


class _PhotoMessage:
    def __init__(self, media_group_id: str | None, message_id: int = 11):
        self.photo = [SimpleNamespace(width=60, height=40, file_id="f")]
        self.document = None
        self.media_group_id = media_group_id
        self.message_id = message_id
        self.chat = SimpleNamespace(id=5)
        self.replies: list[str] = []

    async def answer(self, text: str) -> None:
        self.replies.append(text)


class _SlowBot:
    """Stands in for aiogram's Bot, holding the download open so the state of
    the album can be inspected while the page is still in flight."""

    def __init__(self):
        self.started = asyncio.Event()
        self.finish = asyncio.Event()

    async def download(self, photo):
        self.started.set()
        await self.finish.wait()
        return io.BytesIO(_jpeg())


async def test_an_album_page_is_announced_while_still_downloading(session):
    albums.reset()
    user = await _user(session)
    message = _PhotoMessage("grp-1", message_id=11)
    bot = _SlowBot()

    handling = asyncio.create_task(handlers.handle_photo(message, session, user, bot))
    try:
        await asyncio.wait_for(bot.started.wait(), timeout=2)

        # Mid-download: Telegram has told us this page exists, so the album
        # must already know about it.
        assert albums._announced.get("grp-1") == {11}
        # And its bytes are, of course, not there yet.
        assert albums._buffer.get("grp-1") is None
    finally:
        handling.cancel()
        bot.finish.set()
        await asyncio.gather(handling, return_exceptions=True)
        albums.reset()


async def test_a_single_photo_is_not_registered_as_an_album(session):
    albums.reset()
    user = await _user(session)
    message = _PhotoMessage(None, message_id=12)
    bot = _SlowBot()

    handling = asyncio.create_task(handlers.handle_photo(message, session, user, bot))
    try:
        await asyncio.wait_for(bot.started.wait(), timeout=2)
        assert albums._announced == {}
    finally:
        handling.cancel()
        bot.finish.set()
        await asyncio.gather(handling, return_exceptions=True)
        albums.reset()
