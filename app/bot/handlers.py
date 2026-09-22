"""Aiogram handlers."""

import asyncio
import logging
import time
from dataclasses import asdict

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import albums, corpus, texts
from app.core.config import settings
from app.core.events import log_event
from app.db.models import Note, User
from app.services import (
    docx,
    graphcheck,
    images,
    limits,
    mathcheck,
    photoguard,
    vision,
)

logger = logging.getLogger(__name__)

router = Router()

# Telegram documents over this size are refused before download.
_MAX_DOCX_BYTES = 5 * 1024 * 1024


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User) -> None:
    await message.answer(texts.START)


@router.message(F.photo)
async def handle_photo(
    message: Message, session: AsyncSession, user: User, bot: Bot
) -> None:
    photo = message.photo[-1]
    # Announced before the download, not after: albums.collect() times the
    # album from here, and a page that takes seconds to fetch must not let the
    # batch close without it (albums.announce explains the rest).
    if message.media_group_id:
        albums.announce(message.media_group_id, message.message_id)

    original = (await bot.download(photo)).read()
    # Resizing a 12-megapixel photo is CPU-bound; on the event loop it would
    # freeze every other page of the same album while it runs.
    compressed = await asyncio.to_thread(
        images.compress, original, settings.IMAGE_MAX_SIDE, settings.IMAGE_QUALITY
    )

    # Step 0: an album arrives as separate messages sharing a media_group_id.
    # Buffer this page and let a single update assemble the whole batch; the
    # individual-photo steps 4-16 below do not run for an album page.
    if message.media_group_id:
        albums.add_page(
            message.media_group_id,
            albums.PageInput(
                data=compressed,
                message_id=message.message_id,
                chat_id=message.chat.id,
                media_group_id=message.media_group_id,
                bytes_before=len(original),
                bytes_after=len(compressed),
                width=photo.width,
                height=photo.height,
            ),
        )
        pages = await albums.collect(message.media_group_id)
        if pages is None:
            return  # another update owns this batch
        await _process_album(message, session, user, pages)
        return

    await log_event(
        session,
        user.id,
        "note_captured",
        {
            "bytes_before": len(original),
            "bytes_after": len(compressed),
            "width": photo.width,
            "height": photo.height,
            "source_type": "photo",
        },
    )

    # Step 4: limits before the frame check and before any model call. With the
    # kill switch off or a cap hit, there's no point asking for a better photo.
    limit_message = await limits.check_limits(session, user, pages=1)
    if limit_message is not None:
        await message.answer(limit_message)
        return

    # The frame is checked before any model call: on a bad shot the model
    # recognises the topic from the heading and produces a plausible
    # retelling instead of failing. Metrics go to the event for every photo,
    # accepted ones included — data for future threshold calibration.
    photo_verdict = photoguard.check_photo_bytes(compressed)
    await log_event(
        session,
        user.id,
        "photo_accepted" if photo_verdict.ok else "photo_rejected",
        {
            "reason": photo_verdict.reason,
            "line_height_px": photo_verdict.line_height_px,
            "sharpness": photo_verdict.sharpness,
            "paper_fraction": photo_verdict.paper_fraction,
            "contrast": photo_verdict.contrast,
        },
    )
    if not photo_verdict.ok:
        await message.answer(photo_verdict.reason)
        return

    await message.answer(texts.PROCESSING)

    started = time.monotonic()  # note_processed.latency_ms: step 7 -> end of 15
    result, stats = await vision.transcribe_consensus(compressed)
    await vision.log_ai_calls(user.id, stats)  # always — the tokens were spent

    if result is None:
        await message.answer(texts.ERROR_GENERIC)
        return
    if result.verdict == "rejected":
        await message.answer(texts.REJECTED_QUALITY)
        return
    if len(result.best.markdown.strip()) < settings.MIN_MARKDOWN_LEN:
        await message.answer(texts.NO_TEXT_FOUND)
        return

    # Step 12: deterministic arithmetic check, no model call. mathcheck compares
    # physical constants against a reference table and checks that chains of
    # equalities converge. Only a "critical" issue downgrades the verdict, and
    # only clean -> needs_review, one way; warnings are shown but leave the
    # status alone. From here result.verdict is the pipeline's final verdict.
    # graphcheck is the same kind of check on a different subject: a matrix
    # against the graph drawn beside it. Its findings join the same list, so
    # they reach the same downgrade, the same event and the same callout.
    report = mathcheck.Report(
        issues=mathcheck.check(result.best.markdown).issues
        + graphcheck.check(result.best.markdown)
    )
    has_critical = any(i.severity == "critical" for i in report.issues)
    if has_critical and result.verdict == "clean":
        result.verdict = "needs_review"
    if report.issues:
        await log_event(
            session,
            user.id,
            "math_issues_found",
            {
                "count": len(report.issues),
                "kinds": [i.kind for i in report.issues],
            },
        )

    # Step 13: persist the record. "rejected" already exited at step 10, so the
    # verdict here is "clean" or "needs_review". Dataclasses are flattened to
    # plain dicts — JSONB won't take them as they are.
    note = Note(
        user_id=user.id,
        title=result.best.title,
        subject=result.best.subject,
        markdown=result.best.markdown,
        source_type="photo",
        page_count=1,
        status="needs_review" if result.verdict == "needs_review" else "ready",
        margin_notes=result.best.margin_notes,
        uncertain=[asdict(u) for u in result.best.uncertain],
        issues=[asdict(i) for i in report.issues],
        numeric_divergences=[asdict(d) for d in result.numeric_divergences],
        unreadable_count=result.best.unreadable_count,
        text_agreement=result.text_agreement,
        photo_sharpness=photo_verdict.sharpness,
        photo_line_height=photo_verdict.line_height_px,
        photo_paper_fraction=photo_verdict.paper_fraction,
        photo_contrast=photo_verdict.contrast,
    )
    session.add(note)

    # Step 14: debit the daily page quota, now that the record is saved.
    await limits.consume(session, user, pages=1)

    # Step 15: processing finished end to end. Transactional — commits with the
    # Note and the quota bump in the main session.
    await log_event(
        session,
        user.id,
        "note_processed",
        {
            "verdict": result.verdict,
            "page_count": 1,
            "source_type": "photo",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "cost_usd": vision.total_cost(stats),
        },
    )

    # Step 16: the record itself goes out as a PDF — recognised notes are full
    # of LaTeX, and a formula reads as noise until it is drawn. The flags
    # follow as a message, as before.
    await session.flush()  # note.id, for the file name and the caption
    await corpus.send_record(message, note)

    # Items 2–5 of the final reply go in one message after the main text: the
    # needs-review flag, what mathcheck found, the numeric divergences between
    # runs, then the spots the model flagged as ambiguous.
    flags: list[str] = []
    if report.issues:
        flags.append(report.render())
    if result.numeric_divergences:
        lines = [texts.DIVERGENCES_HEADER]
        lines += [
            texts.divergence_line(d.context, d.variants)
            for d in result.numeric_divergences
        ]
        flags.append("\n".join(lines))
    if result.best.uncertain:
        lines = [texts.UNCERTAIN_HEADER]
        lines += [texts.uncertain_line(u.text, u.why) for u in result.best.uncertain]
        flags.append("\n".join(lines))

    # The generic line only when there is nothing specific to say: above a list
    # of what actually diverged it repeats that list's own heading.
    if result.verdict == "needs_review" and not flags:
        flags.insert(0, texts.NEEDS_REVIEW)
    if flags:
        await message.answer("\n\n".join(flags))


@router.message(F.document)
async def handle_document(
    message: Message, session: AsyncSession, user: User, bot: Bot
) -> None:
    """.docx only. The text is already machine-readable, so there is no model
    call: no limits are checked and no quota is spent — a Word file is
    processed even with AI_ENABLED=false. Steps 0, 4-10, 12 and 14 are skipped;
    step 11 (empty text) still applies."""
    document = message.document
    name = document.file_name or ""
    if not name.lower().endswith(".docx"):
        await message.answer(texts.DOCX_ONLY)
        return
    if document.file_size and document.file_size > _MAX_DOCX_BYTES:
        await message.answer(texts.FILE_TOO_BIG)
        return

    data = (await bot.download(document)).read()
    await log_event(
        session,
        user.id,
        "note_captured",
        {"bytes_before": len(data), "source_type": "docx"},
    )

    started = time.monotonic()  # note_processed.latency_ms for docx: extraction
    try:
        markdown = docx.extract_markdown(data)
    except Exception:
        logger.exception("docx extraction failed")
        await message.answer(texts.ERROR_GENERIC)
        return
    extract_ms = int((time.monotonic() - started) * 1000)

    if len(markdown.strip()) < settings.MIN_MARKDOWN_LEN:
        await message.answer(texts.NO_TEXT_FOUND)
        return

    note = Note(
        user_id=user.id,
        title=docx.derive_title(markdown, name.rsplit(".", 1)[0]),
        subject=None,
        markdown=markdown,
        source_type="docx",
        page_count=1,
        status="ready",
        margin_notes=[],
        uncertain=[],
        issues=[],
        numeric_divergences=[],
        unreadable_count=0,
        text_agreement=None,
        photo_sharpness=None,
        photo_line_height=None,
        photo_paper_fraction=None,
        photo_contrast=None,
    )
    session.add(note)

    await log_event(
        session,
        user.id,
        "note_processed",
        {
            "verdict": "clean",
            "page_count": 1,
            "source_type": "docx",
            "latency_ms": extract_ms,
            "cost_usd": None,  # no model call
        },
    )

    await session.flush()  # note.id, for the file name and the caption
    await corpus.send_record(message, note)


async def _process_album(
    message: Message,
    session: AsyncSession,
    user: User,
    pages: list[albums.PageInput],
) -> None:
    """Assemble a buffered album into one Note. The single-photo pipeline never
    runs for album pages — this is the batch equivalent, and the per-page work
    (frame check, recognition, mathcheck) happens in albums.process_batch,
    which never touches the database."""
    if len(pages) > settings.MAX_ALBUM_PAGES:
        # A shape-of-request check, so it comes before the spend check: an
        # oversized album is refused even with the quota exhausted.
        await message.answer(texts.TOO_MANY_PAGES)
        return

    # message_id order is the page order; the number is assigned here and used
    # everywhere after — note_captured, per-page fields, every message.
    ordered = sorted(pages, key=lambda p: p.message_id)

    limit_message = await limits.check_limits(session, user, pages=len(ordered))
    if limit_message is not None:
        await message.answer(limit_message)
        return

    for number, page in enumerate(ordered, 1):
        await log_event(
            session,
            user.id,
            "note_captured",
            {
                "bytes_before": page.bytes_before,
                "bytes_after": page.bytes_after,
                "width": page.width,
                "height": page.height,
                "source_type": "photo",
                "page": number,
                "media_group_id": page.media_group_id,
            },
        )

    await message.answer(texts.PROCESSING)

    started = time.monotonic()  # note_processed.latency_ms: gather -> end of save
    outcome = await albums.process_batch(ordered)
    await vision.log_ai_calls(user.id, outcome.stats)  # once, every page's calls

    if outcome.record is None:
        await message.answer(texts.REJECTED_QUALITY)
        return

    if outcome.skips:
        # A record missing a page still reads as a whole one, and nothing in it
        # says which page is gone — the corpus would quietly carry a hole. The
        # pages that were recognised are charged for either way: the model
        # calls behind them were made and billed.
        await limits.consume(session, user, pages=len(outcome.pages_ok))
        await log_event(
            session,
            user.id,
            "album_incomplete",
            {
                "pages": len(ordered),
                "pages_ok": len(outcome.pages_ok),
                "reasons": [reason for _, reason in outcome.skips],
                "latency_ms": int((time.monotonic() - started) * 1000),
                "cost_usd": vision.total_cost(outcome.stats),
            },
        )
        await message.answer(texts.album_incomplete(outcome.skips))
        return

    rec = outcome.record
    note = Note(
        user_id=user.id,
        title=rec.title,
        subject=rec.subject,
        markdown=rec.markdown,
        source_type="photo",
        page_count=rec.page_count,
        status=rec.status,
        margin_notes=rec.margin_notes,
        uncertain=rec.uncertain,
        issues=rec.issues,
        numeric_divergences=rec.numeric_divergences,
        unreadable_count=rec.unreadable_count,
        text_agreement=rec.text_agreement,
        photo_sharpness=rec.photo_sharpness,
        photo_line_height=rec.photo_line_height,
        photo_paper_fraction=rec.photo_paper_fraction,
        photo_contrast=rec.photo_contrast,
    )
    session.add(note)

    await limits.consume(session, user, pages=rec.page_count)

    await log_event(
        session,
        user.id,
        "note_processed",
        {
            "verdict": rec.verdict,
            "page_count": rec.page_count,
            "source_type": "photo",
            "pages_skipped": len(outcome.skips),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "cost_usd": vision.total_cost(outcome.stats),
        },
    )

    await session.flush()  # note.id, for the file name and the caption
    await corpus.send_record(message, note)

    flags: list[str] = []
    math_blocks = [
        texts.page_prefix(p.page, p.report.render())
        for p in outcome.pages_ok
        if p.report.issues
    ]
    if math_blocks:
        flags.append("\n\n".join(math_blocks))
    if rec.numeric_divergences:
        lines = [texts.DIVERGENCES_HEADER]
        lines += [
            texts.divergence_line(d["context"], d["variants"], page=d["page"])
            for d in rec.numeric_divergences
        ]
        flags.append("\n".join(lines))
    if rec.uncertain:
        lines = [texts.UNCERTAIN_HEADER]
        lines += [
            texts.uncertain_line(u["text"], u["why"], page=u["page"])
            for u in rec.uncertain
        ]
        flags.append("\n".join(lines))
    if outcome.skips:
        flags.append(
            "\n".join(
                texts.page_skipped(number, reason)
                for number, reason in outcome.skips
            )
        )
    if flags:
        await message.answer("\n\n".join(flags))


# Registered last on purpose: aiogram matches handlers in registration order,
# so a filterless @router.message() placed any higher would swallow photos and
# documents. Everything that reaches here — text, voice, stickers, video —
# previously got no reply at all.
@router.message()
async def handle_unsupported(
    message: Message, session: AsyncSession, user: User
) -> None:
    await log_event(
        session,
        user.id,
        "unsupported_message",
        {"content_type": message.content_type},
    )
    await message.answer(texts.UNSUPPORTED)
