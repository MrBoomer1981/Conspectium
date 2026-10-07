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

The bot's week (task 74) is the same week across every chat, for whoever
reads the отзывы: `/stats` in the feedback chat.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from aiogram import Bot
from sqlalchemy import ColumnElement, func, or_, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.events import log_event
from app.db.models import AiCall, Feedback, Group, Note, User
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
    return await _tally(
        session, since, until, Note.group_id == group_id, Feedback.group_id == group_id
    )


async def _tally(
    session: AsyncSession,
    since: date,
    until: date,
    notes_in: ColumnElement[bool],
    feedback_in: ColumnElement[bool],
) -> Week:
    """Records and отзывы from `since` up to `until`, by person, of the
    records and the feedback the two conditions take in: one group's, or
    every chat's for the bot's week."""
    start, end = _midnight(since), _midnight(until)
    sender = func.coalesce(Note.sender_id, Note.user_id)
    records = dict(
        (
            await session.execute(
                select(sender, func.count())
                .where(notes_in, Note.created_at >= start, Note.created_at < end)
                .group_by(sender)
            )
        ).all()
    )
    ratings = dict(
        (
            await session.execute(
                select(Feedback.user_id, func.count())
                .where(
                    feedback_in, Feedback.created_at >= start, Feedback.created_at < end
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


# ── The bot's week (task 74) ─────────────────────────────────────────────────

# The most groups and people the bot's week names; the rest are counted. Ten
# groups hold every chat the bot is in today, and fifteen people fit a phone.
_GROUPS_SHOWN = 10
_PEOPLE_SHOWN = 15


@dataclass
class ChatWeek:
    """A group's week as the bot's week shows it, or every private chat's as
    one."""

    title: str | None
    private: bool
    records: int
    pages: int
    people: int
    ratings: int
    spent: float


@dataclass
class BotWeek:
    """Every chat's week so far, and all time."""

    since: date
    records: int
    pages: int
    all_records: int
    senders: int
    raters: int
    users: int
    new_users: int
    good: int
    bad: int
    all_ratings: int
    spent_today: float
    spent_week: float
    spent_all: float
    groups: list[ChatWeek]
    more_groups: int
    private: list[ChatWeek]
    people: list[tuple[str, int, int]]
    more_people: int


async def bot_stats(session: AsyncSession) -> str:
    """`/stats` in the feedback chat (task 74): the whole bot's week so far
    and all time — records, people, отзывы and spend — every chat active in
    the week, and the week's people across every chat. Counted from what is
    stored, as a group's week is; a group's spend from `ai_calls.group_id`,
    which is written since task 41's deploy only."""
    now = datetime.now(timezone.utc)
    since = week_start(now.date())
    start, end = _midnight(since), _midnight(since + timedelta(days=7))
    notes_in = (Note.created_at >= start, Note.created_at < end)
    feedback_in = (Feedback.created_at >= start, Feedback.created_at < end)
    calls_in = (AiCall.created_at >= start, AiCall.created_at < end)
    sender = func.coalesce(Note.sender_id, Note.user_id)
    spent = func.coalesce(func.sum(AiCall.cost_usd), 0.0)

    async def scalar(stmt) -> Any:
        return (await session.execute(stmt)).scalar_one()

    records, pages, senders = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Note.page_count), 0),
                func.count(func.distinct(sender)),
            ).where(*notes_in)
        )
    ).one()
    by_rating = dict(
        (
            await session.execute(
                select(Feedback.rating, func.count())
                .where(*feedback_in)
                .group_by(Feedback.rating)
            )
        ).all()
    )
    groups, private = await _chats(session, notes_in, feedback_in, calls_in)
    everyone = await _tally(session, since, since + timedelta(days=7), true(), true())
    return texts.bot_week(
        BotWeek(
            since=since,
            records=records,
            pages=pages,
            all_records=await scalar(select(func.count()).select_from(Note)),
            senders=senders,
            raters=await scalar(
                select(func.count(func.distinct(Feedback.user_id))).where(*feedback_in)
            ),
            users=await scalar(select(func.count()).select_from(User)),
            new_users=await scalar(
                select(func.count())
                .select_from(User)
                .where(User.created_at >= start, User.created_at < end)
            ),
            good=by_rating.get("good", 0),
            bad=by_rating.get("bad", 0),
            all_ratings=await scalar(select(func.count()).select_from(Feedback)),
            spent_today=await scalar(
                select(spent).where(AiCall.created_at >= _midnight(now.date()))
            ),
            spent_week=await scalar(select(spent).where(*calls_in)),
            spent_all=await scalar(select(spent)),
            groups=groups[:_GROUPS_SHOWN],
            more_groups=max(len(groups) - _GROUPS_SHOWN, 0),
            private=private,
            people=everyone.people[:_PEOPLE_SHOWN],
            more_people=max(len(everyone.people) - _PEOPLE_SHOWN, 0),
        )
    )


async def _chats(
    session: AsyncSession,
    notes_in: tuple[ColumnElement[bool], ...],
    feedback_in: tuple[ColumnElement[bool], ...],
    calls_in: tuple[ColumnElement[bool], ...],
) -> tuple[list[ChatWeek], list[ChatWeek]]:
    """Every chat with a record, an отзыв or a call in the week: the groups by
    records, and the private chats as one, if any. A call counts, so a group
    that only paid for readings that came to nothing is seen too."""
    sender = func.coalesce(Note.sender_id, Note.user_id)
    records = {
        group_id: (count, pages)
        for group_id, count, pages in (
            await session.execute(
                select(
                    Note.group_id,
                    func.count(),
                    func.coalesce(func.sum(Note.page_count), 0),
                )
                .where(*notes_in)
                .group_by(Note.group_id)
            )
        ).all()
    }
    ratings = dict(
        (
            await session.execute(
                select(Feedback.group_id, func.count())
                .where(*feedback_in)
                .group_by(Feedback.group_id)
            )
        ).all()
    )
    spent = dict(
        (
            await session.execute(
                select(AiCall.group_id, func.coalesce(func.sum(AiCall.cost_usd), 0.0))
                .where(*calls_in)
                .group_by(AiCall.group_id)
            )
        ).all()
    )
    people: dict[int | None, set[int]] = defaultdict(set)
    for group_id, person in (
        await session.execute(select(Note.group_id, sender).where(*notes_in).distinct())
    ).all():
        people[group_id].add(person)
    for group_id, person in (
        await session.execute(
            select(Feedback.group_id, Feedback.user_id).where(*feedback_in).distinct()
        )
    ).all():
        people[group_id].add(person)

    active = set(records) | set(ratings) | set(spent)
    ids = active - {None}
    titles = (
        dict(
            (
                await session.execute(
                    select(Group.id, Group.title).where(Group.id.in_(ids))
                )
            ).all()
        )
        if ids
        else {}
    )

    def chat(group_id: int | None) -> ChatWeek:
        count, pages = records.get(group_id, (0, 0))
        return ChatWeek(
            title=titles.get(group_id),
            private=group_id is None,
            records=count,
            pages=pages,
            people=len(people[group_id]),
            ratings=ratings.get(group_id, 0),
            spent=float(spent.get(group_id, 0.0)),
        )

    groups = sorted(
        (chat(group_id) for group_id in ids),
        key=lambda c: (-c.records, -c.ratings, -c.spent, (c.title or "").lower()),
    )
    return groups, [chat(None)] if None in active else []
