"""Aiogram handlers."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot import texts

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(texts.START)
