"""«В группу «…»», a private lecture moved into a group (task 63, the CEO's
of 2026-10-12).

A lecture photographed in the private chat — an album, a notebook sent
whole — is the person's; under its document stands a button for each group
the person and the bot are both in, and a press makes the lecture that
group's: its notebooks go to the group's subject of the same "#word", where
a classmate's notebook of the lecture joins them by the rule a record is
filed by (subjects.refile), and the group is shown one line. Nothing is
read again and nothing is paid: the pages were read in the private chat,
and the group's day does not count them (`notes.moved_at`).

A lecture moved is the group's, not the private chat's: the person finds
it in the group, as everyone there does. Nothing here calls the model.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import feedback, rating, subjects, texts
from app.core.config import settings
from app.core.events import log_event
from app.db.models import Group, Lecture, Note, User
from app.services import merge, pdf

logger = logging.getLogger(__name__)

router = Router()

# One question to Telegram a group: whether the person is in it. Asked of
# every group at once, so a delivery waits for the slowest of them.
_ASK_TIMEOUT_S = 5
# What Telegram calls a member: anyone but one who left or was removed — a
# restricted member is one while `is_member` says so.
_MEMBERS = ("creator", "administrator", "member")


def _is_member(found: object) -> bool:
    status = getattr(found, "status", None)
    if status in _MEMBERS:
        return True
    return status == "restricted" and getattr(found, "is_member", False) is True


async def _member(bot: Bot, group: Group, tg_user_id: int) -> bool:
    """Whether the person is in the group now. False when Telegram cannot
    say — the bot was removed, the chat is gone, the question timed out:
    a button to a group nobody can confirm is a button to nowhere."""
    try:
        found = await bot.get_chat_member(
            group.tg_chat_id, tg_user_id, request_timeout=_ASK_TIMEOUT_S
        )
    except Exception:
        logger.info("membership in group %s could not be read", group.id, exc_info=True)
        return False
    return _is_member(found)


async def targets(message: Message, session: AsyncSession, note: Note) -> list[Group]:
    """The groups a record's document offers to move it into: under a
    private chat's document of a record with its subject, every group the
    bot is in that the person is a member of — Telegram asked about each at
    once; none for a group's record or one of no subject. The chat every
    «Плохо» goes to is no group of students (task 74).

    Every group the bot is in, rather than those the person was seen in: a
    member who never wrote to the bot there is a member all the same, and
    the bot drops what is not addressed to it unread ("Scale debt")."""
    chat = getattr(message, "chat", None)
    bot = getattr(message, "bot", None)
    if (
        bot is None
        or chat is None
        or chat.type != "private"
        or note.tag is None
        or note.group_id is not None
    ):
        return []
    groups = [
        group
        for group in (await session.execute(select(Group).order_by(Group.id))).scalars().all()
        if group.tg_chat_id != settings.FEEDBACK_CHAT_ID
    ]
    if not groups:
        return []
    asked = await asyncio.gather(*(_member(bot, group, chat.id) for group in groups))
    return [group for group, member in zip(groups, asked) if member]


async def markup(message: Message, session: AsyncSession, note: Note) -> InlineKeyboardMarkup | None:
    """The buttons alone, for the line that files a record after its
    document went out without them — its subject came with the answer."""
    rows = feedback.move_rows(note.id, await targets(message, session, note))
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


@dataclass
class Moved:
    """A private lecture made a group's: its notebooks, the group's lecture
    they are in now, whether the group had that lecture before, and — when
    it had — whether they lead it now or what they add to its document."""

    notes: list[Note]
    lecture: Lecture
    joined: bool
    leads: bool
    added: int


async def move(session: AsyncSession, user: User, note: Note, target: Group) -> Moved | None:
    """Move the private lecture a record is a notebook of into `target`:
    every notebook of it, filed again into the group's subject of its word.
    None when there is nothing left to move — the lecture is a group's
    already.

    The notebooks are claimed by one conditional update first: two presses
    at once — a double tap — move the lecture once, the second waiting for
    the first's commit and finding nothing to claim. The private lecture's
    row goes with its last notebook; its subject stays, the person's word."""
    lecture_id = note.lecture_id
    which = Note.lecture_id == lecture_id if lecture_id is not None else Note.id == note.id
    claimed = (
        await session.execute(
            update(Note)
            .where(which, Note.user_id == user.id, Note.group_id.is_(None))
            .values(group_id=target.id, moved_at=func.now())
            .returning(Note.id)
            .execution_options(synchronize_session=False)
        )
    ).scalars().all()
    if not claimed:
        return None
    notes = list(
        (
            await session.execute(
                select(Note)
                .where(Note.id.in_(claimed))
                .order_by(Note.id)
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
    )
    private = await session.get(Lecture, lecture_id) if lecture_id is not None else None
    day = subjects.Day(private.given_on, private.date_source) if private is not None else None
    filing = await subjects.refile(session, notes, note.tag, day)
    if private is not None:
        left = (
            await session.execute(
                select(func.count()).select_from(Note).where(Note.lecture_id == private.id)
            )
        ).scalar_one()
        if not left:
            await session.delete(private)
            await session.flush()

    leads, added = False, 0
    if filing.joined:
        everything = await subjects.materials(session, filing.lecture.id)
        base = subjects.base_of(everything)
        mine = {moved.id for moved in notes}
        if base.id in mine:
            leads = True
        else:
            others = [other for other in everything if other.id != base.id]
            merged = await asyncio.to_thread(
                merge.merged,
                base.markdown,
                [other.markdown for other in others],
                texts.INSERT_LABEL,
            )
            added = sum(
                len(passages)
                for other, passages in zip(others, merged.passages)
                if other.id in mine
            )
    return Moved(notes, filing.lecture, filing.joined, leads, added)


def _pressed(data: str | None) -> tuple[int, int] | None:
    """(74, 3) for "move:74:3", None for anything else."""
    parts = (data or "").split(":")
    if (
        len(parts) != 3
        or parts[0] != feedback.MOVE_PREFIX
        or not parts[1].isdigit()
        or not parts[2].isdigit()
    ):
        return None
    return int(parts[1]), int(parts[2])


async def _notice(callback: CallbackQuery, text: str | None = None) -> None:
    """The press answered, whether or not Telegram still takes the notice —
    a press answered late is refused, and the move stands (feedback.on_rate,
    task 103)."""
    try:
        await callback.answer(text)
    except Exception:
        logger.warning("the notice of a press was refused", exc_info=True)


async def _unbuttoned(message: Message) -> None:
    """The group buttons taken off the document the lecture was moved from:
    the lecture is not the private chat's to move any more. The rest stay."""
    current = getattr(message, "reply_markup", None)
    if current is None:
        return
    rows = [
        row
        for row in current.inline_keyboard
        if not any(
            (button.callback_data or "").startswith(f"{feedback.MOVE_PREFIX}:")
            for button in row
        )
    ]
    try:
        await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    except Exception:
        logger.info("the group buttons could not be taken off", exc_info=True)


@router.callback_query(F.data.startswith(f"{feedback.MOVE_PREFIX}:"))
async def on_move(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> None:
    pressed = _pressed(callback.data)
    message = callback.message
    note = await session.get(Note, pressed[0]) if pressed is not None else None
    target = await session.get(Group, pressed[1]) if pressed is not None else None
    if (
        note is None
        or target is None
        or message is None
        or group is not None
        or note.user_id != user.id
        or note.tag is None
    ):
        await _notice(callback)
        return
    if note.group_id is not None:
        await _notice(callback, texts.MOVE_ALREADY)
        await _unbuttoned(message)
        return
    # Asked again at the press: the button may be days old, and the person
    # may have left the group since, or the bot been removed from it.
    if not await _member(bot, target, callback.from_user.id):
        await _notice(callback, texts.MOVE_NOT_MEMBER)
        return

    from_lecture = note.lecture_id
    moved = await move(session, user, note, target)
    if moved is None:
        await _notice(callback, texts.MOVE_ALREADY)
        await _unbuttoned(message)
        return
    await log_event(
        session,
        user.id,
        "lecture_moved",
        {
            "note_ids": [moved_note.id for moved_note in moved.notes],
            "from_lecture": from_lecture,
            "lecture_id": moved.lecture.id,
            "lecture_joined": moved.joined,
            "leads": moved.leads,
            "added": moved.added,
            "pages": sum(moved_note.page_count or 0 for moved_note in moved.notes),
        },
        # The group gained a lecture: what this event is about is the group's
        # use of the bot, the question the project exists to answer.
        group_id=target.id,
    )
    # Committed before the group is told: a line that could not be sent
    # leaves the lecture moved, and a move that could not be kept tells
    # nobody anything (handlers._saved, task 104).
    await session.commit()
    await _notice(callback, texts.moved_notice(target.title, moved.notes[0].tag))
    await _unbuttoned(message)
    base = subjects.base_of(moved.notes)
    line = texts.moved_line(
        rating._name(user),
        base.tag,
        moved.lecture.given_on,
        pdf.plain(base.title),
        moved.joined,
        moved.leads,
        moved.added,
    )
    try:
        await bot.send_message(target.tg_chat_id, line)
    except Exception:
        logger.warning(
            "the line about a lecture moved into group %s could not be sent",
            target.id,
            exc_info=True,
        )
