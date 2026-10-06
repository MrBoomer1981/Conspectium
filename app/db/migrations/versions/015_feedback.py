"""feedback

Revision ID: 015_feedback
Revises: 014_subjects_lectures
Create Date: 2026-10-06

Task 70, as the CEO decided it on 2026-10-06: «Хорошо» and «Плохо» under
every document, and after «Плохо» the reader's own words on where the error
is — so the records' faults are read off the groups.

feedback: one row a person a record — its rating, the reader's words, the
    chat (Telegram's id) and the bot's question «что не так», which the
    reply to it finds the row by.

"""

import sqlalchemy as sa
from alembic import op

revision = "015_feedback"
down_revision = "014_subjects_lectures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("prompt_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_feedback_note_user", "feedback", ["note_id", "user_id"], unique=True
    )
    op.create_index(
        "ix_feedback_prompt", "feedback", ["chat_id", "prompt_message_id"]
    )
    op.create_index("ix_feedback_group_id", "feedback", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_group_id", table_name="feedback")
    op.drop_index("ix_feedback_prompt", table_name="feedback")
    op.drop_index("ix_feedback_note_user", table_name="feedback")
    op.drop_table("feedback")
