"""a group's week: who sent a record, and the summary's week

Revision ID: 017_rating
Revises: 016_lecture_days
Create Date: 2026-10-06

Task 72, as the CEO decided it on 2026-10-06: a group sees who sent its
records and who rated them, in /stats and in the week's summary posted with
the first record of the next.

notes.sender_id: whose message carried the pages, when that is not the
    record's user — a reply's "#word" under a classmate's photographs, which
    the replier pays for and the photographer is counted for. NULL: the
    record's user. The records called on before it stay NULL: who sent their
    photographs was not kept.
groups.rating_week: the Monday of the week the group's last summary went
    out in, NULL before the first.

"""

import sqlalchemy as sa
from alembic import op

revision = "017_rating"
down_revision = "016_lecture_days"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notes",
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("groups", sa.Column("rating_week", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("groups", "rating_week")
    op.drop_column("notes", "sender_id")
