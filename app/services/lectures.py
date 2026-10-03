"""One lecture a record: where a lecture begins on a page, and the lecture
that is not the album's cut away.

A notebook runs on, and an album rarely begins and ends where its lecture
does: record 46 opened with the end of the lecture before, and record 62
closed on the next one begun. Nothing in the text tells where a lecture
begins; the model, which sees the page — a date, «Лекция N», the line the
author drew — can say. From prompts-v9.md on, recognition names the first
line of every lecture that begins on a page (`lecture_starts`). This module
keeps the starts every run agrees on and finds them in a page's text;
albums._assemble decides where to cut. Nothing here calls a model or touches
the database.
"""

from __future__ import annotations

import difflib
import re

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
