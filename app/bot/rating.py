"""A group's week (tasks 72 and 73): who sent its records and who rated them.

`/stats` in a group shows the week so far, and every Saturday at 10:00
Moscow time each group active in the week just ended gets it summed up in
its chat, unasked. A week runs from Saturday 00:00 UTC to the next: the
summary goes out on Saturday morning, and `/stats` counts the same week, so
the two never show different numbers. A record counts for whoever sent its
pages — `notes.sender_id`, else its user — and an отзыв is a `feedback` row,
one a person a record. Two numbers a person, ordered by records, and nothing
here touches a limit: an отзыв worth pages would be worth faking, and the
отзывы are how a record's errors are found.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from aiogram import Bot
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.events import log_event
from app.db.models import Feedback, Group, Note, User
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)

# The most people a week names; the rest are counted. A course chat's week
# fits in ten, and a phone's screen does not hold thirty lines.
_SHOWN = 10

# Saturday at 10:00 in Moscow, which keeps no summer time: 07:00 UTC. The
# CEO's hour, 2026-10-07.
POST_AT = time(7, 0)

# How often the timer reads the clock: a summary goes out within this of
# POST_AT, and a deploy at that moment delays it by no more.
_TICK_S = 600


@dataclass
class Week:
    # (name, records, отзывы) for everyone with either, in order.
    people: list[tuple[str, int, int]]
    records: int
    ratings: int

    @property
    def shown(self) -> list[tuple[str, int, int]]:
        return self.people[:_SHOWN]

    @property
    def more(self) -> int:
        return max(len(self.people) - _SHOWN, 0)


def week_start(day: date) -> date:
    """The Saturday the week holding `day` began on."""
    return day - timedelta(days=(day.weekday() - 5) % 7)


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def _name(user: User) -> str:
    """A person as the group knows them: their username, the CEO's choice,
    without the @ that would notify them every time the week is shown; their
    first name when they have no username."""
    return user.username or user.first_name or "без имени"


async def tally(session: AsyncSession, group_id: int, since: date, until: date) -> Week:
    """The group's records and отзывы from `since` up to `until`, by person."""
    start, end = _midnight(since), _midnight(until)
    sender = func.coalesce(Note.sender_id, Note.user_id)
    records = dict(
        (
            await session.execute(
                select(sender, func.count())
                .where(
                    Note.group_id == group_id,
                    Note.created_at >= start,
                    Note.created_at < end,
                )
                .group_by(sender)
            )
        ).all()
    )
    ratings = dict(
        (
            await session.execute(
                select(Feedback.user_id, func.count())
                .where(
                    Feedback.group_id == group_id,
                    Feedback.created_at >= start,
                    Feedback.created_at < end,
                )
                .group_by(Feedback.user_id)
            )
        ).all()
    )
    ids = set(records) | set(ratings)
    users = (
        (await session.execute(select(User).where(User.id.in_(ids)).order_by(User.id)))
        .scalars()
        .all()
        if ids
        else []
    )
    people = [
        (_name(user), records.get(user.id, 0), ratings.get(user.id, 0)) for user in users
    ]
    people.sort(key=lambda person: (-person[1], -person[2], person[0].lower()))
    return Week(people, sum(records.values()), sum(ratings.values()))


async def stats(session: AsyncSession, group: Group) -> str | None:
    """`/stats` in a group: the week so far and the group's all time, or None
    for a group with neither a record nor an отзыв."""
    all_records = (
        await session.execute(
            select(func.count()).select_from(Note).where(Note.group_id == group.id)
        )
    ).scalar_one()
    all_ratings = (
        await session.execute(
            select(func.count()).select_from(Feedback).where(Feedback.group_id == group.id)
        )
    ).scalar_one()
    if not all_records and not all_ratings:
        return None
    since = week_start(datetime.now(timezone.utc).date())
    week = await tally(session, group.id, since, since + timedelta(days=7))
    return texts.group_week(
        group.title,
        since,
        week.records,
        week.ratings,
        week.shown,
        week.more,
        all_records,
        all_ratings,
    )


async def saturdays(bot: Bot) -> None:
    """The bot's one timer (task 73), started with the process: it reads the
    clock every ten minutes and sends the summaries that are due. A restart
    on Saturday neither loses them nor sends them twice — what was sent is
    on the groups' rows."""
    while True:
        try:
            await post_due(bot)
        except Exception:
            logger.exception("the week's summaries failed")
        await asyncio.sleep(_TICK_S)


async def post_due(bot: Bot, now: datetime | None = None) -> int:
    """From Saturday's POST_AT to that day's end, the week just ended summed
    up in the chat of every group with a record or an отзыв in it, each
    once. How many went out."""
    now = now or datetime.now(timezone.utc)
    if now.weekday() != 5 or now.time() < POST_AT:
        return 0
    until = now.date()
    since = until - timedelta(days=7)
    start, end = _midnight(since), _midnight(until)
    active = (
        select(Note.group_id)
        .where(Note.group_id.is_not(None), Note.created_at >= start, Note.created_at < end)
        .union(
            select(Feedback.group_id).where(
                Feedback.group_id.is_not(None),
                Feedback.created_at >= start,
                Feedback.created_at < end,
            )
        )
    )
    async with async_session_maker() as session:
        due = (
            (
                await session.execute(
                    select(Group.id).where(
                        Group.id.in_(active),
                        or_(Group.rating_week.is_(None), Group.rating_week < until),
                    )
                )
            )
            .scalars()
            .all()
        )
    sent = 0
    for group_id in due:
        sent += await _post(bot, group_id, since, until)
    return sent


async def _post(bot: Bot, group_id: int, since: date, until: date) -> int:
    async with async_session_maker() as session:
        # Claimed on the group's row, and committed before anything is sent:
        # of two timers at once — a deploy's old process and its new one —
        # one updates the row, the other finds the week taken, and a summary
        # goes out once at most.
        claimed = await session.execute(
            update(Group)
            .where(
                Group.id == group_id,
                or_(Group.rating_week.is_(None), Group.rating_week < until),
            )
            .values(rating_week=until)
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            return 0
        week = await tally(session, group_id, since, until)
        chat_id = (
            await session.execute(select(Group.tg_chat_id).where(Group.id == group_id))
        ).scalar_one()
        await session.commit()
    if not week.people:
        return 0
    try:
        # No topic named: in a group divided into topics it is the general
        # one, the bot keeping none yet (task 66).
        await bot.send_message(
            chat_id,
            texts.week_summary(
                since,
                until - timedelta(days=1),
                week.records,
                week.ratings,
                week.shown,
                week.more,
            ),
        )
    except Exception:
        logger.warning(
            "the week's summary could not be sent to group %s", group_id, exc_info=True
        )
        return 0
    async with async_session_maker() as session:
        await log_event(
            session,
            None,
            "rating_posted",
            {
                "week": since.isoformat(),
                "records": week.records,
                "feedback": week.ratings,
                "people": len(week.people),
            },
            group_id=group_id,
        )
        await session.commit()
    return 1
