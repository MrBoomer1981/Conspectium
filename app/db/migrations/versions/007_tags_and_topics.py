"""tags and topics

Revision ID: 007_tags_and_topics
Revises: 006_tokens_thought
Create Date: 2026-09-23

One route through the product: photograph a page, answer which subject it
belongs to, find it again by the name of a topic. `notes.tag` holds the
subject the user answered with; `note_topics` holds the topics the bot read
off the record's own headings.

`notes.tag` is nullable and that is load-bearing rather than lenient: a record
with no tag is one whose question has not been answered, which is how the next
"#word" from that user is told from a search.

"""

import sqlalchemy as sa
from alembic import op

revision = "007_tags_and_topics"
down_revision = "006_tokens_thought"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("tag", sa.String(), nullable=True))
    op.create_index("ix_notes_tag", "notes", ["tag"])
    op.create_table(
        "note_topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(), nullable=False),
    )
    op.create_index("ix_note_topics_note_id", "note_topics", ["note_id"])
    op.create_index("ix_note_topics_topic", "note_topics", ["topic"])


def downgrade() -> None:
    op.drop_table("note_topics")
    op.drop_index("ix_notes_tag", table_name="notes")
    op.drop_column("notes", "tag")
