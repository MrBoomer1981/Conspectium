"""thinking tokens

Revision ID: 006_tokens_thought
Revises: 005_numeric_agreement
Create Date: 2026-09-23

`tokens_out` stores `candidates_token_count` — the visible answer. A thinking
model spends `thoughts_token_count` out of the same `max_output_tokens`, and
that is where an 8192 ceiling was actually being reached: a call finished with
`finish_reason=MAX_TOKENS` while the column said 498. Every truncated call
looked innocent in this table, and a query over three days read as proof that
the ceiling was not the problem.

Nullable: a model that does not think reports nothing, and rows written before
this migration were not measured. Zero would be a claim.

"""

import sqlalchemy as sa
from alembic import op

revision = "006_tokens_thought"
down_revision = "005_numeric_agreement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_calls", sa.Column("tokens_thought", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_calls", "tokens_thought")
