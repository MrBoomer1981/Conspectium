"""note_figures

Revision ID: 013_note_figures
Revises: 012_group_pages
Create Date: 2026-10-01

Task 54, as the CEO decided it on 2026-10-01 after record 59 printed nine
drawings as nine sentences: a drawing is cut out of the page it was drawn on
and set in the document.

note_figures: a record's drawings, each the darkness of its ink cut out of
    the photograph — never the photograph — as a greyscale PNG, numbered as
    "[рисунок N: …]" numbers it in the record's markdown. Rule 3 changed with
    it: the drawing is kept, so a record a "#word" brings back keeps it too.

"""

import sqlalchemy as sa
from alembic import op

revision = "013_note_figures"
down_revision = "012_group_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "note_figures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("png", sa.LargeBinary(), nullable=False),
    )
    op.create_index("ix_note_figures_note_id", "note_figures", ["note_id"])


def downgrade() -> None:
    op.drop_index("ix_note_figures_note_id", table_name="note_figures")
    op.drop_table("note_figures")
