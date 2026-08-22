"""Event logging."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)


async def log_event(
    session: AsyncSession,
    user_id: int | None,
    event_type: str,
    payload: dict | None = None,
) -> None:
    """Write an event to the caller's (main) session. Transactional: lost if
    the update rolls back, and that's fine — the event describes something
    that, in the end, didn't happen.

    Never raises. The insert runs inside a SAVEPOINT so that a failed insert
    doesn't poison the whole transaction and take down the next request too.

    Named event_type, not type: no need to shadow the builtin. The database
    column is still called `type`.
    """
    try:
        async with session.begin_nested():
            session.add(Event(user_id=user_id, type=event_type, payload=payload or {}))
    except Exception:
        logger.exception("log_event failed: %s", event_type)


async def log_event_standalone(
    user_id: int | None,
    event_type: str,
    payload: dict | None = None,
) -> None:
    """Same thing, but in its own session with an immediate commit.

    Only for cases where the main transaction is already rolling back —
    i.e. note_failed from the global error handler (task 10). Don't use it
    anywhere else.
    """
    try:
        async with async_session_maker() as session, session.begin():
            session.add(Event(user_id=user_id, type=event_type, payload=payload or {}))
    except Exception:
        logger.exception("log_event_standalone failed: %s", event_type)
