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
from dataclasses import asdict, dataclass

from app.bot import texts
from app.core.config import settings
from app.services import mathcheck, photoguard, vision
from app.services.vision import CallStats, Transcription

logger = logging.getLogger(__name__)

# Wait this long with no new page before assembling the batch.
_QUIET_SECONDS = 1.0


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


_buffer: dict[str, list[PageInput]] = {}


def add_page(media_group_id: str, page: PageInput) -> None:
    _buffer.setdefault(media_group_id, []).append(page)


async def collect(media_group_id: str) -> list[PageInput] | None:
    """Block until the album stops growing, then hand the whole batch to one
    caller. Every other caller for the same group gets None and must return
    without replying — otherwise the batch is processed once per page."""
    while True:
        if media_group_id not in _buffer:
            return None  # another caller already claimed this batch
        size = len(_buffer[media_group_id])
        await asyncio.sleep(_QUIET_SECONDS)
        if media_group_id in _buffer and len(_buffer[media_group_id]) == size:
            break
    # No await between the stability check and this pop: exactly one caller
    # gets the list, the rest get None.
    return _buffer.pop(media_group_id, None)


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


async def process_page(page_input: PageInput, page: int) -> PageResult:
    """One album page through the pipeline minus the database and minus any
    reply: frame check, three recognition runs, the result gates, then the
    arithmetic check. Returns either a skip reason or the data for the record.
    The CallStats list is returned in every case — empty only when the frame
    was rejected before any model call."""
    frame = photoguard.check_photo_bytes(page_input.data)
    if not frame.ok:
        return PageResult(page, [], skip_reason=frame.reason)

    result, stats = await vision.transcribe_consensus(page_input.data)
    if result is None:
        return PageResult(page, stats, skip_reason=texts.SKIP_UNRECOGNIZED)
    if result.verdict == "rejected":
        return PageResult(page, stats, skip_reason=texts.SKIP_DIVERGED)
    if len(result.best.markdown.strip()) < settings.MIN_MARKDOWN_LEN:
        return PageResult(page, stats, skip_reason=texts.SKIP_NO_TEXT)

    report = mathcheck.check(result.best.markdown)
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
    skips: list[tuple[int, str]]  # (page number, reason), in page order
    pages_ok: list[PageResult]  # successful pages, in page order
    record: AssembledRecord | None  # None => not a single page passed


async def process_batch(pages: list[PageInput]) -> AlbumOutcome:
    """Run every page in parallel and combine the survivors. `pages` is already
    sorted; a page's position + 1 is its number, used in every per-page field
    and message. One page failing never cancels the others."""
    outcomes = await asyncio.gather(
        *(process_page(page, i) for i, page in enumerate(pages, 1)),
        return_exceptions=True,
    )

    stats: list[CallStats] = []
    results: list[PageResult] = []
    for i, outcome in enumerate(outcomes, 1):
        if isinstance(outcome, BaseException):
            logger.warning("album page %d crashed: %s", i, outcome)
            results.append(PageResult(i, [], skip_reason=texts.SKIP_ERROR))
            continue
        results.append(outcome)
        stats.extend(outcome.stats)

    pages_ok = [r for r in results if r.ok]
    skips = [(r.page, r.skip_reason) for r in results if not r.ok]
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
