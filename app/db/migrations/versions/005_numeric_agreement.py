"""numeric agreement

Revision ID: 005_numeric_agreement
Revises: 004_margin_notes
Create Date: 2026-09-22

The runs have been compared by their numbers since the verdict learned to
hear them, but the number itself only ever reached the log. Comparing two
prompts against the same album is then a grep through Railway's logs, which
roll off, instead of a query against rows that do not.

Nullable with no default: records written before this migration were not
measured this way, and a zero would read as perfect disagreement. `.docx`
records have no runs to compare at all and keep NULL for ever.

"""

import sqlalchemy as sa
from alembic import op

revision = "005_numeric_agreement"
down_revision = "004_margin_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("numeric_agreement", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("notes", "numeric_agreement")
