"""What a chat sees while its record is made (task 105): one line, changed in
place every few seconds — «Работаем…», «Считаю формулы…», «Учусь, чтобы
вам не пришлось…» — and deleted on the way out, once the record, or the
reason there is none, has gone to the chat. What stays is the record alone,
in one message (corpus.deliver).

The CEO's of 2026-10-12: «пока пользователь ждет будет крутить какие нибудь
надписи … когда меняем ее, старую удаляем». Changed in place, the CEO's
choice: no notification, and in a group no line jumping to the foot of the
chat every few seconds. Nothing here fails a record: a line Telegram will
not change or delete is a line in the log.
"""

import asyncio
import itertools
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import Message

from app.bot import texts

logger = logging.getLogger(__name__)

# How long a line stands before the next: long enough to be read, short
# enough that a wait of three minutes never looks stuck.
EVERY_S = 8.0


async def _turn(line: Message) -> None:
    """The line changed every EVERY_S round the phrases, the first last, until
    cancelled. Two lines in a row are never the same, which Telegram would
    refuse as not modified."""
    for text in itertools.cycle(texts.WAITING[1:] + texts.WAITING[:1]):
        await asyncio.sleep(EVERY_S)
        try:
            await line.edit_text(text)
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
        except TelegramAPIError as exc:
            # The reader deleted it, or the chat no longer takes the bot's
            # words: the line stays as it is, and is deleted at the end.
            logger.info("the waiting line stopped turning: %s", exc)
            return


@asynccontextmanager
async def shown(message: Message) -> AsyncIterator[None]:
    """The waiting line in `message`'s chat while the body runs, deleted on
    every way out of it: the record sent, a reason sent instead, an
    exception on its way to the error handler, a deploy's cancellation. Sent
    as «Обрабатываю...» was, so a chat that takes no words from the bot
    fails here, before anything is spent."""
    line = await message.answer(texts.WAITING[0])
    turning = asyncio.create_task(_turn(line)) if line is not None else None
    try:
        yield
    finally:
        if turning is not None:
            turning.cancel()
            await asyncio.gather(turning, return_exceptions=True)
            try:
                await line.delete()
            except TelegramAPIError as exc:
                logger.info("the waiting line could not be deleted: %s", exc)
