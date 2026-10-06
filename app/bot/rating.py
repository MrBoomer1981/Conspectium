"""A group's week (task 72): who sent its records and who rated them.

`/stats` in a group shows the week so far; the week before is summed up in
the chat, unasked, after the group's first record of a new week. A week runs
from Monday 00:00 UTC, as every day here is counted. A record counts for
whoever sent its pages — `notes.sender_id`, else its user — and an отзыв is a
`feedback` row, one a person a record. Two numbers a person, ordered by
records, and nothing here touches a limit: an отзыв worth pages would be
worth faking, and the отзывы are how a record's errors are found.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from aiogram.types import Message
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.events import log_event
from app.db.models import Feedback, Group, Note, User

logger = logging.getLogger(__name__)

# The most people a week names; the rest are counted. A course chat's week
# fits in ten, and a phone's screen does not hold thirty lines.
_SHOWN = 10


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


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


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
    this_week = monday(datetime.now(timezone.utc).date())
    week = await tally(session, group.id, this_week, this_week + timedelta(days=7))
    return texts.group_week(
        group.title,
        week.records,
        week.ratings,
        week.shown,
        week.more,
        all_records,
        all_ratings,
    )


async def after_record(
    message: Message, session: AsyncSession, user: User, group: Group | None
) -> None:
    """After a group's record, the week before summed up — by the first
    record of a week, once. Nothing of it costs the record: its queries run in
    savepoints, and whatever fails is a warning in the log."""
    if group is None:
        return
    this_week = monday(datetime.now(timezone.utc).date())
    last_week = this_week - timedelta(days=7)
    try:
        # The week is claimed on the group's row. Of two records at once one
        # updates it; the other waits on the row and finds the week taken.
        async with session.begin_nested():
            claimed = await session.execute(
                update(Group)
                .where(
                    Group.id == group.id,
                    or_(Group.rating_week.is_(None), Group.rating_week < this_week),
                )
                .values(rating_week=this_week)
                .execution_options(synchronize_session=False)
            )
        if claimed.rowcount != 1:
            return
        # Claimed before it is counted: a summary that fails is not tried
        # again on every record of the week.
        async with session.begin_nested():
            week = await tally(session, group.id, last_week, this_week)
        if not week.people:
            return
        await message.answer(
            texts.week_summary(
                last_week,
                this_week - timedelta(days=1),
                week.records,
                week.ratings,
                week.shown,
                week.more,
            )
        )
    except Exception:
        logger.warning("the week's summary failed in group %s", group.id, exc_info=True)
        return
    await log_event(
        session,
        user.id,
        "rating_posted",
        {
            "week": last_week.isoformat(),
            "records": week.records,
            "feedback": week.ratings,
            "people": len(week.people),
        },
        group_id=group.id,
    )
