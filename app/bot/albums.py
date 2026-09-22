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
import time
from dataclasses import asdict, dataclass

from app.bot import texts
from app.core.config import settings
from app.services import graphcheck, mathcheck, photoguard, vision
from app.services.vision import CallStats, Transcription

logger = logging.getLogger(__name__)

# Wait this long with no *new* page before assembling the batch. Measured from
# the last arrival, not as a single fixed sleep: pages do not land in the
# buffer as fast as Telegram delivers them, because handle_photo downloads and
# compresses each photo before calling add_page. A large page over a slow link
# can take seconds, and at 1.0 s the first page decided the album was over and
# claimed the batch alone — one album arrived as four one-page records.
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
    data: bytes
    message_id: int
    chat_id: int
    media_group_id: str
    bytes_before: int
    bytes_after: int
    width: int
    height: int


# Pages whose bytes have arrived.
_buffer: dict[str, list[PageInput]] = {}
# Pages Telegram has told us about, downloaded or not. This is the authority
# on what the album contains; _buffer only says how much of it is ready.
_announced: dict[str, set[int]] = {}
_first_page_at: dict[str, float] = {}
_last_page_at: dict[str, float] = {}
# Groups already handed to a caller, with when. A page that turns up after its
# batch went out is dropped rather than allowed to open a second record.
_claimed: dict[str, float] = {}


def announce(media_group_id: str, message_id: int) -> None:
    """Register a page the moment its update arrives, *before* it is
    downloaded.

    This is the whole point of the two steps. Telegram delivers the updates of
    an album milliseconds apart, but a page only reaches `_buffer` once it has
    been fetched and compressed, which takes seconds per photo. Timing the
    debounce from the buffer measured our own download speed: the first page to
    finish saw a quiet album and claimed the batch alone while the rest were
    still in flight. Timing it from here measures what it is supposed to.
    """
    now = time.monotonic()
    _prune_claimed(now)
    if media_group_id in _claimed:
        return
    _announced.setdefault(media_group_id, set()).add(message_id)
    _first_page_at.setdefault(media_group_id, now)
    _last_page_at[media_group_id] = now


def add_page(media_group_id: str, page: PageInput) -> None:
    """The page's bytes, once downloaded. Announcing first is the normal path;
    a page that was never announced is taken as its own announcement so the
    buffer can never be fed behind the registry's back."""
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
    the album has stopped growing, and every announced page downloaded, so
    nothing still in flight is left behind. The _COLLECT_MAX_S ceiling bounds
    the wait either way — a download that never finishes must not strand the
    pages that did."""
    while True:
        if media_group_id not in _announced:
            return None  # another caller already claimed this batch
        now = time.monotonic()
        quiet_for = now - _last_page_at[media_group_id]
        downloaded = len(_buffer.get(media_group_id, ()))
        expected = len(_announced[media_group_id])
        if quiet_for >= _QUIET_SECONDS and downloaded >= expected:
            break
        if now - _first_page_at[media_group_id] >= _COLLECT_MAX_S:
            logger.warning(
                "album %s: %d of %d pages ready after %ds, assembling anyway",
                media_group_id,
                downloaded,
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
    transcription: Transcription | None = None
    report: mathcheck.Report | None = None
    verdict: str | None = None
    text_agreement: float | None = None
    numeric_divergences: list | None = None
    photo_sharpness: float | None = None
    photo_line_height: float | None = None
    photo_paper_fraction: float | None = None
    photo_contrast: float | None = None

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
    if frame.line_height_px < photoguard.MIN_LINE_HEIGHT_PX:
        return "line height"
    return "none"


async def process_page(page_input: PageInput, page: int) -> PageResult:
    """One album page through the pipeline minus the database and minus any
    reply: frame check, three recognition runs, the result gates, then the
    arithmetic check. Returns either a skip reason or the data for the record.
    The CallStats list is returned in every case — empty only when the frame
    was rejected before any model call."""
    frame = photoguard.check_photo_bytes(page_input.data)

    def refused(reason: str, stats: list[CallStats]) -> PageResult:
        """Every skip carries the frame metrics, refusals included.

        They used to be dropped here, so the album was the one path where a
        page could be turned away and leave nothing to check the decision
        against — while a single photo wrote all four to photo_rejected. A
        page that passed the frame and then failed recognition lost them too,
        for no reason: the numbers had already been measured.
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

    if not frame.ok:
        # Against the thresholds, because the number alone says nothing about
        # how far off it was — and one of these four is a whole album now.
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
        return refused(frame.reason, [])

    result, stats = await vision.transcribe_consensus(page_input.data)
    if result is None:
        return refused(texts.SKIP_UNRECOGNIZED, stats)
    if result.verdict == "rejected":
        return refused(texts.SKIP_DIVERGED, stats)
    if len(result.best.markdown.strip()) < settings.MIN_MARKDOWN_LEN:
        return refused(texts.SKIP_NO_TEXT, stats)

    report = mathcheck.Report(
        issues=mathcheck.check(result.best.markdown).issues
        + graphcheck.check(result.best.markdown)
    )
    verdict = result.verdict
    if verdict == "clean" and any(i.severity == "critical" for i in report.issues):
        verdict = "needs_review"

    return PageResult(
        page=page,
        stats=stats,
        transcription=result.best,
        report=report,
        verdict=verdict,
        text_agreement=result.text_agreement,
        numeric_divergences=result.numeric_divergences,
        photo_sharpness=frame.sharpness,
        photo_line_height=frame.line_height_px,
        photo_paper_fraction=frame.paper_fraction,
        photo_contrast=frame.contrast,
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
    photo_sharpness: float | None
    photo_line_height: float | None
    photo_paper_fraction: float | None
    photo_contrast: float | None
    page_count: int


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
    record = _assemble(pages_ok) if pages_ok else None
    return AlbumOutcome(stats=stats, skips=skips, pages_ok=pages_ok, record=record)


def _assemble(pages_ok: list[PageResult]) -> AssembledRecord:
    """Combine successful pages into one record. Every aggregate is over these
    pages only — skipped pages contribute nothing. Whole runs are concatenated,
    never spliced."""
    needs_review = any(p.verdict == "needs_review" for p in pages_ok)
    return AssembledRecord(
        title=pages_ok[0].transcription.title,
        subject=next(
            (p.transcription.subject for p in pages_ok if p.transcription.subject),
            None,
        ),
        markdown="\n\n---\n\n".join(p.transcription.markdown for p in pages_ok),
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
        text_agreement=min(p.text_agreement for p in pages_ok),
        photo_sharpness=_min_metric(pages_ok, "photo_sharpness"),
        photo_line_height=_min_metric(pages_ok, "photo_line_height"),
        photo_paper_fraction=_min_metric(pages_ok, "photo_paper_fraction"),
        photo_contrast=_min_metric(pages_ok, "photo_contrast"),
        page_count=len(pages_ok),
    )


def _min_metric(pages_ok: list[PageResult], attr: str) -> float | None:
    present = [getattr(p, attr) for p in pages_ok if getattr(p, attr) is not None]
    return min(present) if present else None
