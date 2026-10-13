"""a subject's whole semester, kept

Revision ID: 024_semester
Revises: 023_notebook
Create Date: 2026-10-13

Task 63, the CEO's of 2026-10-12 and 2026-10-13: «Весь семестр одним PDF»
under the list a subject's "#word" answers with — every lecture's text set
out by the semester's topics, a study version of the whole subject.

subjects.semester: its arrangement — the topics, their units through the
    semester, the questions — and the fingerprint of the lectures it was
    built from, as a lecture's study version is kept on its base
    (notes.study). A second press draws it again and pays nothing; a lecture
    added and it is built again. NULL until the first press.

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "024_semester"
down_revision = "023_notebook"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subjects", sa.Column("semester", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("subjects", "semester")
