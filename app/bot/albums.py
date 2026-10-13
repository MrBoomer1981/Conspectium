"""In-process album buffer and batch assembly.

Telegram delivers an album as separate messages that share a media_group_id,
each its own webhook update with its own DB session. Pages are buffered here
until the group goes quiet, then one update assembles the whole batch. A send
of more than ten pages arrives as several albums, and they are one batch:
see _send_of (task 81).

Nothing in this module touches the database — the handler does the writes.
See CLAUDE.md -> Sessions and transactions.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import time
from dataclasses import asdict, dataclass, field, replace

from app.bot import subjects, texts
from app.core.config import settings
from app.services import figures, images, lectures, mathcheck, photoguard, sketches, vision
from app.services.vision import CallStats, Transcription

logger = logging.getLogger(__name__)

# Wait this long with no *new* page before assembling the batch. Measured from
# the last arrival, not as a single fixed sleep. It was set when each page was
# downloaded and compressed before it reached the buffer, which over a slow link
# took seconds: at 1.0 s the first page decided the album was over and claimed
# the batch alone — one album arrived as four one-page records. A page is
# buffered on arrival now and downloaded once the batch is claimed, so the
# window only has to cover Telegram's own spacing; 3 s stays because it was
# measured and nothing has been measured since.
_QUIET_SECONDS = 3.0

# How often the quiet window is re-checked. Only an upper bound: the wait is
# shortened to land exactly when the window expires, so a fast album is not
# delayed by the poll interval.
_POLL_SECONDS = 0.3

# Telegram puts at most ten photographs in an album. A send of more arrives
# as several albums, every one but the last holding ten, each a media group
# of its own — and a page left over after the tens can come as a photo with
# no media group at all (task 81).
TELEGRAM_ALBUM_MAX = 10

# How long an album of exactly ten waits, with nothing new from its sender,
# for the rest of its send. A phone sends each album of a send once its
# photographs are uploaded: thirty-two pages on 2026-10-08 brought the next
# album 19.1 s after the last page of the one before, twice, and at 15 s
# they were three records (task 85). Three times that, for an upload twice
# as slow. Two sends of twelve the same day, uploaded before they went,
# came 0.07 s and 0.45 s apart. Every album of ten pays it whether or not
# more comes — a minute, on a record that takes several.
_CONTINUE_S = 60.0

# Hard ceiling from the send's first page: a stream that never goes quiet
# must not be waited on for ever. One _CONTINUE_S for every album a send
# of MAX_ALBUM_PAGES holds, and one more, so a send that keeps coming is
# never cut by it — 240 s at thirty pages. A waiting page holds no
# connection (handlers.handle_photo), only its place in memory.
_COLLECT_MAX_S = (
    math.ceil(settings.MAX_ALBUM_PAGES / TELEGRAM_ALBUM_MAX) + 1
) * _CONTINUE_S
# The same for a send into a private chat, which may be a whole notebook of
# NOTEBOOK_MAX_PAGES (task 63) — 660 s at a hundred pages.
_NOTEBOOK_COLLECT_MAX_S = (
    math.ceil(settings.NOTEBOOK_MAX_PAGES / TELEGRAM_ALBUM_MAX) + 1
) * _CONTINUE_S

# Ten pages at three runs each under Semaphore(10) is three waves of one run's
# worst case — five since a page may ask for two runs more to read itself
# whole (vision.MORE_RUNS, task 65), fifteen since a send of thirty pages is
# one album (task 81). Computed rather than written down:
# vision's call timeout is a setting now, and a ceiling that did not follow it
# would cut a slow album short. Normative, not an estimate — the margin is not
# to be lowered (PLAN.md task 10).
def _waves(pages: int, runs: int, slots: int) -> int:
    """How many times the semaphore fills before every call has been made. A
    function, not an expression, because the rounding only matters when the
    calls do not divide evenly into slots — and the settings this process was
    started with are exactly the case where they do."""
    return math.ceil(pages * runs / slots)


# A page that describes a sketch makes sketches.RUNS calls more (task 101),
# after its runs and on the same slots: counted where they are made.
_WAVES = _waves(
    settings.MAX_ALBUM_PAGES,
    settings.VISION_RUNS
    + vision.MORE_RUNS
    + (sketches.RUNS if settings.SKETCHES_ENABLED else 0),
    vision.API_SLOTS,
)
_ALBUM_TIMEOUT_S = int(_WAVES * vision.RUN_WORST_CASE_S * vision.TIMEOUT_MARGIN)

# A notebook's pages are read this many at a time (task 63): its runs keep
# the bot's API_SLOTS full — four pages are twelve runs — while another
# chat's album, asked for meanwhile, waits behind one window of them rather
# than behind a hundred pages ("Scale debt").
NOTEBOOK_AT_ONCE = 4
# Its ceiling, as the album's: every wave of NOTEBOOK_MAX_PAGES' runs.
_NOTEBOOK_WAVES = _waves(
    settings.NOTEBOOK_MAX_PAGES,
    settings.VISION_RUNS
    + vision.MORE_RUNS
    + (sketches.RUNS if settings.SKETCHES_ENABLED else 0),
    vision.API_SLOTS,
)
NOTEBOOK_TIMEOUT_S = int(
    _NOTEBOOK_WAVES * vision.RUN_WORST_CASE_S * vision.TIMEOUT_MARGIN
)


@dataclass
class PageInput:
    # The compressed page. Empty until the batch is claimed and the page is
    # downloaded by `file_id` (handlers._fetch_pages): an album is buffered as
    # Telegram's references, so one nobody tagged in a group is never fetched.
    data: bytes
    message_id: int
    chat_id: int
    # None for a photo sent apart from the album it continues (task 81).
    media_group_id: str | None
    bytes_before: int
    bytes_after: int
    # None for an image sent as a file: Telegram gives a photo's size, not a
    # file's.
    width: int | None
    height: int | None
    # The "#word" in this page's caption. Telegram puts an album's caption on
    # one page only, so most pages carry None; see tag_of.
    tag: str | None = None
    # The caption itself, for the lecture's date written in it — "#матан
    # 12.09" (task 63); see caption_of.
    caption: str | None = None
    file_id: str | None = None
    # A PDF's page keeps its number in the PDF (task 100), so a blank page
    # left out does not renumber the rest, and a message that names a page
    # names the PDF's. None for a photograph: its place in the album is its
    # number.
    number: int | None = None


def tag_of(pages: list[PageInput]) -> str | None:
    """The subject an album was sent with: the tag of the first page, in page
    order, that carries one. In a group chat an album without one is not the
    bot's to take."""
    for page in sorted(pages, key=lambda p: p.message_id):
        if page.tag:
            return page.tag
    return None


def caption_of(pages: list[PageInput]) -> str | None:
    """The caption an album was sent with — the first in page order, the one
    tag_of reads its subject from."""
    for page in sorted(pages, key=lambda p: p.message_id):
        if page.caption:
            return page.caption
    return None


# Pages handed in by their updates.
_buffer: dict[str, list[PageInput]] = {}
# Pages Telegram has told us about, handed in or not. This is the authority
# on what the album contains; _buffer only says how much of it is ready.
_announced: dict[str, set[int]] = {}
_first_page_at: dict[str, float] = {}
_last_page_at: dict[str, float] = {}
# Groups already handed to a caller, with when. A page that turns up after its
# batch went out is dropped rather than allowed to open a second record.
_claimed: dict[str, float] = {}
# Who sent each album still waiting: its chat, and its sender's Telegram id.
# The albums of one send are found by it (task 81); an album announced
# without one — a reply's call on pages written down — is a send of its own.
_sender: dict[str, tuple[int, int]] = {}


def announce(
    media_group_id: str, message_id: int, sender: tuple[int, int] | None = None
) -> None:
    """Register a page the moment its update arrives, before anything else is
    done with it.

    This was the whole point of the two steps while each page was fetched and
    compressed before it reached `_buffer`, which took seconds per photo:
    timing the debounce from the buffer measured our own download speed, and
    the first page to finish saw a quiet album and claimed the batch alone
    while the rest were still in flight. A page is handed in right after this
    now — in a group, after its reference is written down — and the batch is
    still timed from here, which measures what it is supposed to.

    `sender`, the chat and the Telegram id of whoever sent the page, is what
    joins the albums of one send.
    """
    now = time.monotonic()
    _prune_claimed(now)
    if media_group_id in _claimed:
        return
    _announced.setdefault(media_group_id, set()).add(message_id)
    if sender is not None:
        _sender.setdefault(media_group_id, sender)
    _first_page_at.setdefault(media_group_id, now)
    _last_page_at[media_group_id] = now


def collecting(sender: tuple[int, int]) -> bool:
    """Whether an album this person sent into this chat is still being
    collected — a photo they send now may be the rest of it (task 81)."""
    return any(_sender.get(group) == sender for group in _announced)


def apart(message_id: int) -> str:
    """What a photo sent apart from an album is buffered under: an album of
    its own, of one page, which joins the send before it when that one may
    go on (task 81)."""
    return f"photo:{message_id}"


def parts_of(pages: list[PageInput]) -> int:
    """How many albums, and photos sent apart, a batch arrived as."""
    return len({page.media_group_id or page.message_id for page in pages})


def add_page(media_group_id: str, page: PageInput) -> None:
    """The page itself, as a reference the batch's owner downloads. Announcing
    first is the normal path; a page that was never announced is taken as its
    own announcement so the buffer can never be fed behind the registry's
    back."""
    if media_group_id in _claimed:
        logger.warning(
            "page %d arrived after album %s was assembled; dropped",
            page.message_id,
            media_group_id,
        )
        return
    if page.message_id not in _announced.get(media_group_id, ()):
        announce(media_group_id, page.message_id)
    _buffer.setdefault(media_group_id, []).append(page)


def reset() -> None:
    """Drop every album in flight. The buffer lives in the process, so a
    restart does exactly this in production: an unfinished album is lost, which
    is the accepted trade for not introducing Redis for one user."""
    for registry in (
        _buffer, _announced, _first_page_at, _last_page_at, _claimed, _sender
    ):
        registry.clear()


def _prune_claimed(now: float) -> None:
    """A claimed group is only remembered long enough to catch stragglers."""
    for group, when in list(_claimed.items()):
        if now - when > max(_COLLECT_MAX_S, _NOTEBOOK_COLLECT_MAX_S):
            del _claimed[group]


def _pages(send: list[str]) -> int:
    return sum(len(_announced[group]) for group in send)


def _tag(send: list[str]) -> str | None:
    return tag_of([page for group in send for page in _buffer.get(group, ())])


def _day(send: list[str]):
    """The day the send's caption names, "#матан 12.09" — None without one."""
    caption = caption_of([page for group in send for page in _buffer.get(group, ())])
    if not caption:
        return None
    day = subjects.day_of(caption, [], subjects.today())
    return day.value if day.source == "caption" else None


def private(group: str) -> bool:
    """Whether an album was sent into a private chat: Telegram gives a
    private chat its person's own id."""
    sender = _sender.get(group)
    return sender is not None and sender[0] == sender[1]


def _most(send: list[str]) -> int:
    """The pages a send may hold: a private chat's may be a whole notebook
    (task 63), a group's an album's."""
    return settings.NOTEBOOK_MAX_PAGES if private(send[0]) else settings.MAX_ALBUM_PAGES


def _follows(send: list[str], group: str) -> bool:
    """Whether an album is the rest of the send before it. Telegram fills
    every album of a send but the last, so a send that ends on fewer than
    ten pages has ended. So has one the album would take past the pages a
    send may hold: the album begins a send of its own, and thirty-five
    pages are two records rather than one refused. And an album whose
    "#word" is not the send's is a send of its own — two subjects sent in a
    breath are two lectures — and so is one whose caption names another
    day than the send's: two lectures, each dated (task 63)."""
    if len(_announced[send[-1]]) < TELEGRAM_ALBUM_MAX:
        return False
    if _pages(send) + len(_announced[group]) > _most(send):
        return False
    ours, its = _tag(send), _tag([group])
    if ours is not None and its is not None and ours != its:
        return False
    day, its_day = _day(send), _day([group])
    return day is None or its_day is None or day == its_day


def _send_of(media_group_id: str) -> list[str]:
    """The albums of the send this one belongs to, in page order (task 81):
    those its sender sent into its chat that are still waiting, cut where a
    send ends (_follows).

    Worked out over every album still waiting each time it is asked, never
    fixed when a page arrives: pages are registered in the order their
    updates finish their database work, which is not quite the order they
    came in, and only a send that has gone quiet has all of its pages."""
    sender = _sender.get(media_group_id)
    if sender is None:
        return [media_group_id]
    theirs = sorted(
        (group for group in _announced if _sender.get(group) == sender),
        key=lambda group: min(_announced[group]),
    )
    send: list[str] = []
    for group in theirs:
        if send and not _follows(send, group):
            if media_group_id in send:
                return send
            send = []
        send.append(group)
    return send


def _open(send: list[str]) -> bool:
    """Whether more of a send may be on its way: it ends on a full album and
    has room for another page."""
    return (
        send[-1] in _sender
        and len(_announced[send[-1]]) >= TELEGRAM_ALBUM_MAX
        and _pages(send) < _most(send)
    )


def _collect_max(send: list[str]) -> float:
    return _NOTEBOOK_COLLECT_MAX_S if private(send[0]) else _COLLECT_MAX_S


def _forget(send: list[str]) -> list[PageInput] | None:
    now = time.monotonic()
    pages: list[PageInput] = []
    for group in send:
        pages.extend(_buffer.pop(group, ()))
        _announced.pop(group, None)
        _sender.pop(group, None)
        _first_page_at.pop(group, None)
        _last_page_at.pop(group, None)
        _claimed[group] = now
    pages.sort(key=lambda page: page.message_id)
    # None, not an empty list: the caller reads None as "not mine, say
    # nothing", and process_batch has nothing to wait on for an empty batch.
    return pages or None


async def collect(media_group_id: str) -> list[PageInput] | None:
    """Block until the album stops growing, then hand the whole batch to one
    caller — every album of its send (task 81). Every other caller for the
    same batch gets None and must return without replying — otherwise the
    batch is processed once per page.

    Two conditions have to hold: _QUIET_SECONDS with nothing new announced, so
    the album has stopped growing — _CONTINUE_S when the send ends on a full
    album, which the next of it may follow — and every announced page handed
    in, so nothing still in flight is left behind. The _COLLECT_MAX_S
    ceiling bounds the wait either way — an update that never hands its page
    in must not strand the pages that did."""
    while True:
        if media_group_id not in _announced:
            return None  # another caller already claimed this batch
        now = time.monotonic()
        send = _send_of(media_group_id)
        quiet_for = now - max(_last_page_at[group] for group in send)
        window = _CONTINUE_S if _open(send) else _QUIET_SECONDS
        handed_in = all(
            len(_buffer.get(group, ())) >= len(_announced[group]) for group in send
        )
        if quiet_for >= window and handed_in:
            break
        ceiling = _collect_max(send)
        if now - min(_first_page_at[group] for group in send) >= ceiling:
            logger.warning(
                "album %s: %d of %d pages ready after %ds, assembling anyway",
                send[0],
                sum(len(_buffer.get(group, ())) for group in send),
                _pages(send),
                ceiling,
            )
            break
        # Never overshoot the moment the quiet window expires.
        await asyncio.sleep(min(_POLL_SECONDS, max(window - quiet_for, 0.01)))
    # Exactly one of these per send is what a healthy album looks like. Two
    # means the batch was claimed twice and the album split into separate
    # records — the failure that took three attempts to find, and which
    # nothing in the log could previously tell from one slow page. A send of
    # several albums names the gap before each: what _CONTINUE_S is measured
    # against.
    gaps = [
        _first_page_at[later] - _last_page_at[earlier]
        for earlier, later in zip(send, send[1:])
    ]
    logger.info(
        "album %s: batch closed, %d of %d pages%s, %.1fs since the first",
        send[0],
        sum(len(_buffer.get(group, ())) for group in send),
        _pages(send),
        f" in {len(send)} albums, "
        + ", ".join(f"{gap:.2f}s" for gap in gaps)
        + " apart"
        if gaps
        else "",
        time.monotonic() - min(_first_page_at[group] for group in send),
    )
    # No await between the decision and this pop: exactly one caller gets the
    # list, every other one comes back around and finds its album gone.
    return _forget(send)


@dataclass
class PageResult:
    page: int
    stats: list[CallStats]
    skip_reason: str | None = None
    # Set when the page is in the record but nothing confirmed its reading:
    # the runs disagreed badly, or only one came back. A skip and this are
    # different answers to the same doubt — one throws the page away, the
    # other keeps it and says so.
    unverified_reason: str | None = None
    transcription: Transcription | None = None
    report: mathcheck.Report | None = None
    verdict: str | None = None
    text_agreement: float | None = None
    numeric_agreement: float | None = None
    numeric_divergences: list | None = None
    photo_sharpness: float | None = None
    photo_line_height: float | None = None
    photo_paper_fraction: float | None = None
    photo_contrast: float | None = None
    # The page's drawings, taken from its image before the image is let go,
    # and how many of its sketches the runs framed alike (task 101).
    cutouts: list[figures.Cutout] = field(default_factory=list)
    sketched: int = 0
    # Where a lecture begins on the page, as every run read it (task 64).
    lecture_starts: list[str] = field(default_factory=list)
    # Runs the page asked for to read itself whole, and whether it was read
    # further for them (task 65).
    runs_added: int = 0
    read_further: bool = False

    @property
    def ok(self) -> bool:
        return self.skip_reason is None


def reason_en(frame: photoguard.PhotoVerdict) -> str:
    """Which of the four thresholds refused the frame, in English for the log.

    photoguard's own `reason` is the sentence shown to the user, in Russian.
    Recomputing the name from the numbers rather than translating that
    sentence keeps this from breaking silently the day its wording changes.
    """
    if frame.paper_fraction < photoguard.MIN_PAPER_FRACTION:
        return "paper fraction"
    if frame.sharpness < photoguard.MIN_SHARPNESS:
        return "sharpness"
    if frame.contrast < photoguard.MIN_CONTRAST:
        return "contrast"
    if (
        frame.line_height_px != photoguard.UNMEASURED_LINE_HEIGHT
        and frame.line_height_px < photoguard.MIN_LINE_HEIGHT_PX
    ):
        return "line height"
    return "none"


def _log_refusal(page: int, frame: photoguard.PhotoVerdict) -> None:
    # Against the thresholds, because the number alone says nothing about how
    # far off it was.
    logger.warning(
        "album page %d refused by the frame check (%s): "
        "line height %.1f/%d, sharpness %.0f/%.0f, "
        "paper %.0f%%/%.0f%%, contrast %.1f/%.0f",
        page,
        reason_en(frame),
        frame.line_height_px, photoguard.MIN_LINE_HEIGHT_PX,
        frame.sharpness, photoguard.MIN_SHARPNESS,
        frame.paper_fraction * 100, photoguard.MIN_PAPER_FRACTION * 100,
        frame.contrast, photoguard.MIN_CONTRAST,
    )


def _frame_refused(page: int, frame: photoguard.PhotoVerdict, reason: str,
                   stats: list[CallStats]) -> PageResult:
    """A skipped page, carrying the frame metrics whatever skipped it.

    They used to be dropped, so the album was the one path where a page could
    be turned away and leave nothing to check the decision against — while a
    single photo wrote all four to photo_rejected. A page that passed the
    frame and then failed recognition lost them too, for no reason: the
    numbers had already been measured.
    """
    return PageResult(
        page,
        stats,
        skip_reason=reason,
        photo_sharpness=frame.sharpness,
        photo_line_height=frame.line_height_px,
        photo_paper_fraction=frame.paper_fraction,
        photo_contrast=frame.contrast,
    )


async def refused_frames(ordered: list[PageInput]) -> list[PageResult]:
    """The pages of an album the frame check turns away, checked before any
    page is read — numbered in the order given, or by their place in their
    PDF.

    A refused frame is the one reason a page is lost that only the
    photographer can fix, and at this point nothing has been spent. So the
    album is not read with a hole in it; it waits to come again, whole
    (task 43 — record 45 came back without its first page and a line saying
    "send it separately", which is not being asked to retake it). A frame that
    cannot even be opened is not refused here: process_page reports it as a
    page that failed, as it always has.
    """

    async def check(page_input: PageInput, page: int) -> PageResult | None:
        try:
            frame = await images.in_worker(photoguard.check_photo_bytes, page_input.data)
        except Exception:
            logger.exception("album page %d: the frame could not be checked", page)
            return None
        if frame.ok:
            return None
        _log_refusal(page, frame)
        return _frame_refused(page, frame, frame.reason, [])

    checked = await asyncio.gather(
        *(
            check(page_input, page_input.number or place)
            for place, page_input in enumerate(ordered, 1)
        )
    )
    return [result for result in checked if result is not None]


async def process_page(
    page_input: PageInput, page: int, prompt: str | None = None
) -> PageResult:
    """One album page through the pipeline minus the database and minus any
    reply: frame check, three recognition runs, the result gates, then the
    arithmetic check. Returns either a skip reason or the data for the record.
    The CallStats list is returned in every case — empty only when the frame
    was rejected before any model call. `prompt` is a notebook's (task 63);
    an album's page is read with PROMPT_FILE's."""
    frame = photoguard.check_photo_bytes(page_input.data)

    def refused(reason: str, stats: list[CallStats]) -> PageResult:
        return _frame_refused(page, frame, reason, stats)

    if not frame.ok:
        # refused_frames has already asked for this page again before the
        # album was read; a frame refused here is one that got past that.
        _log_refusal(page, frame)
        return refused(frame.reason, [])

    result, stats = await vision.transcribe_consensus(
        page_input.data, **({"prompt": prompt} if prompt else {})
    )
    if result is None:
        # Not one run came back readable: there is no text to keep.
        return refused(texts.SKIP_UNRECOGNIZED, stats)
    if len(result.best.markdown.strip()) < settings.MIN_MARKDOWN_LEN:
        return refused(texts.SKIP_NO_TEXT, stats)

    # The page's drawings, taken while its image is still here; the record
    # places them after composing. A sketch is drawn again from the page
    # (task 101) — three calls for where each is and what its labels say,
    # part of reading the page, and every one in the page's stats — or, under
    # a prompt that frames drawings (v8), cut out.
    sketched: list = []
    if settings.SKETCHES_ENABLED and figures.count(result.best.markdown):
        sketched, sketch_stats = await sketches.read(page_input.data, result.best.markdown)
        stats = stats + sketch_stats
        cutouts = await images.in_worker(
            figures.redraw, page_input.data, result.best.markdown, sketched
        )
    else:
        cutouts = await images.in_worker(
            figures.cut, page_input.data, result.best.markdown, result.best.drawings
        )

    # A page is dropped for the frame, for nothing parsed, and for no text —
    # and for nothing else. Disagreement between the runs used to drop it too,
    # and the photographs behind those refusals turned out to carry perfectly
    # legible text: what the disagreement measured was how the runs laid the
    # page out, not whether they could read it. The page is kept and marked.
    unverified = None
    if result.text_agreement is None:
        unverified = texts.UNVERIFIED_ONE_RUN
    elif result.verdict == "rejected":
        unverified = texts.UNVERIFIED_DIVERGED
        logger.warning(
            "album page %d kept unverified: text_agreement %.3f",
            page,
            result.text_agreement,
        )

    # Each finding is kept with the text it is about, which the document sets
    # it under once the pages are joined and composed.
    report = mathcheck.Report(issues=vision.findings(result.best.markdown))
    # Two things lower a verdict here and nothing raises one: a page nobody
    # could check, and a critical arithmetic finding. "rejected" arrives as
    # one of the first, because that band no longer removes anything.
    verdict = result.verdict
    if unverified or any(i.severity == "critical" for i in report.issues):
        verdict = "needs_review"

    return PageResult(
        page=page,
        stats=stats,
        transcription=result.best,
        report=report,
        verdict=verdict,
        unverified_reason=unverified,
        text_agreement=result.text_agreement,
        numeric_agreement=result.numeric_agreement,
        numeric_divergences=result.numeric_divergences,
        photo_sharpness=frame.sharpness,
        photo_line_height=frame.line_height_px,
        photo_paper_fraction=frame.paper_fraction,
        photo_contrast=frame.contrast,
        cutouts=cutouts,
        sketched=sum(sketch is not None for sketch in sketched),
        lecture_starts=result.lecture_starts,
        runs_added=result.runs_added,
        read_further=result.read_further,
    )


@dataclass
class AssembledRecord:
    title: str
    subject: str | None
    markdown: str
    status: str  # "ready" | "needs_review"
    verdict: str  # "clean" | "needs_review" — for the note_processed event
    uncertain: list[dict]
    issues: list[dict]
    numeric_divergences: list[dict]
    margin_notes: list[str]
    unreadable_count: int
    text_agreement: float | None
    numeric_agreement: float | None
    photo_sharpness: float | None
    photo_line_height: float | None
    photo_paper_fraction: float | None
    photo_contrast: float | None
    page_count: int
    # The pages that were not read, by number. The markdown already carries a
    # marker where each of them would have been; this is what the callout and
    # the chat message are built from, so neither counts anything of its own.
    missing_pages: list[int]
    # The pages that are in the record with nothing to confirm their reading.
    unverified_pages: list[dict]
    # Every page's drawings in page order, for figures.place, and how many the
    # pages only described — the two numbers note_processed reports.
    cutouts: list[figures.Cutout] = field(default_factory=list)
    drawings: int = 0
    sketched: int = 0
    # Lines cut off the first page — the lecture before — and off the last —
    # the lecture after (task 64); what note_processed reports.
    lecture_head_cut: int = 0
    lecture_tail_cut: int = 0
    # Runs the pages asked for to read themselves whole, and how many pages
    # were read further for them (task 65); what note_processed reports.
    runs_added: int = 0
    read_further: int = 0


@dataclass
class AlbumOutcome:
    stats: list[CallStats]
    # The refused pages themselves, not just their reasons: a refusal has to
    # be arguable, and the four frame metrics are what it is argued with.
    skips: list[PageResult]  # refused pages, in page order
    pages_ok: list[PageResult]  # successful pages, in page order
    record: AssembledRecord | None  # None => not a single page passed


async def process_batch(
    pages: list[PageInput],
    prompt: str | None = None,
    at_once: int | None = None,
    timeout: float = _ALBUM_TIMEOUT_S,
    assemble: bool = True,
) -> AlbumOutcome:
    """Run every page in parallel and combine the survivors. `pages` is already
    sorted; a page's position + 1 is its number — a PDF's page keeps its own —
    used in every per-page field and message. One page failing never cancels
    the others, and a page still unfinished at the ceiling becomes a skip —
    asyncio.wait rather than wait_for so the stats of finished pages are not
    lost with the cancellation.

    A notebook's pages (task 63) come with its `prompt`, `at_once` pages
    read at a time under its own `timeout`, and are not assembled into one
    record: the notebook is cut into its lectures (notebook.py)."""
    window = asyncio.Semaphore(at_once) if at_once else None

    async def read(page: PageInput, number: int) -> PageResult:
        if prompt is None:
            return await process_page(page, number)
        async with window:
            return await process_page(page, number, prompt)

    tasks = {
        number: asyncio.create_task(read(page, number))
        for number, page in (
            (page.number or place, page) for place, page in enumerate(pages, 1)
        )
    }
    try:
        done, pending = await asyncio.wait(tasks.values(), timeout=timeout)
        if pending:
            logger.warning(
                "album: %d/%d pages unfinished in %ds",
                len(pending),
                len(pages),
                timeout,
            )
    finally:
        # asyncio.wait leaves its tasks running; cancel any straggler so a
        # timed-out or cancelled batch doesn't keep pages making paid calls.
        leftover = [task for task in tasks.values() if not task.done()]
        for task in leftover:
            task.cancel()
        if leftover:
            await asyncio.gather(*leftover, return_exceptions=True)

    stats: list[CallStats] = []
    results: list[PageResult] = []
    for number, task in tasks.items():
        if task not in done:
            results.append(PageResult(number, [], skip_reason=texts.SKIP_ERROR))
            continue
        try:
            page_result = task.result()
        except Exception as exc:
            logger.warning("album page %d crashed: %s", number, exc)
            results.append(PageResult(number, [], skip_reason=texts.SKIP_ERROR))
            continue
        results.append(page_result)
        stats.extend(page_result.stats)

    results.sort(key=lambda r: r.page)
    pages_ok = [r for r in results if r.ok]
    skips = [r for r in results if not r.ok]
    record = _assemble(pages_ok, skips) if pages_ok and assemble else None
    return AlbumOutcome(stats=stats, skips=skips, pages_ok=pages_ok, record=record)


def _assemble(
    pages_ok: list[PageResult], skips: list[PageResult]
) -> AssembledRecord:
    """Combine successful pages into one record. Every aggregate is over the
    pages that were read — a skipped page contributes no text, no uncertainty
    and no metric. Whole runs are concatenated, never spliced.

    What a skipped page does contribute is a marker at its own position. The
    rule used to be that a record is all its pages or none, because a record
    missing a page reads as a whole one and nothing in it says which page is
    gone. The second half of that sentence is the part worth keeping: the hole
    is named, in place, and the record is delivered. Two five-page albums were
    lost in one evening over a single page each, and in a group chat a lost
    album is a course without its lecture.
    """
    pages_ok, head_cut, tail_cut = _one_lecture(
        pages_ok, [p.page for p in pages_ok + skips]
    )
    # A record with a hole always needs a reader's eye, whatever the pages
    # that were read scored.
    needs_review = bool(skips) or any(
        p.verdict == "needs_review" for p in pages_ok
    )
    return AssembledRecord(
        title=pages_ok[0].transcription.title,
        subject=next(
            (p.transcription.subject for p in pages_ok if p.transcription.subject),
            None,
        ),
        markdown=_markdown_with_holes(pages_ok, skips),
        status="needs_review" if needs_review else "ready",
        verdict="needs_review" if needs_review else "clean",
        uncertain=[
            {**asdict(u), "page": p.page}
            for p in pages_ok
            for u in p.transcription.uncertain
        ],
        issues=[
            {**asdict(i), "page": p.page} for p in pages_ok for i in p.report.issues
        ],
        numeric_divergences=[
            {**asdict(d), "page": p.page}
            for p in pages_ok
            for d in p.numeric_divergences
        ],
        margin_notes=[
            note
            for p in pages_ok
            for note in p.transcription.margin_notes
        ],
        unreadable_count=sum(p.transcription.unreadable_count for p in pages_ok),
        # None-tolerant now: a page read by a single run has no agreement to
        # contribute, and the album's number is the worst of those that do.
        text_agreement=_min_metric(pages_ok, "text_agreement"),
        numeric_agreement=_min_metric(pages_ok, "numeric_agreement"),
        photo_sharpness=_min_metric(pages_ok, "photo_sharpness"),
        photo_line_height=_min_metric(pages_ok, "photo_line_height"),
        photo_paper_fraction=_min_metric(pages_ok, "photo_paper_fraction"),
        photo_contrast=_min_metric(pages_ok, "photo_contrast"),
        page_count=len(pages_ok),
        missing_pages=[p.page for p in skips],
        unverified_pages=[
            {"page": p.page, "reason": p.unverified_reason}
            for p in pages_ok
            if p.unverified_reason
        ],
        cutouts=[cutout for p in pages_ok for cutout in p.cutouts],
        drawings=sum(figures.count(p.transcription.markdown) for p in pages_ok),
        sketched=sum(p.sketched for p in pages_ok),
        lecture_head_cut=head_cut,
        lecture_tail_cut=tail_cut,
        runs_added=sum(p.runs_added for p in pages_ok),
        read_further=sum(1 for p in pages_ok if p.read_further),
    )


def _one_lecture(
    pages_ok: list[PageResult], numbers: list[int]
) -> tuple[list[PageResult], int, int]:
    """The pages with the lecture before cut off the album's first page and
    the lecture after off its last, and how many lines each cut took.
    `numbers` are the album's pages, read or not — a PDF's by their place in
    it, which a blank page left out leaves a gap in.

    Only with two pages read or more, and only on the album's own first and
    last page: a single page — a photograph, or the one page an album kept —
    says nothing of which of its lectures is meant, and a lecture beginning
    in the middle of an album is the album's to keep.
    Only where every run named the start (lectures.agreed), and never a whole
    page (lectures.without_after). What is cut is not kept. A cut page's
    findings are found again on what stays, and when the first page loses its
    head, the title it was given may be the lecture before's: the record
    takes its title from what stays — its first heading, or the next page's.
    """
    if len(numbers) < 2 or len(pages_ok) < 2:
        return pages_ok, 0, 0
    pages_ok = list(pages_ok)
    head_cut = tail_cut = 0

    first = pages_ok[0]
    if first.page == min(numbers) and first.lecture_starts:
        kept, head_cut = lectures.without_before(
            first.transcription.markdown, first.lecture_starts
        )
        if head_cut:
            heading = next(
                (
                    line.lstrip("#").strip()
                    for line in kept.split("\n")
                    if line.startswith("#") and line.lstrip("#").strip()
                ),
                None,
            )
            title = heading[:60] if heading else (
                pages_ok[1].transcription.title
                if len(pages_ok) > 1
                else first.transcription.title
            )
            pages_ok[0] = _trimmed(first, kept, title)

    last = pages_ok[-1]
    if last.page == max(numbers) and last.lecture_starts:
        kept, tail_cut = lectures.without_after(
            last.transcription.markdown, last.lecture_starts
        )
        if tail_cut:
            pages_ok[-1] = _trimmed(last, kept, last.transcription.title)

    if head_cut or tail_cut:
        logger.info(
            "album: one lecture — %d lines cut before it, %d after", head_cut, tail_cut
        )
    return pages_ok, head_cut, tail_cut


def _trimmed(page: PageResult, markdown: str, title: str) -> PageResult:
    """A page with part of its text cut away, and its findings found again
    on what stays — a finding about a line that is gone would anchor nowhere
    and stand at the record's end."""
    return replace(
        page,
        transcription=replace(page.transcription, markdown=markdown, title=title),
        report=mathcheck.Report(issues=vision.findings(markdown)),
    )


# A line that ends a sentence, and one that cannot continue somebody else's.
_SENTENCE_END = ".!?:;…"
# Prose, as opposed to everything the page break is allowed to interrupt: a
# table row, a list item, a heading, a display formula, a drawing, a quote.
_NOT_PROSE = ("|", "#", "-", "*", "•", ">", "$$", "[", "!")
_LOWER_START = re.compile(r"^[^\W\dA-ZА-ЯЁ_]", re.UNICODE)


def _is_prose(line: str) -> bool:
    return bool(line) and not line.startswith(_NOT_PROSE)


def _continues(before: str, after: str) -> bool:
    """Does the next page finish a sentence this one began?

    Pages are read one at a time and joined by a rule, so a sentence that ran
    over the edge of the paper came out as two halves with a horizontal line
    between them — "Если граф ориентирован, то ребро" / --- / "учитывается
    один раз". Nothing downstream can repair that: the composing stage sees
    the rule as the hard boundary it is, and by then it is right to.

    The test is deliberately narrow, because joining two things that were not
    one sentence is worse than the seam: both sides must be ordinary prose,
    the first half must not end like a finished sentence, and the second must
    begin in lower case.
    """
    last = next(
        (line.strip() for line in reversed(before.splitlines()) if line.strip()), ""
    )
    first = next(
        (line.strip() for line in after.splitlines() if line.strip()), ""
    )
    if not _is_prose(last) or not _is_prose(first):
        return False
    return last[-1] not in _SENTENCE_END and bool(_LOWER_START.match(first))


def _markdown_with_holes(
    pages_ok: list[PageResult], skips: list[PageResult]
) -> str:
    """The record, with a marker where each unread page would have been, and
    with a sentence that ran over the edge of a page put back together.

    Ordered by page number over both lists at once, so a hole in the middle
    reads as a hole in the middle rather than as a note at the end.
    """
    blocks = [(p.page, p.transcription.markdown) for p in pages_ok]
    blocks += [(p.page, texts.page_missing_marker(p.page)) for p in skips]
    return joined(blocks)


def joined(blocks: list[tuple[int, str]]) -> str:
    """Pages' texts, by their numbers, as one record: a rule between two
    pages, or the sentence one page began put back together with its end
    on the next (_continues)."""
    blocks = sorted(blocks, key=lambda block: block[0])
    out = ""
    for index, (_, markdown) in enumerate(blocks):
        if index == 0:
            out = markdown
        elif _continues(out, markdown):
            # The rule goes with the seam: a horizontal line inside a sentence
            # is exactly what made the record read as broken.
            out = f"{out.rstrip()} {markdown.lstrip()}"
        else:
            out = f"{out}\n\n---\n\n{markdown}"
    return out


def _min_metric(pages_ok: list[PageResult], attr: str) -> float | None:
    present = [getattr(p, attr) for p in pages_ok if getattr(p, attr) is not None]
    return min(present) if present else None
