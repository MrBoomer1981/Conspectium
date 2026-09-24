"""explanations and summary

Revision ID: 010_explanations
Revises: 009_unverified_pages
Create Date: 2026-09-24

Stage three: what the bot adds of its own to a record — hard places
explained, each with the sources the search gave for it, and the record summed
up. Kept in columns of their own and never mixed into `markdown`: the
document prints them as the bot's, and a reader has to be able to tell an
explanation from what the author wrote.

explanations: [{"anchor": "...", "title": "...", "text": "...",
                "sources": [{"title": "...", "uri": "..."}]}]
summary: the summary, or NULL when there is none

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "010_explanations"
down_revision = "009_unverified_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notes",
        sa.Column(
            "explanations",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column("notes", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("notes", "summary")
    op.drop_column("notes", "explanations")
