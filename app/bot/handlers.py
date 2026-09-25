"""Aiogram handlers."""

import asyncio
import logging
import time
from dataclasses import asdict

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import (
    JOIN_TRANSITION,
    LEAVE_TRANSITION,
    PROMOTED_TRANSITION,
    ChatMemberUpdatedFilter,
    CommandStart,
)
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import albums, corpus, tags, texts
from app.core.config import settings
from app.core.events import log_event
from app.db.models import Group, Note, User
from app.services import (
    compose,
    docx,
    explain,
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
async def cmd_start(
    message: Message, session: AsyncSession, user: User, group: Group | None = None
) -> None:
    await message.answer(texts.GROUP_HELP if group is not None else texts.START)


# ── The bot's own place in a group chat ──────────────────────────────────────
# Telegram reports the bot being added, promoted and removed as my_chat_member
# updates. The same updates arrive from a private chat when someone blocks or
# unblocks the bot, which is why each handler first asks whether there is a
# group at all.


async def _sees_photos(bot: Bot, status: str) -> bool:
    """With privacy mode on — a setting of the bot in BotFather, not of this
    code — the bot sees a group's photos only where it is an admin."""
    me = await bot.me()
    return bool(me.can_read_all_group_messages) or status == ChatMemberStatus.ADMINISTRATOR


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_joined(
    event: ChatMemberUpdated,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> None:
    """Added to a chat: say how the bot works there, and whether it can see
    the photographs at all — a bot that silently ignores every page would
    look broken, and the fix is one tap by whoever added it."""
    if group is None:
        return
    sees = await _sees_photos(bot, event.new_chat_member.status)
    await log_event(
        session, user.id, "group_joined", {"sees_photos": sees}, group_id=group.id
    )
    await bot.send_message(event.chat.id, texts.group_welcome(sees))


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=PROMOTED_TRANSITION))
async def on_promoted(
    event: ChatMemberUpdated,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> None:
    """Made an admin after joining, which is what the welcome asks for when
    privacy mode hides the chat. Said out loud, because nothing else would
    show that it worked."""
    if group is None:
        return
    await log_event(session, user.id, "group_promoted", group_id=group.id)
    if not (await bot.me()).can_read_all_group_messages:
        await bot.send_message(event.chat.id, texts.GROUP_SEES_PHOTOS)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def on_left(
    event: ChatMemberUpdated,
    session: AsyncSession,
    user: User,
    group: Group | None = None,
) -> None:
    if group is None:
        return
    await log_event(session, user.id, "group_left", group_id=group.id)


@router.message(F.photo)
async def handle_photo(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> None:
    photo = message.photo[-1]
    # The subject the photo was sent with; in a private chat it spares the
    # question afterwards. In a group it is what makes the photo the bot's at
    # all. middlewares.heard stops an untagged one before a session is even
    # opened, and this keeps a group's record from ever being made without
    # its subject whatever reaches here. An album is judged whole, in
    # _process_album.
    tag = tags.from_caption(message.caption)
    if group is not None and tag is None and not message.media_group_id:
        return
    group_id = group.id if group is not None else None
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
                tag=tag,
            ),
        )
        pages = await albums.collect(message.media_group_id)
        if pages is None:
            return  # another update owns this batch
        await _process_album(message, session, user, pages, group)
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
        group_id=group_id,
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
        group_id=group_id,
    )
    if not photo_verdict.ok:
        await message.answer(photo_verdict.reason)
        return

    await message.answer(texts.PROCESSING)

    started = time.monotonic()  # note_processed.latency_ms: step 7 -> end of 15
    result, stats = await vision.transcribe_consensus(compressed)
    await vision.log_ai_calls(user.id, stats)  # always — the tokens were spent

    if result is None:
        # Not one run came back readable: there is nothing to keep.
        await message.answer(texts.ERROR_GENERIC)
        return
    if len(result.best.markdown.strip()) < settings.MIN_MARKDOWN_LEN:
        await message.answer(texts.NO_TEXT_FOUND)
        return

    # Disagreement between the runs used to end the photo here. It does not
    # any more: the pages behind those refusals carried legible text, and what
    # the disagreement measured was the shape the runs gave the page. The
    # record is saved and says which page nobody could confirm.
    unverified: list[dict] = []
    if result.text_agreement is None:
        unverified = [{"page": 1, "reason": texts.UNVERIFIED_ONE_RUN}]
    elif result.verdict == "rejected":
        unverified = [{"page": 1, "reason": texts.UNVERIFIED_DIVERGED}]
        logger.warning(
            "photo kept unverified: text_agreement %.3f", result.text_agreement
        )
    if unverified:
        result.verdict = "needs_review"

    # Step 12: deterministic arithmetic check, no model call. mathcheck compares
    # physical constants against a reference table and checks that chains of
    # equalities converge. Only a "critical" issue downgrades the verdict, and
    # only clean -> needs_review, one way; warnings are shown but leave the
    # status alone. From here result.verdict is the pipeline's final verdict.
    # graphcheck is the same kind of check on a different subject: a matrix
    # against the graph drawn beside it. Its findings join the same list, so
    # they reach the same downgrade, the same event and the same callout.
    report = mathcheck.Report(
        issues=vision.arithmetic_issues(result.best.markdown)
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
            group_id=group_id,
        )

    # Step 12a: stage two, formatting. It is given the text the three runs
    # agreed on and never the photograph, so it has nothing to invent from,
    # and what it returns is checked against what went in — by code, not by
    # another model call. Refused for any reason, the record is the one we
    # already had. It runs after the checks above deliberately: mathcheck and
    # graphcheck judge what was *read*, and this stage is presentation.
    composition = compose.Composition(result.best.markdown)
    # Rule 6, limits before the model call. pages=0 because composition is one
    # call per record rather than per page — the page budget is already
    # debited for the recognition — but the kill switch and the daily cost cap
    # still decide whether it may run at all.
    if await limits.check_limits(session, user, pages=0) is None:
        composition = await compose.compose(result.best.markdown)
        await vision.log_ai_calls(user.id, composition.stats)

    # Step 12b: stage three, what the bot adds of its own — hard places
    # explained, each with the sources the search gave, and the record summed
    # up. Over the composed text and never the photograph, stored apart from
    # the author's text and printed as the bot's. Rule 6 again: a third call
    # is still a call, and the kill switch and the cost cap decide first.
    explaining = explain.Explaining()
    if await limits.check_limits(session, user, pages=0) is None:
        explaining = await explain.explain(composition.markdown)
        await vision.log_ai_calls(user.id, explaining.stats)

    # Step 13: persist the record. "rejected" already exited at step 10, so the
    # verdict here is "clean" or "needs_review". Dataclasses are flattened to
    # plain dicts — JSONB won't take them as they are.
    note = Note(
        user_id=user.id,
        group_id=group_id,
        tag=tag,
        title=result.best.title,
        subject=result.best.subject,
        markdown=composition.markdown,
        explanations=[asdict(item) for item in explaining.explanations],
        summary=explaining.summary,
        source_type="photo",
        page_count=1,
        status="needs_review" if result.verdict == "needs_review" else "ready",
        margin_notes=result.best.margin_notes,
        uncertain=[asdict(u) for u in result.best.uncertain],
        issues=[asdict(i) for i in report.issues],
        numeric_divergences=[asdict(d) for d in result.numeric_divergences],
        unreadable_count=result.best.unreadable_count,
        unverified_pages=unverified,
        text_agreement=result.text_agreement,
        numeric_agreement=result.numeric_agreement,
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
            "composed": composition.refused is None and bool(composition.stats),
            "compose_refused": composition.refused,
            "compose_drift": composition.drift,
            "compose_demoted": composition.demoted,
            "compose_unmarked": composition.unmarked,
            "explained": len(explaining.explanations),
            "explain_refused": explaining.refused,
            "explain_unsourced": explaining.unsourced,
            "summary": explaining.summary is not None,
            "summary_refused": explaining.summary_refused,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "cost_usd": vision.total_cost(stats + composition.stats + explaining.stats),
        },
        group_id=group_id,
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
    if unverified:
        flags.append(
            "\n".join(
                [texts.UNVERIFIED_HEADER]
                + [texts.unverified_line(u["page"], u["reason"]) for u in unverified]
            )
        )

    # The generic line only when there is nothing specific to say: above a list
    # of what actually diverged it repeats that list's own heading.
    if result.verdict == "needs_review" and not flags:
        flags.insert(0, texts.NEEDS_REVIEW)
    if flags:
        await message.answer("\n\n".join(flags))

    # Step 17: which subject does this belong to. Last, so the question is
    # what the user is looking at when they reply.
    await corpus.ask_for_tag(message, session, user, note, group)


@router.message(F.document)
async def handle_document(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> None:
    """.docx only. The text is already machine-readable, so there is no model
    call: no limits are checked and no quota is spent — a Word file is
    processed even with AI_ENABLED=false. Steps 0, 4-10, 12 and 14 are skipped;
    step 11 (empty text) still applies."""
    tag = tags.from_caption(message.caption)
    if group is not None and tag is None:
        return  # not the bot's in a group; see handle_photo
    group_id = group.id if group is not None else None
    document = message.document
    name = document.file_name or ""
    if not name.lower().endswith(".docx"):
        # In a group a file with a "#word" under it is slides or a textbook
        # shared with the others, not something sent to the bot.
        if group is None:
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
        group_id=group_id,
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
        group_id=group_id,
        tag=tag,
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
        numeric_agreement=None,  # a .docx has no runs to compare
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
        group_id=group_id,
    )

    await session.flush()  # note.id, for the file name and the caption
    await corpus.send_record(message, note)
    await corpus.ask_for_tag(message, session, user, note, group)


def _skip_payload(skips: list[albums.PageResult]) -> list[dict]:
    """What a refused page leaves behind: its number, its reason, and the four
    frame metrics the refusal was made on."""
    return [
        {
            "page": p.page,
            "reason": p.skip_reason,
            "line_height_px": p.photo_line_height,
            "sharpness": p.photo_sharpness,
            "paper_fraction": p.photo_paper_fraction,
            "contrast": p.photo_contrast,
        }
        for p in skips
    ]


async def _process_album(
    message: Message,
    session: AsyncSession,
    user: User,
    pages: list[albums.PageInput],
    group: Group | None = None,
) -> None:
    """Assemble a buffered album into one Note. The single-photo pipeline never
    runs for album pages — this is the batch equivalent, and the per-page work
    (frame check, recognition, mathcheck) happens in albums.process_batch,
    which never touches the database."""
    # In a group an album is the bot's only when one of its pages carries a
    # "#word" in its caption; without one it is people sharing photos, and the
    # bot says nothing — before the size check too, which would answer.
    tag = albums.tag_of(pages)
    if group is not None and tag is None:
        return
    group_id = group.id if group is not None else None

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
            group_id=group_id,
        )

    # Every frame is checked before any page is read. A page the check turns
    # away is the one loss only the photographer can fix, and nothing has been
    # spent yet — so the album is not read with a hole in it: it is asked for
    # again, whole, and nothing is charged (task 43, the author's decision
    # after record 45).
    refused = await albums.refused_frames(ordered)
    if refused:
        await log_event(
            session,
            user.id,
            "album_retake_requested",
            {"pages": len(ordered), "refused": _skip_payload(refused)},
            group_id=group_id,
        )
        await message.answer(
            texts.album_retake([(p.page, p.skip_reason) for p in refused])
        )
        return

    await message.answer(texts.PROCESSING)

    started = time.monotonic()  # note_processed.latency_ms: gather -> end of save
    outcome = await albums.process_batch(ordered)
    await vision.log_ai_calls(user.id, outcome.stats)  # once, every page's calls

    if outcome.record is None:
        # Not one page was read, so there is nothing to deliver and nothing to
        # charge: `record is None` is exactly `pages_ok == []`. An album with
        # *some* pages read is saved with the holes named in it — see
        # albums._assemble for why that replaced "all its pages or none".
        await log_event(
            session,
            user.id,
            "album_incomplete",
            {
                "pages": len(ordered),
                "pages_ok": 0,
                # The metrics, not just the reasons. A page turned away by the
                # frame check has to be arguable after the fact rather than
                # from memory — "Текст мелкий" on a page written in a large
                # hand is a claim, and these four numbers are the evidence.
                "skipped": _skip_payload(outcome.skips),
                "latency_ms": int((time.monotonic() - started) * 1000),
                "cost_usd": vision.total_cost(outcome.stats),
            },
            group_id=group_id,
        )
        await message.answer(
            texts.album_incomplete(
                [(p.page, p.skip_reason) for p in outcome.skips]
            )
        )
        return

    rec = outcome.record
    # Stage two runs once over the assembled record, not once per page: a
    # document formatted page by page keeps the seams the assembly removed.
    composition = compose.Composition(rec.markdown)
    if await limits.check_limits(session, user, pages=0) is None:
        composition = await compose.compose(rec.markdown)
        await vision.log_ai_calls(user.id, composition.stats)

    # Stage three once over the whole record too, for the same reason.
    explaining = explain.Explaining()
    if await limits.check_limits(session, user, pages=0) is None:
        explaining = await explain.explain(composition.markdown)
        await vision.log_ai_calls(user.id, explaining.stats)

    note = Note(
        user_id=user.id,
        group_id=group_id,
        tag=tag,
        title=rec.title,
        subject=rec.subject,
        markdown=composition.markdown,
        explanations=[asdict(item) for item in explaining.explanations],
        summary=explaining.summary,
        source_type="photo",
        page_count=rec.page_count,
        status=rec.status,
        margin_notes=rec.margin_notes,
        uncertain=rec.uncertain,
        issues=rec.issues,
        numeric_divergences=rec.numeric_divergences,
        unreadable_count=rec.unreadable_count,
        missing_pages=rec.missing_pages,
        unverified_pages=rec.unverified_pages,
        text_agreement=rec.text_agreement,
        numeric_agreement=rec.numeric_agreement,
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
            # The same four numbers as in album_incomplete, and for the same
            # reason: a page is turned away on these, and now that the record
            # is saved anyway this is the only place they would be kept.
            "skipped": _skip_payload(outcome.skips),
            "composed": composition.refused is None and bool(composition.stats),
            "compose_refused": composition.refused,
            "compose_drift": composition.drift,
            "compose_demoted": composition.demoted,
            "compose_unmarked": composition.unmarked,
            "explained": len(explaining.explanations),
            "explain_refused": explaining.refused,
            "explain_unsourced": explaining.unsourced,
            "summary": explaining.summary is not None,
            "summary_refused": explaining.summary_refused,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "cost_usd": vision.total_cost(
                outcome.stats + composition.stats + explaining.stats
            ),
        },
        group_id=group_id,
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
    if rec.unverified_pages:
        flags.append(
            "\n".join(
                [texts.UNVERIFIED_HEADER]
                + [
                    texts.unverified_line(u["page"], u["reason"])
                    for u in rec.unverified_pages
                ]
            )
        )
    if outcome.skips:
        flags.append(
            texts.album_partial(
                [(p.page, p.skip_reason) for p in outcome.skips]
            )
        )
    if flags:
        await message.answer("\n\n".join(flags))

    await corpus.ask_for_tag(message, session, user, note, group)


# Registered last on purpose: aiogram matches handlers in registration order,
# so a filterless @router.message() placed any higher would swallow photos and
# documents. Everything that reaches here — text, voice, stickers, video —
# previously got no reply at all.
@router.message()
async def handle_unsupported(
    message: Message, session: AsyncSession, user: User, group: Group | None = None
) -> None:
    if group is not None:
        # What reaches here in a group is a notice about the chat or a command
        # meant for another bot (middlewares.heard lets both through). None of
        # it is addressed to this one, and a reply would be noise in the chat.
        return
    await log_event(
        session,
        user.id,
        "unsupported_message",
        {"content_type": message.content_type},
    )
    await message.answer(texts.UNSUPPORTED)
