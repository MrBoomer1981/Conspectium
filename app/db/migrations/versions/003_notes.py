"""notes

Revision ID: 003_notes
Revises: 002_ai_calls
Create Date: 2026-09-02

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003_notes"
down_revision = "002_ai_calls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("page_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "uncertain",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "issues",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "numeric_divergences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "unreadable_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("text_agreement", sa.Float(), nullable=True),
        sa.Column("photo_sharpness", sa.Float(), nullable=True),
        sa.Column("photo_line_height", sa.Float(), nullable=True),
        sa.Column("photo_paper_fraction", sa.Float(), nullable=True),
        sa.Column("photo_contrast", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_user_id", "notes", ["user_id"])
    op.create_index("ix_notes_created_at", "notes", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notes_created_at", table_name="notes")
    op.drop_index("ix_notes_user_id", table_name="notes")
    op.drop_table("notes")
