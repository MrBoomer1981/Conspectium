"""check_limits / consume — the money-critical path (PLAN.md task 8).

Runs on in-memory SQLite: the checks touch only `users` and `ai_calls`, never
JSONB or `notes`, so SQLite behaves exactly like Postgres here — SUM,
COALESCE, the NULL-cost exclusion and the UTC day boundary all included.
"""

from datetime import date, datetime, timedelta, timezone

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.bot import texts
from app.core.config import settings
from app.db.models import AiCall, Base, User
from app.services import limits


@pytest_asyncio.fixture
async def session():
    # StaticPool + a single shared connection: otherwise every checkout gets a
    # fresh, empty :memory: database and the created tables vanish.
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[User.__table__, AiCall.__table__],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def _add_user(session, **overrides) -> User:
    fields = dict(tg_id=1, pages_used_today=0, quota_reset_at=_today())
    fields.update(overrides)
    user = User(**fields)
    session.add(user)
    await session.flush()
    return user


async def _add_ai_call(session, cost_usd, when=None) -> None:
    session.add(
        AiCall(
            kind="transcribe",
            model="gemini-2.5-flash-lite",
            cost_usd=cost_usd,
            latency_ms=1000,
            success=cost_usd is not None,
            created_at=when or datetime.now(timezone.utc),
        )
    )
    await session.flush()


async def test_under_the_limit_passes(session):
    user = await _add_user(session, pages_used_today=10)
    assert await limits.check_limits(session, user, pages=1) is None


async def test_exactly_at_the_limit_passes(session):
    # used + pages == cap is allowed; only strictly over is refused.
    user = await _add_user(
        session, pages_used_today=settings.DAILY_PAGES_PER_USER - 1
    )
    assert await limits.check_limits(session, user, pages=1) is None


async def test_over_the_limit_refused(session):
    user = await _add_user(
        session, pages_used_today=settings.DAILY_PAGES_PER_USER
    )
    assert await limits.check_limits(session, user, pages=1) == texts.LIMIT_PAGES


async def test_new_user_quota_reset_at_none(session):
    user = await _add_user(session, quota_reset_at=None, pages_used_today=0)
    assert await limits.check_limits(session, user, pages=1) is None
    assert user.quota_reset_at == _today()


async def test_counter_resets_on_a_new_day(session):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    user = await _add_user(
        session,
        quota_reset_at=yesterday,
        pages_used_today=settings.DAILY_PAGES_PER_USER,
    )
    assert await limits.check_limits(session, user, pages=1) is None
    assert user.pages_used_today == 0
    assert user.quota_reset_at == _today()


async def test_ai_disabled(session, monkeypatch):
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    user = await _add_user(session)
    assert await limits.check_limits(session, user, pages=1) == texts.AI_DISABLED


async def test_cost_cap_exceeded(session, monkeypatch):
    monkeypatch.setattr(settings, "DAILY_COST_LIMIT_USD", 1.0)
    user = await _add_user(session)
    await _add_ai_call(session, cost_usd=0.6)
    await _add_ai_call(session, cost_usd=0.6)  # 1.2 >= 1.0
    assert await limits.check_limits(session, user, pages=1) == texts.LIMIT_COST


async def test_cost_none_rows_ignored(session, monkeypatch):
    monkeypatch.setattr(settings, "DAILY_COST_LIMIT_USD", 1.0)
    user = await _add_user(session)
    await _add_ai_call(session, cost_usd=None)  # must not crash or count
    await _add_ai_call(session, cost_usd=None)
    await _add_ai_call(session, cost_usd=0.5)  # real spend, under the cap
    assert await limits.check_limits(session, user, pages=1) is None
