"""margin notes

Revision ID: 004_margin_notes
Revises: 003_notes
Create Date: 2026-09-21

The model has always been asked for `margin_notes` and parse_response has
always read them; until now they were dropped on the floor. Rule 11 of the
prompt routes the lecturer's name, the date and a page number there instead
of into the body of the record, so they need somewhere to live.

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "004_margin_notes"
down_revision = "003_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notes",
        sa.Column(
            "margin_notes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("notes", "margin_notes")
