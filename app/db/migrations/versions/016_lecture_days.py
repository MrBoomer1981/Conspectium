"""lecture days a margin could not have given

Revision ID: 016_lecture_days
Revises: 015_feedback
Create Date: 2026-10-06

Task 71. A margin's day after the day its pages came was taken for last
year's: «10 ноября» in the margin of a notebook sent on 6 October 2026 dated
record 79's lecture 10.11.2025. Such a day dates nothing now, and the lecture
takes the day it was sent (subjects._day). This puts the lectures filed by
the old rule where the new one would have: every lecture dated by a page is
read again from its notebooks' margins, and one that no margin dates any
more takes the day its first notebook was sent.

The reading of a margin is copied here rather than imported from
app.bot.subjects: a migration has to do tomorrow what it does today.

Nothing to undo: the old dates were the error.
"""

import json
import re
from datetime import date, datetime, timedelta, timezone

import sqlalchemy as sa
from alembic import op

revision = "016_lecture_days"
down_revision = "015_feedback"
branch_labels = None
depends_on = None

_MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
_NUMERIC_DAY = r"(\d{1,2})[./](\d{1,2})(?:[./](\d{4}|\d{2}))?\.?"
_WORDED_DAY = rf"(\d{{1,2}})\s+({'|'.join(_MONTHS)})(?:\s+(\d{{4}}))?"
_DAY_ALONE_RE = re.compile(rf"^(?:{_NUMERIC_DAY}|{_WORDED_DAY})$", re.IGNORECASE)
_MARGIN_SEPARATOR_RE = re.compile(r"\s*[·,;]\s*")


def _sent(stamp: datetime | date) -> date:
    if not isinstance(stamp, datetime):
        return stamp
    if stamp.tzinfo is None:
        return stamp.date()
    return stamp.astimezone(timezone.utc).date()


def _page_day(found: re.Match, sent: date) -> date | None:
    """A margin's day by the rule of task 71: in the year written or the year
    the pages came, and nothing after them."""
    numeric_day, numeric_month, numeric_year, worded_day, month_name, worded_year = (
        found.groups()
    )
    if numeric_day:
        day, month, year = int(numeric_day), int(numeric_month), numeric_year
    else:
        day = int(worded_day)
        month = _MONTHS.index(month_name.lower()) + 1
        year = worded_year
    try:
        if year:
            value = int(year)
            given = date(value + 2000 if value < 100 else value, month, day)
        else:
            given = date(sent.year, month, day)
    except ValueError:
        return None
    return None if given > sent + timedelta(days=1) else given


def _margin_day(margin_notes, sent: date) -> date | None:
    """The one day a notebook's margin names, or None."""
    if isinstance(margin_notes, str):
        margin_notes = json.loads(margin_notes)
    days = set()
    for note in margin_notes or []:
        for part in _MARGIN_SEPARATOR_RE.split(str(note).strip()):
            found = _DAY_ALONE_RE.match(part)
            given = _page_day(found, sent) if found else None
            if given is not None:
                days.add(given)
    return days.pop() if len(days) == 1 else None


def upgrade() -> None:
    bind = op.get_bind()
    lectures = bind.execute(
        sa.text("SELECT id, given_on FROM lectures WHERE date_source = 'page'")
    ).fetchall()
    for lecture_id, given_on in lectures:
        notebooks = bind.execute(
            sa.text(
                "SELECT margin_notes, created_at FROM notes "
                "WHERE lecture_id = :lecture ORDER BY id"
            ),
            {"lecture": lecture_id},
        ).fetchall()
        if not notebooks:
            continue
        days = [
            day
            for margin_notes, created_at in notebooks
            if (day := _margin_day(margin_notes, _sent(created_at))) is not None
        ]
        if given_on in days:
            continue  # a margin still names it
        if days:
            day, source = days[0], "page"
        else:
            day, source = _sent(notebooks[0][1]), "sent"
        bind.execute(
            sa.text(
                "UPDATE lectures SET given_on = :day, date_source = :source "
                "WHERE id = :lecture"
            ),
            {"day": day, "source": source, "lecture": lecture_id},
        )


def downgrade() -> None:
    pass
