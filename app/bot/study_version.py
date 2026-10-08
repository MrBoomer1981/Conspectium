"""A lecture's study version on request (task 80): «Учебная версия», the
button under every document.

The CEO's of 2026-10-08. Nothing is built unasked: the presses are the
measure of whether a group wants it. The first press on a record calls the
model once, inside the day's limits, and the record keeps what came back;
every later press draws it again and pays nothing. While one is being built,
a second press on the same record is told so and starts nothing — in this
process, which "Scale debt" says is the only one.

The model call is study.build's; the drawing corpus.send_study_pdf's, as a
record's own document is drawn there.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import corpus, feedback, texts
from app.core.events import log_event
from app.db.models import Group, Note, User
from app.services import limits, study, vision

logger = logging.getLogger(__name__)

router = Router()

# The records whose study version is being built in this process.
_building: set[int] = set()


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
    group_id = group.id if group is not None else None

    kept = study.from_stored(note.study)
    if kept is not None and kept.unit_count != len(study.units(note.markdown)):
        kept = None  # cut by another rule than the one drawing it now
    if kept is None and note.id in _building:
        await callback.answer(texts.STUDY_BUSY)
        return
    if kept is None:
        refusal = await limits.check_limits(session, user, pages=0, group=group)
        if refusal is not None:
            await callback.answer()
            await message.answer(refusal)
            return
    await callback.answer(texts.STUDY_SENDING if kept is not None else texts.STUDY_BUILDING)
    await log_event(
        session,
        user.id,
        "study_requested",
        {"note_id": note.id, "kept": kept is not None},
        group_id=group_id,
    )

    version = kept
    if version is None:
        _building.add(note.id)
        try:
            version = await study.build(note.markdown)
        finally:
            _building.discard(note.id)
        await vision.log_ai_calls(user.id, version.stats, group_id=group_id)
        if version.refused is not None:
            await log_event(
                session,
                user.id,
                "study_failed",
                {"note_id": note.id, "reason": version.refused},
                group_id=group_id,
            )
            await message.answer(texts.STUDY_FAILED)
            return
        note.study = version.stored()

    if not await corpus.send_study_pdf(message, session, note, version):
        await log_event(
            session, user.id, "study_failed", {"note_id": note.id, "reason": "pdf"},
            group_id=group_id,
        )
        await message.answer(texts.STUDY_FAILED)
        return
    await log_event(
        session,
        user.id,
        "study_sent",
        {
            "note_id": note.id,
            "kept": kept is not None,
            "topics": len(version.topics),
            "units": sum(len(topic.units) for topic in version.topics),
            "missing": version.missing,
            "repeated": version.repeated,
            "abouts_dropped": version.abouts_dropped,
            "questions": len(version.questions),
            "questions_dropped": version.questions_dropped,
        },
        group_id=group_id,
    )
