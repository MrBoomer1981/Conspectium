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
    assert handlers._split_message("коротко") == ["коротко"]


def test_text_exactly_at_the_limit_is_not_split():
    text = "я" * 10
    assert handlers._split_message(text, limit=10) == [text]


def test_split_happens_on_blank_lines():
    chunks = handlers._split_message("аааа\n\nбббб\n\nвввв", limit=10)
    assert chunks == ["аааа\n\nбббб", "вввв"]


def test_a_paragraph_longer_than_the_limit_is_hard_cut():
    chunks = handlers._split_message("я" * 25, limit=10)
    assert chunks == ["я" * 10, "я" * 10, "я" * 5]


def test_every_chunk_respects_the_limit():
    text = "\n\n".join("абзац номер %d" % i for i in range(50))
    assert all(len(chunk) <= 100 for chunk in handlers._split_message(text, limit=100))


def test_nothing_is_lost_when_splitting():
    text = "\n\n".join("абзац %d" % i for i in range(30))
    assert "".join(handlers._split_message(text, limit=40)).replace("\n", "") == (
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
