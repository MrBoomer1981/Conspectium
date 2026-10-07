"""spend counted per group: the group a model call was made for

Revision ID: 018_ai_calls_group
Revises: 017_rating
Create Date: 2026-10-07

Task 41, as the CEO decided it on 2026-10-07: a group's day is counted in
pages, from its records, and what a group costs is read off its calls.

ai_calls.group_id: the group chat a call was made for, NULL in a private
    chat. The rows written before it stay NULL: which group a call was for
    was not kept, and the records it was made for do not say which of their
    calls were theirs.

"""

import sqlalchemy as sa
from alembic import op

revision = "018_ai_calls_group"
down_revision = "017_rating"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_calls",
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=True),
    )
    op.create_index("ix_ai_calls_group_id", "ai_calls", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_calls_group_id", table_name="ai_calls")
    op.drop_column("ai_calls", "group_id")
