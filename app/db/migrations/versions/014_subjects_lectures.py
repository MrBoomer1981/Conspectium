"""subjects and lectures

Revision ID: 014_subjects_lectures
Revises: 013_note_figures
Create Date: 2026-10-04

Task 63, the subject's base, as the CEO decided it on 2026-10-04: a chat's
"#word" becomes a row of its own, a lecture is one class of it on one day,
and every notebook of that class — a classmate's too — points at it.

subjects: a chat's subject — its group, or in a private chat its user — and
    its word, unique in that chat.
lectures: a subject's class on the day it was given (`given_on`), and how
    that day is known (`date_source`: caption, page, sent).
notes.subject_id, notes.lecture_id: where a record is filed.

Today's tags become subjects, and each record filed under one becomes a
lecture of its own on the day it was sent: what joins a lecture is decided
from now on, as a record is filed.

"""

from datetime import timezone

import sqlalchemy as sa
from alembic import op

revision = "014_subjects_lectures"
down_revision = "013_note_figures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("word", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_subjects_group_word", "subjects", ["group_id", "word"], unique=True,
        postgresql_where=sa.text("group_id IS NOT NULL"),
    )
    op.create_index(
        "ix_subjects_user_word", "subjects", ["user_id", "word"], unique=True,
        postgresql_where=sa.text("group_id IS NULL"),
    )

    op.create_table(
        "lectures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False
        ),
        sa.Column("given_on", sa.Date(), nullable=False),
        sa.Column("date_source", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_lectures_subject_given", "lectures", ["subject_id", "given_on"]
    )

    op.add_column(
        "notes",
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=True),
    )
    op.add_column(
        "notes",
        sa.Column("lecture_id", sa.Integer(), sa.ForeignKey("lectures.id"), nullable=True),
    )
    op.create_index("ix_notes_subject_id", "notes", ["subject_id"])
    op.create_index("ix_notes_lecture_id", "notes", ["lecture_id"])

    op.execute(
        "INSERT INTO subjects (group_id, word) "
        "SELECT DISTINCT group_id, tag FROM notes "
        "WHERE tag IS NOT NULL AND group_id IS NOT NULL"
    )
    op.execute(
        "INSERT INTO subjects (user_id, word) "
        "SELECT DISTINCT user_id, tag FROM notes "
        "WHERE tag IS NOT NULL AND group_id IS NULL"
    )
    op.execute(
        "UPDATE notes SET subject_id = subjects.id FROM subjects "
        "WHERE notes.tag = subjects.word AND ("
        "(notes.group_id IS NOT NULL AND subjects.group_id = notes.group_id) OR "
        "(notes.group_id IS NULL AND subjects.group_id IS NULL "
        "AND subjects.user_id = notes.user_id))"
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, subject_id, created_at FROM notes "
            "WHERE subject_id IS NOT NULL ORDER BY id"
        )
    ).fetchall()
    for note_id, subject_id, created_at in rows:
        lecture_id = bind.execute(
            sa.text(
                "INSERT INTO lectures (subject_id, given_on, date_source) "
                "VALUES (:subject, :day, 'sent') RETURNING id"
            ),
            {"subject": subject_id, "day": created_at.astimezone(timezone.utc).date()},
        ).scalar_one()
        bind.execute(
            sa.text("UPDATE notes SET lecture_id = :lecture WHERE id = :note"),
            {"lecture": lecture_id, "note": note_id},
        )


def downgrade() -> None:
    op.drop_index("ix_notes_lecture_id", table_name="notes")
    op.drop_index("ix_notes_subject_id", table_name="notes")
    op.drop_column("notes", "lecture_id")
    op.drop_column("notes", "subject_id")
    op.drop_index("ix_lectures_subject_given", table_name="lectures")
    op.drop_table("lectures")
    op.drop_index("ix_subjects_user_word", table_name="subjects")
    op.drop_index("ix_subjects_group_word", table_name="subjects")
    op.drop_table("subjects")
