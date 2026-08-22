"""Aiogram handlers."""

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.events import log_event
from app.db.models import User
from app.services import images

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User) -> None:
    await message.answer(texts.START)


@router.message(F.photo)
async def handle_photo(
    message: Message, session: AsyncSession, user: User, bot: Bot
) -> None:
    photo = message.photo[-1]
    original = (await bot.download(photo)).read()
    compressed = images.compress(original)

    await message.answer(texts.PROCESSING)

    await log_event(
        session,
        user.id,
        "note_captured",
        {
            "bytes_before": len(original),
            "bytes_after": len(compressed),
            "width": photo.width,
            "height": photo.height,
            "source_type": "photo",
        },
    )
