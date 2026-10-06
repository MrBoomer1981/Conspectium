"""What a reader says of a record (task 70): «Хорошо» and «Плохо» under every
document the bot sends, and after «Плохо» the reader's own words on where the
error is.

The CEO's reason, 2026-10-06: every fault fixed so far was found by the CEO
reading a record against its photographs, one record at a time, while the
groups read every record and said nothing. A press is a row of `feedback`,
one a person a record. The question «что не так» is a message in the chat,
and the reply to it finds its row by that message: nothing is kept in the
process, so a restart between the question and the answer loses nothing.
With FEEDBACK_CHAT_ID set, every «Плохо» and every answer goes there at once,
with the document — the CEO sees where the error is the moment it is said.

The router stands before the corpus's in app/main.py: a reply to the bot's
question is feedback whatever it says, a "#word" included.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.types import User as TgUser
from aiogram.utils.formatting import Text, TextMention
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.config import settings
from app.core.events import log_event
from app.db.models import Feedback, Group, Note, User
from app.services import pdf

logger = logging.getLogger(__name__)

router = Router()

_PREFIX = "rate"
_RATINGS = ("good", "bad")


def keyboard(note_id: int) -> InlineKeyboardMarkup:
    """The two buttons under a document. Each names the record the document
    is drawn from — for a lecture of several notebooks, its base."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.RATE_GOOD, callback_data=f"{_PREFIX}:good:{note_id}"
                ),
                InlineKeyboardButton(
                    text=texts.RATE_BAD, callback_data=f"{_PREFIX}:bad:{note_id}"
                ),
            ]
        ]
    )


def _pressed(data: str | None) -> tuple[str, int] | None:
    """("bad", 74) for "rate:bad:74", None for anything else."""
    parts = (data or "").split(":")
    if (
        len(parts) != 3
        or parts[0] != _PREFIX
        or parts[1] not in _RATINGS
        or not parts[2].isdigit()
    ):
        return None
    return parts[1], int(parts[2])


def _who(tg_user: TgUser) -> str:
    return tg_user.full_name + (f" @{tg_user.username}" if tg_user.username else "")


async def _rated(
    session: AsyncSession,
    note: Note,
    user: User,
    group: Group | None,
    chat_id: int,
    rating: str,
) -> tuple[Feedback, bool]:
    """The person's row for the record with its rating set, and whether it
    changed one given before. Two presses landing at once make one row: the
    loser fetches the winner's, as a user row is fetched in the middleware."""
    lookup = select(Feedback).where(
        Feedback.note_id == note.id, Feedback.user_id == user.id
    )
    row = (await session.execute(lookup)).scalar_one_or_none()
    if row is None:
        row = Feedback(
            note_id=note.id,
            user_id=user.id,
            group_id=group.id if group is not None else None,
            rating=rating,
            chat_id=chat_id,
        )
        try:
            async with session.begin_nested():
                session.add(row)
        except IntegrityError:
            row = (await session.execute(lookup)).scalar_one()
        else:
            return row, False
    changed = row.rating != rating
    row.rating = rating
    # Where it was said last: the question, if one follows, is asked there.
    row.chat_id = chat_id
    row.group_id = group.id if group is not None else None
    return row, changed


async def _report(bot: Bot, chat_id: int, line: str, message_id: int) -> None:
    """A line to FEEDBACK_CHAT_ID, and the message it is about copied under
    it. Never reaches the reader: a chat that cannot be written to is a
    warning in the log. Nothing is sent when the feedback came from that chat
    itself — whoever reads it there has just seen it."""
    target = settings.FEEDBACK_CHAT_ID
    if target is None or target == chat_id:
        return
    try:
        await bot.send_message(target, line)
        await bot.copy_message(
            chat_id=target, from_chat_id=chat_id, message_id=message_id
        )
    except Exception:
        logger.warning("feedback could not be sent to FEEDBACK_CHAT_ID", exc_info=True)


@router.callback_query(F.data.startswith(f"{_PREFIX}:"))
async def on_rate(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> None:
    pressed = _pressed(callback.data)
    message = callback.message
    note = await session.get(Note, pressed[1]) if pressed is not None else None
    if pressed is None or note is None or message is None:
        await callback.answer()
        return
    rating = pressed[0]
    row, changed = await _rated(session, note, user, group, message.chat.id, rating)
    await log_event(
        session,
        user.id,
        "note_rated",
        {"note_id": note.id, "rating": rating, "changed": changed},
        group_id=group.id if group is not None else None,
    )
    if rating == "good":
        await callback.answer(texts.RATED_GOOD)
        return

    await callback.answer(texts.RATED_BAD)
    title = pdf.plain(note.title)
    question = texts.feedback_question(title)
    markup = ForceReply(selective=True, input_field_placeholder=texts.FEEDBACK_PLACEHOLDER)
    try:
        if group is not None:
            # Named, so that Telegram opens the reply field for this reader
            # alone and not for the whole chat.
            content = Text(
                TextMention(callback.from_user.first_name, user=callback.from_user),
                ", ",
                question[0].lower() + question[1:],
            )
            asked = await message.answer(**content.as_kwargs(), reply_markup=markup)
        else:
            asked = await message.answer(question, reply_markup=markup)
    except Exception:
        logger.warning("could not ask what is wrong with note %s", note.id, exc_info=True)
    else:
        row.prompt_message_id = asked.message_id
    await _report(
        bot,
        message.chat.id,
        texts.feedback_report(
            note.id,
            title,
            rating,
            texts.feedback_where(group.title if group is not None else None),
            _who(callback.from_user),
        ),
        message.message_id,
    )


async def _answering(
    message: Message, session: AsyncSession, user: User, bot: Bot
) -> dict | bool:
    """Whether a message answers the bot's question «что не так» — a reply to
    it, from the reader it was asked of — and if so, that reader's row."""
    asked = message.reply_to_message
    if asked is None or asked.from_user is None or asked.from_user.id != bot.id:
        return False
    row = (
        await session.execute(
            select(Feedback).where(
                Feedback.chat_id == message.chat.id,
                Feedback.prompt_message_id == asked.message_id,
                Feedback.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    return {"feedback": row} if row is not None else False


@router.message(_answering)
async def on_answer(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    feedback: Feedback,
    group: Group | None = None,
) -> None:
    """The reader's account of the error, stored with their rating — a
    caption counts, and a screenshot goes to FEEDBACK_CHAT_ID as it is."""
    words = (message.text or message.caption or "").strip()
    if words:
        feedback.text = f"{feedback.text}\n{words}" if feedback.text else words
    await log_event(
        session,
        user.id,
        "note_feedback",
        {"note_id": feedback.note_id, "chars": len(words), "photo": bool(message.photo)},
        group_id=group.id if group is not None else None,
    )
    await message.reply(texts.FEEDBACK_THANKS)
    note = await session.get(Note, feedback.note_id)
    title = pdf.plain(note.title) if note is not None else ""
    await _report(
        bot,
        message.chat.id,
        texts.feedback_answer_report(
            feedback.note_id,
            title,
            texts.feedback_where(group.title if group is not None else None),
            _who(message.from_user),
        ),
        message.message_id,
    )
