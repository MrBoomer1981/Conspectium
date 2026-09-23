"""unverified pages

Revision ID: 009_unverified_pages
Revises: 008_missing_pages
Create Date: 2026-09-23

A page whose runs disagreed badly, or which only one run came back for, used
to be thrown away — and with it, until 008, the whole album. Looking at the
photographs behind those refusals the author said the plainest thing that could
be said about them: the text on them is perfectly legible. They are kept now
and marked instead, and this column is what the document's box and the chat
message are both built from.

[{"page": 3, "reason": "прогоны распознавания сильно разошлись"}]

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "009_unverified_pages"
down_revision = "008_missing_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notes",
        sa.Column(
            "unverified_pages",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("notes", "unverified_pages")
