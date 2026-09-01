"""Aiogram handlers."""

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.events import log_event
from app.db.models import User
from app.services import images, photoguard

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

    # The frame is checked before any model call: on a bad shot the model
    # recognises the topic from the heading and produces a plausible
    # retelling instead of failing. Metrics go to the event for every photo,
    # accepted ones included — data for future threshold calibration.
    photo_verdict = photoguard.check_photo_bytes(compressed)
    await log_event(
        session,
        user.id,
        "photo_accepted" if photo_verdict.ok else "photo_rejected",
        {
            "reason": photo_verdict.reason,
            "line_height_px": photo_verdict.line_height_px,
            "sharpness": photo_verdict.sharpness,
            "paper_fraction": photo_verdict.paper_fraction,
            "contrast": photo_verdict.contrast,
        },
    )
    if not photo_verdict.ok:
        await message.answer(photo_verdict.reason)
        return

    await message.answer(texts.PROCESSING)
