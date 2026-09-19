"""Reading the corpus — app/bot/corpus.py (PLAN.md tasks 11-14).

The corpus is the product, so the invariant that matters most here is
ownership: every query filters by user_id, and a record belonging to someone
else has to be indistinguishable from one that does not exist.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.bot import corpus, texts
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
    def __init__(self):
        self.replies: list[str] = []

    async def answer(self, text: str) -> None:
        self.replies.append(text)


def _cmd(args: str | None = None):
    return SimpleNamespace(args=args)


async def _user(session, tg_id: int = 1) -> User:
    user = User(tg_id=tg_id)
    session.add(user)
    await session.flush()
    return user


async def _note(session, user: User, **overrides) -> Note:
    fields = dict(
        user_id=user.id,
        title="Производная сложной функции",
        subject="матан",
        markdown="Пусть дана функция f(g(x)).",
        source_type="photo",
        page_count=1,
        status="ready",
        uncertain=[],
        issues=[],
        numeric_divergences=[],
        unreadable_count=0,
        created_at=datetime.now(timezone.utc),
    )
    fields.update(overrides)
    note = Note(**fields)
    session.add(note)
    await session.flush()
    return note


async def _events(session, type_: str) -> list[Event]:
    stmt = select(Event).where(Event.type == type_)
    return list((await session.execute(stmt)).scalars().all())


# ── argument parsing ─────────────────────────────────────────────────────────


def test_page_defaults_to_one():
    assert corpus._page_number(None) == 1
    assert corpus._page_number("") == 1


def test_page_is_parsed():
    assert corpus._page_number("3") == 3
    assert corpus._page_number("  2  ") == 2


def test_a_nonsense_page_shows_the_first_one():
    # A typo should show the first page, not an error message.
    assert corpus._page_number("вторая") == 1
    assert corpus._page_number("-4") == 1


def test_note_id_is_parsed_with_or_without_a_hash():
    assert corpus._note_id("42") == 42
    assert corpus._note_id("#42") == 42
    assert corpus._note_id(None) is None
    assert corpus._note_id("сорок два") is None


# ── /notes ───────────────────────────────────────────────────────────────────


async def test_empty_corpus_invites_a_photo(session):
    user = await _user(session)
    message = _Message()

    await corpus.cmd_notes(message, _cmd(), session, user)

    assert message.replies == [texts.CORPUS_EMPTY]


async def test_records_are_listed_newest_first(session):
    user = await _user(session)
    now = datetime.now(timezone.utc)
    await _note(session, user, title="Старая", created_at=now - timedelta(days=2))
    await _note(session, user, title="Новая", created_at=now)
    message = _Message()

    await corpus.cmd_notes(message, _cmd(), session, user)

    body = message.replies[0]
    assert body.index("Новая") < body.index("Старая")


async def test_a_listed_record_shows_its_details(session):
    user = await _user(session)
    note = await _note(session, user, page_count=3)
    message = _Message()

    await corpus.cmd_notes(message, _cmd(), session, user)

    assert f"#{note.id}" in message.replies[0]
    assert "Производная сложной функции" in message.replies[0]
    assert "матан" in message.replies[0]
    assert "3 с." in message.replies[0]


async def test_a_record_needing_review_says_so(session):
    user = await _user(session)
    await _note(session, user, status="needs_review")
    message = _Message()

    await corpus.cmd_notes(message, _cmd(), session, user)

    assert texts.NEEDS_REVIEW_SHORT in message.replies[0]


async def test_a_record_without_a_subject_has_no_empty_gap(session):
    user = await _user(session)
    await _note(session, user, subject=None)
    message = _Message()

    await corpus.cmd_notes(message, _cmd(), session, user)

    assert " ·  · " not in message.replies[0]


async def test_a_full_page_offers_the_next_one(session):
    user = await _user(session)
    now = datetime.now(timezone.utc)
    for i in range(15):
        await _note(session, user, title=f"Запись {i}", created_at=now - timedelta(minutes=i))
    message = _Message()

    await corpus.cmd_notes(message, _cmd(), session, user)

    assert "/notes 2" in message.replies[0]
    assert message.replies[0].count("#") == 10


async def test_the_last_page_offers_nothing_further(session):
    user = await _user(session)
    now = datetime.now(timezone.utc)
    for i in range(15):
        await _note(session, user, created_at=now - timedelta(minutes=i))
    message = _Message()

    await corpus.cmd_notes(message, _cmd("2"), session, user)

    assert "/notes 3" not in message.replies[0]
    assert message.replies[0].count("#") == 5


async def test_a_page_past_the_end_says_so(session):
    user = await _user(session)
    await _note(session, user)
    message = _Message()

    await corpus.cmd_notes(message, _cmd("9"), session, user)

    assert message.replies == [texts.NOTES_PAGE_EMPTY]


async def test_listing_only_shows_your_own_records(session):
    mine = await _user(session, tg_id=1)
    theirs = await _user(session, tg_id=2)
    await _note(session, mine, title="Моя запись")
    await _note(session, theirs, title="Чужая запись")
    message = _Message()

    await corpus.cmd_notes(message, _cmd(), session, mine)

    assert "Моя запись" in message.replies[0]
    assert "Чужая запись" not in message.replies[0]


async def test_listing_is_logged(session):
    user = await _user(session)
    await _note(session, user)

    await corpus.cmd_notes(_Message(), _cmd(), session, user)

    events = await _events(session, "corpus_listed")
    assert events[0].payload == {"page": 1, "shown": 1}


# ── /note ────────────────────────────────────────────────────────────────────


async def test_note_without_an_id_explains_itself(session):
    user = await _user(session)
    message = _Message()

    await corpus.cmd_note(message, _cmd(), session, user)

    assert message.replies == [texts.NOTE_USAGE]


async def test_a_missing_record_is_reported(session):
    user = await _user(session)
    message = _Message()

    await corpus.cmd_note(message, _cmd("999"), session, user)

    assert message.replies == [texts.NOTE_NOT_FOUND]


async def test_someone_elses_record_looks_exactly_like_a_missing_one(session):
    mine = await _user(session, tg_id=1)
    theirs = await _user(session, tg_id=2)
    foreign = await _note(session, theirs, title="Чужая запись")
    message = _Message()

    await corpus.cmd_note(message, _cmd(str(foreign.id)), session, mine)

    # Same answer as for an id that was never used: confirming the record
    # exists would leak the corpus of another user.
    assert message.replies == [texts.NOTE_NOT_FOUND]


async def test_opening_a_record_returns_its_text(session):
    user = await _user(session)
    note = await _note(session, user)
    message = _Message()

    await corpus.cmd_note(message, _cmd(str(note.id)), session, user)

    assert "Производная сложной функции" in message.replies[0]
    assert "Пусть дана функция f(g(x))." in message.replies[0]


async def test_a_long_record_is_split(session):
    user = await _user(session)
    note = await _note(session, user, markdown="абзац\n\n" * 3000)
    message = _Message()

    await corpus.cmd_note(message, _cmd(str(note.id)), session, user)

    assert len(message.replies) > 1
    assert all(len(chunk) <= texts.MESSAGE_LIMIT for chunk in message.replies)


async def test_opening_a_record_is_logged(session):
    user = await _user(session)
    note = await _note(session, user)

    await corpus.cmd_note(_Message(), _cmd(str(note.id)), session, user)

    events = await _events(session, "note_opened")
    assert events[0].payload == {"note_id": note.id}


# ── the flags stored with a record ───────────────────────────────────────────


async def test_a_record_needing_review_carries_the_warning(session):
    user = await _user(session)
    note = await _note(session, user, status="needs_review")
    message = _Message()

    await corpus.cmd_note(message, _cmd(str(note.id)), session, user)

    assert texts.NEEDS_REVIEW in message.replies[-1]


async def test_stored_issues_are_rendered_by_mathcheck(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        issues=[
            {
                "kind": "constant",
                "severity": "critical",
                "message": "Постоянная Планка записана неверно",
                "detail": "6.67e-34",
                "suggestion": "",
            }
        ],
    )
    message = _Message()

    await corpus.cmd_note(message, _cmd(str(note.id)), session, user)

    assert "Постоянная Планка записана неверно" in message.replies[-1]
    assert "❌" in message.replies[-1]  # critical, not a warning


async def test_stored_divergences_and_uncertain_spots_come_back(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        numeric_divergences=[{"context": "g =", "variants": {"9.8": 2, "9.3": 1}}],
        uncertain=[{"text": "щ", "why": "читается двояко"}],
    )
    message = _Message()

    await corpus.cmd_note(message, _cmd(str(note.id)), session, user)

    tail = message.replies[-1]
    assert texts.DIVERGENCES_HEADER in tail and "9.8 — 2" in tail
    assert texts.UNCERTAIN_HEADER in tail and "читается двояко" in tail


async def test_album_flags_keep_their_page_numbers(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        page_count=3,
        uncertain=[{"text": "щ", "why": "двоится", "page": 2}],
    )
    message = _Message()

    await corpus.cmd_note(message, _cmd(str(note.id)), session, user)

    assert "с. 2 —" in message.replies[-1]


async def test_an_unreadable_issues_payload_does_not_lose_the_record(session):
    # Rows written by an older version must not make a record unopenable: the
    # text is what the user asked for.
    user = await _user(session)
    note = await _note(session, user, issues=[{"совсем": "не то"}])
    message = _Message()

    await corpus.cmd_note(message, _cmd(str(note.id)), session, user)

    assert "Пусть дана функция f(g(x))." in message.replies[0]


async def test_a_clean_record_gets_no_trailing_flag_message(session):
    user = await _user(session)
    note = await _note(session, user)
    message = _Message()

    await corpus.cmd_note(message, _cmd(str(note.id)), session, user)

    assert len(message.replies) == 1


# ── /search ──────────────────────────────────────────────────────────────────
# PostgreSQL full text cannot run on SQLite: to_tsvector does not exist there.
# What is checkable without a server is the shape of the statement, and that
# is worth checking — the regconfig has to be inlined rather than bound, or
# asyncpg fails at run time on a query that looks perfectly fine here.

import os  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402


def _compiled() -> str:
    return str(
        corpus._search_stmt(1, "производная").compile(dialect=postgresql.dialect())
    )


def test_search_uses_the_russian_configuration():
    # Inlined, not bound: asyncpg cannot infer regconfig for a placeholder.
    assert "to_tsvector('russian'" in _compiled()
    assert "plainto_tsquery('russian'" in _compiled()


def test_search_covers_both_title_and_body():
    sql = _compiled()
    assert "notes.title" in sql and "notes.markdown" in sql


def test_search_is_ranked_and_scoped_and_capped():
    sql = _compiled()
    assert "ts_rank(" in sql
    assert "notes.user_id =" in sql  # never search another corpus
    assert "LIMIT" in sql


async def test_search_without_a_query_explains_itself(session):
    user = await _user(session)
    message = _Message()

    await corpus.cmd_search(message, _cmd("   "), session, user)

    assert message.replies == [texts.SEARCH_USAGE]


_TEST_DB = os.environ.get("TEST_DATABASE_URL")

pg_only = pytest.mark.skipif(
    not _TEST_DB, reason="TEST_DATABASE_URL not set (full text needs PostgreSQL)"
)


@pytest_asyncio.fixture
async def pg_session():
    engine = create_async_engine(_TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pg_only
async def test_a_declined_form_is_found(pg_session):
    """The reason this is full text and not ILIKE: «производная» has to find
    «производной». A search that misses the declined form of the word you just
    typed is not a search."""
    user = await _user(pg_session)
    await _note(
        pg_session, user, markdown="Вычисление производной сложной функции."
    )
    message = _Message()

    await corpus.cmd_search(message, _cmd("производная"), pg_session, user)

    assert "Производная сложной функции" in message.replies[0]


@pg_only
async def test_search_finds_nothing_politely(pg_session):
    user = await _user(pg_session)
    await _note(pg_session, user)
    message = _Message()

    await corpus.cmd_search(message, _cmd("фотосинтез"), pg_session, user)

    assert message.replies == [texts.search_empty("фотосинтез")]


@pg_only
async def test_search_never_reaches_another_corpus(pg_session):
    mine = await _user(pg_session, tg_id=1)
    theirs = await _user(pg_session, tg_id=2)
    await _note(pg_session, theirs, title="Чужая запись", markdown="производная")
    message = _Message()

    await corpus.cmd_search(message, _cmd("производная"), pg_session, mine)

    assert message.replies == [texts.search_empty("производная")]


@pg_only
async def test_search_is_logged_with_the_query(pg_session):
    user = await _user(pg_session)
    await corpus.cmd_search(_Message(), _cmd("интеграл"), pg_session, user)

    events = await _events(pg_session, "corpus_searched")
    assert events[0].payload == {"query": "интеграл", "found": 0}
