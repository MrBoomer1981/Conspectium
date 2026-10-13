"""a record moved from a private chat into a group

Revision ID: 022_lecture_moved
Revises: 021_one_lecture
Create Date: 2026-10-13

Task 63, the CEO's of 2026-10-12: a lecture photographed in a private chat
is moved into a group by a button under its document, and is the group's
from then on.

notes.moved_at: when the record was moved, NULL for a record made in its
    chat. Its pages were read and paid for in the private chat, so the
    group's day — the pages of its records made since midnight — does not
    count them (limits.group_pages_left).

"""

import sqlalchemy as sa
from alembic import op

revision = "022_lecture_moved"
down_revision = "021_one_lecture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notes", sa.Column("moved_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("notes", "moved_at")
