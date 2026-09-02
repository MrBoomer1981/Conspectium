"""Daily spend limits: checked before processing starts, debited after a save.

check_limits is step 4 of the canonical order (PLAN.md): it runs before the
frame check and before any Gemini call, so a disabled kill switch or an
exhausted cap never costs a model call or a pointless "retake the photo".

All day boundaries are UTC.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.config import settings
from app.db.models import AiCall, User


async def check_limits(session: AsyncSession, user: User, pages: int) -> str | None:
    """Return the rejection text (already in Russian, straight from texts.py)
    if this request must be turned away, or None if it may proceed.

    Order is fixed:
      1. AI kill switch off                      -> texts.AI_DISABLED
      2. today's total model spend at the cap    -> texts.LIMIT_COST
      3. this user's page budget would overflow  -> texts.LIMIT_PAGES
    """
    if not settings.AI_ENABLED:
        return texts.AI_DISABLED

    today = datetime.now(timezone.utc).date()

    # The cost cap is a global circuit breaker, not per-user: it guards the
    # daily bill regardless of who ran it up. Soft by design — checked here,
    # with no budget reserved for the operation about to start.
    if await _spent_today_usd(session, today) >= settings.DAILY_COST_LIMIT_USD:
        return texts.LIMIT_COST

    # Lazy daily rollover. A brand-new user has quota_reset_at = None, and
    # `None < today` raises TypeError, so the None check has to come first.
    if user.quota_reset_at is None or user.quota_reset_at < today:
        user.pages_used_today = 0
        user.quota_reset_at = today

    if user.pages_used_today + pages > settings.DAILY_PAGES_PER_USER:
        return texts.LIMIT_PAGES

    return None


async def consume(session: AsyncSession, user: User, pages: int) -> None:
    """Add `pages` to the user's daily counter. Called only after the record
    has been saved — step 14. No row lock on the user: for a single user the
    worst case is one page double-counted (PLAN.md -> Known risks)."""
    user.pages_used_today += pages


async def _spent_today_usd(session: AsyncSession, today: date) -> float:
    """Sum of ai_calls.cost_usd since 00:00 UTC today. Rows with cost_usd NULL
    are skipped by SUM; SUM over zero rows is NULL, coalesced to 0.0."""
    day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    stmt = select(func.coalesce(func.sum(AiCall.cost_usd), 0.0)).where(
        AiCall.created_at >= day_start
    )
    return float((await session.execute(stmt)).scalar_one())
