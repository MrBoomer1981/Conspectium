"""One lecture a record: where a lecture begins on a page, and the lecture
that is not the album's cut away.

A notebook runs on, and an album rarely begins and ends where its lecture
does: record 46 opened with the end of the lecture before, and record 62
closed on the next one begun. Nothing in the text tells where a lecture
begins; the model, which sees the page — a date, «Лекция N», the line the
author drew — can say. From prompts-v9.md on, recognition names the first
line of every lecture that begins on a page (`lecture_starts`). This module
keeps the starts every run agrees on and finds them in a page's text;
albums._assemble decides where to cut an album, and `cut` cuts a whole
notebook into its lectures (task 63). Nothing here calls a model or touches
the database.
"""

from __future__ import annotations

import difflib
import math
import re
from dataclasses import dataclass, field

# What the comparison ignores: space, and the markup two runs write one line
# with differently — dollars, emphasis, a heading's hashes, braces.
_NOISE_RE = re.compile(r"[\s$*#_`~>{}\\]+")
# Two writings of one line, compared without that noise: a date one run reads
# "24.09" and another "24.09." is one start, a different line is not.
_SAME = 0.8
# A quote shorter than this, without its noise, could begin many lines — "1)",
# "Д-во" — and is taken as a whole line only, never as a line's beginning.
_PREFIX_MIN = 6
# A line drawn across the page, as the record writes it: the author's line
# that ended the lecture stays with the lecture after when that is cut away.
_RULE_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,}|~{3,})$")


def _plain(text: str) -> str:
    return _NOISE_RE.sub("", text).lower()


def _same(a: str, b: str) -> bool:
    a, b = _plain(a), _plain(b)
    if not a or not b:
        return False
    if a == b:
        return True
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() >= _SAME


def agreed(runs: list[list[str]], chosen: int) -> list[str]:
    """The chosen run's lecture starts that every other run names too, in the
    chosen run's order. One run alone agrees on nothing: a cut made on one
    reading's word is the model deciding, which is what three runs are for."""
    if len(runs) < 2:
        return []
    others = [run for index, run in enumerate(runs) if index != chosen]
    return [
        start
        for start in runs[chosen]
        if all(any(_same(start, theirs) for theirs in run) for run in others)
    ]


def _line_of(lines: list[str], start: str) -> int | None:
    """The line a start quotes: the whole line, or its beginning when the
    quote is long enough to begin only one."""
    quote = _plain(start)
    if not quote:
        return None
    for index, line in enumerate(lines):
        plain = _plain(line)
        if not plain:
            continue
        if _same(line, start) or (len(quote) >= _PREFIX_MIN and plain.startswith(quote)):
            return index
    return None


def _found(lines: list[str], starts: list[str]) -> list[int]:
    return sorted({i for i in (_line_of(lines, start) for start in starts) if i is not None})


def _written(lines: list[str]) -> int:
    return sum(1 for line in lines if line.strip())


def without_before(markdown: str, starts: list[str]) -> tuple[str, int]:
    """The page from the first lecture that begins on it, and how many lines
    were cut above it — the lecture before. The page whole and 0 when no start
    is found in it, or nothing stands above the first."""
    lines = markdown.split("\n")
    found = _found(lines, starts)
    if not found:
        return markdown, 0
    cut = _written(lines[: found[0]])
    if not cut:
        return markdown, 0
    return "\n".join(lines[found[0] :]), cut


def without_after(markdown: str, starts: list[str]) -> tuple[str, int]:
    """The page up to the last lecture that begins on it, and how many lines
    were cut from there on — the lecture after. The page whole and 0 when no
    start is found in it, or nothing of the page's own lecture would be left:
    a page is never cut away whole."""
    lines = markdown.split("\n")
    found = _found(lines, starts)
    if not found:
        return markdown, 0
    kept = lines[: found[-1]]
    while kept and (not kept[-1].strip() or _RULE_RE.match(kept[-1].strip())):
        kept.pop()
    if not _written(kept):
        return markdown, 0
    return "\n".join(kept), _written(lines[found[-1] :])


# ── A whole notebook cut into its lectures (task 63) ────────────────────────


@dataclass
class Piece:
    """A page's share of one lecture: the page from where the lecture begins
    on it to where the next begins, or the page whole. None for a page that
    could not be read: a marker stands for it in the lecture."""

    page: int
    markdown: str | None


@dataclass
class Cut:
    """One lecture of a notebook, as its pages give it. `start` is the page
    it opens on and which of that page's starts it is — None for what stood
    before the notebook's first start; `part` marks a share of a stretch
    where no start was found, cut by its pages."""

    pieces: list[Piece] = field(default_factory=list)
    start: tuple[int, int] | None = None
    part: bool = False

    @property
    def pages(self) -> list[int]:
        return list(dict.fromkeys(piece.page for piece in self.pieces))

    def written(self) -> bool:
        return any(
            piece.markdown is not None and _written(piece.markdown.split("\n"))
            for piece in self.pieces
        )


def _closed(lines: list[str]) -> list[str]:
    """A lecture's last lines without the blank lines and the author's line
    drawn under it before the next begins."""
    kept = list(lines)
    while kept and (not kept[-1].strip() or _RULE_RE.match(kept[-1].strip())):
        kept.pop()
    return kept


def starts_on(markdown: str, starts: list[str]) -> list[int]:
    """The lines of a page a lecture begins on, as `cut` finds them."""
    return _found(markdown.split("\n"), starts)


def cut(pages: list[tuple[int, str | None, list[str]]], most: int) -> list[Cut]:
    """A notebook's pages, in order — each its number, its text or None when
    it could not be read, and the lecture starts every run named on it — cut
    into its lectures: one from every start to the next, across pages.
    What stands before the first start is a lecture of its own, the end of
    one begun before the notebook or its first whose start went unseen.

    A stretch of more than `most` pages with no start found is cut by its
    pages into near equal parts of `most` at most — the CEO's of 2026-10-13
    — each as large as a send the bot reads whole. A lecture is never cut
    inside a page but where a start is. Nothing written is left out: a
    lecture with no written line — an unread page alone — is none, and its
    page is the notebook's unread page."""
    lectures: list[Cut] = []
    current = Cut()
    for number, markdown, starts in pages:
        if markdown is None:
            current.pieces.append(Piece(number, None))
            continue
        lines = markdown.split("\n")
        edges = _found(lines, starts)
        head = lines[: edges[0]] if edges else lines
        if _written(head):
            current.pieces.append(
                Piece(number, "\n".join(_closed(head)) if edges else markdown)
            )
        for index, begin in enumerate(edges):
            end = edges[index + 1] if index + 1 < len(edges) else len(lines)
            body = lines[begin:end]
            if index + 1 < len(edges):
                body = _closed(body)
            if current.written():
                lectures.append(current)
            current = Cut(pieces=[Piece(number, "\n".join(body))], start=(number, index))
    if current.written():
        lectures.append(current)

    out: list[Cut] = []
    for lecture in lectures:
        pages_of = lecture.pages
        if len(pages_of) <= most:
            out.append(lecture)
            continue
        parts = math.ceil(len(pages_of) / most)
        size = math.ceil(len(pages_of) / parts)
        for index in range(parts):
            share = set(pages_of[index * size : (index + 1) * size])
            piece_list = [piece for piece in lecture.pieces if piece.page in share]
            part = Cut(
                pieces=piece_list,
                start=lecture.start if index == 0 else None,
                part=True,
            )
            if part.written():
                out.append(part)
    return out

