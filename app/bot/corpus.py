"""The corpus: tagging a record, finding one again, and delivering it.

Its own Router, and `main.py` includes it **before** `handlers.router`:
handlers ends with a filterless catch-all that matches every message, so a
router registered after it would never receive a message beginning with "#".

Nothing here calls the model — the corpus is already text. Every query
filters by `user_id`: one user today is not a reason to write a query that
returns someone else's record tomorrow.

This module used to carry seven commands for browsing, opening, searching,
renaming and deleting records. They were built, tested, deployed, and in the
event table not one of them was ever used. What replaced them is one gesture:
the bot asks which subject a record belongs to, and a "#word" either answers
that question or looks for it.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import tags, texts
from app.core.events import log_event
from app.db.models import Note, NoteTopic, User
from app.services import mathcheck, pdf

logger = logging.getLogger(__name__)

router = Router()

# mathcheck.Issue's own fields. Stored issues carry an extra `page` for album
# records, and rows written by an older version may not match today's
# dataclass at all — so the dict is filtered down rather than splatted.
_ISSUE_FIELDS = ("kind", "severity", "message", "detail", "suggestion")


def _stored_report(note: Note) -> mathcheck.Report | None:
    """mathcheck's own Report, rebuilt from JSONB, or None when there is
    nothing stored — or when the stored shape is one this version cannot read.
    A record is not worth failing over its flags: the text is what was asked
    for."""
    if not note.issues:
        return None
    try:
        return mathcheck.Report(
            issues=[
                mathcheck.Issue(**{k: v for k, v in issue.items() if k in _ISSUE_FIELDS})
                for issue in note.issues
            ]
        )
    except (TypeError, AttributeError):
        logger.warning("note %d: unreadable issues payload", note.id)
        return None


def _divergence_lines(note: Note) -> list[str]:
    return [
        texts.divergence_line(
            d.get("context", ""), d.get("variants", {}), page=d.get("page")
        )
        for d in note.numeric_divergences
        if isinstance(d, dict)
    ]


def _uncertain_lines(note: Note) -> list[str]:
    return [
        texts.uncertain_line(u.get("text", ""), u.get("why", ""), page=u.get("page"))
        for u in note.uncertain
        if isinstance(u, dict)
    ]


def _callouts(note: Note) -> list[pdf.Callout]:
    """The same flags as boxes on the first page of the document.

    Built from the same three readers as `_flags`, so the message and the
    document cannot come to disagree about what a record is flagged for. What
    differs is only the presentation: a box has a short title of its own, and
    the severity of an arithmetic issue is carried by the colour rather than
    by a marker the document's font cannot draw.
    """
    boxes: list[pdf.Callout] = []

    report = _stored_report(note)
    if report is not None and report.issues:
        boxes.append(
            pdf.Callout(
                texts.CALLOUT_MATH,
                [
                    texts.issue_line(i.message, i.detail, i.suggestion)
                    for i in report.issues
                ],
                "warning"
                if any(i.severity == "critical" for i in report.issues)
                else "info",
            )
        )

    divergences = _divergence_lines(note)
    if divergences:
        boxes.append(pdf.Callout(texts.CALLOUT_DIVERGENCES, divergences))

    if note.unverified_pages:
        boxes.append(
            pdf.Callout(
                texts.CALLOUT_UNVERIFIED,
                [
                    texts.unverified_line(u["page"], u["reason"])
                    for u in note.unverified_pages
                ],
                "warning",
            )
        )

    # First of the boxes by importance, last to be appended only because the
    # order here is the order they were built in. A hole is the one flag that
    # is about the record rather than about its text: the marker stands where
    # the page would have been, and this says so on the first page, where a
    # reader decides whether they are holding the whole lecture.
    if note.missing_pages:
        boxes.insert(
            0,
            pdf.Callout(
                texts.CALLOUT_MISSING,
                [texts.page_missing_marker(page) for page in note.missing_pages],
                "warning",
            ),
        )

    # Same rule as the message: the generic box only when nothing more exact
    # is there to fill it. The subtitle already carries "нужна проверка".
    if note.status == "needs_review" and not boxes:
        boxes.append(
            pdf.Callout(texts.CALLOUT_REVIEW, [texts.NEEDS_REVIEW], "warning")
        )

    return boxes


def _remarks(note: Note) -> list[pdf.Remark]:
    """The spots that read two ways, as remarks to be set beside them.

    These used to be a box at the top of the document, which said what was
    doubtful without saying where. `uncertain.text` is what the model read, so
    it is also the anchor: whichever line of the record contains it gets the
    remark. One that anchors nowhere is not lost — `pdf.render` puts it at the
    end.

    What was read, why it is doubtful and what else it might be are quoted as
    the page was transcribed — inside a formula that is LaTeX with no dollars
    round it — so their LaTeX is marked to be drawn. The anchor stays the raw
    text: it has to be found in the record exactly as it stands there.
    """
    return [
        pdf.Remark(
            anchor=str(u.get("text", "")),
            label=texts.remark_label(u.get("page")),
            lines=texts.uncertain_remark(
                pdf.as_formula(str(u.get("text", ""))),
                pdf.as_formula(str(u.get("why", ""))),
                [pdf.as_formula(str(a)) for a in u.get("alternatives") or []],
            ),
        )
        for u in note.uncertain
        if isinstance(u, dict)
    ]


def _explanations(note: Note) -> list[pdf.Explanation]:
    """What the explaining stage added, as boxes to set in the document.

    Each keeps the sources it was stored with; a stored shape this version
    cannot read is skipped rather than allowed to sink the document.
    """
    boxes: list[pdf.Explanation] = []
    for item in note.explanations or []:
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            continue
        sources = [
            (str(s.get("title", "")) or str(s.get("uri", "")), str(s.get("uri", "")))
            for s in item.get("sources") or []
            if isinstance(s, dict) and s.get("uri")
        ]
        boxes.append(
            pdf.Explanation(
                anchor=str(item.get("anchor", "")),
                label=texts.EXPLANATION_LABEL,
                lines=[
                    texts.explanation_line(
                        str(item.get("title", "")), str(item.get("text", ""))
                    )
                ],
                sources=sources,
                sources_label=texts.SOURCES_LABEL,
            )
        )
    return boxes


def _summary(note: Note) -> pdf.Summary | None:
    if not note.summary:
        return None
    return pdf.Summary(label=texts.SUMMARY_LABEL, lines=[note.summary])


def _utc_date(value: datetime) -> date:
    """SQLite hands back naive datetimes, PostgreSQL aware ones. Both are UTC
    by construction — every timestamp in this project is server_default now()."""
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(timezone.utc).date()


def _streak(days: set[date], today: date) -> int:
    """Consecutive days of capture, counting back from today — or from
    yesterday when nothing has arrived yet today. A streak that reads zero
    every morning until you post would be noise, not a signal; it breaks only
    when a whole day passes with nothing."""
    anchor = today if today in days else today - timedelta(days=1)
    count = 0
    while anchor in days:
        count += 1
        anchor -= timedelta(days=1)
    return count


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, user: User) -> None:
    totals = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Note.page_count), 0),
                func.min(Note.created_at),
                func.max(Note.created_at),
            ).where(Note.user_id == user.id)
        )
    ).one()
    notes, pages, first, last = totals
    if not notes:
        await message.answer(texts.STATS_EMPTY)
        return

    stamps = (
        (await session.execute(select(Note.created_at).where(Note.user_id == user.id)))
        .scalars()
        .all()
    )
    today = datetime.now(timezone.utc).date()
    days = {_utc_date(stamp) for stamp in stamps}

    await log_event(session, user.id, "stats_viewed")
    await message.answer(
        texts.stats(
            notes=notes,
            pages=pages,
            first=_utc_date(first),
            last=_utc_date(last),
            streak=_streak(days, today),
            today=today,
        )
    )


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession, user: User) -> None:
    await log_event(session, user.id, "help_viewed")
    await message.answer(texts.HELP)


# ── Delivering a record as a file ────────────────────────────────────────────
# Lives here rather than in handlers.py because showing a saved record is this
# module's job; the capture handlers import it after saving one.

_FILENAME_KEEP = re.compile(r"[^\w\s-]", re.UNICODE)
_FILENAME_GAPS = re.compile(r"[\s_]+")


def pdf_filename(note_id: int, title: str) -> str:
    """A file name a phone will not choke on, still recognisable in a
    downloads folder, and carrying the record number."""
    safe = _FILENAME_GAPS.sub("-", _FILENAME_KEEP.sub("", title).strip())[:40]
    safe = safe.strip("-")
    return f"{note_id}-{safe}.pdf" if safe else f"zapis-{note_id}.pdf"


async def send_record_pdf(message: Message, note: Note) -> bool:
    """Send one record as a PDF. Returns False if it could not be built, so the
    caller can fall back to plain text — a record is never worth losing over
    its presentation."""
    subtitle = texts.pdf_subtitle(
        note.created_at, note.page_count, note.status == "needs_review"
    )
    try:
        # Drawing formulas is CPU-bound; the webhook must not stall on it.
        data = await asyncio.to_thread(
            pdf.render,
            note.title,
            note.markdown,
            subtitle,
            _callouts(note),
            texts.byline(note.margin_notes),
            _remarks(note),
            _explanations(note),
            _summary(note),
        )
    except Exception:
        logger.exception("could not build a PDF for note %s", note.id)
        return False

    await message.answer_document(
        BufferedInputFile(data, filename=pdf_filename(note.id, note.title)),
        caption=texts.record_caption(note.id, note.page_count),
    )
    return True


async def send_record(message: Message, note: Note) -> None:
    """A saved record delivered to the user: the PDF when it can be built, the
    plain text when it cannot."""
    if await send_record_pdf(message, note):
        return
    await message.answer(texts.PDF_FAILED)
    for chunk in texts.split_message(f"{note.title}\n\n{note.markdown}"):
        await message.answer(chunk)


# ── Tags: the way a record is filed and the way it comes back ────────────────
# A message that is a single "#word" means one of two things, and the state of
# the corpus decides which rather than a state machine: if the newest record
# has no subject, the bot's question is still open and the word answers it;
# if it has one, nothing was asked and the word is a search.
#
# Stateless on purpose. Remembering "who is being asked" in the process is the
# shortcut that already costs this project an album buffer which cannot
# survive a second replica, and this one is avoidable for free — the answer is
# a column.

_SEARCH_LIMIT = 10


async def known_tags(session: AsyncSession, user: User) -> list[str]:
    """The subjects this user has filed under before, most used first.

    The question comes with its own answers because the alternative is a
    corpus that quietly grows «физика», «Физика» and «физос» as three
    different subjects and can never be searched again.
    """
    stmt = (
        select(Note.tag)
        .where(Note.user_id == user.id, Note.tag.is_not(None))
        .group_by(Note.tag)
        .order_by(func.count().desc(), Note.tag)
    )
    return list((await session.execute(stmt)).scalars().all())


async def save_topics(session: AsyncSession, note: Note) -> list[str]:
    """Store the topics read off a record's headings, and return them.

    Called where the record is created rather than where it is tagged, so a
    record is findable by its own topics even if the user never answers the
    question about its subject — which is the likeliest thing to happen to it.
    """
    topics = tags.topics_of(note.title, note.markdown)
    session.add_all([NoteTopic(note_id=note.id, topic=topic) for topic in topics])
    return topics


async def _newest(session: AsyncSession, user: User) -> Note | None:
    stmt = (
        select(Note)
        .where(Note.user_id == user.id)
        # id breaks the tie: two records can share a second.
        .order_by(Note.created_at.desc(), Note.id.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


async def _matching(session: AsyncSession, user: User, tag: str) -> list[Note]:
    """Records carrying this tag as their subject or among their topics."""
    by_topic = select(NoteTopic.note_id).where(NoteTopic.topic == tag)
    stmt = (
        select(Note)
        .where(
            Note.user_id == user.id,
            or_(Note.tag == tag, Note.id.in_(by_topic)),
        )
        .order_by(Note.created_at.desc(), Note.id.desc())
        .limit(_SEARCH_LIMIT)
    )
    return list((await session.execute(stmt)).scalars().all())


@router.message(F.text.startswith("#"))
async def on_tag(message: Message, session: AsyncSession, user: User) -> None:
    tag = tags.parse(message.text)
    if tag is None:
        await message.answer(texts.TAG_UNREADABLE)
        return

    newest = await _newest(session, user)
    if newest is not None and newest.tag is None:
        newest.tag = tag
        await log_event(
            session, user.id, "note_tagged", {"note_id": newest.id, "tag": tag}
        )
        await message.answer(texts.tagged(tag))
        return

    found = await _matching(session, user, tag)
    await log_event(
        session, user.id, "topic_searched", {"tag": tag, "found": len(found)}
    )
    if not found:
        await message.answer(
            texts.nothing_tagged(tag, await known_tags(session, user))
        )
        return
    if len(found) == 1:
        # One match is the answer itself, not a line about the answer.
        await send_record(message, found[0])
        return
    await message.answer(texts.several_tagged(tag, await _listing(session, found)))


async def _listing(
    session: AsyncSession, notes: list[Note]
) -> list[tuple[str, list[str]]]:
    """Each record with its own topics, so the list can be acted on: the next
    message is expected to be one of them."""
    rows = (
        await session.execute(
            select(NoteTopic.note_id, NoteTopic.topic)
            .where(NoteTopic.note_id.in_([n.id for n in notes]))
            .order_by(NoteTopic.id)
        )
    ).all()
    by_note: dict[int, list[str]] = {}
    for note_id, topic in rows:
        by_note.setdefault(note_id, []).append(topic)
    return [(n.title, by_note.get(n.id, [])) for n in notes]


async def ask_for_tag(
    message: Message, session: AsyncSession, user: User, note: Note
) -> None:
    """Store the record's topics and ask which subject it belongs to.

    The last thing every capture path does, so the question is what the user
    is looking at when they reply — and so a "#word" arriving next means the
    answer rather than a search.
    """
    topics = await save_topics(session, note)
    await message.answer(texts.ask_tag(topics, await known_tags(session, user)))
