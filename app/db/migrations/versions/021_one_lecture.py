"""a lecture one row, however many notebooks of it came

Revision ID: 021_one_lecture
Revises: 020_hashtags
Create Date: 2026-10-12

Task 63, the CEO's of 2026-10-12, «удаление повторов»: a lecture is one row
however many notebooks of it came. A record has joined the lecture its text
is a notebook of as it is filed since 2026-10-04 (subjects._lecture_of);
before, 014_subjects_lectures made every record filed under a subject a
lecture of its own, and an album sent twice stood in its subject's list
twice — in production one page a group sent three days apart.

This files every lecture again by the rule a record is filed by, in the
order the lectures were made: a lecture joins the earlier lecture of its
subject it would join were it filed now — its day within a week of that
one's, never another day when both days were written down, half of one's
text found in the other's — the best of them when several would do. Its
notebooks move there, that lecture takes the better-known of the two days
as filing a notebook gives it, and the emptied row goes. Nothing about a
record changes but the lecture it points at.

The rule is copied here rather than imported from app.services.merge and
app.bot.subjects: a migration has to do tomorrow what it does today. What
it changes is decided by `plan`, apart from the writing, so that it can be
read against a database without writing to it.

Nothing to undo: two rows of one lecture were the error.
"""

import re
from dataclasses import dataclass, field
from datetime import date

import sqlalchemy as sa
from alembic import op

revision = "021_one_lecture"
down_revision = "020_hashtags"
branch_labels = None
depends_on = None

# merge.py on 2026-10-12: a text as the comparison reads it.
_LAYOUT_RE = re.compile(
    r"\\(?:left|right|quad|qquad|displaystyle|text|mathrm|mathbf|boxed"
    r"|big|Big|bigg|Bigg|[,;!:])(?![A-Za-z])"
)
_UNREADABLE_RE = re.compile(r"\[неразборчиво\]")
_DRAWING_RE = re.compile(
    r"\[(?:схема|рисунок|граф|прямая|числовая|ось|отображен)(?:[^\[\]]|\[[^\[\]]*[\])])*\]",
    re.DOTALL,
)
_NOISE_RE = re.compile(r"[\s$*#_`~>{}\\|\-:.,;!?\"«»()\[\]]+")
_INSERT_LINE_RE = re.compile(r"^⟦\+[^⟧]*⟧\s*$", re.MULTILINE)
_RUN = 5
SAME_LECTURE = 0.5
# subjects.py on 2026-10-12: a week either way, and the sources of a day,
# worst first.
_SAME_WEEK_DAYS = 7
_SOURCES = ("sent", "page", "caption")


def _runs(text: str) -> set[str]:
    text = _INSERT_LINE_RE.sub(" ", text)
    text = _DRAWING_RE.sub(" ", _UNREADABLE_RE.sub(" ", _LAYOUT_RE.sub(" ", text)))
    plain = _NOISE_RE.sub("", text).lower()
    return {plain[i : i + _RUN] for i in range(len(plain) - _RUN + 1)}


def _overlap(runs_a: set[str], runs_b: set[str]) -> float:
    if not runs_a or not runs_b:
        return 0.0
    shared = len(runs_a & runs_b)
    return max(shared / len(runs_a), shared / len(runs_b))


@dataclass
class Plan:
    # A lecture filed into another: its id, the other's.
    joined: dict[int, int] = field(default_factory=dict)
    # The day a lecture takes from one filed into it, and how it is known.
    days: dict[int, tuple[date, str]] = field(default_factory=dict)


def plan(lectures, notes) -> Plan:
    """What upgrade() writes, from what it reads: `lectures` as (id,
    subject_id, given_on, date_source) in id order, `notes` as (id,
    lecture_id, markdown) for every record in a lecture."""
    changes = Plan()
    texts: dict[int, list[set[str]]] = {}
    for _, lecture_id, markdown in notes:
        texts.setdefault(lecture_id, []).append(_runs(markdown or ""))

    kept: dict[int, list[int]] = {}
    day_of: dict[int, tuple[date, str]] = {}
    for lecture_id, subject_id, given_on, source in lectures:
        if lecture_id not in texts:
            continue
        best, best_score = None, SAME_LECTURE
        for other in kept.get(subject_id, []):
            day, other_source = day_of[other]
            if abs((given_on - day).days) > _SAME_WEEK_DAYS:
                continue
            if source != "sent" and other_source != "sent" and given_on != day:
                continue
            score = max(_overlap(a, b) for a in texts[lecture_id] for b in texts[other])
            if score >= best_score:
                best, best_score = other, score
        if best is None:
            kept.setdefault(subject_id, []).append(lecture_id)
            day_of[lecture_id] = (given_on, source)
            continue
        changes.joined[lecture_id] = best
        texts[best] = texts[best] + texts[lecture_id]
        if _SOURCES.index(source) > _SOURCES.index(day_of[best][1]):
            day_of[best] = (given_on, source)
            changes.days[best] = (given_on, source)
    return changes


def _each(bind, statement: str, rows: list[dict]) -> None:
    if rows:
        bind.execute(sa.text(statement), rows)


def upgrade() -> None:
    bind = op.get_bind()
    changes = plan(
        bind.execute(
            sa.text("SELECT id, subject_id, given_on, date_source FROM lectures ORDER BY id")
        ).all(),
        bind.execute(
            sa.text(
                "SELECT id, lecture_id, markdown FROM notes "
                "WHERE lecture_id IS NOT NULL ORDER BY id"
            )
        ).all(),
    )
    joined = [{"joined": lecture_id, "kept": kept} for lecture_id, kept in changes.joined.items()]
    _each(bind, "UPDATE notes SET lecture_id = :kept WHERE lecture_id = :joined", joined)
    _each(bind, "DELETE FROM lectures WHERE id = :joined", [{"joined": r["joined"]} for r in joined])
    _each(
        bind,
        "UPDATE lectures SET given_on = :day, date_source = :source WHERE id = :id",
        [
            {"id": lecture_id, "day": day, "source": source}
            for lecture_id, (day, source) in changes.days.items()
        ],
    )


def downgrade() -> None:
    pass
