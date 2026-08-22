"""Async engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Managed Postgres drops idle connections, and this bot idles for hours
# between photos: without pre_ping the first request after a pause would take
# a dead connection from the pool and fail as a random-looking database error.
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# Also used directly, outside FastAPI dependencies: ai_calls and note_failed
# are written in their own session so they survive the main transaction's
# rollback. See "Transaction model" in PLAN.md.
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency. Aiogram handlers get their session from middleware."""
    async with async_session_maker() as session:
        yield session
