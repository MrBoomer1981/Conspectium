"""missing pages

Revision ID: 008_missing_pages
Revises: 007_tags_and_topics
Create Date: 2026-09-23

A record used to be all its pages or none: an album with one unreadable page
was thrown away whole, and on 2026-09-23 that cost two five-page albums in one
evening over a single page each. It is delivered now with the hole named in
the document at the position the page would have had, and `notes.missing_pages`
is what both the document and the chat read, so they cannot come to disagree.

Empty for every record made before this, which is true: those albums either
had all their pages or were never saved.

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008_missing_pages"
down_revision = "007_tags_and_topics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notes",
        sa.Column(
            "missing_pages",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("notes", "missing_pages")
