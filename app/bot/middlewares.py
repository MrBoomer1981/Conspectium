"""Session-per-update middleware: opens a DB session, resolves the user."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.db.models import User
from app.db.session import async_session_maker


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            data["user"] = await self._get_or_create_user(session, event)
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            await session.commit()
            return result

    @staticmethod
    async def _get_or_create_user(session: AsyncSession, event: Message) -> User:
        tg_user = event.from_user
        result = await session.execute(select(User).where(User.tg_id == tg_user.id))
        user = result.scalar_one_or_none()
        if user is not None:
            return user

        user = User(
            tg_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
        )
        session.add(user)
        await session.flush()  # assigns user.id, needed for the event below
        await log_event(session, user.id, "user_registered")
        return user
