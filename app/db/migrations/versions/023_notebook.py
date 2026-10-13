"""the whole notebook a record was cut from

Revision ID: 023_notebook
Revises: 022_lecture_moved
Create Date: 2026-10-13

Task 63, the CEO's of 2026-10-12: a whole notebook sent at once in a
private chat is cut into its lectures, each a record of its own.

notes.notebook: the notebook a record was cut from, the same for every
    lecture of it — "notebook:<chat>:<first page's message>" — NULL for a
    record of an album, a photo or a file. The subject asked once files
    every lecture of it, and «Все в группу» moves them all. Indexed: both
    look a notebook up by it.

"""

import sqlalchemy as sa
from alembic import op

revision = "023_notebook"
down_revision = "022_lecture_moved"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("notebook", sa.String(), nullable=True))
    op.create_index("ix_notes_notebook", "notes", ["notebook"])


def downgrade() -> None:
    op.drop_index("ix_notes_notebook", table_name="notes")
    op.drop_column("notes", "notebook")
