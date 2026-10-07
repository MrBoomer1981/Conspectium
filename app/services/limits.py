"""Daily spend limits: checked before processing starts, debited after a save.

check_limits is step 4 of the canonical order (PLAN.md): it runs before the
frame check and before any Gemini call, so a disabled kill switch or an
exhausted cap never costs a model call or a pointless "retake the photo".

All day boundaries are UTC.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.bot import texts
from app.core.config import settings
from app.db.models import AiCall, Group, Note, User


async def check_limits(
    session: AsyncSession, user: User, pages: int, group: Group | None = None
) -> str | None:
    """Return the rejection text (already in Russian, straight from texts.py)
    if this request must be turned away, or None if it may proceed.

    Order is fixed:
      1. AI kill switch off                      -> texts.AI_DISABLED
      2. today's total model spend at the cap    -> texts.LIMIT_COST
      3. the group's pages would overflow        -> texts.group_day_over
      4. this user's page budget would overflow  -> texts.LIMIT_PAGES
    """
    if not settings.AI_ENABLED:
        return texts.AI_DISABLED

    today = datetime.now(timezone.utc).date()

    # The cost cap is a global circuit breaker, not per-user: it guards the
    # daily bill regardless of who ran it up. Soft by design — checked here,
    # with no budget reserved for the operation about to start.
    if await _spent_today_usd(session, today) >= settings.DAILY_COST_LIMIT_USD:
        return texts.LIMIT_COST

    # A group's own day (task 41), so one busy group cannot spend the day of
    # every other. Asked when pages come, never for a record's later stages
    # (pages=0): a record let in is composed and explained whatever the count
    # says by then — the document is not traded for a count.
    if group is not None and pages > 0:
        left = await group_pages_left(session, group, today)
        if pages > left:
            return texts.group_day_over(left, pages, settings.DAILY_PAGES_PER_GROUP)

    # Today's pages, read and not written: a day that is over counts as none,
    # and so does a brand-new user's, whose quota_reset_at is None. The
    # rollover used to be written here; the next event flushed it, and the
    # row stayed locked for the whole record — minutes — so a second album
    # from the same person waited for the first, then zeroed its pages
    # (task 76). consume() writes the day.
    used = user.pages_used_today if user.quota_reset_at == today else 0
    if used + pages > settings.DAILY_PAGES_PER_USER:
        return texts.LIMIT_PAGES

    return None


async def consume(session: AsyncSession, user: User, pages: int) -> None:
    """Add `pages` to the user's day. Called only after the record has been
    saved — step 14.

    One statement, its arithmetic the database's, a day that is over starting
    again from these pages. Two records saved at once both count — the second
    waits for the first's commit and adds to what it wrote — and the row is
    locked only from here to the commit, seconds (task 76). Two checked at
    once can still both pass: soft, as the cost cap is (PLAN.md -> Known
    risks). The object takes the result as committed state, so nothing is
    flushed over it."""
    today = datetime.now(timezone.utc).date()
    counted = await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            pages_used_today=case(
                (User.quota_reset_at == today, User.pages_used_today + pages),
                else_=pages,
            ),
            quota_reset_at=today,
        )
        .returning(User.pages_used_today)
        .execution_options(synchronize_session=False)
    )
    set_committed_value(user, "pages_used_today", counted.scalar_one())
    set_committed_value(user, "quota_reset_at", today)


async def group_pages_left(
    session: AsyncSession, group: Group, today: date | None = None
) -> int:
    """What is left of the group's day: DAILY_PAGES_PER_GROUP less the pages
    of its records made since 00:00 UTC — what was read and charged. Counted
    from the records rather than kept on the group's row, so there is nothing
    to reset and two albums saved at once lose none of the count. A .docx
    costs nothing and is not counted. Never below 0, though the group can go
    past its day: two albums let in at once both pass (PLAN.md -> Known
    risks)."""
    today = today or datetime.now(timezone.utc).date()
    stmt = select(func.coalesce(func.sum(Note.page_count), 0)).where(
        Note.group_id == group.id,
        Note.created_at >= _day_start(today),
        Note.source_type != "docx",
    )
    used = int((await session.execute(stmt)).scalar_one())
    return max(settings.DAILY_PAGES_PER_GROUP - used, 0)


async def _spent_today_usd(session: AsyncSession, today: date) -> float:
    """Sum of ai_calls.cost_usd since 00:00 UTC today. Rows with cost_usd NULL
    are skipped by SUM; SUM over zero rows is NULL, coalesced to 0.0."""
    stmt = select(func.coalesce(func.sum(AiCall.cost_usd), 0.0)).where(
        AiCall.created_at >= _day_start(today)
    )
    return float((await session.execute(stmt)).scalar_one())


def _day_start(today: date) -> datetime:
    return datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
