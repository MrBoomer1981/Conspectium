"""The corpus: tagging a record, finding one again, and delivering it.

Its own Router, and `main.py` includes it **before** `handlers.router`:
handlers ends with a filterless catch-all that matches every message, so a
router registered after it would never receive a message beginning with "#".

Nothing here calls the model — the corpus is already text. Every query is
scoped to its owner (`_owned`): in a group chat the group, whose records any
member reaches, and in a private chat the user, whose own records made there
nobody else does. A record belongs to the chat it was made in — its
photographer finds a group's record in the group, like everyone else.

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
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import middlewares, tags, texts
from app.core.events import log_event
from app.db.models import Group, Note, NoteFigure, NoteTopic, User
from app.services import explain, graphcheck, pdf, vision

logger = logging.getLogger(__name__)

router = Router()


def _callouts(note: Note) -> list[pdf.Callout]:
    """The box above the record: the pages it is missing, if any.

    A hole is about the record rather than about its text: the marker stands
    where the page would have been, and this says so on the first page, where
    a reader decides whether they are holding the whole lecture. It used to
    stand among boxes about how the page was read — numbers the runs read
    differently, pages no second reading confirmed, a general "нужна
    проверка". None of those is printed any more: the author's decision,
    2026-09-25. The group studies from the document, and talk about the
    recognition is noise to it; the columns stay for the measurements.
    """
    if not note.missing_pages:
        return []
    return [
        pdf.Callout(
            texts.CALLOUT_MISSING,
            [texts.page_missing_marker(page) for page in note.missing_pages],
            "warning",
        )
    ]


# What graphcheck checks — a matrix against its graph — which is not a
# calculation, and whose box says so.
_GRAPH_KINDS = ("matrix", "incidence")
# mathcheck's detail for a chain: "<link> = <value>   ⟶   <link> = <value>
# (отличие в N раз)". Each side of the arrow is a formula; the bracket is not.
_ARROW = "⟶"
_TRAILING_BRACKET_RE = re.compile(r"\s*(\([^()]*\))\s*$")


def _remarks(note: Note) -> list[pdf.Remark]:
    """What the checks by code found wrong in the record — an equality that
    does not hold, a constant written wrong, a matrix its graph contradicts —
    each set under the text it is about.

    Only errors in the work: never how a page was read. A spot that reads two
    ways was a remark here, labelled with what stood in the manuscript; the
    author ruled it out on 2026-09-25 together with the boxes about the
    reading, and so graphcheck's cell that could not be read is not printed
    either. These used to be one box at the top, "Проверка вычислений", which
    said what was wrong and not where.

    `anchor` is stored with the finding when the page is checked. A record
    made before that (2026-09-25) has none, so the same checks run again over
    its stored text: that gives each finding its text back, and drops what
    they no longer find — record 45's congruence, read as a chain before task
    42. A stored shape this version cannot read is skipped rather than
    allowed to sink the record.
    """
    issues = note.issues or []
    if any(isinstance(issue, dict) and "anchor" not in issue for issue in issues):
        issues = [asdict(found) for found in vision.findings(note.markdown or "")]
    boxes: list[pdf.Remark] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        message = str(issue.get("message") or "").strip()
        if not message or message == graphcheck.UNREAD_CELLS:
            continue
        kind = str(issue.get("kind") or "")
        boxes.append(
            pdf.Remark(
                anchor=str(issue.get("anchor") or ""),
                label=(
                    texts.GRAPH_FINDING_LABEL
                    if kind in _GRAPH_KINDS
                    else texts.FINDING_LABEL
                ),
                lines=texts.finding_lines(
                    message,
                    _drawn(str(issue.get("detail") or "")),
                    str(issue.get("suggestion") or ""),
                ),
                tone="warning" if issue.get("severity") == "critical" else "info",
            )
        )
    return boxes


def _drawn(detail: str) -> str:
    """A finding's detail with its formulas marked to be drawn. mathcheck
    quotes the links of a chain as the page wrote them, which inside a
    formula is LaTeX with no dollars round it — "\\frac{1}{2}" printed as its
    own source. Each side of the arrow is marked as a formula; the bracket
    after it is prose and stays as it is."""
    tail = _TRAILING_BRACKET_RE.search(detail)
    body = detail[: tail.start()] if tail else detail
    sides = [pdf.as_formula(" ".join(side.split())) for side in body.split(_ARROW)]
    drawn = f" {_ARROW} ".join(sides)
    return f"{drawn} {tail.group(1)}" if tail else drawn


def _explanations(note: Note) -> list[pdf.Explanation]:
    """What the explaining stage added, as boxes to set in the document.

    Each keeps the sources it was stored with but a forum's, which is no
    source (explain.not_a_source) — so a record stored before that rule is
    drawn by it too, and one whose every source was a forum is not printed,
    as it would not be made today. A stored shape this version cannot read
    is skipped rather than allowed to sink the document.
    """
    boxes: list[pdf.Explanation] = []
    for item in note.explanations or []:
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            continue
        stored = [
            (str(s.get("title", "")) or str(s.get("uri", "")), str(s.get("uri", "")))
            for s in item.get("sources") or []
            if isinstance(s, dict) and s.get("uri")
        ]
        sources = [s for s in stored if not explain.not_a_source(s[0])]
        if stored and not sources:
            continue
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


def _owned(user: User, group: Group | None):
    """The records a chat may reach: in a group, the group's; in a private
    chat, the user's own that belong to no group."""
    if group is not None:
        return Note.group_id == group.id
    return and_(Note.user_id == user.id, Note.group_id.is_(None))


def _group_id(group: Group | None) -> int | None:
    return group.id if group is not None else None


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
async def cmd_stats(
    message: Message, session: AsyncSession, user: User, group: Group | None = None
) -> None:
    totals = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Note.page_count), 0),
                func.min(Note.created_at),
                func.max(Note.created_at),
            ).where(_owned(user, group))
        )
    ).one()
    notes, pages, first, last = totals
    if not notes:
        await message.answer(texts.STATS_EMPTY)
        return

    stamps = (
        (await session.execute(select(Note.created_at).where(_owned(user, group))))
        .scalars()
        .all()
    )
    today = datetime.now(timezone.utc).date()
    days = {_utc_date(stamp) for stamp in stamps}

    await log_event(session, user.id, "stats_viewed", group_id=_group_id(group))
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
async def cmd_help(
    message: Message, session: AsyncSession, user: User, group: Group | None = None
) -> None:
    await log_event(session, user.id, "help_viewed", group_id=_group_id(group))
    await message.answer(texts.GROUP_HELP if group is not None else texts.HELP)


# ── Delivering a record as a file ────────────────────────────────────────────
# Lives here rather than in handlers.py because showing a saved record is this
# module's job; the capture handlers import it after saving one.

_FILENAME_KEEP = re.compile(r"[^\w\s-]", re.UNICODE)
_FILENAME_GAPS = re.compile(r"[\s_]+")


def pdf_filename(note_id: int, title: str) -> str:
    """A file name a phone will not choke on, still recognisable in a
    downloads folder, and carrying the record number. A formula in the title
    is written out in characters first: stripped of its markup as it stood,
    "$2^{1001}$" became "21001"."""
    safe = _FILENAME_KEEP.sub("", pdf.plain(title)).strip()
    safe = _FILENAME_GAPS.sub("-", safe)[:40]
    safe = safe.strip("-")
    return f"{note_id}-{safe}.pdf" if safe else f"zapis-{note_id}.pdf"


async def _bot_username(message: Message) -> str:
    """The bot's own name, for the signature at the foot of every page and the
    QR code that opens it. Asked of the bot itself rather than written down,
    so a document always names the bot that sent it; aiogram keeps the answer
    after the first time. A document without it is still a document."""
    bot = getattr(message, "bot", None)
    if bot is None:
        return ""
    try:
        return (await bot.me()).username or ""
    except Exception:
        logger.warning("could not read the bot's name for the signature", exc_info=True)
        return ""


def _page(note: Note, bot_username: str) -> pdf.Page:
    """What every page of the record carries besides it: its subject and day
    at the head, the invitation and the bot's name at the foot."""
    return pdf.Page(
        subject=texts.pdf_subject(note.tag),
        date=texts.pdf_date(note.created_at),
        page_word=texts.PDF_PAGE_WORD,
        invite=texts.PDF_INVITE,
        bot_username=bot_username,
    )


async def figures_of(session: AsyncSession, note_id: int) -> dict[int, bytes]:
    """The drawings a record keeps, by the N of "[рисунок N: …]" — read for
    every document, so the record a "#word" brings back is drawn as whole as
    the one that was just made."""
    rows = await session.execute(
        select(NoteFigure.number, NoteFigure.png).where(NoteFigure.note_id == note_id)
    )
    return {number: png for number, png in rows}


async def send_record_pdf(message: Message, session: AsyncSession, note: Note) -> bool:
    """Send one record as a PDF. Returns False if it could not be built, so the
    caller can fall back to plain text — a record is never worth losing over
    its presentation."""
    page = _page(note, await _bot_username(message))
    drawings = await figures_of(session, note.id)
    try:
        # Drawing formulas is CPU-bound; the webhook must not stall on it.
        data = await asyncio.to_thread(
            pdf.render,
            note.title,
            note.markdown,
            callouts=_callouts(note),
            byline=texts.byline(note.margin_notes),
            remarks=_remarks(note),
            explanations=_explanations(note),
            summary=_summary(note),
            page=page,
            figures=drawings,
        )
    except Exception:
        logger.exception("could not build a PDF for note %s", note.id)
        return False

    await message.answer_document(
        BufferedInputFile(data, filename=pdf_filename(note.id, note.title)),
        caption=texts.record_caption(note.id, note.page_count),
    )
    return True


async def send_record(message: Message, session: AsyncSession, note: Note) -> None:
    """A saved record delivered to the user: the PDF when it can be built, the
    plain text when it cannot."""
    if await send_record_pdf(message, session, note):
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
#
# A private chat only. In a group the newest record is everyone's and the next
# "#word" may be anyone's, so a group never asks: a record is made there only
# when its photo came with its subject, and a "#word" in a group only searches.

_SEARCH_LIMIT = 10


async def known_tags(
    session: AsyncSession, user: User, group: Group | None = None
) -> list[str]:
    """The subjects this chat has filed under before, most used first.

    The question comes with its own answers because the alternative is a
    corpus that quietly grows «физика», «Физика» and «физос» as three
    different subjects and can never be searched again.
    """
    stmt = (
        select(Note.tag)
        .where(_owned(user, group), Note.tag.is_not(None))
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
    """The newest record of the user's private chat — the only place the bot
    asks a question for a "#word" to answer."""
    stmt = (
        select(Note)
        .where(_owned(user, None))
        # id breaks the tie: two records can share a second.
        .order_by(Note.created_at.desc(), Note.id.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


async def _matching(
    session: AsyncSession, user: User, group: Group | None, tag: str
) -> list[Note]:
    """This chat's records carrying the tag as their subject or among their
    topics."""
    by_topic = select(NoteTopic.note_id).where(NoteTopic.topic == tag)
    stmt = (
        select(Note)
        .where(
            _owned(user, group),
            or_(Note.tag == tag, Note.id.in_(by_topic)),
        )
        .order_by(Note.created_at.desc(), Note.id.desc())
        .limit(_SEARCH_LIMIT)
    )
    return list((await session.execute(stmt)).scalars().all())


def source_key(message: Message) -> str:
    """What a record in a group chat is made of: an album by its media group,
    a single page by its message. The same pages always give the same key,
    whether they came with their subject or were called on later."""
    if message.media_group_id:
        return f"album:{message.media_group_id}"
    return f"msg:{message.message_id}"


async def recorded(session: AsyncSession, group: Group, key: str) -> Note | None:
    """The chat's record already made of these pages, if there is one — so a
    second call on them sends it rather than paying to read them again."""
    stmt = (
        select(Note)
        .where(Note.group_id == group.id, Note.source_key == key)
        .order_by(Note.id.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


def _not_a_summon(message: Message) -> bool:
    # A "#word" under a page somebody sent calls the bot on that page; it is
    # handled in handlers.handle_summon and is never a search.
    return not middlewares.is_summon(message)


@router.message(F.text.startswith("#"), _not_a_summon)
async def on_tag(
    message: Message, session: AsyncSession, user: User, group: Group | None = None
) -> None:
    tag = tags.parse(message.text)
    if tag is None:
        if group is None:
            await message.answer(texts.TAG_UNREADABLE)
        return

    if group is None:
        newest = await _newest(session, user)
        if newest is not None and newest.tag is None:
            newest.tag = tag
            await log_event(
                session, user.id, "note_tagged", {"note_id": newest.id, "tag": tag}
            )
            await message.answer(texts.tagged(tag))
            return

    found = await _matching(session, user, group, tag)
    await log_event(
        session,
        user.id,
        "topic_searched",
        {"tag": tag, "found": len(found)},
        group_id=_group_id(group),
    )
    if not found:
        # In a group a "#word" that finds nothing is most likely a hashtag the
        # members use among themselves — "#дз" — and an answer to each one
        # would be the bot talking over the chat. The miss is still logged.
        if group is None:
            await message.answer(
                texts.nothing_tagged(tag, await known_tags(session, user))
            )
        return
    if len(found) == 1:
        # One match is the answer itself, not a line about the answer.
        await send_record(message, session, found[0])
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
    # The title as characters: a chat message cannot draw "$2^{1001}$".
    return [(pdf.plain(n.title), by_note.get(n.id, [])) for n in notes]


async def ask_for_tag(
    message: Message,
    session: AsyncSession,
    user: User,
    note: Note,
    group: Group | None = None,
) -> None:
    """Store the record's topics and ask which subject it belongs to — unless
    the photo came with it, and then say where it was filed.

    The last thing every capture path does, so the question is what the user
    is looking at when they reply — and so a "#word" arriving next means the
    answer rather than a search. A record made in a group always came with its
    subject; the question is a private chat's.
    """
    topics = await save_topics(session, note)
    if note.tag is not None:
        await message.answer(texts.filed(note.tag, topics))
        return
    await message.answer(
        texts.ask_tag(topics, await known_tags(session, user, group))
    )
