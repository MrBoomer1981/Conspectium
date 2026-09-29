"""Session-per-update middleware: opens a DB session, resolves the user and the
group chat, and in a group lets through only what is addressed to the bot."""

from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple, TypeVar

from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import tags
from app.core.events import log_event
from app.db.models import Group, User
from app.db.session import async_session_maker

# Telegram's two kinds of group chat. A channel is neither: nobody sends the
# bot a page of notes there.
GROUP_CHATS = ("group", "supergroup")

# An image sent as a file is a page like a photo: people send one uncompressed
# to keep the handwriting sharp. These are the formats Pillow opens; a HEIC
# from an iPhone it cannot, and stays a file like any other.
PAGE_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

_Row = TypeVar("_Row", User, Group)


class PageFile(NamedTuple):
    """A page as Telegram holds it: what the bot downloads it by, and its size
    where Telegram says it — a photo does, a file does not."""

    file_id: str
    width: int | None
    height: int | None


def page_file(message: Message | None) -> PageFile | None:
    """The page a message carries — the largest size of a photo, or an image
    sent as a file — and None for anything else."""
    if message is None:
        return None
    if message.photo:
        size = message.photo[-1]
        return PageFile(size.file_id, size.width, size.height)
    document = message.document
    if document is not None and document.mime_type in PAGE_IMAGE_TYPES:
        return PageFile(document.file_id, None, None)
    return None


def is_page(message: Message) -> bool:
    return page_file(message) is not None


def is_summon(message: Message) -> bool:
    """A reply in a group chat to a page somebody sent. What the reply says
    decides whether it calls the bot (tags.from_reply) — but a "#word" under a
    page is never a search, so the corpus leaves every one of these alone."""
    return message.chat.type in GROUP_CHATS and (
        page_file(message.reply_to_message) is not None
    )


def heard(message: Message, bot_username: str | None = None) -> bool:
    """Whether a message is any of the bot's business.

    In a private chat every message is. In a group the bot, once it can see
    the chat at all, sees every message in it, and nearly all of them are
    people talking to each other. Those stop here: no session is opened, no
    user row is made for a classmate who only ever said hello, nothing is
    logged and nothing is answered. What gets through is what the bot acts on
    in a group — a command, a "#word" on its own, a photo or an image file
    whose caption carries a "#word", a reply to a page that calls the bot on
    it or names it — and every page of an album, because an album's caption
    rides on one page only and the album is judged whole, in
    handlers._process_album. So does the notice that the chat's id changed:
    it is what moves the group.
    """
    if message.chat.type not in GROUP_CHATS:
        return True
    if message.migrate_to_chat_id or message.migrate_from_chat_id:
        return True
    if message.text is not None:
        if message.text.startswith("/") or tags.is_bare(message.text):
            return True
        # Naming the bot without a subject earns a hint rather than silence:
        # silence is what made the bot look broken in a group.
        return is_summon(message) and (
            tags.from_reply(message.text, bot_username) is not None
            or tags.mentions(message.text, bot_username)
        )
    if message.media_group_id and is_page(message):
        return True
    if message.photo or message.document:
        return tags.from_caption(message.caption) is not None
    return False


async def _bot_username(event: Any, data: dict[str, Any]) -> str | None:
    """The bot's own @name, which a reply in a group may call it by. Only a
    group asks — a private chat is heard whole — and aiogram keeps the answer
    from the first time, which the startup log already asked for."""
    bot = data.get("bot")
    chat = getattr(event, "chat", None)
    if bot is None or chat is None or chat.type not in GROUP_CHATS:
        return None
    return (await bot.me()).username


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        # Registered for messages and for the bot's own membership changes;
        # only a message can be chatter.
        if isinstance(event, Message) and not heard(
            event, await _bot_username(event, data)
        ):
            return None
        async with async_session_maker() as session:
            data["session"] = session
            data["user"] = await self._get_or_create_user(session, event)
            data["group"] = await self._get_or_create_group(session, event)
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            await session.commit()
            return result

    @staticmethod
    async def _get_or_create_user(session: AsyncSession, event: Any) -> User:
        tg_user = event.from_user
        lookup = select(User).where(User.tg_id == tg_user.id)
        user = (await session.execute(lookup)).scalar_one_or_none()
        if user is not None:
            return user

        user = User(
            tg_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
        )
        registered = await _insert_or_fetch(session, user, lookup)
        if registered is not user:
            return registered  # another page of the same album got here first
        await log_event(session, user.id, "user_registered")
        # Commit the new user now, before the handler runs. log_ai_calls opens
        # its own session mid-handler and inserts ai_calls.user_id: without this
        # commit that row would reference a user this other session can't see
        # yet, and the FK insert would fail. A user who messaged the bot is
        # registered regardless of how their first update turns out.
        await session.commit()
        return user

    @staticmethod
    async def _get_or_create_group(session: AsyncSession, event: Any) -> Group | None:
        """The group chat an update came from, registered on first sight; None
        in a private chat."""
        chat = getattr(event, "chat", None)
        if chat is None or chat.type not in GROUP_CHATS:
            return None

        chat_id = chat.id
        # A group that becomes a supergroup gets a new chat id, and Telegram
        # says so twice: migrate_to_chat_id in the old chat and
        # migrate_from_chat_id in the new one, two updates that may be handled
        # at once. Whichever comes first moves the row, and every record of the
        # group moves with it — they point at our id, not at Telegram's.
        moved_to = getattr(event, "migrate_to_chat_id", None)
        moved_from = getattr(event, "migrate_from_chat_id", None)
        if moved_to:
            await _move_group(session, chat_id, moved_to)
            chat_id = moved_to
        elif moved_from:
            await _move_group(session, moved_from, chat_id)

        lookup = select(Group).where(Group.tg_chat_id == chat_id)
        group = (await session.execute(lookup)).scalar_one_or_none()
        if group is None:
            return await _insert_or_fetch(
                session, Group(tg_chat_id=chat_id, title=chat.title), lookup
            )
        if chat.title and group.title != chat.title:
            group.title = chat.title
        return group


async def _insert_or_fetch(session: AsyncSession, row: _Row, lookup: Select) -> _Row:
    """Insert a row keyed by a unique Telegram id, or fetch the one another
    update inserted a moment earlier.

    The pages of an album are separate updates handled at once, and in a
    group chat an album is a likely first message from someone the bot has
    never seen: every page tries to register them, and all but one would fail
    on the unique index — the page lost, and an error posted to the chat. The
    SAVEPOINT keeps the failed insert from poisoning the session.
    """
    try:
        async with session.begin_nested():
            session.add(row)
    except IntegrityError:
        return (await session.execute(lookup)).scalar_one()
    return row


async def _move_group(session: AsyncSession, old_chat_id: int, new_chat_id: int) -> None:
    taken = await session.execute(select(Group.id).where(Group.tg_chat_id == new_chat_id))
    if taken.first() is not None:
        return  # the other half of the notice got here first
    group = (
        await session.execute(select(Group).where(Group.tg_chat_id == old_chat_id))
    ).scalar_one_or_none()
    if group is not None:
        group.tg_chat_id = new_chat_id
        await session.flush()
