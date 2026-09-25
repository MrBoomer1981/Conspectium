"""groups

Revision ID: 011_groups
Revises: 010_explanations
Create Date: 2026-09-25

Phase C: the bot lives in a course chat, and a record made there belongs to
the chat rather than to whoever photographed it — any member finds it by a
"#word" in that chat.

groups: one row per group chat, keyed by our own id, because Telegram's chat
    id changes when a group becomes a supergroup and the row is what moves
notes.group_id: the chat that owns the record; NULL for a record made in a
    private chat, which stays its photographer's
events.group_id: the chat an event happened in, so that whether a group uses
    the bot week after week can be counted rather than guessed

"""

import sqlalchemy as sa
from alembic import op

revision = "011_groups"
down_revision = "010_explanations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tg_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_groups_tg_chat_id", "groups", ["tg_chat_id"], unique=True)

    op.add_column(
        "notes",
        sa.Column(
            "group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=True
        ),
    )
    op.create_index("ix_notes_group_id", "notes", ["group_id"])

    op.add_column(
        "events",
        sa.Column(
            "group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=True
        ),
    )
    op.create_index("ix_events_group_id", "events", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_events_group_id", table_name="events")
    op.drop_column("events", "group_id")
    op.drop_index("ix_notes_group_id", table_name="notes")
    op.drop_column("notes", "group_id")
    op.drop_index("ix_groups_tg_chat_id", table_name="groups")
    op.drop_table("groups")
