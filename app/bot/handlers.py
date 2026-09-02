"""Aiogram handlers."""

from dataclasses import asdict

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.config import settings
from app.core.events import log_event
from app.db.models import Note, User
from app.services import images, limits, mathcheck, photoguard, vision

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User) -> None:
    await message.answer(texts.START)


# Telegram rejects messages over 4096 characters. Split on blank lines; hard-cut
# only a single paragraph that is itself longer than the limit.
_MESSAGE_LIMIT = 4000


def _split_message(text: str, limit: int = _MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(para) > limit:
            chunks.append(para[:limit])
            para = para[limit:]
        current = para
    if current:
        chunks.append(current)
    return chunks


@router.message(F.photo)
async def handle_photo(
    message: Message, session: AsyncSession, user: User, bot: Bot
) -> None:
    photo = message.photo[-1]
    original = (await bot.download(photo)).read()
    compressed = images.compress(original)

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
    report = mathcheck.check(result.best.markdown)
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
    # Note and the quota bump in the main session. The full contract lands in
    # task 10; for now, only the fields that already exist.
    await log_event(
        session,
        user.id,
        "note_processed",
        {
            "verdict": result.verdict,
            "page_count": 1,
            "source_type": "photo",
        },
    )

    for chunk in _split_message(f"{result.best.title}\n\n{result.best.markdown}"):
        await message.answer(chunk)

    # Items 2–4 of the final reply go in one message after the main text: the
    # needs-review flag, then what mathcheck found, then the numeric divergences
    # between runs.
    flags: list[str] = []
    if result.verdict == "needs_review":
        flags.append(texts.NEEDS_REVIEW)
    if report.issues:
        flags.append(report.render())
    if result.numeric_divergences:
        lines = [texts.DIVERGENCES_HEADER]
        lines += [
            texts.divergence_line(d.context, d.variants)
            for d in result.numeric_divergences
        ]
        flags.append("\n".join(lines))
    if flags:
        await message.answer("\n\n".join(flags))
