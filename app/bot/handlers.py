"""Aiogram handlers."""

import asyncio
import logging
import re
import time
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import (
    JOIN_TRANSITION,
    LEAVE_TRANSITION,
    PROMOTED_TRANSITION,
    ChatMemberUpdatedFilter,
    CommandObject,
    CommandStart,
)
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import albums, corpus, middlewares, notebook, subjects, tags, texts, to_group, waiting
from app.core.config import settings
from app.core.events import log_event
from app.db.models import Event, Group, GroupPage, Lecture, Note, NoteFigure, NoteTopic, User
from app.services import (
    charts,
    compose,
    docx,
    explain,
    figures,
    images,
    limits,
    mathcheck,
    photoguard,
    sketches,
    study,
    vision,
)
from app.services.pdf import plain

logger = logging.getLogger(__name__)

router = Router()

# Telegram documents over this size are refused before download.
_MAX_DOCX_BYTES = 5 * 1024 * 1024
# An image sent as a file, or a PDF: the most Telegram lets a bot download.
_MAX_IMAGE_BYTES = 20 * 1024 * 1024
# A PDF of more pages than this many albums hold is refused before a page of
# it is drawn (task 100). A scan of both sides of every sheet holds twice the
# pages its writing fills, the blank backs left out once drawn; past that a
# PDF is no lecture's, and drawing it would hold an image thread for minutes.
_PDF_DRAWN_ALBUMS = 2

# How long a page of a group's album can still be called on by a reply. A
# lecture is reached for within days of it — the author's choice, 2026-09-29.
_PAGES_KEPT = timedelta(days=7)

# A notebook's pages downloaded this many at a time (task 63): a hundred
# photographs fetched at once held a hundred originals in memory at once.
_FETCH_AT_ONCE = 10
# Why a page is skipped when it is not its frame: what the notebook's event
# counts the frames refused apart from.
_NOT_FRAMES = (texts.SKIP_UNRECOGNIZED, texts.SKIP_NO_TEXT, texts.SKIP_ERROR)
# The page a photo sent again names in its caption: «17», «стр. 17».
_PAGE_NUMBER_RE = re.compile(r"(?<!\d)(\d{1,3})(?!\d)")
# A notebook's lectures made this many at a time, in its order: a lecture
# begins once the one this many before it has been sent, so the first comes
# while the rest are made, and the bot's API_SLOTS stay every chat's.
_LECTURES_AT_ONCE = 2


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    user: User,
    command: CommandObject,
    group: Group | None = None,
) -> None:
    if group is not None:
        if command.args:
            # Added through the button, the person's client sends
            # "/start@<bot> add" into the chat on its own, right after the
            # welcome: answering it would say the welcome twice. It is counted
            # instead — how often the button brings the bot into a chat.
            await log_event(
                session, user.id, "group_invited", {"via": command.args}, group_id=group.id
            )
            return
        await message.answer(texts.GROUP_HELP)
        return
    await message.answer(texts.START, reply_markup=await corpus.add_to_group(message))


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


# A photo, or an image sent as a file: middlewares.page_file decides which
# messages carry a page, for this handler and for a group's filter alike.
@router.message(middlewares.is_page)
async def handle_photo(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> None:
    page = middlewares.page_file(message)
    # A page of a whole notebook it could not read, sent again in reply to
    # the notebook's last message (task 63): it goes into its lecture.
    replied = getattr(message, "reply_to_message", None)
    if group is None and replied is not None and not message.media_group_id:
        shelf = await _notebook_asked(session, user, replied)
        if shelf is not None:
            await _notebook_page(message, session, user, bot, shelf, page)
            return
    # The subject the photo was sent with; in a private chat it spares the
    # question afterwards. In a group it is what makes the photo the bot's at
    # all. middlewares.heard stops an untagged one before a session is even
    # opened, and this keeps a group's record from ever being made without
    # its subject whatever reaches here. An album is judged whole, in
    # _process_album, and a page sent without its subject can still be called
    # on by a reply that carries one — handle_summon.
    tag = tags.from_caption(message.caption)
    # A photo sent while the same person's album is still being collected may
    # be the rest of it — Telegram holds ten pages in an album, and the
    # eleventh can come as a photo of its own (task 81) — so it is buffered
    # as an album of one page, which joins that send or stands alone.
    sender = (message.chat.id, user.tg_id)
    album = message.media_group_id or (
        albums.apart(message.message_id) if albums.collecting(sender) else None
    )
    if group is not None and tag is None and album is None:
        return
    source_key = corpus.source_key(message) if group is not None else None

    # Step 0: an album arrives as separate messages sharing a media_group_id.
    # Buffer this page and let a single update assemble the whole batch; the
    # individual-photo steps 4-16 do not run for an album page. The page goes
    # in as Telegram's reference and is not downloaded here: the update that
    # claims the batch fetches the pages once it knows the album is to be read,
    # so in a group an album nobody tagged is never fetched at all.
    if album is not None:
        # Announced first: albums.collect() times the album from here.
        albums.announce(album, message.message_id, sender)
        if group is not None and message.media_group_id:
            await _remember_page(session, group, message, page)
        albums.add_page(
            album,
            albums.PageInput(
                data=b"",
                message_id=message.message_id,
                chat_id=message.chat.id,
                media_group_id=message.media_group_id,
                bytes_before=0,
                bytes_after=0,
                width=page.width,
                height=page.height,
                tag=tag,
                caption=message.caption,
                file_id=page.file_id,
            ),
        )
        # Nothing of this update's is left to write while it waits, and an
        # album of ten waits for the rest of its send: committed, the wait
        # holds no connection. A send of thirty pages is thirty updates
        # waiting at once, and the pool is twenty. A group's page committed
        # already, when it wrote itself down.
        await session.commit()
        pages = await albums.collect(album)
        if pages is None:
            return  # another update owns this batch
        # A send of several albums is known in a group by its first
        # (task 81), whichever page's update owns the batch.
        if group is not None:
            first = min(pages, key=lambda p: p.message_id)
            source_key = corpus.page_key(first.media_group_id, first.message_id)
        # A tagged album claims its pages against a reply's call on them, one
        # reading at a time (task 41); in a group an untagged one is not read,
        # and claims nothing. Already being read — a reply's call got there
        # first — the record goes to the chat once, from that reading.
        claimed = source_key if albums.tag_of(pages) is not None else None
        async with corpus.reading(session, group, claimed) as ours:
            if ours:
                await _process_album(
                    message, session, user, pages, group, bot=bot,
                    source_key=source_key,
                )
        return

    if message.document is not None and (
        message.document.file_size or 0
    ) > _MAX_IMAGE_BYTES:
        await message.answer(texts.IMAGE_TOO_BIG)
        return
    # In a group the photo is tagged by now, and claims its page as an album
    # does, against a reply's call on it (task 41).
    async with corpus.reading(session, group, source_key) as ours:
        if not ours:
            return
        original = (await bot.download(page.file_id)).read()
        # Resizing a 12-megapixel photo is CPU-bound; on the event loop it
        # would freeze every other update while it runs.
        compressed = await images.in_worker(
            images.compress, original, settings.IMAGE_MAX_SIDE, settings.IMAGE_QUALITY
        )
        await _read_photo(
            message, session, user, group, tag, original, compressed, page,
            source_key, caption=message.caption,
        )


async def _read_photo(
    message: Message,
    session: AsyncSession,
    user: User,
    group: Group | None,
    tag: str | None,
    original: bytes,
    compressed: bytes,
    page: middlewares.PageFile,
    source_key: str | None,
    caption: str | None = None,
    sender: User | None = None,
) -> None:
    """Steps 4-17 for one page: a page sent with its subject, or a page
    somebody else sent that a reply called the bot on. The answers go under
    `message`, and `user` is who pays for the reading; `caption` may carry
    the lecture's day; `sender` is whoever sent the page, when it is not
    `user`."""
    group_id = group.id if group is not None else None
    await log_event(
        session,
        user.id,
        "note_captured",
        {
            "bytes_before": len(original),
            "bytes_after": len(compressed),
            "width": page.width,
            "height": page.height,
            "source_type": "photo",
        },
        group_id=group_id,
    )

    # Step 4: limits before the frame check and before any model call. With the
    # kill switch off or a cap hit, there's no point asking for a better photo.
    limit_message = await limits.check_limits(session, user, pages=1, group=group)
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

    async with waiting.shown(message):

        started = time.monotonic()  # note_processed.latency_ms: step 7 -> end of 15
        result, stats = await vision.transcribe_consensus(compressed)
        # Always — the tokens were spent.
        await vision.log_ai_calls(user.id, stats, group_id=group_id)

        if result is None:
            # Not one run came back readable: there is nothing to keep.
            await message.answer(texts.ERROR_GENERIC)
            return
        if len(result.best.markdown.strip()) < settings.MIN_MARKDOWN_LEN:
            await message.answer(texts.NO_TEXT_FOUND)
            return

        # The page's drawings, taken from the image while it is still here —
        # rule 3 keeps nothing else of it. A sketch is drawn again from the page
        # (task 101): three calls read where each is and what its labels say,
        # part of reading the page as task 65's further runs are, and its lines
        # are traced off the photograph. Under a prompt that frames drawings
        # (v8) they are cut out instead. Pixels in a thread: CPU work the
        # webhook must not stall on.
        sketch_stats: list = []
        sketched: list = []
        if settings.SKETCHES_ENABLED and figures.count(result.best.markdown):
            sketched, sketch_stats = await sketches.read(
                compressed, result.best.markdown
            )
            await vision.log_ai_calls(user.id, sketch_stats, group_id=group_id)
            cutouts = await images.in_worker(
                figures.redraw, compressed, result.best.markdown, sketched
            )
        else:
            cutouts = await images.in_worker(
                figures.cut, compressed, result.best.markdown, result.best.drawings
            )

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
        # they reach the same downgrade and the same event, and each is kept with
        # the text it is about — the document sets it under that text.
        report = mathcheck.Report(issues=vision.findings(result.best.markdown))
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
        if await limits.check_limits(session, user, pages=0, group=group) is None:
            composition = await compose.compose(result.best.markdown)
            await vision.log_ai_calls(user.id, composition.stats, group_id=group_id)

        # The drawings go back where their lines stand: after composing, which
        # never saw them, and before explaining, so the text explained and the
        # text stored are one text.
        markdown, placed = figures.place(composition.markdown, cutouts)

        # The page photographed twice (task 63): this page may be the last of
        # the subject's album before, the lecture before's end read again,
        # with this lecture begun under it. That end is its own record's, and
        # it goes before anything below reads the text.
        title, issues = result.best.title, report.issues
        repeat = None
        if tag is not None:
            repeat = await subjects.repeated(
                session, group_id, user.id, tag, markdown,
                result.best.margin_notes, caption, 1,
            )
        if repeat is not None:
            markdown = repeat.markdown
            title = subjects.retitled(title, repeat)
            issues = [i for i in issues if not subjects.cut_only(i.anchor, repeat)]
            placed = _still_placed(placed, markdown)

        # The lecture this page is a notebook of, if its subject has it already
        # (task 63): a notebook that will only add to another is not explained —
        # its lecture's document carries the base's explanations.
        joining = None
        if tag is not None:
            joining = await subjects.joining(
                session, group_id, user.id, tag, markdown,
                result.best.margin_notes, caption,
            )
        explain_skipped = joining is not None and not joining.leads

        # Step 12b: stage three, what the bot adds of its own — hard places
        # explained, each with the sources the search gave, and the record summed
        # up. Over the composed text and never the photograph, stored apart from
        # the author's text and printed as the bot's. Rule 6 again: a third call
        # is still a call, and the kill switch and the cost cap decide first.
        # Beside it the study version, for a record that joins no lecture
        # (_explained, task 104).
        explaining, early = explain.Explaining(), None
        if (
            not explain_skipped
            and await limits.check_limits(session, user, pages=0, group=group) is None
        ):
            explaining, early = await _explained(
                user, group_id, markdown, joining is None
            )

        # Step 13: persist the record. "rejected" already exited at step 10, so the
        # verdict here is "clean" or "needs_review". Dataclasses are flattened to
        # plain dicts — JSONB won't take them as they are.
        note = Note(
            user_id=user.id,
            sender_id=sender.id if sender is not None else None,
            group_id=group_id,
            source_key=source_key,
            tag=tag,
            title=title,
            subject=result.best.subject,
            markdown=markdown,
            # The teacher's boxes and the captions stand in the same list, each
            # naming its kind; an explanation names none, as every one stored
            # before them.
            explanations=[asdict(item) for item in explaining.explanations]
            + [asdict(item) for item in explaining.elements]
            + [asdict(item) for item in explaining.captions],
            summary=explaining.summary,
            source_type="photo",
            page_count=1,
            status="needs_review" if result.verdict == "needs_review" else "ready",
            margin_notes=result.best.margin_notes,
            uncertain=[asdict(u) for u in result.best.uncertain],
            issues=[asdict(i) for i in issues],
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
        filing = (
            await subjects.file(
                session, note, tag, caption, joining.lecture if joining else None
            )
            if tag is not None
            else None
        )

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
                "compose_restored": composition.restored,
                "compose_retried": composition.retried,
                "explained": len(explaining.explanations),
                "explain_refused": explaining.refused,
                "explain_unsourced": explaining.unsourced,
                "explain_judged": explaining.judged,
                "elements": len(explaining.elements),
                "elements_dropped": explaining.elements_dropped,
                "captions": len(explaining.captions),
                "captions_dropped": explaining.captions_dropped,
                "summary": explaining.summary is not None,
                "summary_refused": explaining.summary_refused,
                "drawings": figures.count(result.best.markdown),
                "sketched": sum(sketch is not None for sketch in sketched),
                "figures": len(placed),
                "charts": charts.count(markdown),
                "runs_added": result.runs_added,
                "read_further": int(result.read_further),
                **_filing_payload(filing, explain_skipped, repeat),
                "latency_ms": int((time.monotonic() - started) * 1000),
                "cost_usd": vision.total_cost(
                    stats + sketch_stats + composition.stats + explaining.stats
                ),
            },
            group_id=group_id,
        )

        # Step 16: the record itself goes out as a PDF — recognised notes are full
        # of LaTeX, and a formula reads as noise until it is drawn. Nothing
        # follows it: what the checks found stands in the document beside the
        # line it is about, and how the page was read — the numbers the runs read
        # differently, the spots that read two ways, a page no second reading
        # confirmed — is not the group's business. The author's decision,
        # 2026-09-25; in a group chat that message was noise for everyone.
        await session.flush()  # note.id, for the file name, the caption, the drawings
        await _keep_figures(session, note, placed)
        # Step 17: which subject does this belong to — said under the document, in
        # one message with it (task 105), so the question is what the user is
        # looking at when they reply. The topics it shows are kept with the record.
        after = await corpus.tag_line(session, user, note, group, filing)
        await _saved(session)
        await corpus.deliver(message, session, note, user, group, early, after)


@router.message(F.document)
async def handle_document(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> None:
    """A .docx or a PDF. A PDF is read page by page as an album (_read_pdf).
    A .docx is already machine-readable, so there is no model call: no limits
    are checked and no quota is spent — a Word file is processed even with
    AI_ENABLED=false. Steps 0, 4-10, 12 and 14 are skipped; step 11 (empty
    text) still applies."""
    tag = tags.from_caption(message.caption)
    if group is not None and tag is None:
        return  # not the bot's in a group; see handle_photo
    if _is_pdf(message.document):
        await _read_pdf(message, session, user, bot, group, tag)
        return
    group_id = group.id if group is not None else None
    document = message.document
    name = document.file_name or ""
    if not name.lower().endswith(".docx"):
        # In a group a file with a "#word" under it that is neither is slides
        # or a textbook shared with the others, not something sent to the bot.
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
        # In a thread: a file of many paragraphs parses for seconds, and on
        # the event loop every other chat would wait them out.
        markdown = await asyncio.to_thread(docx.extract_markdown, data)
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
    filing = (
        await subjects.file(session, note, tag, message.caption)
        if tag is not None
        else None
    )

    await log_event(
        session,
        user.id,
        "note_processed",
        {
            "verdict": "clean",
            "page_count": 1,
            "source_type": "docx",
            **_filing_payload(filing, False),
            "latency_ms": extract_ms,
            "cost_usd": None,  # no model call
        },
        group_id=group_id,
    )

    await session.flush()  # note.id, for the file name and the caption
    after = await corpus.tag_line(session, user, note, group, filing)
    await _saved(session)
    # Its study version is a call of some twenty seconds: the chat waits for
    # it as for a photo's reading.
    async with waiting.shown(message):
        await corpus.deliver(message, session, note, user, group, after=after)


def _is_pdf(document) -> bool:
    """A PDF by the type Telegram gives it, or by its name: a file sent from a
    computer may come without the type."""
    name = (document.file_name or "").lower()
    return document.mime_type == "application/pdf" or name.endswith(".pdf")


async def _read_pdf(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None,
    tag: str | None,
) -> None:
    """A PDF of notes (task 100): every page drawn as a picture and read as an
    album's page, whatever the PDF holds — a typed PDF's text layer flattens
    its formulas, and a scanner lays a junk one over handwriting. An album's
    limits and refusals hold, a page the frame check refuses stopping the
    whole PDF; a blank page is left out without a word. Nothing of the file
    is kept: its pages exist while they are read (rule 3)."""
    document = message.document
    if (document.file_size or 0) > _MAX_IMAGE_BYTES:
        await message.answer(texts.PDF_TOO_BIG)
        return
    # In a group the PDF claims itself as a photograph does (task 41).
    source_key = corpus.source_key(message) if group is not None else None
    async with corpus.reading(session, group, source_key) as ours:
        if not ours:
            return
        data = (await bot.download(document)).read()
        # A private chat's PDF may be a whole notebook (task 63).
        limit = (
            settings.MAX_ALBUM_PAGES if group is not None else settings.NOTEBOOK_MAX_PAGES
        )
        try:
            count = await images.in_worker(images.pdf_page_count, data)
            drawn = (
                await images.in_worker(
                    images.pdf_pages,
                    data,
                    settings.IMAGE_MAX_SIDE,
                    settings.IMAGE_QUALITY,
                )
                if count <= _PDF_DRAWN_ALBUMS * limit
                else None
            )
        except Exception:
            # Broken, or locked by a password: PDFium's words are in the log.
            logger.warning("a PDF could not be opened or drawn", exc_info=True)
            await message.answer(texts.PDF_UNREADABLE)
            return
        if drawn is not None and not drawn:
            await message.answer(texts.PDF_BLANK)
            return
        if drawn is None or len(drawn) > limit:
            await message.answer(
                texts.pdf_too_many_pages(limit)
                if group is not None
                else texts.notebook_too_long(limit)
            )
            return
        logger.info("pdf: %d pages, %d blank left out", count, count - len(drawn))
        pages = [
            albums.PageInput(
                data=page.image,
                message_id=message.message_id,
                chat_id=message.chat.id,
                media_group_id=None,
                bytes_before=page.drawn,
                bytes_after=len(page.image),
                width=page.width,
                height=page.height,
                tag=tag,
                caption=message.caption,
                number=page.number,
            )
            for page in drawn
        ]
        await _process_album(
            message, session, user, pages, group, bot=bot, tag=tag,
            source_key=source_key, source_type="pdf",
        )


async def _explained(
    user: User, group_id: int | None, markdown: str, alone: bool
) -> tuple[explain.Explaining, study.Study | None]:
    """Stage three, and beside it the record's study version (task 104):
    the record waits for the slower of the two calls, not for both — the
    study call's twenty-odd seconds of every delivery. Only for a record
    that joins no lecture (`alone`): one that does is studied whole, from
    the lecture's text once it is filed, at its delivery. The version comes
    back refused or not, and corpus.deliver sends it or the record.

    Neither call touches the database, as nothing that calls the model
    does; both are written down here whichever of them failed (rule 4),
    and what one raised is raised after."""

    async def nothing() -> None:
        return None

    studies = alone and settings.EXPLAIN_ENABLED
    explaining, early = await asyncio.gather(
        explain.explain(markdown),
        study.build(markdown) if studies else nothing(),
        return_exceptions=True,
    )
    for done in (explaining, early):
        if done is not None and not isinstance(done, BaseException):
            await vision.log_ai_calls(user.id, done.stats, group_id=group_id)
    for done in (explaining, early):
        if isinstance(done, BaseException):
            raise done
    return explaining, early


async def _saved(session: AsyncSession) -> None:
    """The record committed before it is sent (task 104). Its reading is
    paid for, and a document Telegram refused — a chat that takes none,
    flood control, a dropped connection — or a message after it rolled the
    update back with the record in it: the money spent, nothing kept, and
    the reader told to send the photo again. What delivery writes after
    this, the study version kept and its event, commits with the update."""
    await session.commit()


async def _keep_figures(
    session: AsyncSession, note: Note, placed: list[tuple[int, bytes]]
) -> None:
    """The drawings placed in a record, kept with it in the main transaction,
    so the document drawn next reads them like any later one."""
    if not placed:
        return
    session.add_all(
        NoteFigure(note_id=note.id, number=number, png=png) for number, png in placed
    )
    await session.flush()


async def _remember_page(
    session: AsyncSession,
    group: Group,
    message: Message,
    page: middlewares.PageFile,
) -> None:
    """Write down an album page posted in a group, as Telegram's reference to
    it, for a reply that may call the bot on the album later — and drop the
    references that have outlived _PAGES_KEPT on the way."""
    await session.execute(
        delete(GroupPage)
        .where(GroupPage.created_at < datetime.now(timezone.utc) - _PAGES_KEPT)
        # Nothing this session holds is being deleted, and matching the rows
        # in Python as well would compare timestamps SQLite hands back naive.
        .execution_options(synchronize_session=False)
    )
    session.add(
        GroupPage(
            group_id=group.id,
            media_group_id=message.media_group_id,
            message_id=message.message_id,
            file_id=page.file_id,
            width=page.width,
            height=page.height,
        )
    )
    # Committed now rather than with the update. The update that claims the
    # batch holds its session through the whole album, and a reference lost to
    # that album's rollback would be a page missing from every later call on it.
    await session.commit()


async def _remembered_album(
    session: AsyncSession, group: Group, chat_id: int, media_group_id: str
) -> list[albums.PageInput]:
    """The pages of one of the group's albums that the bot saw and still keeps,
    as references to download, in page order."""
    rows = (
        await session.execute(
            select(GroupPage)
            .where(
                GroupPage.group_id == group.id,
                GroupPage.media_group_id == media_group_id,
                GroupPage.created_at >= datetime.now(timezone.utc) - _PAGES_KEPT,
            )
            .order_by(GroupPage.message_id)
        )
    ).scalars().all()
    # One page a message: an update Telegram delivers twice writes its row twice.
    by_message = {row.message_id: row for row in rows}
    return [
        albums.PageInput(
            data=b"",
            message_id=row.message_id,
            chat_id=chat_id,
            media_group_id=media_group_id,
            bytes_before=0,
            bytes_after=0,
            width=row.width,
            height=row.height,
            file_id=row.file_id,
        )
        for row in by_message.values()
    ]


async def _fetch_pages(
    bot: Bot | None, pages: list[albums.PageInput], at_once: int | None = None
) -> list[albums.PageInput]:
    """Download and compress the pages still held as references, all at once
    — a notebook's `at_once` at a time.

    A page that cannot be fetched stays empty, and the recognition reports it
    as a page that could not be opened: the record is delivered with the hole
    named in it rather than the album lost."""
    window = asyncio.Semaphore(at_once or max(len(pages), 1))

    async def fetch(page: albums.PageInput) -> albums.PageInput:
        if page.data or page.file_id is None:
            return page
        async with window:
            return await fetched(page)

    async def fetched(page: albums.PageInput) -> albums.PageInput:
        try:
            original = (await bot.download(page.file_id)).read()
            compressed = await images.in_worker(
                images.compress,
                original,
                settings.IMAGE_MAX_SIDE,
                settings.IMAGE_QUALITY,
            )
        except Exception:
            logger.exception("album page %d could not be fetched", page.message_id)
            return page
        return replace(
            page,
            data=compressed,
            bytes_before=len(original),
            bytes_after=len(compressed),
        )

    return list(await asyncio.gather(*(fetch(page) for page in pages)))


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
    bot: Bot | None = None,
    tag: str | None = None,
    source_key: str | None = None,
    sender: User | None = None,
    source_type: str = "photo",
) -> None:
    """Assemble a buffered album into one Note. The single-photo pipeline never
    runs for album pages — this is the batch equivalent, and the per-page work
    (frame check, recognition, mathcheck) happens in albums.process_batch,
    which never touches the database.

    `tag` is the subject a reply called the bot with, for an album that came
    without one (handle_summon), and `sender` whoever sent that album;
    `source_key` is what a group's record is made of. Pages still held as
    Telegram's references are downloaded with `bot`. A PDF's pages come
    drawn, as `source_type` "pdf" (task 100), and the replies say PDF where
    an album's say album."""
    pdf = source_type == "pdf"
    # In a group an album is the bot's only when one of its pages carries a
    # "#word" in its caption, or a reply called the bot on it; without one it
    # is people sharing photos, and the bot says nothing — before the size
    # check too, which would answer.
    tag = tag or albums.tag_of(pages)
    if group is not None and tag is None:
        return
    group_id = group.id if group is not None else None
    caption = albums.caption_of(pages)

    # A whole notebook, sent in a private chat (task 63): cut into its
    # lectures rather than read as one record.
    if group is None and notebook.wanted(len(pages), caption):
        await _read_notebook(message, session, user, bot, pages, tag, caption, source_type)
        return

    if len(pages) > settings.MAX_ALBUM_PAGES:
        # A shape-of-request check, so it comes before the spend check: an
        # oversized album is refused even with the quota exhausted.
        await message.answer(texts.TOO_MANY_PAGES)
        return

    # message_id order is the page order; the number is assigned here and used
    # everywhere after — note_captured, per-page fields, every message.
    ordered = sorted(pages, key=lambda p: p.message_id)

    limit_message = await limits.check_limits(
        session, user, pages=len(ordered), group=group
    )
    if limit_message is not None:
        await message.answer(limit_message)
        return

    # Downloaded now and not earlier: up to here the album could still be
    # turned away — untagged, too large, over the limit — with nothing fetched.
    ordered = await _fetch_pages(bot, ordered)

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
                "source_type": source_type,
                "page": page.number or number,
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
        retake = [(p.page, p.skip_reason) for p in refused]
        await message.answer(
            texts.pdf_retake(retake) if pdf else texts.album_retake(retake)
        )
        return

    async with waiting.shown(message):

        started = time.monotonic()  # note_processed.latency_ms: gather -> end of save
        outcome = await albums.process_batch(ordered)
        # Once, every page's calls.
        await vision.log_ai_calls(user.id, outcome.stats, group_id=group_id)

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
                    # The metrics, not just the reasons. A page turned away by
                    # the frame check has to be arguable after the fact rather
                    # than from memory — "Текст мелкий" on a page written in a
                    # large hand is a claim, and these four numbers are the
                    # evidence.
                    "skipped": _skip_payload(outcome.skips),
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "cost_usd": vision.total_cost(outcome.stats),
                },
                group_id=group_id,
            )
            await message.answer(
                texts.album_incomplete(
                    [(p.page, p.skip_reason) for p in outcome.skips],
                    texts.PDF_RESEND if pdf else texts.ALBUM_RESEND,
                )
            )
            return

        rec = outcome.record
        # Stage two runs once over the assembled record, not once per page: a
        # document formatted page by page keeps the seams the assembly removed.
        composition = compose.Composition(rec.markdown)
        if await limits.check_limits(session, user, pages=0, group=group) is None:
            composition = await compose.compose(rec.markdown)
            await vision.log_ai_calls(user.id, composition.stats, group_id=group_id)

        # Every page's drawings back where their lines stand, numbered through
        # the record — after composing, which never saw them.
        markdown, placed = figures.place(composition.markdown, rec.cutouts)

        # Its first page the last of the subject's album before, photographed
        # again, as for a photo (task 63). The seams count the unread pages
        # too: each stands in the text as its marker.
        title, issues = rec.title, rec.issues
        repeat = None
        if tag is not None:
            repeat = await subjects.repeated(
                session, group_id, user.id, tag, markdown, rec.margin_notes, caption,
                rec.page_count + len(rec.missing_pages),
            )
        if repeat is not None:
            markdown = repeat.markdown
            title = subjects.retitled(title, repeat)
            issues = [
                i for i in issues if not subjects.cut_only(str(i.get("anchor", "")), repeat)
            ]
            placed = _still_placed(placed, markdown)

        # The lecture this album is a notebook of, as for a photo (task 63).
        joining = None
        if tag is not None:
            joining = await subjects.joining(
                session, group_id, user.id, tag, markdown, rec.margin_notes, caption,
                len(rec.missing_pages),
            )
        explain_skipped = joining is not None and not joining.leads

        # Stage three once over the whole record too, for the same reason, and
        # the study version beside it, as for a photo.
        explaining, early = explain.Explaining(), None
        if (
            not explain_skipped
            and await limits.check_limits(session, user, pages=0, group=group) is None
        ):
            explaining, early = await _explained(
                user, group_id, markdown, joining is None
            )

        note = _album_note(
            rec,
            user=user,
            sender=sender,
            group_id=group_id,
            source_key=source_key,
            tag=tag,
            title=title,
            markdown=markdown,
            issues=issues,
            explaining=explaining,
            source_type=source_type,
        )
        session.add(note)
        filing = (
            await subjects.file(
                session, note, tag, caption, joining.lecture if joining else None
            )
            if tag is not None
            else None
        )

        await limits.consume(session, user, pages=rec.page_count)

        await log_event(
            session,
            user.id,
            "note_processed",
            _album_processed(
                rec,
                source_type=source_type,
                skips=outcome.skips,
                composition=composition,
                explaining=explaining,
                parts=albums.parts_of(ordered),
                placed=placed,
                markdown=markdown,
                filing=filing,
                explain_skipped=explain_skipped,
                repeat=repeat,
                started=started,
                stats=outcome.stats,
            ),
            group_id=group_id,
        )

        await session.flush()  # note.id, for the file name, the caption, the drawings
        await _keep_figures(session, note, placed)
        # Under the document, in one message with it (task 105): what only the
        # photographer can act on — the pages it went out without — and which
        # subject it is. The rest is in the document or nowhere, as on the photo
        # path.
        after = [await corpus.tag_line(session, user, note, group, filing)]
        if outcome.skips:
            after.insert(
                0, texts.album_partial([(p.page, p.skip_reason) for p in outcome.skips])
            )
        await _saved(session)
        await corpus.deliver(
            message, session, note, user, group, early, "\n\n".join(after)
        )


async def _read_notebook(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot | None,
    pages: list[albums.PageInput],
    tag: str | None,
    caption: str | None,
    source_type: str,
) -> None:
    """A whole notebook sent in a private chat (task 63, the CEO's of
    2026-10-12): read with its own prompt, cut into its lectures where every
    run named a start, and every lecture made, kept and sent as an album's
    record is, in order as each is done; then one message sums it up.

    One a person a day, beyond their pages — counted once a notebook has
    come out whole (limits.notebook_read_today), and its pages not counted
    in the person's day. A page the frame check refuses does not stop it,
    unlike an album: it is left out where it stands, and its last message
    asks for it again, as a reply, to go into its lecture (_notebook_page,
    the CEO's of 2026-10-13) — a hundred pages are not sent again for one.
    The pages are read a few at a time (albums.NOTEBOOK_AT_ONCE) and the
    lectures made two at a time, so that the bot's calls are still every
    chat's while a notebook is read; a line says how far it is."""
    pdf = source_type == "pdf"
    ordered = sorted(pages, key=lambda p: p.message_id)
    if len(ordered) > settings.NOTEBOOK_MAX_PAGES:
        await message.answer(texts.notebook_too_long(settings.NOTEBOOK_MAX_PAGES))
        return
    # The kill switch and the bot's day; the person's pages are not asked:
    # a notebook is one a day beyond them.
    limit_message = await limits.check_limits(session, user, pages=0)
    if limit_message is not None:
        await message.answer(limit_message)
        return
    if await limits.notebook_read_today(session, user):
        await message.answer(texts.NOTEBOOK_ONE_A_DAY)
        return

    ordered = await _fetch_pages(bot, ordered, at_once=_FETCH_AT_ONCE)
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
                "source_type": source_type,
                "page": page.number or number,
                "media_group_id": page.media_group_id,
                "notebook": True,
            },
        )
    shelf = notebook.key(message.chat.id, ordered[0].message_id)
    # Nothing of the update's is held while a hundred pages are read.
    await session.commit()

    total = len(ordered)
    async with waiting.progress(message, texts.notebook_reading(0, total)) as bar:
        started = time.monotonic()
        read = 0

        def page_read() -> None:
            nonlocal read
            read += 1
            bar.set(texts.notebook_reading(read, total))

        outcome = await albums.process_batch(
            ordered,
            prompt=vision.NOTEBOOK_PROMPT,
            at_once=albums.NOTEBOOK_AT_ONCE,
            timeout=albums.NOTEBOOK_TIMEOUT_S,
            assemble=False,
            done_one=page_read,
        )
        await vision.log_ai_calls(user.id, outcome.stats)
        if not outcome.pages_ok:
            await log_event(
                session,
                user.id,
                "album_incomplete",
                {
                    "pages": len(ordered),
                    "pages_ok": 0,
                    "skipped": _skip_payload(outcome.skips),
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "cost_usd": vision.total_cost(outcome.stats),
                    "notebook": True,
                },
            )
            await message.answer(
                texts.album_incomplete(
                    [(p.page, p.skip_reason) for p in outcome.skips],
                    texts.PDF_RESEND if pdf else texts.ALBUM_RESEND,
                )
            )
            return

        cut = notebook.lectures_of(
            outcome.pages_ok, outcome.skips, settings.MAX_ALBUM_PAGES, subjects.today()
        )
        bar.set(texts.notebook_making(0, len(cut)))
        finished = 0

        def lecture_done() -> None:
            nonlocal finished
            finished += 1
            bar.set(texts.notebook_making(finished, len(cut)))

        made, failed = await _notebook_lectures(
            message, session, user, cut, outcome.skips, tag, shelf, source_type,
            albums.parts_of(ordered), lecture_done,
        )
        # The last message first: its id is what a page sent again replies to.
        prompt = await _notebook_said(
            message, session, user, made, failed, cut, outcome.skips, tag
        )
        await log_event(
            session,
            user.id,
            limits.NOTEBOOK_READ,
            {
                "notebook": shelf,
                "source_type": source_type,
                "pages": len(ordered),
                "pages_ok": len(outcome.pages_ok),
                "pages_skipped": len(outcome.skips),
                "lectures": len(made),
                "lectures_failed": len(failed),
                "starts": sum(1 for lecture in cut if lecture.started),
                "parts": sum(1 for lecture in cut if lecture.part),
                "dated": sum(1 for lecture in cut if lecture.day is not None),
                "tagged": tag is not None,
                "frames_refused": sum(
                    1 for page in outcome.skips if page.skip_reason not in _NOT_FRAMES
                ),
                # The last message, which the pages it could not read are sent
                # again in reply to (_notebook_asked).
                "prompt": prompt,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "cost_usd": vision.total_cost(outcome.stats),
            },
        )
        # Counted as the person's notebook of the day once it is kept.
        await session.commit()


async def _notebook_lectures(
    message: Message,
    session: AsyncSession,
    user: User,
    cut: list[notebook.Lecture],
    skips: list[albums.PageResult],
    tag: str | None,
    shelf: str,
    source_type: str,
    parts: int,
    lecture_done: Callable[[], None] | None = None,
) -> tuple[list[tuple[Note, notebook.Lecture]], list[notebook.Lecture]]:
    """Every lecture of a notebook made as an album's record is — composed,
    its drawings placed, joined to its subject's lecture of it, explained
    and studied, kept, sent — `_LECTURES_AT_ONCE` at a time, and sent in the
    notebook's order as each is done: a lecture begins once the one that
    many before it is sent, and waits for the one before it to be sent
    before it is. The model is called outside the session, and the session
    used by one lecture at a time: one session cannot be used by two
    coroutines at once.

    A lecture that fails is left out and named in the last message; the
    rest go on. What it wrote is rolled back, and the lectures before it
    are kept already: each is committed before it is sent."""
    lock = asyncio.Lock()
    turns = [asyncio.Event() for _ in cut]
    made: dict[int, Note] = {}
    holes = {page.page: page for page in skips}

    async def make(index: int, lecture: notebook.Lecture) -> None:
        rec = lecture.record
        try:
            if index >= _LECTURES_AT_ONCE:
                await turns[index - _LECTURES_AT_ONCE].wait()
            started = time.monotonic()
            async with lock:
                may_compose = await limits.check_limits(session, user, pages=0) is None
            composition = compose.Composition(rec.markdown)
            if may_compose:
                composition = await compose.compose(rec.markdown)
                await vision.log_ai_calls(user.id, composition.stats)
            markdown, placed = figures.place(composition.markdown, rec.cutouts)

            async with lock:
                joining = (
                    await subjects.joining(
                        session, None, user.id, tag, markdown, rec.margin_notes, None,
                        len(rec.missing_pages),
                    )
                    if tag is not None
                    else None
                )
                may_explain = await limits.check_limits(session, user, pages=0) is None
            explain_skipped = joining is not None and not joining.leads
            explaining, early = explain.Explaining(), None
            if not explain_skipped and may_explain:
                explaining, early = await _explained(
                    user, None, markdown, joining is None
                )

            if index:
                await turns[index - 1].wait()
            async with lock:
                note = _album_note(
                    rec,
                    user=user,
                    sender=None,
                    group_id=None,
                    source_key=None,
                    tag=tag,
                    title=rec.title,
                    markdown=markdown,
                    issues=rec.issues,
                    explaining=explaining,
                    source_type=source_type,
                    notebook_key=shelf,
                )
                session.add(note)
                # Dated by its margin alone: a caption's day is the notebook's,
                # not each lecture's.
                filing = (
                    await subjects.file(
                        session, note, tag, None, joining.lecture if joining else None
                    )
                    if tag is not None
                    else None
                )
                await log_event(
                    session,
                    user.id,
                    "note_processed",
                    _album_processed(
                        rec,
                        source_type=source_type,
                        skips=[holes[page] for page in rec.missing_pages if page in holes],
                        composition=composition,
                        explaining=explaining,
                        parts=parts,
                        placed=placed,
                        markdown=markdown,
                        filing=filing,
                        explain_skipped=explain_skipped,
                        repeat=None,
                        started=started,
                        stats=lecture.stats,
                        notebook_key=shelf,
                    ),
                )
                await session.flush()
                await _keep_figures(session, note, placed)
                # Filed, the line says where; sent without its "#word", the
                # notebook is asked its subject once, in its last message.
                if tag is not None:
                    after = await corpus.tag_line(session, user, note, None, filing)
                else:
                    await corpus.save_topics(session, note)
                    after = ""
                await _saved(session)
                made[index] = note
                await corpus.deliver(message, session, note, user, None, early, after)
                # What delivery kept — the study version, its event — kept
                # now: a later lecture's failure rolls back what is not.
                await session.commit()
        except Exception:
            logger.exception("notebook %s: lecture %d could not be made", shelf, index + 1)
            async with lock:
                await session.rollback()
                await session.refresh(user)
        finally:
            turns[index].set()
            if lecture_done is not None:
                lecture_done()

    await asyncio.gather(*(make(index, lecture) for index, lecture in enumerate(cut)))
    return (
        [(made[index], lecture) for index, lecture in enumerate(cut) if index in made],
        [lecture for index, lecture in enumerate(cut) if index not in made],
    )


async def _notebook_said(
    message: Message,
    session: AsyncSession,
    user: User,
    made: list[tuple[Note, notebook.Lecture]],
    failed: list[notebook.Lecture],
    cut: list[notebook.Lecture],
    skips: list[albums.PageResult],
    tag: str | None,
) -> int | None:
    """The notebook's last message: what it was cut into, by day; where no
    lecture's start was found; what could not be read, each page with why,
    to be sent again in reply to it; what could not be made; then where the
    lectures are — with «Все в группу» under it — or the one question which
    subject they are. The id of the message a reply finds it by, None when
    it could not be sent."""
    text = texts.notebook_done(
        [(plain(note.title), lecture.day) for note, lecture in made],
        [(lecture.pages[0], lecture.pages[-1]) for lecture in cut if lecture.part],
        [(page.page, page.skip_reason or texts.SKIP_ERROR) for page in skips],
        notebook.ranges([page for lecture in failed for page in lecture.pages]),
        tag,
        await corpus.known_tags(session, user) if tag is None else [],
    )
    markup = None
    if tag is not None and made:
        markup = await to_group.all_markup(message, session, made[-1][0])
    chunks = texts.split_message(text)
    sent = None
    for index, chunk in enumerate(chunks):
        try:
            sent = await message.answer(
                chunk, reply_markup=markup if index == len(chunks) - 1 else None
            )
        except Exception:
            logger.warning("a notebook's last message could not be sent", exc_info=True)
            return None
    return getattr(sent, "message_id", None)


async def _notebook_asked(
    session: AsyncSession, user: User, replied: Message
) -> str | None:
    """The notebook whose last message a photo replies to, if it does: found
    through the `notebook_read` event that names the message, as an earlier
    question under a press is found (feedback._asked_before) — nothing kept
    in the process."""
    author = replied.from_user
    if author is None or not author.is_bot:
        return None
    payloads = (
        await session.execute(
            select(Event.payload)
            .where(Event.type == limits.NOTEBOOK_READ, Event.user_id == user.id)
            .order_by(Event.id.desc())
        )
    ).scalars().all()
    for payload in payloads:
        if isinstance(payload, dict) and payload.get("prompt") == replied.message_id:
            shelf = payload.get("notebook")
            return shelf if isinstance(shelf, str) else None
    return None


async def _notebook_page(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    shelf: str,
    page: middlewares.PageFile,
) -> None:
    """A page of a notebook it could not read, sent again in reply to its
    last message (task 63, the CEO's of 2026-10-13): read as a notebook's
    page is, put where its marker stands in its lecture, and the lecture's
    document sent again. The page is named by the number in its caption, or
    is the one page missing. Part of the notebook: its day and the person's
    pages are not asked, the bot's day is."""
    notes = (
        await session.execute(
            select(Note).where(Note.notebook == shelf, Note.user_id == user.id).order_by(Note.id)
        )
    ).scalars().all()
    missing = sorted({number for note in notes for number in note.missing_pages or []})
    if not missing:
        await message.answer(texts.NOTEBOOK_WHOLE)
        return
    named = _PAGE_NUMBER_RE.search(message.caption or "")
    if named is None and len(missing) > 1:
        await message.answer(texts.notebook_page_which(missing))
        return
    number = int(named.group(1)) if named is not None else missing[0]
    if number not in missing:
        await message.answer(texts.notebook_page_not_missing(number, missing))
        return
    note = next(note for note in notes if number in (note.missing_pages or []))

    limit_message = await limits.check_limits(session, user, pages=0)
    if limit_message is not None:
        await message.answer(limit_message)
        return
    if message.document is not None and (message.document.file_size or 0) > _MAX_IMAGE_BYTES:
        await message.answer(texts.IMAGE_TOO_BIG)
        return
    original = (await bot.download(page.file_id)).read()
    compressed = await images.in_worker(
        images.compress, original, settings.IMAGE_MAX_SIDE, settings.IMAGE_QUALITY
    )
    frame = await images.in_worker(photoguard.check_photo_bytes, compressed)
    if not frame.ok:
        await message.answer(frame.reason)
        return

    async with waiting.shown(message):
        started = time.monotonic()
        result, stats = await vision.transcribe_consensus(
            compressed, prompt=vision.NOTEBOOK_PROMPT
        )
        await vision.log_ai_calls(user.id, stats)
        if result is None:
            await message.answer(texts.ERROR_GENERIC)
            return
        if len(result.best.markdown.strip()) < settings.MIN_MARKDOWN_LEN:
            await message.answer(texts.NO_TEXT_FOUND)
            return
        lecture = await session.get(Lecture, note.lecture_id) if note.lecture_id else None
        day = lecture.given_on if lecture is not None and lecture.date_source != "sent" else None
        if not _filled(note, number, result, day):
            logger.warning("notebook %s: no marker for page %d in note %s", shelf, number, note.id)
            await message.answer(texts.NOTEBOOK_PAGE_NOT_PLACED)
            return
        await session.execute(delete(NoteTopic).where(NoteTopic.note_id == note.id))
        session.add_all(
            NoteTopic(note_id=note.id, topic=topic)
            for topic in tags.topics_of(note.title, note.markdown)
        )
        await log_event(
            session,
            user.id,
            "notebook_page_added",
            {
                "notebook": shelf,
                "note_id": note.id,
                "page": number,
                "words": len(result.best.markdown.split()),
                # A start named on it is not cut: the page goes whole into the
                # lecture whose hole it fills. Counted, for the measurement.
                "starts": len(result.lecture_starts),
                "latency_ms": int((time.monotonic() - started) * 1000),
                "cost_usd": vision.total_cost(stats),
            },
        )
        await _saved(session)
        await corpus.deliver(
            message, session, note, user, None,
            after=texts.notebook_page_added(number, plain(note.title)),
        )


def _filled(
    note: Note, number: int, result: vision.TranscriptionResult, day
) -> bool:
    """A notebook's lecture with the page it was missing put where the
    page's marker stands, as read — the lecture is not composed again: its
    explanations point at its text as it was. What the page carries comes
    with it: its findings, what read two ways, its margin but another
    lecture's day. The study version is built again from the new text.
    False when the marker is not there to put the page in."""
    marker = re.compile(rf"\**\[Страница {number} не прочитана\]\**")
    page_markdown = result.best.markdown
    if not marker.search(note.markdown or ""):
        return False
    note.markdown = marker.sub(lambda _: page_markdown, note.markdown, count=1)
    note.missing_pages = [page for page in note.missing_pages or [] if page != number]
    note.page_count = (note.page_count or 0) + 1
    note.issues = list(note.issues or []) + [
        {**asdict(found), "page": number} for found in vision.findings(page_markdown)
    ]
    note.uncertain = list(note.uncertain or []) + [
        {**asdict(u), "page": number} for u in result.best.uncertain
    ]
    note.numeric_divergences = list(note.numeric_divergences or []) + [
        {**asdict(d), "page": number} for d in result.numeric_divergences or []
    ]
    note.margin_notes = list(note.margin_notes or []) + subjects.margin_for(
        result.best.margin_notes, day, subjects.today()
    )
    note.unreadable_count = (note.unreadable_count or 0) + page_markdown.count("[неразборчиво]")
    note.text_agreement = _lower(note.text_agreement, result.text_agreement)
    note.numeric_agreement = _lower(note.numeric_agreement, result.numeric_agreement)
    note.study = None
    return True


def _lower(kept: float | None, new: float | None) -> float | None:
    """A record's agreement is its worst page's."""
    present = [value for value in (kept, new) if value is not None]
    return min(present) if present else None


def _album_note(
    rec: albums.AssembledRecord,
    *,
    user: User,
    sender: User | None,
    group_id: int | None,
    source_key: str | None,
    tag: str | None,
    title: str,
    markdown: str,
    issues: list[dict],
    explaining: explain.Explaining,
    source_type: str,
    notebook_key: str | None = None,
) -> Note:
    """The record of an album, a PDF or one lecture of a notebook, as it is
    kept: the assembled pages, composed and explained."""
    return Note(
        user_id=user.id,
        sender_id=sender.id if sender is not None else None,
        group_id=group_id,
        source_key=source_key,
        notebook=notebook_key,
        tag=tag,
        title=title,
        subject=rec.subject,
        markdown=markdown,
        # The teacher's boxes and the captions stand in the same list, each
        # naming its kind; an explanation names none, as every one stored
        # before them.
        explanations=[asdict(item) for item in explaining.explanations]
        + [asdict(item) for item in explaining.elements]
        + [asdict(item) for item in explaining.captions],
        summary=explaining.summary,
        source_type=source_type,
        page_count=rec.page_count,
        status=rec.status,
        margin_notes=rec.margin_notes,
        uncertain=rec.uncertain,
        issues=issues,
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


def _album_processed(
    rec: albums.AssembledRecord,
    *,
    source_type: str,
    skips: list[albums.PageResult],
    composition: compose.Composition,
    explaining: explain.Explaining,
    parts: int,
    placed: list[tuple[int, bytes]],
    markdown: str,
    filing: subjects.Filing | None,
    explain_skipped: bool,
    repeat: subjects.Repeat | None,
    started: float,
    stats: list,
    notebook_key: str | None = None,
) -> dict:
    """`note_processed` of an album's record, or of a lecture of a notebook,
    which names the notebook (task 63)."""
    payload = {
        "verdict": rec.verdict,
        "page_count": rec.page_count,
        "source_type": source_type,
        "pages_skipped": len(skips),
        # The same four numbers as in album_incomplete, and for the same
        # reason: a page is turned away on these, and now that the record
        # is saved anyway this is the only place they would be kept.
        "skipped": _skip_payload(skips),
        "composed": composition.refused is None and bool(composition.stats),
        "compose_refused": composition.refused,
        "compose_drift": composition.drift,
        "compose_demoted": composition.demoted,
        "compose_unmarked": composition.unmarked,
        "compose_restored": composition.restored,
        "compose_retried": composition.retried,
        "explained": len(explaining.explanations),
        "explain_refused": explaining.refused,
        "explain_unsourced": explaining.unsourced,
        "explain_judged": explaining.judged,
        "elements": len(explaining.elements),
        "elements_dropped": explaining.elements_dropped,
        "captions": len(explaining.captions),
        "captions_dropped": explaining.captions_dropped,
        "summary": explaining.summary is not None,
        "summary_refused": explaining.summary_refused,
        "drawings": rec.drawings,
        "sketched": rec.sketched,
        "lecture_head_cut": rec.lecture_head_cut,
        "lecture_tail_cut": rec.lecture_tail_cut,
        "runs_added": rec.runs_added,
        "read_further": rec.read_further,
        "album_parts": parts,
        "figures": len(placed),
        "charts": charts.count(markdown),
        **_filing_payload(filing, explain_skipped, repeat),
        "latency_ms": int((time.monotonic() - started) * 1000),
        "cost_usd": vision.total_cost(stats + composition.stats + explaining.stats),
    }
    if notebook_key is not None:
        payload["notebook"] = notebook_key
    return payload


def _filing_payload(
    filing: subjects.Filing | None,
    explain_skipped: bool,
    repeat: subjects.Repeat | None = None,
) -> dict:
    """What `note_processed` says of where the record was filed (task 63):
    its lecture, whether that lecture had a notebook already, whether
    explaining was skipped because this one only adds to it, and the words
    of the page photographed twice cut off its head, with the record whose
    last page it was."""
    return {
        "lecture_id": filing.lecture.id if filing is not None else None,
        "lecture_joined": filing.joined if filing is not None else False,
        "explain_skipped": explain_skipped,
        "repeat_cut": repeat.words if repeat is not None else 0,
        "repeat_of": repeat.note_id if repeat is not None else None,
    }


def _still_placed(
    placed: list[tuple[int, bytes]], markdown: str
) -> list[tuple[int, bytes]]:
    """The drawings whose lines stayed when a repeated head was cut."""
    return [(number, png) for number, png in placed if f"[рисунок {number}:" in markdown]


@router.message(F.text, middlewares.is_summon)
async def handle_summon(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group | None = None,
) -> None:
    """A reply in a group that calls the bot on a page or an album somebody
    else sent: "#матан" under it, with the bot's name beside it or not. The
    record is the chat's like any other, filed under the reply's subject and
    paid for by whoever replied, and a second call on the same pages sends the
    record already made — the author's decisions, 2026-09-29."""
    if group is None:
        return
    target = message.reply_to_message
    bot_username = (await bot.me()).username
    tag = tags.from_reply(message.text, bot_username)
    if tag is None:
        # middlewares.heard lets a reply without a subject through only when it
        # names the bot; anything else reaching here is not addressed to it.
        if tags.mentions(message.text, bot_username):
            await log_event(
                session, user.id, "note_summoned", {"outcome": "no_tag"},
                group_id=group.id,
            )
            await message.answer(texts.SUMMON_NEEDS_TAG)
        return

    key = corpus.source_key(target)
    existing = await corpus.recorded(session, group, key)
    if existing is not None:
        await log_event(
            session, user.id, "note_summoned",
            {"outcome": "existing", "note_id": existing.id},
            group_id=group.id,
        )
        await corpus.deliver(message, session, existing, user, group)
        return

    # Being read right now — by their own tagged album, or a call a moment
    # earlier — the pages are not read twice: a second record and a second
    # bill (task 41).
    async with corpus.reading(session, group, key) as ours:
        if not ours:
            await log_event(
                session, user.id, "note_summoned", {"outcome": "reading"},
                group_id=group.id,
            )
            await message.answer(texts.SUMMON_READING)
            return
        await _read_summoned(message, session, user, bot, group, target, tag, key)


async def _read_summoned(
    message: Message,
    session: AsyncSession,
    user: User,
    bot: Bot,
    group: Group,
    target: Message,
    tag: str,
    key: str,
) -> None:
    """The pages a reply called the bot on, once this call is the one reading
    them: an album found whole from what was written down of it, or a single
    page."""
    if target.media_group_id:
        # The reply carries one page of the album; the rest is what the bot
        # wrote down when the album was posted. An album it never saw whole —
        # older than the references are kept, or posted before it could see
        # the chat — is not read with pages missing that nobody would notice.
        pages = await _remembered_album(
            session, group, message.chat.id, target.media_group_id
        )
        if target.message_id not in {page.message_id for page in pages}:
            await log_event(
                session, user.id, "note_summoned", {"outcome": "album_unknown"},
                group_id=group.id,
            )
            await message.answer(texts.SUMMON_ALBUM_UNKNOWN)
            return
        sender = await _sender(session, target, user)
        await log_event(
            session, user.id, "note_summoned",
            {"outcome": "read", "pages": len(pages)},
            group_id=group.id,
        )
        await _process_album(
            message, session, user, pages, group,
            bot=bot, tag=tag, source_key=key, sender=sender,
        )
        return

    page = middlewares.page_file(target)
    if target.document is not None and (
        target.document.file_size or 0
    ) > _MAX_IMAGE_BYTES:
        await message.answer(texts.IMAGE_TOO_BIG)
        return
    sender = await _sender(session, target, user)
    await log_event(
        session, user.id, "note_summoned", {"outcome": "read", "pages": 1},
        group_id=group.id,
    )
    original = (await bot.download(page.file_id)).read()
    compressed = await images.in_worker(
        images.compress, original, settings.IMAGE_MAX_SIDE, settings.IMAGE_QUALITY
    )
    await _read_photo(
        message, session, user, group, tag, original, compressed, page, key,
        sender=sender,
    )


async def _sender(session: AsyncSession, target: Message, user: User) -> User | None:
    """Who sent the pages a reply called the bot on, when that is somebody
    else: the record counts for them in the group's week (task 72), and the
    one who replied still pays. A bot, an anonymous admin or a channel —
    the last two post on behalf of a chat — counts for whoever replied."""
    author = target.from_user
    if (
        author is None
        or author.is_bot
        or target.sender_chat is not None
        or author.id == user.tg_id
    ):
        return None
    return await middlewares.registered(session, author)


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
