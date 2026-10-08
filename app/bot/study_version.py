"""«Учебная версия», the button under a record's own document (task 80).

A chat gets a record's study version, not the record (corpus.deliver, the
CEO's of 2026-10-08); the record's own document goes out only when no study
version could be had, and this button under it asks again — the cap may have
passed, the call may come back this time. The CEO wants the two kept apart
so that one day either can be sent and the other offered by a button: this
is the button, and corpus.deliver the one place that decides.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import corpus, feedback, texts
from app.core.events import log_event
from app.db.models import Group, Note, User

logger = logging.getLogger(__name__)

router = Router()


def _pressed(data: str | None) -> int | None:
    """74 for "study:74", None for anything else."""
    parts = (data or "").split(":")
    if len(parts) != 2 or parts[0] != feedback.STUDY_PREFIX or not parts[1].isdigit():
        return None
    return int(parts[1])


def _reachable(note: Note, user: User, group: Group | None) -> bool:
    """corpus._owned for one record: in a group, the group's; in a private
    chat, the user's own that belongs to no group."""
    if group is not None:
        return note.group_id == group.id
    return note.user_id == user.id and note.group_id is None


@router.callback_query(F.data.startswith(f"{feedback.STUDY_PREFIX}:"))
async def on_study(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    group: Group | None = None,
) -> None:
    note_id = _pressed(callback.data)
    message = callback.message
    note = await session.get(Note, note_id) if note_id is not None else None
    if note is None or message is None or not _reachable(note, user, group):
        await callback.answer()
        return

    source = await corpus._source(session, note)
    kept = corpus._kept(source)
    await callback.answer(texts.STUDY_SENDING if kept else texts.STUDY_BUILDING)
    await log_event(
        session,
        user.id,
        "study_requested",
        {"note_id": source.base.id, "kept": kept},
        group_id=group.id if group is not None else None,
    )
    version, why = await corpus.study_of(session, source, user, group)
    if why == "busy":
        await message.answer(texts.STUDY_BUSY)
        return
    if version is None:
        # The limit's own words when a limit said no; the plain apology for
        # the rest — the stage off, the call refused.
        await message.answer(why if why not in ("off", "refused") else texts.STUDY_FAILED)
        return
    if not await corpus.send_study_pdf(message, session, source, version):
        await message.answer(texts.STUDY_FAILED)
        return
    await corpus.study_sent(session, user, group, source.base, version, kept, via="button")
