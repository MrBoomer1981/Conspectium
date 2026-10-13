"""A chat's subjects and their lectures (task 63): where a record is filed,
which lecture it is a notebook of, and the day that lecture was given.

A subject is a chat's "#word" made a row; a lecture is one class of it on one
day, and every material of that class points at it. Two notebooks of one
lecture — a classmate's sent after the CEO's — are one lecture: merge.py says
so by their text, the fullest is the base, and the document drawn for the
lecture is the base with what the others add (corpus.send_record_pdf).

`Note.tag` stays the word a record was filed under, and the search still
reads it: this module writes it, with the subject and the lecture, and
nothing else does. Nothing here calls the model.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import tags
from app.db.models import Lecture, Note, NoteTopic, Subject
from app.services import merge, pdf

# A notebook is sent within a week of its lecture, or with its date.
_SAME_WEEK = timedelta(days=7)

# How a lecture's day is known, worst first: a later notebook that knows it
# better moves the lecture to its day.
_SOURCES = ("sent", "page", "caption")

_MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
# "12.09", "12.09.2026", "12/09/26", "25.09." — and "12 сентября".
_NUMERIC_DAY = r"(\d{1,2})[./](\d{1,2})(?:[./](\d{4}|\d{2}))?\.?"
_WORDED_DAY = rf"(\d{{1,2}})\s+({'|'.join(_MONTHS)})(?:\s+(\d{{4}}))?"
_DAY_IN_TEXT_RE = re.compile(
    rf"(?<![\d.]){_NUMERIC_DAY}(?![\d])|(?<!\d){_WORDED_DAY}", re.IGNORECASE
)
_DAY_ALONE_RE = re.compile(rf"^(?:{_NUMERIC_DAY}|{_WORDED_DAY})$", re.IGNORECASE)
# What separates the things the margin held, as texts.byline splits them.
_MARGIN_SEPARATOR_RE = re.compile(r"\s*[·,;]\s*")


@dataclass
class Day:
    value: date
    source: str  # "caption" | "page" | "sent"


@dataclass
class Filing:
    """Where a record went: its lecture, whether that lecture had a notebook
    before it, and how many it has now."""

    lecture: Lecture
    joined: bool
    materials: int


def _day(found: re.Match, sent: date, page: bool = False) -> date | None:
    """A day as the caption or the margin wrote it.

    The caption is the sender's: a year it names is the year, and without one
    the latest such day not after the day the pages came — in January a
    lecture of "12.12" was last December's.

    A margin's day is a reading of the page, and a lecture cannot have been
    given after its notebook was photographed: a day the margin names after
    the pages came — a day's grace for the timezone — dates nothing. Taken
    for last year's, «10 ноября» on a notebook sent on 6 October 2026 headed
    record 79's document 10.11.2025 (task 71). Last year's notebook is dated
    by its caption."""
    numeric_day, numeric_month, numeric_year, worded_day, month_name, worded_year = (
        found.groups()
    )
    if numeric_day:
        day, month, year = int(numeric_day), int(numeric_month), numeric_year
    else:
        day = int(worded_day)
        month = _MONTHS.index(month_name.lower()) + 1
        year = worded_year
    try:
        if year:
            value = int(year)
            given = date(value + 2000 if value < 100 else value, month, day)
        else:
            given = date(sent.year, month, day)
        if given > sent + timedelta(days=1):
            if page:
                return None
            if not year:
                given = date(sent.year - 1, month, day)
        return given
    except ValueError:
        return None  # "31.02", or a number that only looks like a day


def day_of(caption: str | None, margin_notes: list, sent: date) -> Day:
    """The day a lecture was given: the one the caption names, else the one
    the margin names when it names one and only one — a page that ends one
    lecture and begins the next can carry both — else the day the pages
    came."""
    if caption:
        found = _DAY_IN_TEXT_RE.search(caption)
        if found:
            given = _day(found, sent)
            if given is not None:
                return Day(given, "caption")
    days = set()
    for note in margin_notes or []:
        for part in _MARGIN_SEPARATOR_RE.split(str(note).strip()):
            found = _DAY_ALONE_RE.match(part)
            given = _day(found, sent, page=True) if found else None
            if given is not None:
                days.add(given)
    if len(days) == 1:
        return Day(days.pop(), "page")
    return Day(sent, "sent")


def _sent(note: Note) -> date:
    stamp = note.created_at
    if not isinstance(stamp, datetime):
        return datetime.now(timezone.utc).date()
    if stamp.tzinfo is None:
        return stamp.date()
    return stamp.astimezone(timezone.utc).date()


def _owner(group_id: int | None, user_id: int):
    """The subjects a chat may file into: a group's, or in a private chat the
    user's own — the rule corpus._owned keeps for records."""
    if group_id is not None:
        return Subject.group_id == group_id
    return (Subject.group_id.is_(None)) & (Subject.user_id == user_id)


async def _subject(
    session: AsyncSession, group_id: int | None, user_id: int, word: str, create: bool
) -> Subject | None:
    lookup = select(Subject).where(_owner(group_id, user_id), Subject.word == word)
    found = (await session.execute(lookup)).scalar_one_or_none()
    if found is not None or not create:
        return found
    subject = Subject(
        group_id=group_id, user_id=None if group_id is not None else user_id, word=word
    )
    # Two albums under a new word at once: the loser fetches the winner's row
    # rather than failing on the unique index, as middlewares._insert_or_fetch
    # does for a user.
    try:
        async with session.begin_nested():
            session.add(subject)
    except IntegrityError:
        return (await session.execute(lookup)).scalar_one()
    return subject


async def materials(session: AsyncSession, lecture_id: int) -> list[Note]:
    """A lecture's notebooks, in the order they were filed."""
    stmt = select(Note).where(Note.lecture_id == lecture_id).order_by(Note.id)
    return list((await session.execute(stmt)).scalars().all())


def _completeness(note: Note) -> int:
    return merge.completeness(note.markdown or "", len(note.missing_pages or []))


def base_of(notes: list[Note]) -> Note:
    """The notebook a lecture's document is drawn from: the fullest, the
    first filed when two are as full."""
    return max(notes, key=lambda note: (_completeness(note), -note.id))


async def _lecture_of(
    session: AsyncSession, subject_id: int, markdown: str | list[str], day: Day
) -> Lecture | None:
    """The lecture of this subject a text is a notebook of, if there is one:
    within a week of its day — never another day when both days were written
    down — and at least half of one text found in the other. Unsure, none:
    two documents are better than one mixed. Several texts — the notebooks
    of one lecture moved together — are one lecture's: the best of any of
    them decides."""
    mine = [markdown] if isinstance(markdown, str) else markdown
    stmt = select(Lecture).where(
        Lecture.subject_id == subject_id,
        Lecture.given_on >= day.value - _SAME_WEEK,
        Lecture.given_on <= day.value + _SAME_WEEK,
    )
    best: Lecture | None = None
    best_score = merge.SAME_LECTURE
    for lecture in (await session.execute(stmt)).scalars().all():
        if (
            day.source != "sent"
            and lecture.date_source != "sent"
            and lecture.given_on != day.value
        ):
            continue
        texts = (
            await session.execute(
                select(Note.markdown).where(Note.lecture_id == lecture.id)
            )
        ).scalars().all()
        score = max(
            (merge.same_lecture(text or "", own) for text in texts for own in mine),
            default=0.0,
        )
        if score >= best_score:
            best, best_score = lecture, score
    return best


@dataclass
class Joining:
    """The lecture a record about to be made would join, and whether it would
    be that lecture's base — known before the record is explained, so a
    notebook that only adds is not explained at all."""

    lecture: Lecture
    leads: bool


async def joining(
    session: AsyncSession,
    group_id: int | None,
    user_id: int,
    word: str,
    markdown: str,
    margin_notes: list,
    caption: str | None,
    missing_pages: int = 0,
) -> Joining | None:
    subject = await _subject(session, group_id, user_id, word, create=False)
    if subject is None:
        return None
    today = datetime.now(timezone.utc).date()
    lecture = await _lecture_of(
        session, subject.id, markdown, day_of(caption, margin_notes, today)
    )
    if lecture is None:
        return None
    base = base_of(await materials(session, lecture.id))
    leads = merge.completeness(markdown, missing_pages) > _completeness(base)
    return Joining(lecture, leads)


async def file(
    session: AsyncSession,
    note: Note,
    word: str,
    caption: str | None = None,
    lecture: Lecture | None = None,
) -> Filing:
    """File a record under `word`: into the chat's subject of that word, made
    if it is new, and into the lecture it is a notebook of, made if there is
    none — `lecture` when the caller has already found it (`joining`).
    Writes `Note.tag` with them."""
    user_id = note.user_id
    subject = await _subject(session, note.group_id, user_id, word, create=True)
    day = day_of(caption, note.margin_notes or [], _sent(note))
    if lecture is None:
        lecture = await _lecture_of(session, subject.id, note.markdown or "", day)
    joined = lecture is not None
    if lecture is None:
        lecture = Lecture(subject_id=subject.id, given_on=day.value, date_source=day.source)
        session.add(lecture)
        await session.flush()
    elif _SOURCES.index(day.source) > _SOURCES.index(lecture.date_source):
        lecture.given_on, lecture.date_source = day.value, day.source
    note.tag = word
    note.subject_id = subject.id
    note.lecture_id = lecture.id
    await session.flush()
    count = (
        await session.execute(
            select(func.count()).select_from(Note).where(Note.lecture_id == lecture.id)
        )
    ).scalar_one()
    return Filing(lecture=lecture, joined=joined, materials=count)


async def refile(
    session: AsyncSession, notes: list[Note], word: str, day: Day | None
) -> Filing:
    """The notebooks of a lecture moved from a private chat into a group
    (task 63), filed together: into the group's subject of their word, made
    if it is new, and into the lecture of it they are notebooks of, as a
    record is filed — else one made on `day`, the private lecture's, which
    keeps a day its caption gave. One lecture they were, and one they stay:
    a classmate's notebook joins them, never one of them another lecture.
    `notes` already carry the group."""
    first = notes[0]
    subject = await _subject(session, first.group_id, first.user_id, word, create=True)
    day = day or day_of(None, first.margin_notes or [], _sent(first))
    lecture = await _lecture_of(
        session, subject.id, [note.markdown or "" for note in notes], day
    )
    joined = lecture is not None
    if lecture is None:
        lecture = Lecture(subject_id=subject.id, given_on=day.value, date_source=day.source)
        session.add(lecture)
        await session.flush()
    elif _SOURCES.index(day.source) > _SOURCES.index(lecture.date_source):
        lecture.given_on, lecture.date_source = day.value, day.source
    for note in notes:
        note.tag = word
        note.subject_id = subject.id
        note.lecture_id = lecture.id
    await session.flush()
    count = (
        await session.execute(
            select(func.count()).select_from(Note).where(Note.lecture_id == lecture.id)
        )
    ).scalar_one()
    return Filing(lecture=lecture, joined=joined, materials=count)


# ── The page photographed twice (task 63) ──────────────────────────────────
# The CEO's of 2026-10-12, «удаление повторов»: a notebook's last page is
# photographed again as the first of its next album when the next lecture
# begins on it, and the record of that album opens on the end of the lecture
# before — which that lecture's record has. The repeat is cut by code, as
# the record is filed, before it is matched to a lecture, explained or
# studied, so that each of them reads what stays.

# How far back the album photographed before it may be: the lecture before,
# or one further when a practice came between.
_REPEAT_WITHIN = timedelta(days=21)
_REPEAT_CANDIDATES = 12
# What a box's anchor is when it names a formula by its number, "(3)".
_NUMBER_ANCHOR_RE = re.compile(r"\(?\s*(\d{1,3})\s*\)?")
_SQUASH_RE = re.compile(r"[\s$*]+")
_LEADING_RULE_RE = re.compile(r"\A(?:-{3,}|\*{3,}|_{3,}|~{3,})[ \t]*(?:\n|\Z)")


@dataclass
class Repeat:
    """A record's head that is the last page of an earlier notebook of its
    subject, photographed again: what stays, what went, the notebook it
    repeats and how many words it held."""

    markdown: str
    cut: str
    note_id: int
    words: int


def _squash(text: str) -> str:
    return _SQUASH_RE.sub("", text).lower()


def _opening(text: str) -> str:
    """What stays from its first words: the page seam the repeat ended on
    goes with it."""
    text = text.lstrip()
    found = _LEADING_RULE_RE.match(text)
    return text[found.end():].lstrip() if found else text


async def repeated(
    session: AsyncSession,
    group_id: int | None,
    user_id: int,
    word: str,
    markdown: str,
    margin_notes: list,
    caption: str | None,
    pages: int,
    sent: date | None = None,
) -> Repeat | None:
    """The head of a record filed under `word` that is the last page of an
    earlier notebook of that subject photographed again, and what stays
    without it.

    Cut only where it is sure (`docs/PLAN.md` → task 63) — a line of the
    lecture before kept is better than a line of this one lost: the earlier
    album sent on a day before this lecture's, and either this lecture's day
    written down, in the caption or the margin, or the page written on past
    the repeat in this album — the earlier photograph held nothing of this
    lecture then. The same page twice with nothing written between, and the
    day only the day the pages came, says neither: a page photographed after
    the next lecture began carries that lecture's first lines. Nothing here
    calls the model."""
    if not markdown:
        return None
    subject = await _subject(session, group_id, user_id, word, create=False)
    if subject is None:
        return None
    day = day_of(caption, margin_notes, sent or datetime.now(timezone.utc).date())
    stmt = (
        select(Note)
        .join(Lecture, Note.lecture_id == Lecture.id)
        .where(
            Lecture.subject_id == subject.id,
            Lecture.given_on < day.value,
            Lecture.given_on >= day.value - _REPEAT_WITHIN,
        )
        .order_by(Lecture.given_on.desc(), Note.id.desc())
        .limit(_REPEAT_CANDIDATES)
    )
    earlier = [
        (note.id, note.markdown or "")
        for note in (await session.execute(stmt)).scalars().all()
        if _sent(note) < day.value
    ]

    def compared() -> list[tuple[int, merge.Head | None]]:
        return [(note_id, merge.repeated_head(text, markdown, pages)) for note_id, text in earlier]

    best: tuple[merge.Head, int] | None = None
    # Word by word over a page or two each, off the event loop.
    for note_id, head in await asyncio.to_thread(compared):
        if head is None or (not head.strict and day.source == "sent"):
            continue
        if best is None or head.end > best[0].end:
            best = (head, note_id)
    if best is None:
        return None
    head, note_id = best
    return Repeat(
        markdown=_opening(markdown[head.end:]),
        cut=markdown[: head.end],
        note_id=note_id,
        words=head.words,
    )


def cut_only(anchor: str, repeat: Repeat) -> bool:
    """Whether a box's or a finding's anchor stands only in what went: it is
    the lecture before's, which its own record prints. A formula's number is
    not text: trim moves it with the formulas that went."""
    wanted = _squash(anchor)
    return (
        len(wanted) >= 3
        and not _NUMBER_ANCHOR_RE.fullmatch(anchor.strip())
        and wanted in _squash(repeat.cut)
        and wanted not in _squash(repeat.markdown)
    )


def retitled(title: str, repeat: Repeat) -> str:
    """The record's title once its head is cut: when it was read off what
    went and stands nowhere in what stays, it was the lecture before's, and
    the first heading of what stays names this one — as task 64 takes it."""
    wanted = _squash(title)
    if not wanted or wanted not in _squash(repeat.cut) or wanted in _squash(repeat.markdown):
        return title
    for line in repeat.markdown.split("\n"):
        heading = line.lstrip("#").strip() if line.startswith("#") else ""
        if heading:
            return heading[:60]
    return title


async def trim(session: AsyncSession, note: Note, word: str) -> Repeat | None:
    """A record filed after it was made — the answer to the question under
    it — loses a repeated head as one filed as it is made does, and with it
    what stood only there: its title read off it, the findings and the
    bot's boxes anchored in it. The formulas it numbered go too, so a box
    pointing at a formula by its number points at the same one after; the
    topics are read again, and the study version is built again from what
    stays."""
    repeat = await repeated(
        session,
        note.group_id,
        note.user_id,
        word,
        note.markdown or "",
        note.margin_notes or [],
        None,
        (note.page_count or 1) + len(note.missing_pages or []),
        _sent(note),
    )
    if repeat is None:
        return None
    gone = pdf.numbered_formulas(repeat.cut)
    boxes = []
    for box in note.explanations or []:
        anchor = str(box.get("anchor", ""))
        number = _NUMBER_ANCHOR_RE.fullmatch(anchor.strip())
        if number and gone:
            if int(number.group(1)) <= gone:
                continue
            box = {**box, "anchor": f"({int(number.group(1)) - gone})"}
        elif cut_only(anchor, repeat):
            continue
        boxes.append(box)
    note.explanations = boxes
    note.issues = [
        issue for issue in note.issues or [] if not cut_only(str(issue.get("anchor", "")), repeat)
    ]
    note.title = retitled(note.title, repeat)
    note.markdown = repeat.markdown
    note.study = None
    await session.execute(delete(NoteTopic).where(NoteTopic.note_id == note.id))
    session.add_all(
        NoteTopic(note_id=note.id, topic=topic)
        for topic in tags.topics_of(note.title, note.markdown)
    )
    await session.flush()
    return repeat
