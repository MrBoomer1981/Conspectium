"""A whole notebook sent at once (task 63, the CEO's of 2026-10-12): the
earlier lectures of a subject, photographed or scanned in one go and sent
in the private chat, cut into its lectures, each a record of its own.

A send of more pages than an album may hold (MAX_ALBUM_PAGES), or one whose
caption says «тетрадь», up to NOTEBOOK_MAX_PAGES, one a person a day beyond
their pages. Its pages are read with a prompt of their own — PROMPT_FILE's
with where each lecture begins (NOTEBOOK_PROMPT_FILE) — and the notebook is
cut where every run named a start (lectures.cut): the CEO's notebooks open a
lecture with its date and a heading. Each lecture is dated by the margin of
the page it begins on, and made, kept and sent as an album's record is
(handlers._read_notebook); a stretch where no start was found is kept in
parts of an album's pages.

This module is what the notebook is cut into and what is said of it;
nothing here calls the model or touches the database.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date

from app.bot import albums, subjects, texts
from app.core.config import settings
from app.services import figures, lectures, vision
from app.services.vision import CallStats

# «тетрадь», «тетради», «Тетрадь целиком» — not a "#word": «#тетрадь» is
# the subject it names.
_ASKED_RE = re.compile(r"(?<![\w#])тетрад[а-яё]*", re.IGNORECASE)
# A title read off a lecture's text: its first heading, else its first line.
_HEADING_RE = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t#]*$", re.MULTILINE)
_TITLE_MAX = 60


def asked(caption: str | None) -> bool:
    """Whether the caption says the pages are a notebook."""
    return bool(caption and _ASKED_RE.search(caption))


def wanted(pages: int, caption: str | None) -> bool:
    """Whether a private chat's send is a whole notebook: more pages than an
    album may hold, or the caption says so."""
    return pages > settings.MAX_ALBUM_PAGES or asked(caption)


def key(chat_id: int, message_id: int) -> str:
    """What every lecture of one notebook carries (`notes.notebook`)."""
    return f"notebook:{chat_id}:{message_id}"


@dataclass
class Lecture:
    """One lecture of a notebook, assembled as an album's record is: the
    record, the day its page's margin gives it, the pages its text came
    from, whether it is a part of a stretch with no start found, and the
    reading of its pages — each page's calls with the first lecture on it."""

    record: albums.AssembledRecord
    day: date | None
    pages: list[int]
    part: bool
    # Opens on a start every run named, rather than on the notebook's first
    # page or a part's.
    started: bool = False
    stats: list[CallStats] = field(default_factory=list)


def _title(markdown: str, fallback: str) -> str:
    heading = _HEADING_RE.search(markdown)
    if heading:
        return heading.group(1).strip()[:_TITLE_MAX]
    for line in markdown.split("\n"):
        line = line.strip().strip("*").strip()
        if line and not line.startswith(("---", "[", "$$", "|")):
            return line[:_TITLE_MAX]
    return fallback


def _day(
    cut: lectures.Cut, by_page: dict[int, albums.PageResult], first: bool, sent: date
) -> date | None:
    """The day a lecture was given, as the margin of the page it begins on
    names it: the page's days in order are its lectures' in order, when it
    names as many as begin on it — a page that ends one lecture and begins
    the next names the next's alone. What stood before the notebook's first
    start is dated by its first page when nothing begins there. Unsure,
    none: the lecture takes the day the pages came, as an album does."""
    if cut.start is not None:
        page = by_page.get(cut.start[0])
        if page is None:
            return None
        days = subjects.days_in(page.transcription.margin_notes, sent)
        begun = lectures.starts_on(page.transcription.markdown, page.lecture_starts)
        return days[cut.start[1]] if len(days) == len(begun) else None
    if not first or cut.part:
        return None
    page = by_page.get(cut.pieces[0].page)
    if page is None or lectures.starts_on(
        page.transcription.markdown, page.lecture_starts
    ):
        return None
    days = subjects.days_in(page.transcription.margin_notes, sent)
    return days[0] if len(days) == 1 else None


def lectures_of(
    pages_ok: list[albums.PageResult],
    skips: list[albums.PageResult],
    most: int,
    sent: date,
) -> list[Lecture]:
    """The notebook's pages, read, as its lectures in order — each an
    album's record of the pages it stands on (albums._assemble), cut where
    a lecture begins."""
    by_page = {page.page: page for page in pages_ok}
    order = sorted([(p.page, p) for p in pages_ok] + [(p.page, None) for p in skips])
    cuts = lectures.cut(
        [
            (
                number,
                page.transcription.markdown if page is not None else None,
                page.lecture_starts if page is not None else [],
            )
            for number, page in order
        ],
        most,
    )
    # A page two lectures share gives neither its drawings — a drawing can
    # go missing, never land in the wrong lecture — and its calls go with
    # the first.
    seen: dict[int, int] = {}
    for index, cut in enumerate(cuts):
        for number in cut.pages:
            seen[number] = seen.get(number, 0) + 1
    counted: set[int] = set()

    out: list[Lecture] = []
    for index, cut in enumerate(cuts):
        read = [piece for piece in cut.pieces if piece.markdown is not None]
        holes = [piece.page for piece in cut.pieces if piece.markdown is None]
        pages = [by_page[piece.page] for piece in read]
        whole = [page for page in pages if seen[page.page] == 1]
        mine = [page for page in pages if page.page not in counted]
        counted.update(page.page for page in mine)
        markdown = albums.joined(
            [(piece.page, piece.markdown) for piece in read]
            + [(page, texts.page_missing_marker(page)) for page in holes]
        )
        day = _day(cut, by_page, index == 0, sent)
        needs_review = bool(holes) or any(page.verdict == "needs_review" for page in pages)
        start_page = by_page.get(cut.start[0]) if cut.start else (pages[0] if pages else None)
        record = albums.AssembledRecord(
            title=_title(
                markdown, start_page.transcription.title if start_page else texts.NOTEBOOK_TITLE
            ),
            subject=next(
                (p.transcription.subject for p in pages if p.transcription.subject), None
            ),
            markdown=markdown,
            status="needs_review" if needs_review else "ready",
            verdict="needs_review" if needs_review else "clean",
            uncertain=[
                {**asdict(u), "page": p.page} for p in pages for u in p.transcription.uncertain
            ],
            # Found again on each page's share: a finding about a line of
            # the lecture before is that lecture's.
            issues=[
                {**asdict(found), "page": piece.page}
                for piece in read
                for found in vision.findings(piece.markdown)
            ],
            numeric_divergences=[
                {**asdict(d), "page": p.page}
                for p in pages
                for d in p.numeric_divergences or []
            ],
            margin_notes=subjects.margin_for(
                [note for p in pages for note in p.transcription.margin_notes], day, sent
            ),
            unreadable_count=markdown.count("[неразборчиво]"),
            text_agreement=albums._min_metric(pages, "text_agreement"),
            numeric_agreement=albums._min_metric(pages, "numeric_agreement"),
            photo_sharpness=albums._min_metric(pages, "photo_sharpness"),
            photo_line_height=albums._min_metric(pages, "photo_line_height"),
            photo_paper_fraction=albums._min_metric(pages, "photo_paper_fraction"),
            photo_contrast=albums._min_metric(pages, "photo_contrast"),
            page_count=len(pages),
            missing_pages=holes,
            unverified_pages=[
                {"page": p.page, "reason": p.unverified_reason}
                for p in pages
                if p.unverified_reason
            ],
            cutouts=[cutout for p in whole for cutout in p.cutouts],
            drawings=figures.count(markdown),
            sketched=sum(p.sketched for p in whole),
            runs_added=sum(p.runs_added for p in mine),
            read_further=sum(1 for p in mine if p.read_further),
        )
        out.append(
            Lecture(
                record=record,
                day=day,
                pages=cut.pages,
                part=cut.part,
                started=cut.start is not None,
                stats=[stat for p in mine for stat in p.stats],
            )
        )
    return out


def ranges(pages: list[int]) -> list[tuple[int, int]]:
    """Page numbers as the runs they make: [3, 4, 5, 9] → [(3, 5), (9, 9)]."""
    runs: list[tuple[int, int]] = []
    for page in sorted(set(pages)):
        if runs and page == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], page)
        else:
            runs.append((page, page))
    return runs
