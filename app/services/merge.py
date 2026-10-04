"""One lecture from several notebooks (task 63): whether two records are
one lecture, which of them is the base, and what the others add to it.

The CEO, 2026-10-04: a lecture two people sent is one document, and what
one notebook lacks the other's sets in at its place, under «Из другого
конспекта». Decided here by code over the records' text — no model is asked,
so the document holds nothing its authors did not write — and nothing here
touches the database.

Measured on the records in production before it was built, which hold the
same albums read many times (`docs/PLAN.md` → task 63):

- **One lecture** is told by how much of one text is found in the other.
  The same pages read again agreed at 0.70 to 1.00, different lectures of
  one course at 0.40 at most.
- **What another notebook adds** is found word by word, never paragraph by
  paragraph: a reading breaks a page into paragraphs its own way, and a
  paragraph of one stood against two of the other. A passage goes in only
  where the base has nothing in its stead. Where the base wrote a line its
  own way, the line is a variant, and the bot never chooses between two
  readings. Nor does what the other notebook carries past a line at its
  edge, which is the next lecture as often as this one. On eighteen pairs
  of one album read again, nothing went in.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from app.services import pdf

# ── What two readings of one line write differently ─────────────────────────
# Spacing, \left and \right, a word set in \text — what changes how a line is
# set, not what it says. The unreadable mark and a drawing's description are
# the reading's words, not the author's, and are left out of every comparison.
_LAYOUT_RE = re.compile(
    r"\\(?:left|right|quad|qquad|displaystyle|text|mathrm|mathbf|boxed"
    r"|big|Big|bigg|Bigg|[,;!:])(?![A-Za-z])"
)
_UNREADABLE_RE = re.compile(r"\[неразборчиво\]")
_DRAWING_RE = re.compile(r"\[(?:схема|рисунок|граф)[^\]]*\]", re.DOTALL)
_NOISE_RE = re.compile(r"[\s$*#_`~>{}\\|\-:.,;!?\"«»()\[\]]+")
# What a passage set in by an earlier merge carries: the lines pdf.inserted
# writes round it.
_INSERT_LINE_RE = re.compile(r"^⟦\+[^⟧]*⟧\s*$", re.MULTILINE)
# A word of the text, a LaTeX command, a number, or a sign that carries
# meaning in a formula. Punctuation and markup are not words: two readings
# put them differently round the same line.
_WORD_RE = re.compile(r"\\[a-z]+|[a-zа-яё]+|\d+|[=+<>^/()\[\]]")
_RULE_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,}|~{3,})$")
_BEGIN_RE = re.compile(r"\\begin\{")
_END_RE = re.compile(r"\\end\{")
_PICTURE_RE = re.compile(r"\[рисунок\s+\d+\s*:", re.IGNORECASE)

# Runs of five letters: what two texts share at this length is what they say,
# not the course's common words.
_RUN = 5

# ── One lecture ──────────────────────────────────────────────────────────────
# Half of one text found in the other: between the 0.40 different lectures of
# one course reached and the 0.70 one album read again never went under.
# Two notebooks of one lecture, by two people, were not there to measure.
SAME_LECTURE = 0.5

# ── What another notebook adds ───────────────────────────────────────────────
# A run of fewer words in common is chance — "x = 1" is in every page.
_MATCH_WORDS = 3
# A gap in the other notebook shorter than this is a word read differently.
_GAP_WORDS = 4
# The base has a line of its own in a gap when half of that line's words
# stand in it: then the gap is a variant, not something the base lacks.
_OWN_LINE = 0.5
# A paragraph of the other notebook goes in when this much of it falls where
# the base has nothing...
_SET_IN = 0.6
# ...and the base does not already carry it somewhere else, in another order
# or inside a table — this much of it found anywhere in the base.
_ALREADY_THERE = 0.6
# A paragraph of fewer words is never a passage of its own.
_PASSAGE_WORDS = 3
# Fewer words than this beside a drawing's description are its labels.
_DRAWING_WORDS = 8

# ── The base ─────────────────────────────────────────────────────────────────
# The fullest notebook, counted in characters of text read: a place it could
# not read costs about a line, a page it is missing about a page.
_UNREADABLE_COST = 40
_MISSING_PAGE_COST = 600


def _plain(text: str) -> str:
    text = _INSERT_LINE_RE.sub(" ", text)
    text = _DRAWING_RE.sub(" ", _UNREADABLE_RE.sub(" ", _LAYOUT_RE.sub(" ", text)))
    return _NOISE_RE.sub("", text).lower()


def _runs(text: str) -> set[str]:
    plain = _plain(text)
    return {plain[i : i + _RUN] for i in range(len(plain) - _RUN + 1)}


def _words(text: str) -> list[str]:
    text = _INSERT_LINE_RE.sub(" ", text)
    text = _DRAWING_RE.sub(" ", _UNREADABLE_RE.sub(" ", _LAYOUT_RE.sub(" ", text)))
    return _WORD_RE.findall(text.lower())


def same_lecture(a: str, b: str) -> float:
    """How much of one text is found in the other, the larger of the two
    ways: a notebook of half the lecture is still that lecture."""
    runs_a, runs_b = _runs(a), _runs(b)
    if not runs_a or not runs_b:
        return 0.0
    shared = len(runs_a & runs_b)
    return max(shared / len(runs_a), shared / len(runs_b))


def completeness(markdown: str, missing_pages: int = 0) -> int:
    """How much of a lecture a notebook holds, to choose the base by."""
    return (
        len(_plain(markdown))
        - _UNREADABLE_COST * len(_UNREADABLE_RE.findall(markdown))
        - _MISSING_PAGE_COST * missing_pages
    )


@dataclass
class _Chunk:
    start: int
    end: int
    kind: str  # "heading" | "rule" | "drawing" | "content"


def _chunks(markdown: str) -> list[_Chunk]:
    """The record's paragraphs, by the blank lines between them — never
    inside a display formula or an environment, which a blank line does not
    end — with a heading a paragraph of its own."""
    spans: list[tuple[int, int]] = []
    begin: int | None = None
    end = 0
    depth, dollars = 0, False
    offset = 0
    for line in markdown.split("\n"):
        stripped = line.strip()
        here = (offset, offset + len(line))
        offset += len(line) + 1
        free = depth == 0 and not dollars
        if free and (not stripped or stripped.startswith("#")):
            if begin is not None:
                spans.append((begin, end))
                begin = None
            if stripped:
                spans.append(here)
            continue
        if begin is None:
            begin = here[0]
        end = here[1]
        if stripped.count("$$") % 2:
            dollars = not dollars
        depth = max(
            0, depth + len(_BEGIN_RE.findall(stripped)) - len(_END_RE.findall(stripped))
        )
    if begin is not None:
        spans.append((begin, end))

    chunks = []
    for start, stop in spans:
        text = markdown[start:stop].strip()
        if text.startswith("#"):
            kind = "heading"
        elif _RULE_RE.match(text) or _INSERT_LINE_RE.fullmatch(text):
            kind = "rule"
        elif _DRAWING_RE.search(text) and len(_words(text)) < _DRAWING_WORDS:
            # A drawing's description with a label or two beside it is the
            # drawing — "∼ 1/2ⁿ →" read off it by one reading and not another.
            kind = "drawing"
        else:
            kind = "content"
        chunks.append(_Chunk(start, stop, kind))
    return chunks


def _stream(
    markdown: str, chunks: list[_Chunk]
) -> tuple[list[str], list[int], list[int]]:
    """The words of a record in order, the paragraph each comes from, and the
    line — numbered through the record."""
    words: list[str] = []
    owner: list[int] = []
    lines: list[int] = []
    line_number = 0
    for index, chunk in enumerate(chunks):
        if chunk.kind in ("rule", "drawing"):
            continue
        for line in markdown[chunk.start : chunk.end].split("\n"):
            found = _words(line)
            words += found
            owner += [index] * len(found)
            lines += [line_number] * len(found)
            line_number += 1
    return words, owner, lines


def _passages(base: str, other: str) -> list[tuple[int, int, int]]:
    """What `other` has and `base` lacks, as (the base paragraph it goes
    after, -1 for the top; the first and the last paragraph of `other` it is
    made of).

    The two are aligned word by word, by the runs of words they share in
    order. A gap in `other` between two such runs is set in where the base,
    between the same two runs, has no line of its own — only words a reading
    put differently at a line's edge. A gap where the base has a line of its
    own is a variant, and the base stays.
    """
    base_chunks, other_chunks = _chunks(base), _chunks(other)
    base_words, base_owner, base_lines = _stream(base, base_chunks)
    other_words, other_owner, _ = _stream(other, other_chunks)
    if not base_words or not other_words:
        return []

    # By the line, not the paragraph: a line the base read its own way is a
    # small part of a long paragraph, and record 64's «покажем радиус
    # [неразборчиво] носителя шарик» against 62's «покажем рецепт как найти
    # шарик» was a variant, not a line 64 lacked.
    line_size: dict[int, int] = {}
    for line in base_lines:
        line_size[line] = line_size.get(line, 0) + 1

    matcher = difflib.SequenceMatcher(None, base_words, other_words, autojunk=False)
    runs = [m for m in matcher.get_matching_blocks() if m.size >= _MATCH_WORDS]
    in_gap: dict[int, int] = {}
    after: dict[int, int] = {}
    previous_a = previous_b = 0
    for match in runs + [difflib.Match(len(base_words), len(other_words), 0)]:
        if match.b - previous_b >= _GAP_WORDS:
            facing: dict[int, int] = {}
            for position in range(previous_a, match.a):
                facing[base_lines[position]] = facing.get(base_lines[position], 0) + 1
            own = any(
                count / line_size[line] >= _OWN_LINE and line_size[line] >= 2
                for line, count in facing.items()
            )
            if not own:
                at = base_owner[previous_a - 1] if previous_a > 0 else -1
                for position in range(previous_b, match.b):
                    index = other_owner[position]
                    in_gap[index] = in_gap.get(index, 0) + 1
                    after.setdefault(index, at)
        previous_a, previous_b = match.a + match.size, match.b + match.size

    size: dict[int, int] = {}
    for index in other_owner:
        size[index] = size.get(index, 0) + 1
    base_runs = _runs(base)

    def already_there(index: int) -> bool:
        chunk = other_chunks[index]
        runs_here = _runs(other[chunk.start : chunk.end])
        return bool(runs_here) and len(runs_here & base_runs) / len(runs_here) >= _ALREADY_THERE

    chosen = [
        index
        for index in sorted(in_gap)
        if size[index] >= _PASSAGE_WORDS
        and in_gap[index] / size[index] >= _SET_IN
        and not already_there(index)
    ]
    # A heading goes in only with what it heads.
    chosen = [
        index
        for index in chosen
        if other_chunks[index].kind != "heading" or index + 1 in chosen
    ]

    passages: list[tuple[int, int, int]] = []
    for index in chosen:
        if passages:
            at, first, last = passages[-1]
            between = range(last + 1, index)
            if all(other_chunks[k].kind in ("rule", "drawing") for k in between):
                passages[-1] = (at, first, index)
                continue
        passages.append((after[index], index, index))
    return [
        passage
        for passage in passages
        if not _past_a_line(other_chunks, passage[1], passage[2])
    ]


def _past_a_line(chunks: list[_Chunk], first: int, last: int) -> bool:
    """Whether a passage is what a notebook carries past a line drawn across
    the page at its edge: at its end with the line before it, or at its start
    with the line after it. That is the next lecture begun, or the end of the
    one before, as often as it is this lecture's — record 62 carried
    «A = ((0, 2) ∖ …» after the author's line, the next lecture's first line.
    A page seam is such a line too, so a last page the base lacks is lost
    with it: the base stays as it was, which is better than a lecture that
    is not its own."""
    content = [i for i, chunk in enumerate(chunks) if chunk.kind == "content"]
    if not content:
        return False
    quiet = ("drawing", "heading")
    if last >= content[-1]:
        k = first - 1
        while k >= 0 and chunks[k].kind in quiet:
            k -= 1
        if k >= 0 and chunks[k].kind == "rule":
            return True
    if first <= content[0]:
        k = last + 1
        while k < len(chunks) and chunks[k].kind in quiet:
            k += 1
        if k < len(chunks) and chunks[k].kind == "rule":
            return True
    return False


@dataclass
class Merged:
    """A lecture drawn from its notebooks: the base with every passage the
    others add set in at its place, between pdf.inserted's lines, and the
    passages each of the others gave, in their order."""

    markdown: str
    passages: list[list[str]] = field(default_factory=list)


def merged(base: str, others: list[str], label: str) -> Merged:
    """The base, and what each of `others` adds to it.

    Each is aligned with the base alone; what an earlier one already gave is
    not given twice. A drawing a passage names by its cut-out is the other
    record's, and goes in as the line that described it.
    """
    base_chunks = _chunks(base)
    given: set[str] = set()
    # (after which base paragraph, which notebook, which of its passages, text)
    inserts: list[tuple[int, int, int, str]] = []
    passages: list[list[str]] = []
    for order, other in enumerate(others):
        own: list[str] = []
        other_chunks = _chunks(other)
        for at, first, last in _passages(base, other):
            text = other[other_chunks[first].start : other_chunks[last].end].strip()
            runs_here = _runs(text)
            if runs_here and len(runs_here & given) / len(runs_here) >= _ALREADY_THERE:
                continue
            given |= runs_here
            text = _PICTURE_RE.sub("[схема:", text)
            inserts.append((at, order, len(own), text))
            own.append(text)
        passages.append(own)

    markdown = base
    # From the end, so every offset still to be used stays where it was.
    # Two passages after one paragraph each go in at its end, so the later
    # one is set in first.
    for at, _, _, text in sorted(inserts, key=lambda item: item[:3], reverse=True):
        block = pdf.inserted(label, text)
        if at < 0:
            markdown = f"{block}\n\n{markdown}"
        else:
            cut = base_chunks[at].end
            markdown = f"{markdown[:cut]}\n\n{block}\n\n{markdown[cut:]}"
    return Merged(markdown, passages)
