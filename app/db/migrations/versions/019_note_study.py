"""a record's study version, kept beside it

Revision ID: 019_note_study
Revises: 018_ai_calls_group
Create Date: 2026-10-08

Task 80, the CEO's of 2026-10-08: a button under the document builds the
lecture's study version — the record set out by topic, the author's text
moved whole, the bot's sections marked, questions to check oneself at the
end — and only when it is pressed.

notes.study: what the call answered, once code has checked it — the topics,
    each with its title, its units of the record by number and what it is
    about, and the questions with their answers. Kept so that a second press
    sends it again and pays nothing. NULL until the first press.

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "019_note_study"
down_revision = "018_ai_calls_group"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notes", sa.Column("study", postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("notes", "study")
