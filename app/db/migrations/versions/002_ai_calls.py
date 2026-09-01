"""ai_calls

Revision ID: 002_ai_calls
Revises: 001_users_events
Create Date: 2026-09-01

"""

import sqlalchemy as sa
from alembic import op

revision = "002_ai_calls"
down_revision = "001_users_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_calls_user_id", "ai_calls", ["user_id"])
    op.create_index("ix_ai_calls_created_at", "ai_calls", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_calls_created_at", table_name="ai_calls")
    op.drop_index("ix_ai_calls_user_id", table_name="ai_calls")
    op.drop_table("ai_calls")
