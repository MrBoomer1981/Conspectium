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
    text_agreement: Mapped[float | None] = mapped_column(Float)
    photo_sharpness: Mapped[float | None] = mapped_column(Float)
    photo_line_height: Mapped[float | None] = mapped_column(Float)
    photo_paper_fraction: Mapped[float | None] = mapped_column(Float)
    photo_contrast: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
