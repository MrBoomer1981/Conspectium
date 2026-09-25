"""Handler-level behaviour that no other test reaches — app/bot/handlers.py.

Only the two pieces that stand on their own: splitting a long reply, and the
catch-all for messages the bot has no handler for. The photo and document
pipelines are deliberately not covered here.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.bot import albums, handlers, texts
from app.services import compose, consensus, mathcheck, photoguard, vision
from app.db.models import Base, Event, Group, Note, NoteTopic, User


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
    def __init__(
        self,
        media_group_id: str | None,
        message_id: int = 11,
        caption: str | None = None,
    ):
        self.photo = [SimpleNamespace(width=60, height=40, file_id="f")]
        self.document = None
        self.media_group_id = media_group_id
        self.message_id = message_id
        self.caption = caption
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


def _input(message_id: int, tag: str | None = None) -> albums.PageInput:
    return albums.PageInput(
        data=b"x",
        message_id=message_id,
        chat_id=1,
        media_group_id="grp",
        bytes_before=10,
        bytes_after=5,
        width=100,
        height=100,
        tag=tag,
    )


def _ok_page(number: int) -> albums.PageResult:
    return albums.PageResult(
        page=number,
        stats=[],
        report=mathcheck.Report(issues=[]),
        verdict="clean",
        text_agreement=0.95,
        numeric_agreement=0.62,
    )


def _skipped(number: int, reason: str, line_height: float = 12.0) -> albums.PageResult:
    """A refused page as process_page now builds one: the frame metrics stay
    on it, because a refusal has to be checkable after the fact."""
    return albums.PageResult(
        page=number,
        stats=[],
        skip_reason=reason,
        photo_sharpness=150.0,
        photo_line_height=line_height,
        photo_paper_fraction=0.9,
        photo_contrast=40.0,
    )


def _record(
    page_count: int,
    missing_pages: list[int] | None = None,
    unverified_pages: list[dict] | None = None,
) -> albums.AssembledRecord:
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
        numeric_agreement=0.62,
        photo_sharpness=100.0,
        photo_line_height=20.0,
        photo_paper_fraction=0.9,
        photo_contrast=0.8,
        page_count=page_count,
        missing_pages=missing_pages or [],
        unverified_pages=unverified_pages or [],
    )


async def _run_album(
    session, monkeypatch, skips, pages_ok, record, group=None, tag=None
):
    """_process_album with the pages already read. `tag` rides on the first
    page's caption, the way Telegram sends an album's."""
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
        message,
        session,
        user,
        [_input(i, tag if i == 1 else None) for i in range(1, 5)],
        group,
    )
    return message, user


async def test_an_album_that_lost_a_page_is_saved_with_the_hole_named(
    session, monkeypatch
):
    """The rule used to be that a record is all its pages or none, and two
    five-page albums were lost in one evening over a single page each. What
    survives of it is the reason: a record missing a page must not read as a
    whole one."""
    message, _ = await _run_album(
        session,
        monkeypatch,
        skips=[
            _skipped(2, texts.SKIP_UNRECOGNIZED),
            _skipped(3, texts.SKIP_DIVERGED),
        ],
        pages_ok=[_ok_page(1), _ok_page(4)],
        record=_record(2, missing_pages=[2, 3]),
    )

    notes = (await session.execute(select(Note))).scalars().all()
    assert len(notes) == 1
    assert notes[0].missing_pages == [2, 3]
    assert message.documents


async def test_an_album_record_says_nothing_about_how_it_was_read(
    session, monkeypatch
):
    record = _record(2, unverified_pages=[{"page": 2, "reason": texts.UNVERIFIED_DIVERGED}])
    record.uncertain = [{"text": "Дьюринг", "why": "двоится", "page": 1}]
    record.numeric_divergences = [
        {"context": "x", "variants": {"5": 2, "6": 1}, "page": 1}
    ]
    message, _ = await _run_album(
        session,
        monkeypatch,
        skips=[],
        pages_ok=[_ok_page(1), _ok_page(2)],
        record=record,
    )

    assert message.documents
    for reply in message.replies:
        assert "по-разному" not in reply
        assert "двояко" not in reply
        assert "сверить" not in reply
        assert "Дьюринг" not in reply


async def test_the_reply_names_every_page_that_has_to_be_taken_again(
    session, monkeypatch
):
    message, _ = await _run_album(
        session,
        monkeypatch,
        skips=[
            _skipped(2, texts.SKIP_UNRECOGNIZED),
            _skipped(3, texts.SKIP_DIVERGED),
        ],
        pages_ok=[_ok_page(1), _ok_page(4)],
        record=_record(2, missing_pages=[2, 3]),
    )
    # Not the last reply any more: the record goes out first, and the question
    # about the subject comes after.
    said = "\n".join(message.replies)

    assert "Страница 2" in said and "Страница 3" in said
    assert texts.ALBUM_SEND_MISSING in said


async def test_an_album_with_nothing_read_asks_for_it_again(
    session, monkeypatch
):
    """`record is None` is exactly "not one page was read". Then there is no
    document to deliver and the only useful answer is which pages to take
    again."""
    message, _ = await _run_album(
        session,
        monkeypatch,
        skips=[_skipped(i, texts.SKIP_UNRECOGNIZED) for i in range(1, 5)],
        pages_ok=[],
        record=None,
    )

    assert (await session.execute(select(Note))).scalars().all() == []
    assert message.documents == []
    assert texts.ALBUM_RESEND in message.replies[-1]


async def test_an_incomplete_album_is_written_to_events(session, monkeypatch):
    await _run_album(
        session,
        monkeypatch,
        skips=[_skipped(i, texts.SKIP_UNRECOGNIZED) for i in (1, 2, 3, 4)],
        pages_ok=[],
        record=None,
    )

    events = (
        (await session.execute(select(Event).where(Event.type == "album_incomplete")))
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].payload["pages"] == 4
    assert events[0].payload["pages_ok"] == 0

    # The metrics, not only the reason. "Текст мелкий" on a page written in a
    # large hand costs the page, and the claim has to be checkable after the
    # fact rather than argued from memory.
    assert events[0].payload["skipped"][0] == {
        "page": 1,
        "reason": texts.SKIP_UNRECOGNIZED,
        "line_height_px": 12.0,
        "sharpness": 150.0,
        "paper_fraction": 0.9,
        "contrast": 40.0,
    }


async def test_a_saved_album_keeps_the_metrics_of_the_page_it_lost(
    session, monkeypatch
):
    """Now that the record is delivered anyway, note_processed is the only
    place those four numbers would be kept — and they are the calibration data
    for the frame check."""
    await _run_album(
        session,
        monkeypatch,
        skips=[_skipped(2, texts.SKIP_UNRECOGNIZED, line_height=126.5)],
        pages_ok=[_ok_page(i) for i in (1, 3, 4)],
        record=_record(3, missing_pages=[2]),
    )

    event = (
        (await session.execute(select(Event).where(Event.type == "note_processed")))
        .scalars()
        .one()
    )

    assert event.payload["pages_skipped"] == 1
    assert event.payload["skipped"][0]["line_height_px"] == 126.5


async def test_the_pages_that_were_read_are_still_charged(session, monkeypatch):
    # The model calls behind them were made and billed, and the pages that
    # were skipped are not charged for.
    _, user = await _run_album(
        session,
        monkeypatch,
        skips=[_skipped(2, texts.SKIP_UNRECOGNIZED)],
        pages_ok=[_ok_page(i) for i in (1, 3, 4)],
        record=_record(3, missing_pages=[2]),
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


# ── stage two, where the record is built ─────────────────────────────────────


async def test_the_record_stores_the_composed_text(session, monkeypatch):
    """compose() being right is worth nothing if the handler computes it and
    then builds the Note out of the transcription anyway. That omission is
    invisible to every test in test_compose.py."""

    async def fake_compose(markdown):
        return compose.Composition("# Оформлено\n\n" + markdown)

    monkeypatch.setattr(handlers.compose, "compose", fake_compose)

    await _run_album(
        session,
        monkeypatch,
        skips=[],
        pages_ok=[_ok_page(i) for i in range(1, 5)],
        record=_record(4),
    )

    notes = (await session.execute(select(Note))).scalars().all()
    assert notes[0].markdown.startswith("# Оформлено")


async def test_a_refused_composition_stores_the_text_it_started_from(
    session, monkeypatch
):
    # The whole bargain: the worst case of stage two is the record without it.
    async def fake_compose(markdown):
        return compose.Composition(
            markdown, refused="numbers", stats=[_compose_stat()]
        )

    monkeypatch.setattr(handlers.compose, "compose", fake_compose)

    await _run_album(
        session,
        monkeypatch,
        skips=[],
        pages_ok=[_ok_page(i) for i in range(1, 5)],
        record=_record(4),
    )

    notes = (await session.execute(select(Note))).scalars().all()
    assert notes[0].markdown == _record(4).markdown

    event = (
        await session.execute(
            select(Event).where(Event.type == "note_processed")
        )
    ).scalar_one()
    assert event.payload["compose_refused"] == "numbers"
    assert event.payload["composed"] is False


async def test_composition_gets_its_own_limits_check(session, monkeypatch):
    """Rule 6: limits before the model call, not after. The check at the top
    of the record covers recognition; this is a second model call and a
    second check, and a cost cap hit between them has to stop it."""
    answers = [None, texts.LIMIT_COST, texts.LIMIT_COST]
    seen: list[int] = []

    async def fake_check(session_, user_, pages):
        seen.append(pages)
        return answers.pop(0)

    called = False

    async def fake_compose(markdown):
        nonlocal called
        called = True
        return compose.Composition(markdown)

    monkeypatch.setattr(handlers.limits, "check_limits", fake_check)
    monkeypatch.setattr(handlers.compose, "compose", fake_compose)

    await _run_album(
        session,
        monkeypatch,
        skips=[],
        pages_ok=[_ok_page(i) for i in range(1, 5)],
        record=_record(4),
    )

    assert called is False
    # Not a page: the page budget was already debited for the recognition.
    # The third check is the explaining stage's, a third call with its own.
    assert seen == [4, 0, 0]

    notes = (await session.execute(select(Note))).scalars().all()
    assert notes[0].markdown == _record(4).markdown


# ── the single-photo path, for the one line the album tests cannot reach ─────


_PHOTO_MD = "Пусть $I_n = [a_n; b_n]$ и пересечение непусто везде."


def _compose_stat() -> vision.CallStats:
    return vision.CallStats(
        "compose", "gemini-3.5-flash-lite", 1, 1, None, 0.001, 10, True, None
    )


class _FastBot:
    async def download(self, photo):
        return io.BytesIO(_jpeg())


def _verdict_ok():
    return photoguard.PhotoVerdict(
        ok=True,
        reason="Фото годится для распознавания",
        line_height_px=25.0,
        sharpness=200.0,
        paper_fraction=0.9,
        contrast=40.0,
    )


async def _run_photo(
    session,
    monkeypatch,
    composition,
    composed=None,
    message=None,
    group=None,
    **result_fields,
):
    """handle_photo with everything outside this test's subject stubbed out.

    The album harness above cannot cover the photo path: they are two separate
    functions that each build their own Note, and a composition wired into one
    and dropped in the other is a paid call thrown away on every single page.
    """
    user = await _user(session)

    transcription = vision.Transcription(
        title="Теорема Кантора",
        subject=None,
        markdown=_PHOTO_MD,
        margin_notes=[],
        uncertain=[],
        numeric_tokens=[],
        unreadable_count=0,
    )

    fields = {
        "best": transcription,
        "text_agreement": 0.95,
        "numeric_agreement": 0.62,
        "numeric_divergences": [],
        "verdict": "clean",
        **result_fields,
    }

    async def fake_consensus(image_bytes):
        return vision.TranscriptionResult(**fields), []

    async def fake_compose(markdown):
        if composed is not None:
            composed.append(markdown)
        return composition

    async def no_spend(user_id, stats):
        return None

    async def no_pdf(message, note):
        return None

    monkeypatch.setattr(handlers.photoguard, "check_photo_bytes", lambda data: _verdict_ok())
    monkeypatch.setattr(handlers.vision, "transcribe_consensus", fake_consensus)
    monkeypatch.setattr(handlers.vision, "log_ai_calls", no_spend)
    monkeypatch.setattr(handlers.compose, "compose", fake_compose)
    monkeypatch.setattr(handlers.corpus, "send_record", no_pdf)

    albums.reset()
    await handlers.handle_photo(
        message or _PhotoMessage(None, message_id=21),
        session,
        user,
        _FastBot(),
        group,
    )
    return transcription


async def test_a_single_photo_whose_runs_diverged_is_saved_and_marked(
    session, monkeypatch
):
    """It used to answer "переснимите" and keep nothing. The pages behind those
    refusals carried legible text, and what the band measures is the shape the
    runs gave the page rather than whether they could read it."""
    message = _PhotoMessage(None, message_id=21)
    await _run_photo(
        session,
        monkeypatch,
        compose.Composition(_PHOTO_MD),
        text_agreement=0.19,
        verdict="rejected",
    )

    note = (await session.execute(select(Note))).scalars().one()

    assert note.status == "needs_review"
    assert note.unverified_pages == [
        {"page": 1, "reason": texts.UNVERIFIED_DIVERGED}
    ]


async def test_a_single_photo_read_by_one_run_says_so(session, monkeypatch):
    await _run_photo(
        session,
        monkeypatch,
        compose.Composition(_PHOTO_MD),
        text_agreement=None,
        numeric_agreement=None,
        verdict="needs_review",
    )

    note = (await session.execute(select(Note))).scalars().one()

    assert note.unverified_pages == [{"page": 1, "reason": texts.UNVERIFIED_ONE_RUN}]
    assert note.text_agreement is None


async def test_a_photo_record_says_nothing_about_how_it_was_read(
    session, monkeypatch
):
    """The numbers the runs read differently, a spot that reads two ways, a
    page no second reading confirmed: none of it follows the record into the
    chat — the author's decision, 2026-09-25; in a group it was noise for
    everyone. The columns still keep it."""
    message = _PhotoMessage(None, message_id=21)
    doubtful = vision.Transcription(
        title="Теорема Кантора",
        subject=None,
        markdown=_PHOTO_MD,
        margin_notes=[],
        uncertain=[vision.Uncertain("Дьюринг", "поле", "двоится", ["Тьюринг"])],
        numeric_tokens=[],
        unreadable_count=0,
    )
    await _run_photo(
        session,
        monkeypatch,
        compose.Composition(_PHOTO_MD),
        message=message,
        best=doubtful,
        text_agreement=0.19,
        verdict="rejected",
        numeric_divergences=[
            consensus.Divergence(position=0, variants={"5": 2, "6": 1}, context="x")
        ],
    )

    note = (await session.execute(select(Note))).scalars().one()

    assert note.status == "needs_review" and note.uncertain and note.numeric_divergences
    # The progress line, and the question which subject the record belongs to.
    assert len(message.replies) == 2
    assert message.replies[0] == texts.PROCESSING


async def test_a_finding_on_a_photo_is_stored_with_the_text_it_is_about(
    session, monkeypatch
):
    markdown = "Сложение натуральных чисел на лекции.\nИтак, сложим: $2 + 2 = 4 = 5$"
    wrong = vision.Transcription(
        title="Сложение",
        subject=None,
        markdown=markdown,
        margin_notes=[],
        uncertain=[],
        numeric_tokens=[],
        unreadable_count=0,
    )
    await _run_photo(session, monkeypatch, compose.Composition(markdown), best=wrong)

    note = (await session.execute(select(Note))).scalars().one()

    assert note.status == "needs_review"  # the finding is critical
    assert [issue["anchor"] for issue in note.issues] == ["2 + 2 = 4 = 5"]


async def test_a_photo_that_read_well_is_not_marked(session, monkeypatch):
    await _run_photo(session, monkeypatch, compose.Composition(_PHOTO_MD))

    note = (await session.execute(select(Note))).scalars().one()

    assert note.unverified_pages == []
    assert note.status == "ready"


async def test_a_single_photo_stores_the_composed_text(session, monkeypatch):
    source = await _run_photo(
        session,
        monkeypatch,
        compose.Composition("# Оформлено\n\nтекст", drift=3, stats=[_compose_stat()]),
    )

    notes = (await session.execute(select(Note))).scalars().all()
    assert len(notes) == 1
    assert notes[0].markdown == "# Оформлено\n\nтекст"
    assert notes[0].markdown != source.markdown

    event = (
        await session.execute(select(Event).where(Event.type == "note_processed"))
    ).scalar_one()
    assert event.payload["composed"] is True
    assert event.payload["compose_refused"] is None
    assert event.payload["compose_drift"] == 3


async def test_a_refused_composition_on_a_photo_says_so_in_the_event(
    session, monkeypatch
):
    # compose() already hands back the source when it refuses, which is what
    # test_compose.py proves. What only this path can show is that the reason
    # survives into note_processed, where the experiment will read it.
    await _run_photo(
        session,
        monkeypatch,
        compose.Composition(
            _PHOTO_MD, refused="numbers", drift=7, stats=[_compose_stat()]
        ),
    )

    notes = (await session.execute(select(Note))).scalars().all()
    assert notes[0].markdown == _PHOTO_MD

    event = (
        await session.execute(select(Event).where(Event.type == "note_processed"))
    ).scalar_one()
    assert event.payload["compose_refused"] == "numbers"
    assert event.payload["composed"] is False
    assert event.payload["compose_drift"] == 7


async def test_composition_on_a_photo_gets_its_own_limits_check(
    session, monkeypatch
):
    # The same bargain as the album path: rule 6 admits no exception for a
    # second model call, and pages=0 because the page budget belongs to the
    # recognition that has already been debited.
    answers = [None, texts.LIMIT_COST, texts.LIMIT_COST]
    seen: list[int] = []

    async def fake_check(session_, user_, pages):
        seen.append(pages)
        return answers.pop(0)

    monkeypatch.setattr(handlers.limits, "check_limits", fake_check)
    composed: list[str] = []

    await _run_photo(
        session,
        monkeypatch,
        compose.Composition("# Оформлено", stats=[_compose_stat()]),
        composed=composed,
    )

    assert composed == []
    assert seen == [1, 0, 0]

    notes = (await session.execute(select(Note))).scalars().all()
    assert notes[0].markdown == _PHOTO_MD


async def test_what_the_second_stage_cost_is_counted_in_the_record(
    session, monkeypatch
):
    # note_processed.cost_usd is what the day's spend is read off. Leaving the
    # composition out of it understates every record that used one.
    await _run_photo(
        session,
        monkeypatch,
        compose.Composition("# Оформлено\n\nтекст", stats=[_compose_stat()]),
    )

    event = (
        await session.execute(select(Event).where(Event.type == "note_processed"))
    ).scalar_one()
    assert event.payload["cost_usd"] == pytest.approx(0.001)


async def test_what_the_second_stage_cost_is_counted_in_an_album_record(
    session, monkeypatch
):
    async def fake_compose(markdown):
        return compose.Composition(markdown, stats=[_compose_stat()])

    monkeypatch.setattr(handlers.compose, "compose", fake_compose)

    await _run_album(
        session,
        monkeypatch,
        skips=[],
        pages_ok=[_ok_page(i) for i in range(1, 5)],
        record=_record(4),
    )

    event = (
        await session.execute(select(Event).where(Event.type == "note_processed"))
    ).scalar_one()
    assert event.payload["cost_usd"] == pytest.approx(0.001)
    assert event.payload["composed"] is True


# ── both agreements reach the record ─────────────────────────────────────────

# They are stored so that comparing two prompts against the same album is a
# query rather than a grep through Railway's logs, which roll off. Two
# mistakes would leave the suite green without this: dropping the new number
# on the way to the Note, and copying text_agreement into both. The fixtures
# hold 0.95 for the text and 0.62 for the numbers, so either one fails here.


async def test_an_album_record_stores_both_agreements(session, monkeypatch):
    await _run_album(
        session, monkeypatch, skips=[], pages_ok=[_ok_page(1)], record=_record(1)
    )

    note = (await session.execute(select(Note))).scalar_one()
    assert note.text_agreement == 0.95
    assert note.numeric_agreement == 0.62


async def test_a_photo_record_stores_both_agreements(session, monkeypatch):
    await _run_photo(session, monkeypatch, compose.Composition(_PHOTO_MD))

    note = (await session.execute(select(Note))).scalar_one()
    assert note.text_agreement == 0.95
    assert note.numeric_agreement == 0.62


# ── the question that files a record ─────────────────────────────────────────

# ask_for_tag is the last thing every capture path does, and it does two jobs:
# it stores the topics the record can be found by, and it opens the question
# whose answer the next "#word" is. Dropped from one of the two paths, records
# taken that way would be findable by nothing and nothing would fail — the
# same class of one-line omission the two paths have already paid for twice.


async def test_a_photo_record_can_be_found_by_what_the_bot_read_off_it(
    session, monkeypatch
):
    await _run_photo(session, monkeypatch, compose.Composition(_PHOTO_MD))

    note = (await session.execute(select(Note))).scalar_one()
    topics = (
        await session.execute(
            select(NoteTopic.topic).where(NoteTopic.note_id == note.id)
        )
    ).scalars().all()

    assert topics  # at minimum the title, which every record has


async def test_an_album_record_is_asked_which_subject_it_belongs_to(
    session, monkeypatch
):
    message, _ = await _run_album(
        session, monkeypatch, skips=[], pages_ok=[_ok_page(1)], record=_record(1)
    )

    note = (await session.execute(select(Note))).scalar_one()
    topics = (
        await session.execute(
            select(NoteTopic.topic).where(NoteTopic.note_id == note.id)
        )
    ).scalars().all()

    assert topics
    # The question is last, so it is what the user is looking at when they
    # reply — which is what makes the reply an answer and not a search.
    assert "#" in message.replies[-1]


# ── a group chat ─────────────────────────────────────────────────────────────
# In a course chat the bot takes a page only when it came with its subject in
# the caption, the record it makes is the chat's, and everything not
# addressed to it is left alone — a bot answering every message would be the
# loudest member of the chat within a day.


async def _chat(session) -> Group:
    group = Group(tg_chat_id=-100500, title="Матан, 2 курс")
    session.add(group)
    await session.flush()
    return group


async def test_nothing_unaddressed_is_answered_or_logged_in_a_group(session):
    user = await _user(session)
    group = await _chat(session)
    message = _Message("new_chat_members")

    await handlers.handle_unsupported(message, session, user, group)

    assert message.replies == []
    assert (await session.execute(select(Event))).first() is None


async def test_an_album_nobody_tagged_is_left_alone_in_a_group(session, monkeypatch):
    """Classmates share albums of all kinds. Untagged, it is not the bot's —
    not read, not answered, not even refused for its size."""
    group = await _chat(session)

    async def must_not_run(pages):
        raise AssertionError("an untagged album in a group was read")

    monkeypatch.setattr(handlers.albums, "process_batch", must_not_run)
    user = await _user(session)
    message = _AlbumMessage()
    pages = [_input(i) for i in range(1, 30)]  # over MAX_ALBUM_PAGES, too

    await handlers._process_album(message, session, user, pages, group)

    assert message.replies == []
    assert (await session.execute(select(Event))).first() is None


async def test_a_tagged_album_in_a_group_is_the_groups_and_filed_at_once(
    session, monkeypatch
):
    group = await _chat(session)
    message, _ = await _run_album(
        session,
        monkeypatch,
        skips=[],
        pages_ok=[_ok_page(1)],
        record=_record(1),
        group=group,
        tag="матан",
    )

    note = (await session.execute(select(Note))).scalar_one()
    assert (note.group_id, note.tag) == (group.id, "матан")
    # Where it was filed, not the question: in a group nobody is asked.
    assert message.replies[-1].startswith("Сохранил под #матан")
    events = (await session.execute(select(Event))).scalars().all()
    assert events and all(e.group_id == group.id for e in events)


async def test_a_photo_sent_with_its_subject_is_filed_at_once(session, monkeypatch):
    message = _PhotoMessage(None, message_id=21, caption="Лекция 5 #Матан")
    await _run_photo(
        session, monkeypatch, compose.Composition(_PHOTO_MD), message=message
    )

    note = (await session.execute(select(Note))).scalar_one()
    assert (note.group_id, note.tag) == (None, "матан")
    assert message.replies[-1].startswith("Сохранил под #матан")


async def test_a_photo_taken_in_a_group_is_the_groups(session, monkeypatch):
    group = await _chat(session)
    message = _PhotoMessage(None, message_id=21, caption="#матан")
    await _run_photo(
        session,
        monkeypatch,
        compose.Composition(_PHOTO_MD),
        message=message,
        group=group,
    )

    note = (await session.execute(select(Note))).scalar_one()
    assert (note.group_id, note.tag) == (group.id, "матан")
    events = (await session.execute(select(Event))).scalars().all()
    assert {e.type for e in events} >= {"note_captured", "note_processed"}
    assert all(e.group_id == group.id for e in events)


async def test_an_untagged_photo_in_a_group_is_never_made_a_record(session):
    """middlewares.heard stops it first; the handler keeps the invariant on
    its own, so a group's record cannot exist without its subject."""
    user = await _user(session)
    group = await _chat(session)
    message = _PhotoMessage(None, caption="смешно")

    class _NoDownload:
        async def download(self, photo):
            raise AssertionError("an untagged photo in a group was fetched")

    await handlers.handle_photo(message, session, user, _NoDownload(), group)

    assert message.replies == []
    assert (await session.execute(select(Note))).first() is None


async def test_a_file_that_is_not_docx_gets_no_answer_in_a_group(session):
    # Slides shared with "#матан" under them are for the classmates.
    user = await _user(session)
    group = await _chat(session)
    message = _PhotoMessage(None, caption="#матан")
    message.document = SimpleNamespace(file_name="лекция 5.pdf", file_size=100)

    await handlers.handle_document(message, session, user, None, group)

    assert message.replies == []


# ── the bot's own place in the chat ──────────────────────────────────────────


class _MemberBot:
    """Stands in for aiogram's Bot where a membership handler touches it."""

    def __init__(self, reads_everything: bool):
        self.reads_everything = reads_everything
        self.sent: list[tuple[int, str]] = []

    async def me(self):
        return SimpleNamespace(can_read_all_group_messages=self.reads_everything)

    async def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


def _membership(status: str):
    return SimpleNamespace(
        chat=SimpleNamespace(id=-100500),
        new_chat_member=SimpleNamespace(status=status),
    )


async def test_added_to_a_group_it_says_how_it_works_there(session):
    user = await _user(session)
    group = await _chat(session)
    bot = _MemberBot(reads_everything=True)

    await handlers.on_joined(_membership("member"), session, user, bot, group)

    assert bot.sent == [(-100500, texts.group_welcome(True))]
    event = (await session.execute(select(Event))).scalar_one()
    assert (event.type, event.payload, event.group_id) == (
        "group_joined",
        {"sees_photos": True},
        group.id,
    )


async def test_a_bot_that_cannot_see_the_photos_asks_to_be_made_admin(session):
    """With privacy mode on, an ordinary member sees no photos at all. Every
    page sent to the chat would go unanswered with no hint why — so the fix
    is named in the welcome itself."""
    user = await _user(session)
    group = await _chat(session)
    bot = _MemberBot(reads_everything=False)

    await handlers.on_joined(_membership("member"), session, user, bot, group)

    assert texts.GROUP_CANNOT_SEE in bot.sent[0][1]


async def test_added_as_an_admin_it_sees_the_photos_anyway(session):
    user = await _user(session)
    group = await _chat(session)
    bot = _MemberBot(reads_everything=False)

    await handlers.on_joined(_membership("administrator"), session, user, bot, group)

    assert texts.GROUP_CANNOT_SEE not in bot.sent[0][1]


async def test_being_unblocked_in_a_private_chat_is_not_joining_a_group(session):
    user = await _user(session)
    bot = _MemberBot(reads_everything=False)

    await handlers.on_joined(_membership("member"), session, user, bot, None)

    assert bot.sent == []
    assert (await session.execute(select(Event))).first() is None


async def test_made_an_admin_it_says_it_can_see_now(session):
    user = await _user(session)
    group = await _chat(session)
    bot = _MemberBot(reads_everything=False)

    await handlers.on_promoted(_membership("administrator"), session, user, bot, group)

    assert bot.sent == [(-100500, texts.GROUP_SEES_PHOTOS)]


async def test_made_an_admin_when_it_could_already_see_it_stays_quiet(session):
    user = await _user(session)
    group = await _chat(session)
    bot = _MemberBot(reads_everything=True)

    await handlers.on_promoted(_membership("administrator"), session, user, bot, group)

    assert bot.sent == []
    event = (await session.execute(select(Event))).scalar_one()
    assert event.type == "group_promoted"


async def test_removed_from_a_group_it_is_logged(session):
    user = await _user(session)
    group = await _chat(session)

    await handlers.on_left(_membership("left"), session, user, group)

    event = (await session.execute(select(Event))).scalar_one()
    assert (event.type, event.group_id) == ("group_left", group.id)


# ── a refused frame stops the album before it is read ────────────────────────


async def test_an_album_with_a_refused_frame_is_asked_for_again_unread(
    session, monkeypatch
):
    """Record 45 came back without its first page and "пришлите их отдельно";
    the author read that, rightly, as not being asked to retake it. Now
    nothing is read, nothing is charged, and the reply names the page."""
    user = await _user(session)

    async def refused(pages):
        return [
            albums.PageResult(
                page=1,
                stats=[],
                skip_reason="Текст мелкий — снимите одну страницу крупным планом",
                photo_sharpness=1682.0,
                photo_line_height=12.0,
                photo_paper_fraction=0.71,
                photo_contrast=41.9,
            )
        ]

    async def must_not_run(pages):
        raise AssertionError("an album with a refused frame was read")

    monkeypatch.setattr(handlers.albums, "refused_frames", refused)
    monkeypatch.setattr(handlers.albums, "process_batch", must_not_run)
    message = _AlbumMessage()

    await handlers._process_album(message, session, user, [_input(i) for i in (1, 2, 3)])

    assert message.replies == [
        texts.album_retake([(1, "Текст мелкий — снимите одну страницу крупным планом")])
    ]
    assert "Страница 1: текст мелкий" in message.replies[0]
    assert texts.PROCESSING not in message.replies
    assert user.pages_used_today == 0
    assert (await session.execute(select(Note))).first() is None
    event = (
        await session.execute(select(Event).where(Event.type == "album_retake_requested"))
    ).scalar_one()
    assert event.payload["pages"] == 3
    assert event.payload["refused"][0]["page"] == 1
    assert event.payload["refused"][0]["line_height_px"] == 12.0
