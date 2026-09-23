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
from app.db.models import Base, Event, Note, NoteTopic, User


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
    def __init__(self, text: str = ""):
        self.text = text
        self.replies: list[str] = []
        self.documents: list[tuple[str, bytes, str | None]] = []

    async def answer(self, text: str) -> None:
        self.replies.append(text)

    async def answer_document(self, document, caption: str | None = None) -> None:
        self.documents.append((document.filename, document.data, caption))


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
        margin_notes=[],
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


# ── the flags a record carries ───────────────────────────────────────────────


async def test_the_review_box_gives_way_the_same_way(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        status="needs_review",
        numeric_divergences=[{"context": "p", "variants": {"5": 2, "6": 1}}],
    )

    assert [b.title for b in corpus._callouts(note)] == [texts.CALLOUT_DIVERGENCES]


# ── callouts: the same flags, as boxes inside the document ───────────────────


async def test_a_clean_record_has_no_callouts(session):
    user = await _user(session)
    assert corpus._callouts(await _note(session, user)) == []


async def test_a_hole_in_the_record_is_the_first_box(session):
    """A record missing a page must not read as a whole one. The marker stands
    where the page would have been; this box is what the reader sees before
    deciding they are holding the whole lecture, so it goes above the rest."""
    user = await _user(session)
    note = await _note(
        session,
        user,
        status="needs_review",
        missing_pages=[2, 5],
        numeric_divergences=[{"context": "p", "variants": {"5": 2, "6": 1}}],
    )

    boxes = corpus._callouts(note)

    assert boxes[0].title == texts.CALLOUT_MISSING
    assert boxes[0].tone == "warning"
    assert "2" in boxes[0].lines[0] and "5" in boxes[0].lines[1]
    # And it does not swallow the box that was already there.
    assert texts.CALLOUT_DIVERGENCES in [b.title for b in boxes]


async def test_a_record_with_every_page_says_nothing_about_pages(session):
    user = await _user(session)
    note = await _note(session, user, status="needs_review")

    assert texts.CALLOUT_MISSING not in [b.title for b in corpus._callouts(note)]


async def test_a_page_nobody_could_check_gets_its_own_box(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        status="needs_review",
        unverified_pages=[{"page": 3, "reason": texts.UNVERIFIED_DIVERGED}],
    )

    boxes = corpus._callouts(note)

    assert [b.title for b in boxes] == [texts.CALLOUT_UNVERIFIED]
    assert "Страница 3" in boxes[0].lines[0]
    assert texts.UNVERIFIED_DIVERGED in boxes[0].lines[0]


async def test_needs_review_becomes_a_warning_box(session):
    user = await _user(session)
    note = await _note(session, user, status="needs_review")

    boxes = corpus._callouts(note)

    assert [(b.title, b.tone) for b in boxes] == [(texts.CALLOUT_REVIEW, "warning")]
    assert boxes[0].lines == [texts.NEEDS_REVIEW]


async def test_an_arithmetic_issue_becomes_a_box_without_its_emoji(session):
    # mathcheck marks its lines with ❌ and ⚠️, which is right in Telegram and
    # wrong on the page: DejaVu has a glyph for neither.
    user = await _user(session)
    note = await _note(
        session,
        user,
        issues=[
            {
                "kind": "constant",
                "severity": "warning",
                "message": "h отличается от справочного",
                "detail": "6,62 против 6,626",
                "suggestion": "проверьте константу",
            }
        ],
    )

    boxes = corpus._callouts(note)

    assert [b.title for b in boxes] == [texts.CALLOUT_MATH]
    assert boxes[0].tone == "info"
    assert "❌" not in boxes[0].lines[0] and "⚠" not in boxes[0].lines[0]
    assert "h отличается от справочного" in boxes[0].lines[0]
    assert "проверьте константу" in boxes[0].lines[0]


def test_a_divergent_number_reads_as_a_sentence():
    assert texts.divergence_line("сумма", {"2": 2, "3": 1}, page=3) == (
        "с. 3, «сумма»: 2 (2 из 3) или 3 (1 из 3)"
    )


def test_a_number_missing_from_a_run_is_named_rather_than_dashed():
    # consensus writes a gap as "— (пропущено)". Left alone, the dash reads
    # as a stray minus in the middle of the sentence.
    assert texts.divergence_line("", {"5": 2, "— (пропущено)": 1}) == (
        "5 (2 из 3) или пропущено (1 из 3)"
    )


def test_a_context_that_is_only_the_number_is_not_repeated():
    # The shape that produced "с. 4 — 0: 0 — 2, 2 — 1": consensus hands the
    # number back as its own context, and saying it twice was half of what
    # made the line unreadable.
    assert texts.divergence_line("0", {"0": 2, "2": 1}, page=4) == (
        "с. 4: 0 (2 из 3) или 2 (1 из 3)"
    )


def test_a_long_context_is_cut_rather_than_run_on():
    line = texts.divergence_line("очень длинное окружение из тетради", {"1": 3})
    assert "…" in line and len(line) < 60


def test_an_issue_line_carries_message_detail_and_suggestion():
    assert texts.issue_line("не сходится", "6,62 против 6,626", "проверьте") == (
        "не сходится · 6,62 против 6,626 · → проверьте"
    )


def test_an_issue_line_with_nothing_but_a_message():
    assert texts.issue_line("не сходится", None, None) == "не сходится"


def test_an_issue_line_keeps_a_detail_without_a_suggestion():
    assert texts.issue_line("не сходится", "6,62", None) == "не сходится · 6,62"


async def test_a_critical_issue_turns_the_box_amber(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        issues=[{"kind": "chain", "severity": "critical", "message": "цепочка не сходится"}],
    )

    assert corpus._callouts(note)[0].tone == "warning"


async def test_divergences_get_a_box_and_uncertain_spots_do_not(session):
    # A spot that reads two ways is now a remark beside the line it belongs
    # to; only the numbers stay a box, having nowhere in particular to point.
    user = await _user(session)
    note = await _note(
        session,
        user,
        numeric_divergences=[{"context": "p = ", "variants": {"5": 2, "6": 1}}],
        uncertain=[{"text": "щ", "why": "двоится"}],
    )

    assert [b.title for b in corpus._callouts(note)] == [texts.CALLOUT_DIVERGENCES]


async def test_an_uncertain_spot_becomes_a_remark_anchored_on_what_was_read(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        uncertain=[{"text": "∂cv", "why": "почерк неразборчив", "page": 2}],
    )

    remarks = corpus._remarks(note)

    assert [r.anchor for r in remarks] == ["∂cv"]
    assert remarks[0].label == "В рукописи, с. 2"
    assert "почерк неразборчив" in remarks[0].lines[0]


async def test_a_remark_carries_the_other_readings(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        uncertain=[{"text": "∂cv", "why": "двоится", "alternatives": ["дсv", "∂cu"]}],
    )

    assert corpus._remarks(note)[-1].lines[-1] == "другое прочтение: дсv, ∂cu"


async def test_a_remark_without_a_page_says_so_without_one(session):
    user = await _user(session)
    note = await _note(session, user, uncertain=[{"text": "щ", "why": "двоится"}])

    assert corpus._remarks(note)[0].label == "В рукописи"


async def test_a_stored_uncertain_shape_that_is_not_a_dict_is_skipped(session):
    user = await _user(session)
    note = await _note(session, user, uncertain=["мусор", {"text": "щ", "why": "х"}])

    assert [r.anchor for r in corpus._remarks(note)] == ["щ"]


async def test_an_unreadable_issues_payload_does_not_sink_the_boxes(session):
    # Same bargain as the message path: a shape this version cannot read costs
    # its own box, not the record.
    user = await _user(session)
    note = await _note(
        session, user, issues=[{"совсем": "не то"}], uncertain=[{"text": "щ", "why": "двоится"}]
    )

    assert corpus._callouts(note) == []


async def test_the_document_is_built_with_the_boxes_of_the_record(session, monkeypatch):
    # The boxes being right proves nothing if the PDF is rendered without them.
    user = await _user(session)
    note = await _note(session, user, status="needs_review")
    seen: list[list] = []
    original = corpus.pdf.render

    def spy(title, markdown, subtitle=None, callouts=(), byline=None, remarks=()):
        seen.append(list(callouts))
        return original(title, markdown, subtitle, callouts, byline, remarks)

    monkeypatch.setattr(corpus.pdf, "render", spy)
    await corpus.send_record_pdf(_Message(), note)

    assert [b.title for b in seen[0]] == [texts.CALLOUT_REVIEW]


def test_a_byline_joins_what_stood_in_the_margin():
    assert texts.byline(["Шиманская Г. С.", "21.09"]) == "Шиманская Г. С. · 21.09"


def test_an_empty_margin_has_no_byline():
    # An empty line under a title looks worse than no line at all.
    assert texts.byline([]) is None
    assert texts.byline(["", "   "]) is None


def test_a_byline_survives_a_stored_shape_that_is_not_a_string():
    assert texts.byline([None, 3, "с. 4"]) == "None · 3 · с. 4"


async def test_the_document_is_built_with_the_byline_of_the_record(
    session, monkeypatch
):
    user = await _user(session)
    note = await _note(session, user, margin_notes=["Шиманская Г. С."])
    seen: list[str | None] = []
    original = corpus.pdf.render

    def spy(title, markdown, subtitle=None, callouts=(), byline=None, remarks=()):
        seen.append(byline)
        return original(title, markdown, subtitle, callouts, byline, remarks)

    monkeypatch.setattr(corpus.pdf, "render", spy)
    await corpus.send_record_pdf(_Message(), note)

    assert seen == ["Шиманская Г. С."]


async def test_the_document_is_built_with_the_remarks_of_the_record(
    session, monkeypatch
):
    user = await _user(session)
    note = await _note(session, user, uncertain=[{"text": "щ", "why": "двоится"}])
    seen: list[list] = []
    original = corpus.pdf.render

    def spy(title, markdown, subtitle=None, callouts=(), byline=None, remarks=()):
        seen.append(list(remarks))
        return original(title, markdown, subtitle, callouts, byline, remarks)

    monkeypatch.setattr(corpus.pdf, "render", spy)
    await corpus.send_record_pdf(_Message(), note)

    assert [r.anchor for r in seen[0]] == ["щ"]


# ── /stats ───────────────────────────────────────────────────────────────────

from datetime import date  # noqa: E402


def test_russian_number_agreement():
    # Sloppy plurals in a tool used every day are grating, and the rule has
    # three branches plus the 11-14 exception.
    assert texts._plural(1, "запись", "записи", "записей") == "запись"
    assert texts._plural(2, "запись", "записи", "записей") == "записи"
    assert texts._plural(5, "запись", "записи", "записей") == "записей"
    assert texts._plural(11, "запись", "записи", "записей") == "записей"
    assert texts._plural(14, "запись", "записи", "записей") == "записей"
    assert texts._plural(21, "запись", "записи", "записей") == "запись"
    assert texts._plural(22, "запись", "записи", "записей") == "записи"
    assert texts._plural(25, "запись", "записи", "записей") == "записей"
    assert texts._plural(111, "запись", "записи", "записей") == "записей"
    assert texts._plural(0, "запись", "записи", "записей") == "записей"


def test_recent_days_are_named_not_dated():
    today = date(2026, 9, 19)
    assert texts._day(today, today) == "сегодня"
    assert texts._day(date(2026, 9, 18), today) == "вчера"
    assert texts._day(date(2026, 8, 18), today) == "18 августа"


def test_streak_counts_back_from_today():
    today = date(2026, 9, 19)
    days = {today, date(2026, 9, 18), date(2026, 9, 17)}
    assert corpus._streak(days, today) == 3


def test_a_gap_ends_the_streak():
    today = date(2026, 9, 19)
    days = {today, date(2026, 9, 17), date(2026, 9, 16)}
    assert corpus._streak(days, today) == 1


def test_the_streak_survives_a_day_not_yet_started():
    # Nothing today yet, but yesterday and the day before. A counter that read
    # zero every morning until you posted would be noise, not a signal.
    today = date(2026, 9, 19)
    days = {date(2026, 9, 18), date(2026, 9, 17)}
    assert corpus._streak(days, today) == 2


def test_the_streak_breaks_after_a_whole_missed_day():
    today = date(2026, 9, 19)
    days = {date(2026, 9, 17), date(2026, 9, 16)}
    assert corpus._streak(days, today) == 0


def test_no_records_no_streak():
    assert corpus._streak(set(), date(2026, 9, 19)) == 0


async def test_stats_on_an_empty_corpus(session):
    user = await _user(session)
    message = _Message()

    await corpus.cmd_stats(message, session, user)

    assert message.replies == [texts.STATS_EMPTY]


async def test_stats_counts_records_and_pages(session):
    user = await _user(session)
    await _note(session, user, page_count=3)
    await _note(session, user, page_count=1)
    message = _Message()

    await corpus.cmd_stats(message, session, user)

    assert "2 записи" in message.replies[0]
    assert "4 страницы" in message.replies[0]


async def test_stats_reports_a_running_streak(session):
    user = await _user(session)
    now = datetime.now(timezone.utc)
    for back in (0, 1, 2):
        await _note(session, user, created_at=now - timedelta(days=back))
    message = _Message()

    await corpus.cmd_stats(message, session, user)

    assert "Подряд: 3 дня" in message.replies[0]


async def test_stats_counts_one_record_per_day_not_per_record(session):
    user = await _user(session)
    now = datetime.now(timezone.utc)
    for _ in range(4):
        await _note(session, user, created_at=now)
    message = _Message()

    await corpus.cmd_stats(message, session, user)

    assert "Подряд: 1 день" in message.replies[0]


async def test_stats_ignores_another_corpus(session):
    mine = await _user(session, tg_id=1)
    theirs = await _user(session, tg_id=2)
    await _note(session, mine, page_count=1)
    await _note(session, theirs, page_count=9)
    message = _Message()

    await corpus.cmd_stats(message, session, mine)

    assert "1 запись" in message.replies[0]
    assert "1 страница" in message.replies[0]


async def test_stats_is_logged(session):
    user = await _user(session)
    await _note(session, user)

    await corpus.cmd_stats(_Message(), session, user)

    assert len(await _events(session, "stats_viewed")) == 1


async def test_help_lists_what_the_bot_can_do(session):
    user = await _user(session)
    message = _Message()

    await corpus.cmd_help(message, session, user)

    assert message.replies == [texts.HELP]


async def test_help_is_logged(session):
    user = await _user(session)

    await corpus.cmd_help(_Message(), session, user)

    assert len(await _events(session, "help_viewed")) == 1


# ── delivering a record as a file ────────────────────────────────────────────


def test_a_filename_keeps_the_record_number_and_the_title():
    assert corpus.pdf_filename(42, "Производная функции") == (
        "42-Производная-функции.pdf"
    )


def test_a_filename_drops_characters_a_filesystem_would_object_to():
    name = corpus.pdf_filename(7, 'Граф: "мульти"/петля \\ *?')
    assert name.startswith("7-")
    assert name.endswith(".pdf")
    assert not set(name) & set(':"/\\*?')


def test_a_filename_survives_a_title_with_nothing_usable_in_it():
    assert corpus.pdf_filename(9, "!!! ??? ...") == "zapis-9.pdf"


def test_a_long_title_is_trimmed_in_the_filename():
    assert len(corpus.pdf_filename(1, "я" * 200)) < 60


async def test_a_record_is_delivered_as_a_pdf(session):
    user = await _user(session)
    note = await _note(session, user, markdown="Граф $G$ — пара множеств.")
    message = _Message()

    assert await corpus.send_record_pdf(message, note) is True

    filename, data, caption = message.documents[0]
    assert data.startswith(b"%PDF-")
    assert filename.startswith(f"{note.id}-")
    # The caption names the record and nothing else: it used to offer /note,
    # and a caption pointing at a command the bot no longer answers is worse
    # than one that points nowhere.
    assert f"#{note.id}" in caption
    assert "/" not in caption


async def test_a_record_that_cannot_be_drawn_still_reaches_the_user(session):
    # Presentation is never worth losing a record over.
    user = await _user(session)
    note = await _note(session, user)
    message = _Message()

    import app.services.pdf as pdf_module

    original = pdf_module.render
    pdf_module.render = lambda *a, **k: 1 / 0
    try:
        await corpus.send_record(message, note)
    finally:
        pdf_module.render = original

    assert message.documents == []
    assert texts.PDF_FAILED in message.replies[0]
    assert "Пусть дана функция f(g(x))." in "".join(message.replies)




# ── tags: filing a record and finding it again ───────────────────────────────
# The whole product in two gestures. A "#word" means one of two things and no
# state machine decides which — the newest record does: untagged, and the
# bot's question is still open; tagged, and nothing was asked.


def _days_ago(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


async def _with_topics(session, note: Note, *topics: str) -> Note:
    session.add_all([NoteTopic(note_id=note.id, topic=t) for t in topics])
    await session.flush()
    return note


async def test_a_tag_answers_the_question_the_bot_just_asked(session):
    user = await _user(session)
    note = await _note(session, user)  # no subject yet: the question is open
    message = _Message(text="#физика")

    await corpus.on_tag(message, session, user)

    assert note.tag == "физика"
    assert "физика" in message.replies[0]
    assert not message.documents  # filing is not finding


async def test_filing_a_record_is_logged(session):
    user = await _user(session)
    note = await _note(session, user)

    await corpus.on_tag(_Message(text="#матан"), session, user)

    events = await _events(session, "note_tagged")
    assert [e.payload["note_id"] for e in events] == [note.id]
    assert events[0].payload["tag"] == "матан"


async def test_a_tag_searches_once_nothing_is_waiting_to_be_filed(session):
    user = await _user(session)
    note = await _note(session, user, tag="физика", title="Спектры атомов")
    message = _Message(text="#физика")

    await corpus.on_tag(message, session, user)

    assert note.tag == "физика"  # not overwritten
    assert message.documents  # the record itself came back


async def test_an_older_untagged_record_is_not_filed_by_a_later_search(session):
    """The rule is about the newest record and only the newest.

    An untagged record from last week is a question the user walked away from.
    A search typed today must not answer it — that would file a record under a
    subject nobody chose for it, and silently.
    """
    user = await _user(session)
    forgotten = await _note(session, user, created_at=_days_ago(7))
    await _note(session, user, tag="матан", created_at=_days_ago(0))

    await corpus.on_tag(_Message(text="#физика"), session, user)

    assert forgotten.tag is None


async def test_a_record_is_found_by_a_topic_the_bot_wrote(session):
    # The user never typed this word; the bot read it off a heading. That is
    # the half of the search the user is not expected to remember.
    user = await _user(session)
    note = await _note(session, user, tag="матан", title="Производная")
    await _with_topics(session, note, "производная_сложной_функции")

    message = _Message(text="#производная_сложной_функции")
    await corpus.on_tag(message, session, user)

    assert message.documents


async def test_one_match_is_the_record_and_not_a_line_about_it(session):
    user = await _user(session)
    note = await _note(session, user, tag="физика", markdown="Граф $G$ — пара.")

    message = _Message(text="#физика")
    await corpus.on_tag(message, session, user)

    filename, data, _ = message.documents[0]
    assert data.startswith(b"%PDF-")
    assert filename.startswith(f"{note.id}-")


async def test_several_matches_come_back_as_topics_to_choose_from(session):
    user = await _user(session)
    first = await _note(
        session, user, tag="физика", title="Спектры атомов", created_at=_days_ago(2)
    )
    second = await _note(
        session, user, tag="физика", title="Модель Бора", created_at=_days_ago(1)
    )
    await _with_topics(session, first, "спектры_атомов")
    await _with_topics(session, second, "модель_бора")

    message = _Message(text="#физика")
    await corpus.on_tag(message, session, user)

    assert not message.documents  # a choice, not a document
    reply = message.replies[0]
    assert "Спектры атомов" in reply and "Модель Бора" in reply
    # Every line carries what to type next. A list you cannot act on just
    # makes the user type the same tag again.
    assert "#спектры_атомов" in reply and "#модель_бора" in reply


async def test_nothing_under_a_tag_offers_the_tags_there_are(session):
    user = await _user(session)
    await _note(session, user, tag="матан")

    message = _Message(text="#химия")
    await corpus.on_tag(message, session, user)

    assert "химия" in message.replies[0]
    assert "#матан" in message.replies[0]


async def test_searching_is_logged_with_what_was_looked_for(session):
    user = await _user(session)
    await _note(session, user, tag="матан")

    await corpus.on_tag(_Message(text="#химия"), session, user)

    events = await _events(session, "topic_searched")
    assert events[0].payload == {"tag": "химия", "found": 0}


async def test_a_search_never_reaches_another_corpus(session):
    # The invariant this module exists to keep: one user today is not a reason
    # to write a query that returns someone else's record tomorrow.
    mine = await _user(session, tg_id=1)
    theirs = await _user(session, tg_id=2)
    await _note(session, mine, tag="матан")
    hidden = await _note(session, theirs, tag="физика", title="Чужая запись")
    await _with_topics(session, hidden, "чужая_тема")

    message = _Message(text="#чужая_тема")
    await corpus.on_tag(message, session, mine)

    assert not message.documents
    assert "Чужая запись" not in message.replies[0]


async def test_a_message_that_is_not_a_readable_tag_says_so(session):
    user = await _user(session)
    message = _Message(text="#!!!")

    await corpus.on_tag(message, session, user)

    assert message.replies == [texts.TAG_UNREADABLE]


async def test_known_tags_come_back_most_used_first(session):
    user = await _user(session)
    for _ in range(3):
        await _note(session, user, tag="матан")
    await _note(session, user, tag="физика")

    assert await corpus.known_tags(session, user) == ["матан", "физика"]


async def test_known_tags_are_this_users_own(session):
    mine = await _user(session, tg_id=1)
    theirs = await _user(session, tg_id=2)
    await _note(session, mine, tag="матан")
    await _note(session, theirs, tag="химия")

    assert await corpus.known_tags(session, mine) == ["матан"]


async def test_topics_are_stored_where_the_record_is_made(session):
    user = await _user(session)
    note = await _note(
        session, user, title="Квантовая механика", markdown="## Модель Бора\n\nтекст"
    )

    stored = await corpus.save_topics(session, note)
    await session.flush()

    rows = (
        await session.execute(
            select(NoteTopic.topic).where(NoteTopic.note_id == note.id)
        )
    ).scalars().all()
    assert stored == ["квантовая_механика", "модель_бора"]
    assert set(rows) == set(stored)


async def test_the_question_shows_the_topics_and_the_subjects_in_use(session):
    """The bot wrote those topics, and something the bot wrote should be read
    by the person it belongs to on the day it was made — not discovered months
    later in a search that missed."""
    user = await _user(session)
    await _note(session, user, tag="матан")
    note = await _note(
        session, user, title="Квантовая механика", markdown="## Модель Бора\n"
    )

    message = _Message()
    await corpus.ask_for_tag(message, session, user, note)

    reply = message.replies[0]
    assert "#квантовая_механика" in reply and "#модель_бора" in reply
    assert "#матан" in reply  # so a second spelling of it never gets created
