"""What a reader says of a record (task 70): «Хорошо» and «Плохо» under every
document the bot sends, and after either the reader's own words — a comment,
which after «Плохо» says where the error is (task 103).

The CEO's reason, 2026-10-06: every fault fixed so far was found by the CEO
reading a record against its photographs, one record at a time, while the
groups read every record and said nothing. A press is a row of `feedback`,
one a person a record: pressed again it changes the rating and never counts
twice. Every press asks a question in the chat, and every reply to one is a
comment, counted one by one (rating.py): the button is how a reader adds a
comment — the first to write nine pressed «Плохо» before each (task 103).
The reply finds its row by the question's message: nothing is kept in the
process, so a restart between the question and the answer loses nothing.
With FEEDBACK_CHAT_ID set, a record's «Плохо» goes there with the document
once, not once a press, and every comment the moment it is written.

The router stands before the corpus's in app/main.py: a reply to the bot's
question is feedback whatever it says, a "#word" included.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    ForceReply,
    InaccessibleMessage,
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
from app.db.models import Event, Feedback, Group, Note, User
from app.services import pdf

logger = logging.getLogger(__name__)

router = Router()

_PREFIX = "rate"
_RATINGS = ("good", "bad")
# The event of a press, which carries the question it asked (task 103), and
# of a comment, which rating.py counts: one an отзыв.
RATED = "note_rated"
COMMENTED = "note_feedback"
# The study version's button (task 80), answered in study_version.on_study.
STUDY_PREFIX = "study"
# A private lecture's button into a group (task 63), answered in
# to_group.on_move.
MOVE_PREFIX = "move"


def keyboard(
    note_id: int, study: bool = False, groups: list[Group] | None = None
) -> InlineKeyboardMarkup:
    """The buttons under a document: «Хорошо» and «Плохо», and under them,
    with `study`, «Учебная версия» — under the record's own document, which
    goes out only when its study version could not be had (corpus.deliver) —
    and «В группу «…»» for each of `groups`, under a private lecture's
    (to_group.targets). Each names the record the document is drawn from —
    for a lecture of several notebooks, its base."""
    rows = [
        [
            InlineKeyboardButton(
                text=texts.RATE_GOOD, callback_data=f"{_PREFIX}:good:{note_id}"
            ),
            InlineKeyboardButton(
                text=texts.RATE_BAD, callback_data=f"{_PREFIX}:bad:{note_id}"
            ),
        ]
    ]
    if study:
        rows.append(
            [
                InlineKeyboardButton(
                    text=texts.STUDY_BUTTON, callback_data=f"{STUDY_PREFIX}:{note_id}"
                )
            ]
        )
    rows += move_rows(note_id, groups or [])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def move_rows(note_id: int, groups: list[Group]) -> list[list[InlineKeyboardButton]]:
    """«В группу «…»», a row for each group, the group named: a person may be
    in several."""
    return [
        [
            InlineKeyboardButton(
                text=texts.move_button(group.title),
                callback_data=f"{MOVE_PREFIX}:{note_id}:{group.id}",
            )
        ]
        for group in groups
    ]


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
) -> tuple[Feedback, str | None]:
    """The person's row for the record with its rating set, and the rating it
    held before — None for the first press. Two presses landing at once make
    one row: the loser fetches the winner's, as a user row is fetched in the
    middleware.

    The row keeps the group it was first given in, and its `created_at` the
    week: an отзыв counts where and when it was given, and no later press
    moves it to another chat's count (task 103)."""
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
            return row, None
    before = row.rating
    row.rating = rating
    return row, before


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
    row, before = await _rated(session, note, user, group, message.chat.id, rating)
    # The press is kept whether or not its notice can be shown: a callback
    # answered too late — the update waited for a connection — is refused by
    # Telegram, and the exception would roll the отзыв back.
    try:
        await callback.answer(texts.RATED_GOOD if rating == "good" else texts.RATED_BAD)
    except Exception:
        logger.warning(
            "the notice of a press on note %s was refused", note.id, exc_info=True
        )

    # Every press asks, the same button twice included: it is how a reader
    # adds a comment, and only the comments count again (task 103).
    title = pdf.plain(note.title)
    asked = await _ask(message, callback.from_user, group, title, rating, note.id)
    if asked is not None:
        row.chat_id = message.chat.id
        row.prompt_message_id = asked
    await log_event(
        session,
        user.id,
        RATED,
        {
            "note_id": note.id,
            "rating": rating,
            "changed": before is not None and before != rating,
            "again": before == rating,
            # What finds the row when an earlier question is answered.
            "prompt": asked,
        },
        group_id=group.id if group is not None else None,
    )
    # A record's «Плохо» reaches the feedback chat once, with its document,
    # and again only when the reader comes back to it from «Хорошо»: pressed
    # before every comment, it had sent one PDF there eight times.
    if rating == "bad" and before != "bad":
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


async def _ask(
    message: Message | InaccessibleMessage,
    tg_user: TgUser,
    group: Group | None,
    title: str,
    rating: str,
    note_id: int,
) -> int | None:
    """The question under a press — what is wrong after «Плохо», what was good
    after «Хорошо» — and its message id, which the reply finds the row by;
    None when it could not be sent, the press kept all the same."""
    question = texts.feedback_question(title, rating)
    markup = ForceReply(
        selective=True,
        input_field_placeholder=(
            texts.FEEDBACK_PLACEHOLDER if rating == "bad" else texts.PRAISE_PLACEHOLDER
        ),
    )
    try:
        if group is not None:
            # Named, so that Telegram opens the reply field for this reader
            # alone and not for the whole chat.
            content = Text(
                TextMention(tg_user.first_name, user=tg_user),
                ", ",
                question[0].lower() + question[1:],
            )
            asked = await message.answer(**content.as_kwargs(), reply_markup=markup)
        else:
            asked = await message.answer(question, reply_markup=markup)
    except Exception:
        logger.warning("could not ask about note %s", note_id, exc_info=True)
        return None
    return asked.message_id


async def _answering(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> dict | bool:
    """Whether a message answers one of the bot's questions under a press — a
    reply to it, from the reader it was asked of — and if so, that reader's
    row."""
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
    if row is None:
        row = await _asked_before(session, user, group, asked.message_id)
    return {"feedback": row} if row is not None else False


async def _asked_before(
    session: AsyncSession, user: User, group: Group | None, prompt: int
) -> Feedback | None:
    """The row an earlier question was asked for. The row holds its newest
    question only, and every press asks anew (task 103), so a reply to the
    one before is found through the press that asked it: its event names the
    question, in this chat — the group's, or the reader's own with the bot —
    where a message's id is unique."""
    in_chat = (
        Event.group_id == group.id if group is not None else Event.group_id.is_(None)
    )
    presses = (
        await session.execute(
            select(Event.payload)
            .where(Event.type == RATED, Event.user_id == user.id, in_chat)
            .order_by(Event.id.desc())
        )
    ).scalars().all()
    for payload in presses:
        if isinstance(payload, dict) and payload.get("prompt") == prompt:
            note_id = payload.get("note_id")
            if not isinstance(note_id, int):
                return None
            return (
                await session.execute(
                    select(Feedback).where(
                        Feedback.note_id == note_id, Feedback.user_id == user.id
                    )
                )
            ).scalar_one_or_none()
    return None


@router.message(_answering)
async def on_answer(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    feedback: Feedback,
    group: Group | None = None,
) -> None:
    """A comment — the reader's words after either button, stored with their
    rating and counted as an отзыв of its own (task 103). A caption counts,
    and a screenshot goes to FEEDBACK_CHAT_ID as it is."""
    words = (message.text or message.caption or "").strip()
    if words:
        feedback.text = f"{feedback.text}\n{words}" if feedback.text else words
    await log_event(
        session,
        user.id,
        COMMENTED,
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
            feedback.rating,
            texts.feedback_where(group.title if group is not None else None),
            _who(message.from_user),
        ),
        message.message_id,
    )
