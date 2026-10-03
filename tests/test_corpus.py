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
from app.db.models import Base, Event, Group, Note, NoteTopic, User
from app.services import graphcheck


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

    async def answer(self, text: str, reply_markup=None) -> None:
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


# ── what the document says about the record ─────────────────────────────────
# The author's decision, 2026-09-25: what a check found wrong, at its place, and
# the pages a record is missing — and nothing about how a page was read.


async def test_a_clean_record_has_no_callouts(session):
    user = await _user(session)
    assert corpus._callouts(await _note(session, user)) == []


async def test_a_hole_in_the_record_is_the_one_box(session):
    """A record missing a page must not read as a whole one. The marker stands
    where the page would have been; this box is what the reader sees before
    deciding they are holding the whole lecture."""
    user = await _user(session)
    note = await _note(session, user, status="needs_review", missing_pages=[2, 5])

    boxes = corpus._callouts(note)

    assert [(b.title, b.tone) for b in boxes] == [(texts.CALLOUT_MISSING, "warning")]
    assert "2" in boxes[0].lines[0] and "5" in boxes[0].lines[1]


async def test_how_the_page_was_read_is_never_printed(session):
    """Numbers the runs read differently, a spot that reads two ways, a page no
    second reading confirmed, a record marked for review: the columns keep
    them for the measurements, and the document says none of it."""
    user = await _user(session)
    note = await _note(
        session,
        user,
        status="needs_review",
        numeric_divergences=[{"context": "p", "variants": {"5": 2, "6": 1}}],
        uncertain=[{"text": "Дьюринг", "why": "двоится", "alternatives": ["Тьюринг"]}],
        unverified_pages=[{"page": 3, "reason": texts.UNVERIFIED_DIVERGED}],
    )

    assert corpus._callouts(note) == []
    assert corpus._remarks(note) == []


def test_the_head_of_a_page_carries_no_doubt_about_the_reading():
    # The subject and the day, as facts; the grey line that carried the date
    # under the title once ended in "нужна проверка".
    assert texts.pdf_date(datetime(2026, 9, 25, tzinfo=timezone.utc)) == "25.09.2026"
    assert texts.pdf_subject("матан") == "#матан"
    assert texts.pdf_subject(None) == ""


async def test_a_finding_is_a_remark_under_the_text_it_is_about(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        issues=[
            {
                "kind": "chain",
                "severity": "critical",
                "message": "строка 29: звенья цепочки не сходятся",
                "detail": "2 + 2 = 4   ⟶   5 = 5   (отличие в 1.25 раз)",
                "suggestion": "",
                "anchor": "2 + 2 = 5",
                "page": 2,
            }
        ],
    )

    remarks = corpus._remarks(note)

    assert [(r.anchor, r.label, r.tone) for r in remarks] == [
        ("2 + 2 = 5", texts.FINDING_LABEL, "warning")
    ]
    # Beside the line, its number on the page as recognised says nothing.
    assert remarks[0].lines == [
        "**Звенья цепочки не сходятся.** 2 + 2 = 4 ⟶ 5 = 5 (отличие в 1.25 раз)"
    ]


async def test_a_warning_is_set_in_the_quieter_accent_with_its_suggestion(session):
    # mathcheck marks its lines with ❌ and ⚠️, which is right in Telegram and
    # wrong on the page: the accent of the box carries the severity.
    user = await _user(session)
    note = await _note(
        session,
        user,
        issues=[
            {
                "kind": "constant",
                "severity": "warning",
                "message": "постоянная Планка (h) записана неверно",
                "detail": "в записи 6.6e-34, табличное 6.62607e-34 Дж·с "
                "(расхождение 0.4%)",
                "suggestion": "проверьте константу",
                "anchor": "h = 6.6e-34",
            }
        ],
    )

    remark = corpus._remarks(note)[0]

    assert remark.tone == "info"
    assert remark.lines[0].startswith(
        "**Постоянная Планка (h) записана неверно.** в записи 6.6e-34"
    )
    assert remark.lines[0].endswith("(расхождение 0.4%)")
    assert remark.lines[-1] == "→ проверьте константу"


async def test_the_latex_a_finding_quotes_is_marked_to_be_drawn(session):
    # mathcheck quotes the links of a chain as the page wrote them: inside a
    # formula, LaTeX with no dollars round it.
    user = await _user(session)
    note = await _note(
        session,
        user,
        issues=[
            {
                "kind": "chain",
                "severity": "critical",
                "message": "строка 3: звенья цепочки не сходятся",
                "detail": r"\frac{1}{2} = 0.5   ⟶   0.6 = 0.6   (отличие в 1.2 раз)",
                "anchor": r"\frac{1}{2} = 0.6",
            }
        ],
    )

    assert corpus._remarks(note)[0].lines[0] == (
        r"**Звенья цепочки не сходятся.** $\frac{1}{2} = 0.5$ ⟶ 0.6 = 0.6"
        " (отличие в 1.2 раз)"
    )


async def test_a_matrix_against_its_graph_is_labelled_as_such(session):
    user = await _user(session)
    note = await _note(
        session,
        user,
        issues=[
            {
                "kind": "matrix",
                "severity": "critical",
                "message": "Матрица смежности не сходится с графом",
                "detail": "(1, 2): ребро есть, в матрице 0",
                "anchor": "1-2, 2-3",
            }
        ],
    )

    remark = corpus._remarks(note)[0]

    assert (remark.label, remark.anchor) == (texts.GRAPH_FINDING_LABEL, "1-2, 2-3")


async def test_a_cell_that_could_not_be_read_is_not_an_error(session):
    # graphcheck fills an unread cell from the graph. That is about how the
    # page was read, and the cell carries its own [неразборчиво].
    user = await _user(session)
    note = await _note(
        session,
        user,
        issues=[
            {
                "kind": "matrix",
                "severity": "warning",
                "message": graphcheck.UNREAD_CELLS,
                "detail": "по графу там стоит: (1, 2) = 1",
                "anchor": "1-2",
            }
        ],
    )

    assert corpus._remarks(note) == []


async def test_a_finding_stored_before_anchors_is_found_again_in_the_text(session):
    # Records made before 2026-09-25 carry no anchor: the same checks run
    # again over the stored text and give the finding its text back.
    user = await _user(session)
    note = await _note(
        session,
        user,
        markdown="Сложим:\n\n$$2 + 2 = 4 = 5$$",
        issues=[
            {
                "kind": "chain",
                "severity": "critical",
                "message": "строка 7: звенья цепочки не сходятся",
                "detail": "4 = 4   ⟶   5 = 5   (отличие в 1.25 раз)",
                "page": 2,
            }
        ],
    )

    assert [(r.anchor, r.tone) for r in corpus._remarks(note)] == [
        ("2 + 2 = 4 = 5", "warning")
    ]


async def test_what_the_checks_no_longer_find_is_not_printed(session):
    # Record 45 carried a congruence read as a chain of equalities, stored
    # before task 42 taught the check to leave such a line alone.
    user = await _user(session)
    note = await _note(
        session,
        user,
        markdown=r"$1001 = 12 \cdot 83 + 5 \Rightarrow 2^{1001} \equiv 1^{83} \cdot 2^5 = 32$",
        issues=[
            {
                "kind": "chain",
                "severity": "critical",
                "message": "строка 29: звенья цепочки не сходятся",
                "detail": "1001 = 1001   ⟶   32 = 32   (отличие в 0.03197 раз)",
            }
        ],
    )

    assert corpus._remarks(note) == []


async def test_an_unreadable_issues_payload_does_not_sink_the_boxes(session):
    # A shape this version cannot read costs its own box, not the record.
    user = await _user(session)
    note = await _note(session, user, issues=[{"совсем": "не то"}, "мусор"])

    assert corpus._remarks(note) == []


async def test_what_the_bot_added_is_built_into_boxes_with_their_sources(session):
    user = await _user(session)
    note = await _note(session, user)
    note.explanations = [
        {
            "anchor": "(1)",
            "title": "Формула Эйлера.",
            "text": "поворот на угол",
            "sources": [{"title": "wikipedia.org", "uri": "https://ru.wikipedia.org/x"}],
        },
        "мусор",
        {"anchor": "x", "text": ""},
    ]
    note.summary = "Введена тригонометрическая форма."

    boxes = corpus._explanations(note)

    assert len(boxes) == 1
    assert boxes[0].label == texts.EXPLANATION_LABEL
    assert boxes[0].lines == ["**Формула Эйлера.** поворот на угол"]
    assert boxes[0].sources == [("wikipedia.org", "https://ru.wikipedia.org/x")]
    assert corpus._summary(note).label == texts.SUMMARY_LABEL


async def test_a_record_without_additions_has_no_boxes_and_no_summary(session):
    user = await _user(session)
    note = await _note(session, user)
    assert corpus._explanations(note) == []
    assert corpus._summary(note) is None


async def test_the_document_is_built_with_the_boxes_of_the_record(session, monkeypatch):
    # The boxes being right proves nothing if the PDF is rendered without them.
    user = await _user(session)
    note = await _note(
        session,
        user,
        status="needs_review",
        missing_pages=[2],
        markdown="Пусть $2 + 2 = 5$.",
        issues=[
            {
                "kind": "chain",
                "severity": "critical",
                "message": "не сходится",
                "anchor": "2 + 2 = 5",
            }
        ],
    )
    seen: list = []
    original = corpus.pdf.render

    def spy(title, markdown, **parts):
        seen.append((parts["page"], list(parts["callouts"]), list(parts["remarks"])))
        return original(title, markdown, **parts)

    monkeypatch.setattr(corpus.pdf, "render", spy)
    await corpus.send_record_pdf(_Message(), session, note)

    page, callouts, remarks = seen[0]
    assert "проверка" not in f"{page.subject} {page.date}"
    assert [b.title for b in callouts] == [texts.CALLOUT_MISSING]
    assert [r.anchor for r in remarks] == ["2 + 2 = 5"]


def test_a_byline_joins_what_stood_in_the_margin():
    assert texts.byline(["Шиманская Г. С.", "21.09"]) == "Шиманская Г. С. · 21.09"


def test_an_empty_margin_has_no_byline():
    # An empty line under a title looks worse than no line at all.
    assert texts.byline([]) is None
    assert texts.byline(["", "   "]) is None


def test_a_byline_survives_a_stored_shape_that_is_not_a_string():
    # What is not a name, a date or a page has no place under the title.
    assert texts.byline([None, 3, "с. 4"]) == "3 · с. 4"


async def test_the_document_is_built_with_the_byline_of_the_record(
    session, monkeypatch
):
    user = await _user(session)
    note = await _note(session, user, margin_notes=["Шиманская Г. С."])
    seen: list[str | None] = []
    original = corpus.pdf.render

    def spy(title, markdown, **parts):
        seen.append(parts["byline"])
        return original(title, markdown, **parts)

    monkeypatch.setattr(corpus.pdf, "render", spy)
    await corpus.send_record_pdf(_Message(), session, note)

    assert seen == ["Шиманская Г. С."]


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

    assert await corpus.send_record_pdf(message, session, note) is True

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
        await corpus.send_record(message, session, note)
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


# ── a group chat: the records are the chat's ─────────────────────────────────
# Phase C's one sentence: a record belongs to the chat it was made in, not to
# whoever photographed it. Any member reaches a group's records from the
# group; nobody reaches them from anywhere else — not another group, and not
# the photographer's own private chat.


async def _group(session, chat_id: int = -100500) -> Group:
    group = Group(tg_chat_id=chat_id, title="Матан, 2 курс")
    session.add(group)
    await session.flush()
    return group


async def test_any_member_finds_what_another_photographed(session):
    photographer = await _user(session, tg_id=1)
    classmate = await _user(session, tg_id=2)
    group = await _group(session)
    note = await _note(session, photographer, group_id=group.id, tag="матан")

    message = _Message(text="#матан")
    await corpus.on_tag(message, session, classmate, group)

    filename, _, _ = message.documents[0]
    assert filename.startswith(f"{note.id}-")


async def test_a_group_never_reaches_another_groups_records(session):
    user = await _user(session)
    ours, theirs = await _group(session, -1), await _group(session, -2)
    await _note(session, user, group_id=theirs.id, tag="матан")

    message = _Message(text="#матан")
    await corpus.on_tag(message, session, user, ours)

    assert message.documents == [] and message.replies == []


async def test_a_group_never_reaches_a_private_record(session):
    user = await _user(session)
    group = await _group(session)
    await _note(session, user, tag="матан")  # made in the user's private chat

    message = _Message(text="#матан")
    await corpus.on_tag(message, session, user, group)

    assert message.documents == []


async def test_a_group_record_is_not_found_from_its_photographers_private_chat(
    session,
):
    """It is the chat's record. Its photographer finds it where everyone
    else does — in the group."""
    user = await _user(session)
    group = await _group(session)
    await _note(session, user, group_id=group.id, tag="матан")

    message = _Message(text="#матан")
    await corpus.on_tag(message, session, user)

    assert message.documents == []
    assert "ничего не нашлось" in message.replies[0]


async def test_a_word_in_a_group_only_ever_searches(session):
    """The private chat's stateless question — the newest record untagged, so
    the next "#word" files it — cannot work where the newest record is
    everyone's and the next "#word" anyone's. A group never asks, so a word
    there never files."""
    user = await _user(session)
    group = await _group(session)
    untagged = await _note(session, user, group_id=group.id)

    await corpus.on_tag(_Message(text="#дз"), session, user, group)

    assert untagged.tag is None
    assert await _events(session, "note_tagged") == []


async def test_a_search_that_misses_in_a_group_is_silent_and_still_logged(session):
    # "#дз" in a course chat is the members' own hashtag far more often than
    # a search, and an answer to each one would be the bot talking over them.
    user = await _user(session)
    group = await _group(session)

    message = _Message(text="#дз")
    await corpus.on_tag(message, session, user, group)

    assert message.replies == []
    event = (await _events(session, "topic_searched"))[0]
    assert event.payload == {"tag": "дз", "found": 0}
    assert event.group_id == group.id


async def test_an_unreadable_tag_in_a_group_is_silent(session):
    user = await _user(session)
    group = await _group(session)

    message = _Message(text="#!!!")
    await corpus.on_tag(message, session, user, group)

    assert message.replies == []


async def test_the_subjects_offered_in_a_group_are_the_groups(session):
    user = await _user(session)
    group = await _group(session)
    await _note(session, user, group_id=group.id, tag="матан")
    await _note(session, user, tag="физика")  # private

    assert await corpus.known_tags(session, user, group) == ["матан"]
    assert await corpus.known_tags(session, user) == ["физика"]


async def test_stats_in_a_group_count_the_groups_records(session):
    photographer = await _user(session, tg_id=1)
    classmate = await _user(session, tg_id=2)
    group = await _group(session)
    await _note(session, photographer, group_id=group.id, page_count=3)
    await _note(session, classmate, group_id=group.id, page_count=2)
    await _note(session, classmate, page_count=7)  # private

    message = _Message()
    await corpus.cmd_stats(message, session, classmate, group)

    assert message.replies[0].startswith("2 записи, 5 страниц")
    assert (await _events(session, "stats_viewed"))[0].group_id == group.id


async def test_help_in_a_group_explains_the_group(session):
    user = await _user(session)
    group = await _group(session)

    message = _Message()
    await corpus.cmd_help(message, session, user, group)

    assert message.replies == [texts.GROUP_HELP]
    assert "#матан" in texts.GROUP_HELP  # the tag in the caption is the rule


async def test_a_record_that_came_with_its_subject_is_not_asked_about(session):
    """In a group the tag in the caption is what made the bot take the photo,
    and in a private chat it answers the question before it is asked. Either
    way what comes back is where the record was filed, with the topics it can
    be found by."""
    user = await _user(session)
    note = await _note(
        session, user, tag="матан", title="Комплексные числа", markdown="## Модуль\n"
    )

    message = _Message()
    await corpus.ask_for_tag(message, session, user, note)

    reply = message.replies[0]
    assert reply == texts.filed("матан", ["комплексные_числа", "модуль"])
    assert "Под каким тегом" not in reply
