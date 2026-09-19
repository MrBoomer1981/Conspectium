"""Commands that read and change records already in the corpus.

Its own Router, and `main.py` includes it **before** `handlers.router`:
handlers ends with a filterless catch-all that matches every message, so a
router registered after it would never receive a command.

Nothing here calls the model — the corpus is already text. Every query
filters by `user_id`: one user today is not a reason to write a query that
returns someone else's record tomorrow.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.events import log_event
from app.db.models import Note, User
from app.services import mathcheck

logger = logging.getLogger(__name__)

router = Router()

_PAGE_SIZE = 10

# mathcheck.Issue's own fields. Stored issues carry an extra `page` for album
# records, and rows written by an older version may not match today's
# dataclass at all — so the dict is filtered down rather than splatted.
_ISSUE_FIELDS = ("kind", "severity", "message", "detail", "suggestion")


def _page_number(args: str | None) -> int:
    """`/notes 2` -> 2. Anything unparseable is page 1: a typo should show the
    first page, not an error."""
    if not args:
        return 1
    try:
        return max(1, int(args.strip().split()[0]))
    except (ValueError, IndexError):
        return 1


def _note_id(args: str | None) -> int | None:
    if not args:
        return None
    try:
        return int(args.strip().split()[0].lstrip("#"))
    except (ValueError, IndexError):
        return None


async def _load(session: AsyncSession, user: User, note_id: int) -> Note | None:
    """One record of this user, or None. A record belonging to someone else is
    indistinguishable from one that doesn't exist — there is nothing to gain
    from confirming it is out there."""
    stmt = select(Note).where(Note.id == note_id, Note.user_id == user.id)
    return (await session.execute(stmt)).scalar_one_or_none()


def _flags(note: Note) -> str | None:
    """The same four flag blocks the capture path sends after a record, rebuilt
    from what was stored. The rendering itself is reused — mathcheck's own
    render() and the texts helpers — only the assembly from JSONB is new."""
    blocks: list[str] = []
    if note.status == "needs_review":
        blocks.append(texts.NEEDS_REVIEW)

    if note.issues:
        try:
            report = mathcheck.Report(
                issues=[
                    mathcheck.Issue(
                        **{k: v for k, v in issue.items() if k in _ISSUE_FIELDS}
                    )
                    for issue in note.issues
                ]
            )
            blocks.append(report.render())
        except (TypeError, AttributeError):
            # A stored shape this version cannot read is not a reason to fail
            # the whole record: the text itself is what the user asked for.
            logger.warning("note %d: unreadable issues payload", note.id)

    if note.numeric_divergences:
        lines = [texts.DIVERGENCES_HEADER]
        lines += [
            texts.divergence_line(
                d.get("context", ""), d.get("variants", {}), page=d.get("page")
            )
            for d in note.numeric_divergences
            if isinstance(d, dict)
        ]
        blocks.append("\n".join(lines))

    if note.uncertain:
        lines = [texts.UNCERTAIN_HEADER]
        lines += [
            texts.uncertain_line(u.get("text", ""), u.get("why", ""), page=u.get("page"))
            for u in note.uncertain
            if isinstance(u, dict)
        ]
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks) if blocks else None


@router.message(Command("notes"))
async def cmd_notes(
    message: Message, command: CommandObject, session: AsyncSession, user: User
) -> None:
    page = _page_number(command.args)

    total = (
        await session.execute(
            select(func.count()).select_from(Note).where(Note.user_id == user.id)
        )
    ).scalar_one()
    if total == 0:
        await message.answer(texts.CORPUS_EMPTY)
        return

    stmt = (
        select(Note)
        .where(Note.user_id == user.id)
        # id breaks the tie: several records can share a second.
        .order_by(Note.created_at.desc(), Note.id.desc())
        .offset((page - 1) * _PAGE_SIZE)
        .limit(_PAGE_SIZE)
    )
    notes = (await session.execute(stmt)).scalars().all()

    await log_event(session, user.id, "corpus_listed", {"page": page, "shown": len(notes)})

    if not notes:
        await message.answer(texts.NOTES_PAGE_EMPTY)
        return

    lines = [
        texts.note_line(
            n.id,
            n.created_at,
            n.title,
            n.subject,
            n.page_count,
            n.status == "needs_review",
        )
        for n in notes
    ]
    footer = texts.notes_footer(total, page, _PAGE_SIZE)
    if footer:
        lines += ["", footer]
    for chunk in texts.split_message("\n".join(lines)):
        await message.answer(chunk)


@router.message(Command("note"))
async def cmd_note(
    message: Message, command: CommandObject, session: AsyncSession, user: User
) -> None:
    note_id = _note_id(command.args)
    if note_id is None:
        await message.answer(texts.NOTE_USAGE)
        return

    note = await _load(session, user, note_id)
    if note is None:
        await message.answer(texts.NOTE_NOT_FOUND)
        return

    await log_event(session, user.id, "note_opened", {"note_id": note.id})

    for chunk in texts.split_message(f"{note.title}\n\n{note.markdown}"):
        await message.answer(chunk)
    flags = _flags(note)
    if flags:
        await message.answer(flags)


# The text search configuration, inlined rather than bound. asyncpg cannot
# infer regconfig for a placeholder, so `to_tsvector($1, $2)` fails at run time
# where `to_tsvector('russian', $1)` works.
_RU = literal_column("'russian'")


def _search_stmt(user_id: int, query: str):
    """Full text over title and body, ranked. Built separately from the handler
    so its shape can be checked without a PostgreSQL to run it against.

    Why not ILIKE: Russian morphology. `ILIKE '%производная%'` does not match
    «производной», and a search that misses the declined form of the word you
    just typed is not a search. to_tsvector stems both sides.

    Why no index: a GIN index needs a generated column and a migration, and a
    sequential scan over one student's corpus is instant. Add it when the
    corpus makes it necessary.
    """
    vector = func.to_tsvector(_RU, Note.title + " " + Note.markdown)
    tsquery = func.plainto_tsquery(_RU, query)
    return (
        select(Note)
        .where(Note.user_id == user_id, vector.op("@@")(tsquery))
        .order_by(func.ts_rank(vector, tsquery).desc(), Note.created_at.desc())
        .limit(_PAGE_SIZE)
    )


@router.message(Command("search"))
async def cmd_search(
    message: Message, command: CommandObject, session: AsyncSession, user: User
) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer(texts.SEARCH_USAGE)
        return

    notes = (await session.execute(_search_stmt(user.id, query))).scalars().all()

    # The query text is stored: with one user there is no privacy cost, and
    # what you search for is the most direct signal of what the corpus is for.
    await log_event(
        session, user.id, "corpus_searched", {"query": query, "found": len(notes)}
    )

    if not notes:
        await message.answer(texts.search_empty(query))
        return

    lines = [
        texts.note_line(
            n.id,
            n.created_at,
            n.title,
            n.subject,
            n.page_count,
            n.status == "needs_review",
        )
        for n in notes
    ]
    for chunk in texts.split_message("\n".join(lines)):
        await message.answer(chunk)


# Titles are capped the same way everywhere: vision.py derives them at 60
# characters, and a hand-written one has no reason to be longer.
_TITLE_LIMIT = 60


def _id_and_rest(args: str | None) -> tuple[int | None, str]:
    """`42 Новый заголовок` -> (42, "Новый заголовок")."""
    if not args:
        return None, ""
    head, _, rest = args.strip().partition(" ")
    try:
        return int(head.lstrip("#")), rest.strip()
    except ValueError:
        return None, ""


@router.message(Command("retitle"))
async def cmd_retitle(
    message: Message, command: CommandObject, session: AsyncSession, user: User
) -> None:
    note_id, new_title = _id_and_rest(command.args)
    if note_id is None or not new_title:
        await message.answer(texts.RETITLE_USAGE)
        return

    note = await _load(session, user, note_id)
    if note is None:
        await message.answer(texts.NOTE_NOT_FOUND)
        return

    note.title = new_title[:_TITLE_LIMIT]
    await log_event(session, user.id, "note_retitled", {"note_id": note.id})
    await message.answer(texts.retitled(note.title))


@router.message(Command("delete"))
async def cmd_delete(
    message: Message, command: CommandObject, session: AsyncSession, user: User
) -> None:
    note_id = _note_id(command.args)
    if note_id is None:
        await message.answer(texts.DELETE_USAGE)
        return

    note = await _load(session, user, note_id)
    if note is None:
        await message.answer(texts.NOTE_NOT_FOUND)
        return

    # Read the fields out before the row goes: the event is all that will be
    # left describing what was deleted.
    title, page_count = note.title, note.page_count

    await session.delete(note)
    await session.flush()  # the delete lands before the event's SAVEPOINT
    await log_event(
        session,
        user.id,
        "note_deleted",
        {"note_id": note_id, "title": title, "page_count": page_count},
    )
    # No confirmation step: it needs either inline buttons or a second
    # command, and for one user re-photographing a page costs less than that.
    await message.answer(texts.deleted(title))
