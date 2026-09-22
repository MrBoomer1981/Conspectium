"""Handler-level behaviour that no other test reaches — app/bot/handlers.py.

Only the two pieces that stand on their own: splitting a long reply, and the
catch-all for messages the bot has no handler for. The photo and document
pipelines are deliberately not covered here.
"""

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.bot import albums, handlers, texts
from app.services import mathcheck
from app.db.models import Base, Event, Note, User


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


# ── an album that lost a page is not saved at all ────────────────────────────


class _AlbumMessage:
    """The slice of Message that _process_album touches."""

    def __init__(self):
        self.replies: list[str] = []
        self.documents: list = []

    async def answer(self, text: str) -> None:
        self.replies.append(text)

    async def answer_document(self, document, caption=None) -> None:
        self.documents.append(document)


def _input(message_id: int) -> albums.PageInput:
    return albums.PageInput(
        data=b"x",
        message_id=message_id,
        chat_id=1,
        media_group_id="grp",
        bytes_before=10,
        bytes_after=5,
        width=100,
        height=100,
    )


def _ok_page(number: int) -> albums.PageResult:
    return albums.PageResult(
        page=number,
        stats=[],
        report=mathcheck.Report(issues=[]),
        verdict="clean",
        text_agreement=0.95,
    )


def _record(page_count: int) -> albums.AssembledRecord:
    return albums.AssembledRecord(
        title="Теорема Кантора",
        subject=None,
        markdown="Пусть $I_n = [a_n; b_n]$.",
        status="ready",
        verdict="clean",
        uncertain=[],
        issues=[],
        numeric_divergences=[],
        margin_notes=[],
        unreadable_count=0,
        text_agreement=0.95,
        photo_sharpness=100.0,
        photo_line_height=20.0,
        photo_paper_fraction=0.9,
        photo_contrast=0.8,
        page_count=page_count,
    )


async def _run_album(session, monkeypatch, skips, pages_ok, record):
    user = User(tg_id=1)
    session.add(user)
    await session.flush()

    async def _no_spend(user_id, stats):
        return None

    monkeypatch.setattr(handlers.vision, "log_ai_calls", _no_spend)

    async def _batch(pages):
        return albums.AlbumOutcome(
            stats=[], skips=skips, pages_ok=pages_ok, record=record
        )

    monkeypatch.setattr(handlers.albums, "process_batch", _batch)

    message = _AlbumMessage()
    await handlers._process_album(
        message, session, user, [_input(i) for i in range(1, 5)]
    )
    return message, user


async def test_an_album_that_lost_a_page_is_not_saved(session, monkeypatch):
    # A record missing a page still reads as a whole one, and nothing in it
    # says which page is gone.
    message, _ = await _run_album(
        session,
        monkeypatch,
        skips=[(2, texts.SKIP_UNRECOGNIZED), (3, texts.SKIP_DIVERGED)],
        pages_ok=[_ok_page(1), _ok_page(4)],
        record=_record(2),
    )

    assert (await session.execute(select(Note))).scalars().all() == []
    assert message.documents == []


async def test_the_reply_names_every_page_that_has_to_be_taken_again(
    session, monkeypatch
):
    message, _ = await _run_album(
        session,
        monkeypatch,
        skips=[(2, texts.SKIP_UNRECOGNIZED), (3, texts.SKIP_DIVERGED)],
        pages_ok=[_ok_page(1), _ok_page(4)],
        record=_record(2),
    )
    reply = message.replies[-1]

    assert "Страница 2" in reply and "Страница 3" in reply
    assert texts.ALBUM_RESEND in reply


async def test_an_incomplete_album_is_written_to_events(session, monkeypatch):
    await _run_album(
        session,
        monkeypatch,
        skips=[(2, texts.SKIP_UNRECOGNIZED)],
        pages_ok=[_ok_page(i) for i in (1, 3, 4)],
        record=_record(3),
    )

    events = (
        (await session.execute(select(Event).where(Event.type == "album_incomplete")))
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].payload["pages"] == 4
    assert events[0].payload["pages_ok"] == 3


async def test_the_pages_that_were_read_are_still_charged(session, monkeypatch):
    # The model calls behind them were made and billed. Only the record
    # stopped being written; the quota rule did not change.
    _, user = await _run_album(
        session,
        monkeypatch,
        skips=[(2, texts.SKIP_UNRECOGNIZED)],
        pages_ok=[_ok_page(i) for i in (1, 3, 4)],
        record=_record(3),
    )

    assert user.pages_used_today == 3


async def test_a_whole_album_is_still_saved(session, monkeypatch):
    # The guard must not stand in the way of the case it was built around.
    message, _ = await _run_album(
        session, monkeypatch, skips=[], pages_ok=[_ok_page(i) for i in range(1, 5)], record=_record(4)
    )

    notes = (await session.execute(select(Note))).scalars().all()
    assert len(notes) == 1
    assert notes[0].page_count == 4
    assert message.documents
