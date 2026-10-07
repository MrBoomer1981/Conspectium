"""Aiogram handlers."""

import asyncio
import logging
import time
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

from app.bot import albums, corpus, middlewares, subjects, tags, texts
from app.core.config import settings
from app.core.events import log_event
from app.db.models import Group, GroupPage, Note, NoteFigure, User
from app.services import (
    compose,
    docx,
    explain,
    figures,
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
# An image sent as a file: the most Telegram lets a bot download.
_MAX_IMAGE_BYTES = 20 * 1024 * 1024

# How long a page of a group's album can still be called on by a reply. A
# lecture is reached for within days of it — the author's choice, 2026-09-29.
_PAGES_KEPT = timedelta(days=7)


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
    # The subject the photo was sent with; in a private chat it spares the
    # question afterwards. In a group it is what makes the photo the bot's at
    # all. middlewares.heard stops an untagged one before a session is even
    # opened, and this keeps a group's record from ever being made without
    # its subject whatever reaches here. An album is judged whole, in
    # _process_album, and a page sent without its subject can still be called
    # on by a reply that carries one — handle_summon.
    tag = tags.from_caption(message.caption)
    if group is not None and tag is None and not message.media_group_id:
        return
    source_key = corpus.source_key(message) if group is not None else None

    # Step 0: an album arrives as separate messages sharing a media_group_id.
    # Buffer this page and let a single update assemble the whole batch; the
    # individual-photo steps 4-16 do not run for an album page. The page goes
    # in as Telegram's reference and is not downloaded here: the update that
    # claims the batch fetches the pages once it knows the album is to be read,
    # so in a group an album nobody tagged is never fetched at all.
    if message.media_group_id:
        # Announced first: albums.collect() times the album from here.
        albums.announce(message.media_group_id, message.message_id)
        if group is not None:
            await _remember_page(session, group, message, page)
        albums.add_page(
            message.media_group_id,
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
        pages = await albums.collect(message.media_group_id)
        if pages is None:
            return  # another update owns this batch
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
        compressed = await asyncio.to_thread(
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

    await message.answer(texts.PROCESSING)

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

    # The drawings recognition framed, cut out of the image it read while the
    # image is still here — rule 3 keeps nothing else of it. In a thread:
    # filtering pixels is CPU work, and the webhook must not stall on it.
    cutouts = await asyncio.to_thread(
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

    # The lecture this page is a notebook of, if its subject has it already
    # (task 63): a notebook that will only add to another is not explained —
    # its lecture's document carries the base's explanations.
    joining = None
    if tag is not None:
        joining = await subjects.joining(
            session, group_id, user.id, tag, markdown, result.best.margin_notes, caption
        )
    explain_skipped = joining is not None and not joining.leads

    # Step 12b: stage three, what the bot adds of its own — hard places
    # explained, each with the sources the search gave, and the record summed
    # up. Over the composed text and never the photograph, stored apart from
    # the author's text and printed as the bot's. Rule 6 again: a third call
    # is still a call, and the kill switch and the cost cap decide first.
    explaining = explain.Explaining()
    if (
        not explain_skipped
        and await limits.check_limits(session, user, pages=0, group=group) is None
    ):
        explaining = await explain.explain(markdown)
        await vision.log_ai_calls(user.id, explaining.stats, group_id=group_id)

    # Step 13: persist the record. "rejected" already exited at step 10, so the
    # verdict here is "clean" or "needs_review". Dataclasses are flattened to
    # plain dicts — JSONB won't take them as they are.
    note = Note(
        user_id=user.id,
        sender_id=sender.id if sender is not None else None,
        group_id=group_id,
        source_key=source_key,
        tag=tag,
        title=result.best.title,
        subject=result.best.subject,
        markdown=markdown,
        # The teacher's boxes stand in the same list, each naming its kind;
        # an explanation names none, as every one stored before them.
        explanations=[asdict(item) for item in explaining.explanations]
        + [asdict(item) for item in explaining.elements],
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
            "compose_retried": composition.retried,
            "explained": len(explaining.explanations),
            "explain_refused": explaining.refused,
            "explain_unsourced": explaining.unsourced,
            "explain_judged": explaining.judged,
            "elements": len(explaining.elements),
            "elements_dropped": explaining.elements_dropped,
            "summary": explaining.summary is not None,
            "summary_refused": explaining.summary_refused,
            "drawings": figures.count(result.best.markdown),
            "figures": len(placed),
            "runs_added": result.runs_added,
            "read_further": int(result.read_further),
            **_filing_payload(filing, explain_skipped),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "cost_usd": vision.total_cost(stats + composition.stats + explaining.stats),
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
    await corpus.send_record(message, session, note)

    # Step 17: which subject does this belong to. Last, so the question is
    # what the user is looking at when they reply.
    await corpus.ask_for_tag(message, session, user, note, group, filing)


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
    await corpus.send_record(message, session, note)
    await corpus.ask_for_tag(message, session, user, note, group, filing)


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
    bot: Bot | None, pages: list[albums.PageInput]
) -> list[albums.PageInput]:
    """Download and compress the pages still held as references, all at once.

    A page that cannot be fetched stays empty, and the recognition reports it
    as a page that could not be opened: the record is delivered with the hole
    named in it rather than the album lost."""

    async def fetch(page: albums.PageInput) -> albums.PageInput:
        if page.data or page.file_id is None:
            return page
        try:
            original = (await bot.download(page.file_id)).read()
            compressed = await asyncio.to_thread(
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
) -> None:
    """Assemble a buffered album into one Note. The single-photo pipeline never
    runs for album pages — this is the batch equivalent, and the per-page work
    (frame check, recognition, mathcheck) happens in albums.process_batch,
    which never touches the database.

    `tag` is the subject a reply called the bot with, for an album that came
    without one (handle_summon), and `sender` whoever sent that album;
    `source_key` is what a group's record is made of. Pages still held as
    Telegram's references are downloaded with `bot`."""
    # In a group an album is the bot's only when one of its pages carries a
    # "#word" in its caption, or a reply called the bot on it; without one it
    # is people sharing photos, and the bot says nothing — before the size
    # check too, which would answer.
    tag = tag or albums.tag_of(pages)
    if group is not None and tag is None:
        return
    group_id = group.id if group is not None else None
    caption = albums.caption_of(pages)

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
    if await limits.check_limits(session, user, pages=0, group=group) is None:
        composition = await compose.compose(rec.markdown)
        await vision.log_ai_calls(user.id, composition.stats, group_id=group_id)

    # Every page's drawings back where their lines stand, numbered through
    # the record — after composing, which never saw them.
    markdown, placed = figures.place(composition.markdown, rec.cutouts)

    # The lecture this album is a notebook of, as for a photo (task 63).
    joining = None
    if tag is not None:
        joining = await subjects.joining(
            session, group_id, user.id, tag, markdown, rec.margin_notes, caption,
            len(rec.missing_pages),
        )
    explain_skipped = joining is not None and not joining.leads

    # Stage three once over the whole record too, for the same reason.
    explaining = explain.Explaining()
    if (
        not explain_skipped
        and await limits.check_limits(session, user, pages=0, group=group) is None
    ):
        explaining = await explain.explain(markdown)
        await vision.log_ai_calls(user.id, explaining.stats, group_id=group_id)

    note = Note(
        user_id=user.id,
        sender_id=sender.id if sender is not None else None,
        group_id=group_id,
        source_key=source_key,
        tag=tag,
        title=rec.title,
        subject=rec.subject,
        markdown=markdown,
        # The teacher's boxes stand in the same list, each naming its kind;
        # an explanation names none, as every one stored before them.
        explanations=[asdict(item) for item in explaining.explanations]
        + [asdict(item) for item in explaining.elements],
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
            "compose_retried": composition.retried,
            "explained": len(explaining.explanations),
            "explain_refused": explaining.refused,
            "explain_unsourced": explaining.unsourced,
            "explain_judged": explaining.judged,
            "elements": len(explaining.elements),
            "elements_dropped": explaining.elements_dropped,
            "summary": explaining.summary is not None,
            "summary_refused": explaining.summary_refused,
            "drawings": rec.drawings,
            "lecture_head_cut": rec.lecture_head_cut,
            "lecture_tail_cut": rec.lecture_tail_cut,
            "runs_added": rec.runs_added,
            "read_further": rec.read_further,
            "figures": len(placed),
            **_filing_payload(filing, explain_skipped),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "cost_usd": vision.total_cost(
                outcome.stats + composition.stats + explaining.stats
            ),
        },
        group_id=group_id,
    )

    await session.flush()  # note.id, for the file name, the caption, the drawings
    await _keep_figures(session, note, placed)
    await corpus.send_record(message, session, note)

    # What follows the document is what only the photographer can act on: the
    # pages it went out without. The rest is in the document or nowhere, as on
    # the photo path.
    if outcome.skips:
        await message.answer(
            texts.album_partial([(p.page, p.skip_reason) for p in outcome.skips])
        )

    await corpus.ask_for_tag(message, session, user, note, group, filing)


def _filing_payload(filing: subjects.Filing | None, explain_skipped: bool) -> dict:
    """What `note_processed` says of where the record was filed (task 63):
    its lecture, whether that lecture had a notebook already, and whether
    explaining was skipped because this one only adds to it."""
    return {
        "lecture_id": filing.lecture.id if filing is not None else None,
        "lecture_joined": filing.joined if filing is not None else False,
        "explain_skipped": explain_skipped,
    }


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
        await corpus.send_record(message, session, existing)
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
    compressed = await asyncio.to_thread(
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
