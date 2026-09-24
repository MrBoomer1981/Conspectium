"""Database models."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String)
    first_name: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    pages_used_today: Mapped[int] = mapped_column(Integer, server_default="0")
    # The UTC day the counter above was computed for.
    quota_reset_at: Mapped[date | None] = mapped_column(Date)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class AiCall(Base):
    __tablename__ = "ai_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String)  # "transcribe"
    model: Mapped[str] = mapped_column(String)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    tokens_thought: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    latency_ms: Mapped[int] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    subject: Mapped[str | None] = mapped_column(String)
    markdown: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String)  # "photo" | "docx"
    page_count: Mapped[int] = mapped_column(Integer, server_default="1")
    status: Mapped[str] = mapped_column(String)  # "ready" | "needs_review"
    # Dataclasses (Uncertain, Issue, Divergence) are turned into plain dicts
    # with dataclasses.asdict before they reach these columns.
    margin_notes: Mapped[list] = mapped_column(JSONB, server_default="[]")
    uncertain: Mapped[list] = mapped_column(JSONB, server_default="[]")
    issues: Mapped[list] = mapped_column(JSONB, server_default="[]")
    numeric_divergences: Mapped[list] = mapped_column(JSONB, server_default="[]")
    unreadable_count: Mapped[int] = mapped_column(Integer, server_default="0")
    # The pages of the album that could not be read, by number. A record used
    # to be all its pages or none, so this was always empty by construction;
    # now the record is delivered with the hole named in it, and the document
    # and the chat both read this column rather than counting anything.
    missing_pages: Mapped[list] = mapped_column(JSONB, server_default="[]")
    # Pages that are in the record but were not confirmed by a second reading:
    # the runs disagreed badly, or only one of them came back. They used to be
    # dropped, which cost the page and often the album, while the text on them
    # was legible. [{"page": n, "reason": "..."}]
    unverified_pages: Mapped[list] = mapped_column(JSONB, server_default="[]")
    # What the bot added of its own, kept apart from the author's text so the
    # document can print it as the bot's: hard places explained, each with
    # the sources the search gave for it, and the record summed up.
    # [{"anchor": "...", "title": "...", "text": "...",
    #   "sources": [{"title": "...", "uri": "..."}]}]
    explanations: Mapped[list] = mapped_column(JSONB, server_default="[]")
    summary: Mapped[str | None] = mapped_column(Text)
    text_agreement: Mapped[float | None] = mapped_column(Float)
    numeric_agreement: Mapped[float | None] = mapped_column(Float)
    # The subject the user answered with when the bot asked, stored without
    # its "#". NULL means the question has not been answered yet, and that is
    # what tells the next "#word" from this user to tag rather than to search.
    tag: Mapped[str | None] = mapped_column(String, index=True)
    photo_sharpness: Mapped[float | None] = mapped_column(Float)
    photo_line_height: Mapped[float | None] = mapped_column(Float)
    photo_paper_fraction: Mapped[float | None] = mapped_column(Float)
    photo_contrast: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class NoteTopic(Base):
    """A topic the bot derived from a record's own headings.

    A row per topic rather than a JSONB list on `Note`, because the question
    asked of it is "which records carry this topic" — a join on an indexed
    column, which reads the same on PostgreSQL and on the SQLite the suite
    runs against. JSONB containment would be neither indexable here nor
    expressible there.

    Kept apart from `Note.tag` for the reason this project keeps everything
    machine-written apart from everything a person wrote: the subject is the
    user's answer, these are the bot's reading of the record, and a table they
    do not share is the cheapest way to never confuse the two.
    """

    __tablename__ = "note_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"), index=True
    )
    topic: Mapped[str] = mapped_column(String, index=True)
