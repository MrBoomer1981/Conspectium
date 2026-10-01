"""In-process album buffer and batch assembly.

Telegram delivers an album as separate messages that share a media_group_id,
each its own webhook update with its own DB session. Pages are buffered here
until the group goes quiet, then one update assembles the whole batch.

Nothing in this module touches the database — the handler does the writes.
See CLAUDE.md -> Sessions and transactions.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import time
from dataclasses import asdict, dataclass, field

from app.bot import texts
from app.core.config import settings
from app.services import figures, mathcheck, photoguard, vision
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

# Hard ceiling from the first page. A stream that never goes quiet must not
# hold its middleware DB session open indefinitely.
_COLLECT_MAX_S = 60

# Ten pages at three runs each under Semaphore(10) is three waves of one run's
# worst case. Computed rather than written down: vision's call timeout is a
# setting now, and a ceiling that did not follow it would cut a slow album
# short. Normative, not an estimate — the margin is not to be lowered
# (PLAN.md task 10).
def _waves(pages: int, runs: int, slots: int) -> int:
    """How many times the semaphore fills before every call has been made. A
    function, not an expression, because the rounding only matters when the
    calls do not divide evenly into slots — and the settings this process was
    started with are exactly the case where they do."""
    return math.ceil(pages * runs / slots)


_WAVES = _waves(
    settings.MAX_ALBUM_PAGES, settings.VISION_RUNS, vision.API_SLOTS
)
_ALBUM_TIMEOUT_S = int(_WAVES * vision.RUN_WORST_CASE_S * vision.TIMEOUT_MARGIN)


@dataclass
class PageInput:
    # The compressed page. Empty until the batch is claimed and the page is
    # downloaded by `file_id` (handlers._fetch_pages): an album is buffered as
    # Telegram's references, so one nobody tagged in a group is never fetched.
    data: bytes
    message_id: int
    chat_id: int
    media_group_id: str
    bytes_before: int
    bytes_after: int
    # None for an image sent as a file: Telegram gives a photo's size, not a
    # file's.
    width: int | None
    height: int | None
    # The "#word" in this page's caption. Telegram puts an album's caption on
    # one page only, so most pages carry None; see tag_of.
    tag: str | None = None
    file_id: str | None = None


def tag_of(pages: list[PageInput]) -> str | None:
    """The subject an album was sent with: the tag of the first page, in page
    order, that carries one. In a group chat an album without one is not the
    bot's to take."""
    for page in sorted(pages, key=lambda p: p.message_id):
        if page.tag:
            return page.tag
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


def announce(media_group_id: str, message_id: int) -> None:
    """Register a page the moment its update arrives, before anything else is
    done with it.

    This was the whole point of the two steps while each page was fetched and
    compressed before it reached `_buffer`, which took seconds per photo:
    timing the debounce from the buffer measured our own download speed, and
    the first page to finish saw a quiet album and claimed the batch alone
    while the rest were still in flight. A page is handed in right after this
    now — in a group, after its reference is written down — and the batch is
    still timed from here, which measures what it is supposed to.
    """
    now = time.monotonic()
    _prune_claimed(now)
    if media_group_id in _claimed:
        return
    _announced.setdefault(media_group_id, set()).add(message_id)
    _first_page_at.setdefault(media_group_id, now)
    _last_page_at[media_group_id] = now


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
    for registry in (_buffer, _announced, _first_page_at, _last_page_at, _claimed):
        registry.clear()


def _prune_claimed(now: float) -> None:
    """A claimed group is only remembered long enough to catch stragglers."""
    for group, when in list(_claimed.items()):
        if now - when > _COLLECT_MAX_S:
            del _claimed[group]


def _forget(media_group_id: str) -> list[PageInput] | None:
    pages = _buffer.pop(media_group_id, None)
    _announced.pop(media_group_id, None)
    _first_page_at.pop(media_group_id, None)
    _last_page_at.pop(media_group_id, None)
    _claimed[media_group_id] = time.monotonic()
    # None, not an empty list: the caller reads None as "not mine, say
    # nothing", and process_batch has nothing to wait on for an empty batch.
    return pages or None


async def collect(media_group_id: str) -> list[PageInput] | None:
    """Block until the album stops growing, then hand the whole batch to one
    caller. Every other caller for the same group gets None and must return
    without replying — otherwise the batch is processed once per page.

    Two conditions have to hold: _QUIET_SECONDS with nothing new announced, so
    the album has stopped growing, and every announced page handed in, so
    nothing still in flight is left behind. The _COLLECT_MAX_S ceiling bounds
    the wait either way — an update that never hands its page in must not
    strand the pages that did."""
    while True:
        if media_group_id not in _announced:
            return None  # another caller already claimed this batch
        now = time.monotonic()
        quiet_for = now - _last_page_at[media_group_id]
        handed_in = len(_buffer.get(media_group_id, ()))
        expected = len(_announced[media_group_id])
        if quiet_for >= _QUIET_SECONDS and handed_in >= expected:
            break
        if now - _first_page_at[media_group_id] >= _COLLECT_MAX_S:
            logger.warning(
                "album %s: %d of %d pages ready after %ds, assembling anyway",
                media_group_id,
                handed_in,
                expected,
                _COLLECT_MAX_S,
            )
            break
        # Never overshoot the moment the quiet window expires.
        await asyncio.sleep(min(_POLL_SECONDS, max(_QUIET_SECONDS - quiet_for, 0.01)))
    # Exactly one of these per media_group_id is what a healthy album looks
    # like. Two means the batch was claimed twice and the album split into
    # separate records — the failure that took three attempts to find, and
    # which nothing in the log could previously tell from one slow page.
    logger.info(
        "album %s: batch closed, %d of %d pages, %.1fs since the first",
        media_group_id,
        len(_buffer.get(media_group_id, ())),
        len(_announced[media_group_id]),
        time.monotonic() - _first_page_at[media_group_id],
    )
    # No await between the decision and this pop: exactly one caller gets the
    # list, every other one comes back around and finds the group gone.
    return _forget(media_group_id)


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
    # The page's drawings, cut out of its image before the image is let go.
    cutouts: list[figures.Cutout] = field(default_factory=list)

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
    page is read — numbered in the order given.

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
            frame = await asyncio.to_thread(photoguard.check_photo_bytes, page_input.data)
        except Exception:
            logger.exception("album page %d: the frame could not be checked", page)
            return None
        if frame.ok:
            return None
        _log_refusal(page, frame)
        return _frame_refused(page, frame, frame.reason, [])

    checked = await asyncio.gather(
        *(check(page_input, page) for page, page_input in enumerate(ordered, 1))
    )
    return [result for result in checked if result is not None]


async def process_page(page_input: PageInput, page: int) -> PageResult:
    """One album page through the pipeline minus the database and minus any
    reply: frame check, three recognition runs, the result gates, then the
    arithmetic check. Returns either a skip reason or the data for the record.
    The CallStats list is returned in every case — empty only when the frame
    was rejected before any model call."""
    frame = photoguard.check_photo_bytes(page_input.data)

    def refused(reason: str, stats: list[CallStats]) -> PageResult:
        return _frame_refused(page, frame, reason, stats)

    if not frame.ok:
        # refused_frames has already asked for this page again before the
        # album was read; a frame refused here is one that got past that.
        _log_refusal(page, frame)
        return refused(frame.reason, [])

    result, stats = await vision.transcribe_consensus(page_input.data)
    if result is None:
        # Not one run came back readable: there is no text to keep.
        return refused(texts.SKIP_UNRECOGNIZED, stats)
    if len(result.best.markdown.strip()) < settings.MIN_MARKDOWN_LEN:
        return refused(texts.SKIP_NO_TEXT, stats)

    # The drawings recognition framed, cut out while the page's image is
    # still here; the record places them after composing.
    cutouts = await asyncio.to_thread(
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


@dataclass
class AlbumOutcome:
    stats: list[CallStats]
    # The refused pages themselves, not just their reasons: a refusal has to
    # be arguable, and the four frame metrics are what it is argued with.
    skips: list[PageResult]  # refused pages, in page order
    pages_ok: list[PageResult]  # successful pages, in page order
    record: AssembledRecord | None  # None => not a single page passed


async def process_batch(pages: list[PageInput]) -> AlbumOutcome:
    """Run every page in parallel and combine the survivors. `pages` is already
    sorted; a page's position + 1 is its number, used in every per-page field
    and message. One page failing never cancels the others, and a page still
    unfinished at the 300 s ceiling becomes a skip — asyncio.wait rather than
    wait_for so the stats of finished pages are not lost with the cancellation."""
    tasks = {
        number: asyncio.create_task(process_page(page, number))
        for number, page in enumerate(pages, 1)
    }
    try:
        done, pending = await asyncio.wait(
            tasks.values(), timeout=_ALBUM_TIMEOUT_S
        )
        if pending:
            logger.warning(
                "album: %d/%d pages unfinished in %ds",
                len(pending),
                len(pages),
                _ALBUM_TIMEOUT_S,
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
    record = _assemble(pages_ok, skips) if pages_ok else None
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
    blocks.sort(key=lambda block: block[0])

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
