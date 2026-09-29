"""group_pages

Revision ID: 012_group_pages
Revises: 011_groups
Create Date: 2026-09-29

Task 40, as the author decided it on 2026-09-29: in a course chat a classmate
replies "#матан" to a photo or an album somebody else sent, and the bot makes
the chat's record of it.

group_pages: the pages of the albums posted in a group, as Telegram's
    reference to each photo — never the photo itself. A reply points at one
    page of an album, and these are how the bot finds the rest. Kept 7 days.
notes.source_key: what a record was made of, "album:<media group>" or
    "msg:<message id>", so a second call on the same pages sends the record
    already made instead of paying for it again

"""

import sqlalchemy as sa
from alembic import op

revision = "012_group_pages"
down_revision = "011_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False
        ),
        sa.Column("media_group_id", sa.String(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_group_pages_album", "group_pages", ["group_id", "media_group_id"]
    )
    op.create_index("ix_group_pages_created_at", "group_pages", ["created_at"])

    op.add_column("notes", sa.Column("source_key", sa.String(), nullable=True))
    op.create_index("ix_notes_source_key", "notes", ["source_key"])


def downgrade() -> None:
    op.drop_index("ix_notes_source_key", table_name="notes")
    op.drop_column("notes", "source_key")
    op.drop_index("ix_group_pages_created_at", table_name="group_pages")
    op.drop_index("ix_group_pages_album", table_name="group_pages")
    op.drop_table("group_pages")
