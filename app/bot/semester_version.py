"""«Весь семестр одним PDF» (task 63, the CEO's of 2026-10-12 and 2026-10-13):
the button under the list a subject's "#word" answers with, and the document
it sends — every lecture of the subject set out by the semester's topics
(services/semester.py), drawn as a study version is.

Built where the explaining stage is on, on its model, inside the bot's day
(pages=0) and paid by whoever presses, as a study version is (the CEO's);
its arrangement kept on the subject by the fingerprint of the lectures it
was built from, so a second press draws it again and pays nothing, and a
lecture added builds it anew. The PDF itself is not kept: it is drawn again
from what is, as a record's is.
"""

from __future__ import annotations

import asyncio
import logging
import re

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import corpus, feedback, subjects, texts, waiting
from app.core.config import settings
from app.core.events import log_event
from app.db.models import Group, Lecture, Subject, User
from app.services import limits, merge, pdf, semester, study, vision

logger = logging.getLogger(__name__)

router = Router()

# The subjects whose semester is being built in this process: a second press
# meanwhile starts nothing ("Scale debt").
_building: set[int] = set()
_FIGURE_RE = re.compile(r"\[рисунок (\d+):")


def _pressed(data: str | None) -> int | None:
    """12 for "semester:12", None for anything else."""
    parts = (data or "").split(":")
    if len(parts) != 2 or parts[0] != feedback.SEMESTER_PREFIX or not parts[1].isdigit():
        return None
    return int(parts[1])


def _reachable(subject: Subject, user: User, group: Group | None) -> bool:
    """corpus._owned for a subject: in a group, the group's; in a private
    chat, the person's own."""
    if group is not None:
        return subject.group_id == group.id
    return subject.group_id is None and subject.user_id == user.id


async def lectures_of(
    session: AsyncSession, subject: Subject
) -> tuple[list[semester.Lecture], dict[int, bytes]]:
    """The subject's lectures in the order they were given, each as its
    document draws it — the fullest notebook with what the others add — and
    their drawings, numbered through the semester: each lecture numbers its
    own from one."""
    rows = (
        await session.execute(
            select(Lecture)
            .where(Lecture.subject_id == subject.id)
            .order_by(Lecture.given_on, Lecture.id)
        )
    ).scalars().all()
    lectures: list[semester.Lecture] = []
    drawings: dict[int, bytes] = {}
    for lecture in rows:
        notes = await subjects.materials(session, lecture.id)
        if not notes:
            continue
        base = subjects.base_of(notes)
        others = [note.markdown for note in notes if note.id != base.id]
        text = base.markdown or ""
        if others:
            text = (
                await asyncio.to_thread(merge.merged, text, others, texts.INSERT_LABEL)
            ).markdown
        own = await corpus.figures_of(session, base.id)
        numbers: dict[int, int] = {}

        def renumbered(found: re.Match) -> str:
            number = int(found.group(1))
            if number not in numbers:
                numbers[number] = len(drawings) + len(numbers) + 1
            return f"[рисунок {numbers[number]}:"

        text = _FIGURE_RE.sub(renumbered, text)
        for number, through in numbers.items():
            if number in own:
                drawings[through] = own[number]
        if not text.strip():
            continue
        lectures.append(
            semester.Lecture(
                day=lecture.given_on,
                title=corpus._document_title(base.title, text),
                markdown=text,
            )
        )
    return lectures, drawings


async def _notice(callback: CallbackQuery, text: str | None = None) -> None:
    """The press answered, whether or not Telegram still takes the notice
    (feedback.on_rate, task 103)."""
    try:
        await callback.answer(text)
    except Exception:
        logger.warning("the notice of a press was refused", exc_info=True)


@router.callback_query(F.data.startswith(f"{feedback.SEMESTER_PREFIX}:"))
async def on_semester(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    group: Group | None = None,
) -> None:
    subject_id = _pressed(callback.data)
    message = callback.message
    subject = await session.get(Subject, subject_id) if subject_id is not None else None
    if subject is None or message is None or not _reachable(subject, user, group):
        await _notice(callback)
        return
    group_id = group.id if group is not None else None
    lectures, drawings = await lectures_of(session, subject)
    if len(lectures) < 2:
        await _notice(callback, texts.SEMESTER_FEW)
        return
    kept = study.from_stored(subject.semester)
    fresh = kept is not None and kept.source == semester.fingerprint(lectures)
    await _notice(callback, texts.SEMESTER_SENDING if fresh else texts.SEMESTER_BUILDING)
    await log_event(
        session,
        user.id,
        "semester_requested",
        {"subject_id": subject.id, "lectures": len(lectures), "kept": fresh},
        group_id=group_id,
    )
    if not fresh and subject.id in _building:
        await message.answer(texts.SEMESTER_BUSY)
        return

    async with waiting.shown(message):
        version = kept if fresh else None
        if version is None:
            why = await _why_not(session, user, group)
            if why is None:
                _building.add(subject.id)
                try:
                    version = await semester.build(lectures)
                finally:
                    _building.discard(subject.id)
                await vision.log_ai_calls(user.id, version.stats, group_id=group_id)
                if version.refused is not None:
                    why = version.refused
            if why is not None:
                await log_event(
                    session, user.id, "semester_failed",
                    {"subject_id": subject.id, "reason": why}, group_id=group_id,
                )
                await message.answer(why if why not in _OURS else texts.SEMESTER_FAILED)
                return
            subject.semester = version.stored()
            # Kept whatever the drawing does: it was paid for.
            await session.commit()

        arranged = semester.layout(lectures, version)
        page = pdf.Page(
            subject=texts.pdf_subject(subject.word),
            date=texts.semester_dates(lectures[0].day, lectures[-1].day),
            page_word=texts.PDF_PAGE_WORD,
            invite=texts.PDF_INVITE,
            bot_username=await corpus._bot_username(message),
        )
        title = texts.semester_title(subject.word)
        try:
            data = await asyncio.to_thread(
                pdf.render,
                title,
                arranged.markdown,
                subtitle=texts.SEMESTER_SUBTITLE,
                page=page,
                figures=drawings,
                placed=[corpus._study_box(box) for box in arranged.boxes],
                formula_numbers=arranged.formula_numbers,
            )
        except Exception:
            logger.exception("could not draw the semester of subject %s", subject.id)
            await log_event(
                session, user.id, "semester_failed",
                {"subject_id": subject.id, "reason": "drawing"}, group_id=group_id,
            )
            await message.answer(texts.SEMESTER_FAILED)
            return
        sent = await corpus._sent_document(
            message,
            data,
            corpus.pdf_filename(subject.id, subject.word, texts.SEMESTER_FILE_WORD),
            texts.semester_caption(subject.word, len(lectures), len(version.topics)),
            None,
        )
        await log_event(
            session,
            user.id,
            "semester_sent" if sent else "semester_failed",
            {
                "subject_id": subject.id,
                "lectures": len(lectures),
                "kept": fresh,
                "topics": len(version.topics),
                "units": sum(len(topic.units) for topic in version.topics),
                "missing": version.missing,
                "repeated": version.repeated,
                "off_topic": len(version.off_topic),
                "questions": len(version.questions),
                "bytes": len(data),
            }
            if sent
            else {"subject_id": subject.id, "reason": "sending"},
            group_id=group_id,
        )


# The reasons this module gives itself, which the chat is told plainly; a
# limit's own words go to the chat as they are.
_OURS = ("off", "one lecture", "call failed", "unparseable", "units missing")


async def _why_not(session: AsyncSession, user: User, group: Group | None) -> str | None:
    """Why a semester cannot be built now: the explaining stage off, or a
    limit's own words — the bot's day, the kill switch."""
    if not settings.EXPLAIN_ENABLED:
        return "off"
    return await limits.check_limits(session, user, pages=0, group=group)
