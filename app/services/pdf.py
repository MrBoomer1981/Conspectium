"""A record rendered as a PDF, formulas included.

Recognised lecture notes are full of LaTeX — `$\\sum_{i=1}^{p} \\rho(v_i) = 2q$`
reads as noise until it is drawn. Formulas go through matplotlib's mathtext,
the surrounding text through reportlab.

Two halves on purpose. `blocks()` is a pure parser with no rendering in it, so
the reading of a page can be pinned down exactly by tests; `render()` turns
those blocks into a document. Neither ever raises on bad input: a formula
mathtext cannot read stays on the page as its own source, the same way
parse_response returns None rather than exploding.

The document is what the group receives, so its look is decided here rather
than left to reportlab's defaults, and it follows one file: `BRAND.md`, the
CEO's guide to how a SUM record looks — paper and ink, Onest for the text,
Unbounded for the headings, JetBrains Mono for the page's furniture, a
signature with a QR code at the foot of every page. It is also the
advertisement: a record is forwarded to the group's chat, and whoever opens
it has to see where it came from and how to get one. What the guide leaves
open — the boxes the bot adds, the findings of the checks, the formulas —
is decided here and written back into it.
"""

from __future__ import annotations

import functools
import io
import itertools
import logging
import math
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")  # no display on a server; must precede pyplot
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import patheffects  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from PIL import Image as PILImage  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas as rl_canvas  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Flowable,
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus import paragraph as _rl_paragraph  # noqa: E402

logger = logging.getLogger(__name__)

# reportlab sets a paragraph's first line a font size below its top, whatever
# the line holds, so a tall formula there — a column vector, a fraction over
# a fraction — rose into the line above: record 62's third example over its
# second. Placed by its own ascent instead, the first line makes room for what
# it holds, as autoLeading already makes the lines after it do; an ordinary
# line of text moves by a fraction of a point.
_rl_paragraph.paraFontSizeHeightOffset = 0

# Rendered at this DPI, then scaled to points. High enough that a formula
# stays sharp when the PDF is zoomed on a phone.
_DPI = 300

# ── The fonts ────────────────────────────────────────────────────────────────
# The guide's three faces, all from Google Fonts with full Cyrillic, bundled in
# the repo under their OFL licences as static weights cut from the variable
# fonts — reportlab reads a variable font at its default weight only. Onest
# for the text, Unbounded — the nearest to the logo's wide grotesque — for the
# title and the sections, JetBrains Mono for what serves the page rather than
# the lecture: the running head, a section's number, a box's label, the bot's
# name. DejaVu, which ships inside matplotlib, stays as the face for the
# glyphs they lack: Onest has no ∀, ∈, ⇒, ►, ℝ, nor a Greek letter, and
# reportlab would print them as empty boxes.
_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
_TEXT_FONT = "Onest"
_TEXT_BOLD_FONT = "Onest-SemiBold"
_HEADING_FONT = "Unbounded-Bold"
_HEAVY_FONT = "Unbounded-ExtraBold"
_MONO_FONT = "JetBrainsMono"
_MONO_BOLD_FONT = "JetBrainsMono-SemiBold"
_FALLBACK_FONT = "DejaVu"
# Formulas in Computer Modern, not in the guide's monospace: set in JetBrains
# Mono by mathtext, record 51's "ker φ" ran together into "kerφ", its zero —
# dotted inside — read as a θ, and a variable could not be told from an
# operator without italics. The monospace is kept for what serves the page.
# Computer Modern has no Cyrillic, and mathtext sets a \text{кольца} in a
# serif of its own instead.
_MATH_FONT = "cm"
# Computer Modern's hairlines, drawn as pixels and smoothed, came out a pale
# grey beside the text. A quarter-point stroke round every glyph brings the
# weight up to the text's; half a point was already bold.
_MATH_STROKE_PT = 0.25

# ── The scale: the guide's ───────────────────────────────────────────────────
_BODY_PT = 11.0
_LEADING = 1.5
_TITLE_PT = 22.0
# Levels are counted from the top one the record uses, so a record whose
# sections are "##" looks like one whose sections are "#". The level blocks()
# reads was once thrown away altogether, which made "#" and "###" the same.
# The guide has two sizes of heading, the lecture's and a section's, both in
# Unbounded; a subsection is set in the text's own face, a step above it.
_HEADING_PT = {1: 13.5, 2: 12.5, 3: 11.0}
_HEADING_SPACE_BEFORE = {1: 22, 2: 14, 3: 10}
_HEADING_SPACE_AFTER = {1: 6, 2: 4, 3: 3}
# Computer Modern's x-height is smaller than Onest's, 0.43 of the size against
# 0.53, so a formula is set a little larger than the text round it.
_MATH_SCALE = 1.1
_DISPLAY_PT = _BODY_PT * _MATH_SCALE
_TABLE_PT = 10.0
_SMALL_PT = 9.5
_LABEL_PT = 7.5
_LABEL_TRACKING = 0.9
_FURNITURE_PT = 8.0
_FURNITURE_TRACKING = 0.5

# ── The rhythm ───────────────────────────────────────────────────────────────
# The space between two blocks depends on what both of them are. Lines of one
# paragraph sit at the leading and nothing more: a lecture note is written
# line by line, and space under every line made a page of them read as
# double-spaced. A blank line in the record is a paragraph. A display
# formula, a table and a drawing are set apart, and a run of display formulas
# is one block, the way a chain of equalities is one thing on paper: their
# grounds touch and read as one.
_PARAGRAPH_GAP = 8.0
_SET_APART_GAP = 9.0
_ITEM_GAP = 3.0
_BOX_GAP = 8.0
_MAIN_GAP = 12.0
_SET_APART = {"math", "main", "frame", "table", "figure", "note", "rule", "definition"}

# ── Main formulas ────────────────────────────────────────────────────────────
# When every formula is set at one size, the one a section leads to is lost
# among the steps to it. A main formula is larger, framed the way the author
# frames it in the notebook, and numbered at the column's edge, so that an
# explanation can say "(3)" and be found.
_MAIN_PT = _DISPLAY_PT * 1.2
_FRAME_RULE_PT = 0.8
_FRAME_PAD_X = 12.0
_FRAME_PAD_Y = 6.0
_NUMBER_PT = 9.0
_NUMBER_COLUMN_PT = 36.0

# ── The page ─────────────────────────────────────────────────────────────────
# 66 pt either side of an A4 page, 463 pt of text. The foot of every page is
# the signature's, 22 mm under a line of kraft, and the column ends above it.
_MARGIN_PT = 66.0
_TOP_PT = 60.0
_SIGNATURE_PT = 22 * mm
_BOTTOM_PT = _SIGNATURE_PT + 8 * mm
_TEXT_WIDTH_PT = A4[0] - 2 * _MARGIN_PT
# reportlab's frame pads its content by 6 pt on every side, inside the page
# margins. Unaccounted for, the column was 12 pt narrower than every width
# computed from it, and a box as wide as the column ran past its right edge.
_FRAME_PADDING_PT = 6.0

# ── The guide's five colours, and the one grey it names without a value ─────
# Paper under everything, never white; ink for the text. Amber is graphics
# only — the star, the line beside a definition — being too pale for text on
# paper; the dark amber is its text: a section's number, a finding's label.
# Kraft for lines, frames and the ground under a formula.
_PAPER = "#F1E8D8"
_INK = "#1A1612"
_AMBER = "#F0A040"
_DARK_AMBER = "#B8691A"
_KRAFT = "#D9C9AE"
_FORMULA_GROUND = "#E6DAC5"
# "Серые чернила": ink two-thirds of the way to the paper would be too pale
# for 8 pt, so the ink at 65% — 4.7 to 1 against the paper.
_MUTED = "#6E655A"
# On the one dark block, "Суть", the line that says whose words these are.
_MUTED_ON_INK = "#A3947E"
_HAIRLINE = _KRAFT
# The label of a box about the record, and of a finding set under its line:
# dark amber for what is certainly wrong, grey for what only may be. The bar
# down its side is `_CALLOUT_BARS`'.
_CALLOUT_TONES = {
    "info": _MUTED,
    "warning": _DARK_AMBER,
}
_CALLOUT_BARS = {
    "info": _KRAFT,
    "warning": _DARK_AMBER,
}
# What the bot adds of its own — an explanation — carries the colour of the
# one block that is the bot's by definition, "Суть": ink, with its label. The
# green it had before the guide was a sixth colour; the label says whose words
# these are, as it always did.
_ADDED_TONE = _INK
# The line beside a definition, the author's own text: the guide's amber.
_DEFINITION_BAR = _AMBER
_BAR_PT = 3.0
# A passage another notebook of the lecture adds (task 63) is the lecture's
# text, not a box beside it: it keeps the column's width, so its formulas and
# tables are drawn as the base's are, and a kraft line in the margin beside
# it, its label over it in the grey ink, says it was set in.
_INSERT_BAR = _KRAFT
_INSERT_LABEL = _MUTED
_INSERT_BAR_GAP = 10.0

# ── Drawings ─────────────────────────────────────────────────────────────────
# Three of them still fit across the reference's narrower column at full size.
_GRAPH_WIDTH_PT = 135.0
# Every graph is drawn at one scale, points per unit of the layout circle, so
# a triangle and a hexagon on one page have vertices of one size. The drawing
# is then cut to what is drawn: a square as wide as the circle left a third of
# a triangle's picture empty under it.
_GRAPH_SCALE_PT = _GRAPH_WIDTH_PT / 3.2
_GRAPH_INCHES_PER_UNIT = 0.75
_GRAPH_NODE = 0.17
# More than three drawings in a row and none of them is readable.
_FIGURES_PER_ROW = 3
# Padding either side of a drawing inside its cell of the row.
_FIGURE_GAP_PT = 16.0
# Narrower than this, a graph beside its matrix is unreadable, and the two are
# stacked instead.
_MIN_BESIDE_PT = 90.0
_MIN_COLUMN_PT = 20.0
_MAX_COLUMN_PT = 120.0

# ── Parsing ──────────────────────────────────────────────────────────────────

# $...$ with no newline inside — or $$...$$ written inside a line, which is how
# "$$v = cR(...)$$ — формула Ридберга" arrives: read as the single form, it
# left a stray dollar at either end. A backslash-escaped \$ is left alone: it
# is a literal dollar sign, not the start of a formula.
_MATH_RE = re.compile(
    r"(?<!\\)\$\$([^$\n]+?)(?<!\\)\$\$|(?<!\\)\$([^$\n]+?)(?<!\\)\$"
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^\s*[-*•]\s+(.*)$")
# "1) абелева группа", "2. если ...": numbered the way the author numbered it,
# set with the number hanging like a bullet.
_NUMBERED_RE = re.compile(r"^\s*(\d{1,2}[.)])\s+(\S.*)$")
# The seam _assemble writes between two pages of an album, and the wavy line
# an author draws across a page, which record 62 printed as "~~~".
_RULE_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,}|~{3,})$")
# A passage another notebook of the same lecture adds (task 63): a line
# "⟦+ label⟧" opens it and "⟦+⟧" closes it. Never in a stored record —
# merge.merged writes them into the text it hands to render, and nowhere else.
_INSERT_CLOSE = "⟦+⟧"
_INSERT_OPEN_RE = re.compile(r"^⟦\+\s*(.+?)⟧$")
# A markdown table row, and the "|---|:--|" line that marks the row above it
# as a header rather than data.
_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_ROW_SEPARATOR_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
# "[граф: 1-2]", or "[граф Ориентированный: 1->2]" with a caption.
_GRAPH_RE = re.compile(
    r"^(?:граф|graph)\s*([^:]{0,40}?)\s*:\s*(.*)$", re.IGNORECASE
)
_DIRECTED_RE = re.compile(r"\s*(?:-+>|→)\s*")
_UNDIRECTED_RE = re.compile(r"\s*[-–—]\s*")
# A fragment that is LaTeX rather than prose: a command, or a sub- or
# superscript. Cyrillic in it means prose around the maths, and prose is not
# something mathtext can draw — only the commands standing in it are.
_LATEX_HINT_RE = re.compile(r"\\[A-Za-z]+|[_^]")
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_BARE_COMMAND_RE = re.compile(r"\\[A-Za-z]+(?:\{[^{}]*\})*")
# The composing stage puts <br> inside a table cell to stack lines the author
# wrote one under another. Printed, it was the tag itself, three times a cell.
_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
# What the author drew a frame round. Recognition writes a framed formula as
# \boxed{...} and framed text as [рамка: ...]; records read before that rule
# carry "[в рамке: ...]", a bracket opened on one line and closed lines later,
# or an array with a ruled column spec and \hline — all of them are frames.
# The spec has to be barred at both ends, "{|l|}": a bar only between the
# columns is a table ruled inside — a long division — and is drawn as one
# (ruled_arrays), not framed and numbered as a main formula.
_FRAME_NOTE_RE = re.compile(r"^(?:в\s+)?рамк\w*\s*:\s*(.*)$", re.IGNORECASE | re.DOTALL)
# "[рисунок 3: …]": a drawing cut out of the page, the record's third, and the
# words recognition described it in (figures.place).
_PICTURE_RE = re.compile(r"^рисунок\s+(\d+)\s*:\s*(.*)$", re.IGNORECASE | re.DOTALL)
# A drawing written inside a line of text — "A ⊂ ⋃ U_α [схема: числовая ось]"
# on record 59 — printed its brackets in the middle of the sentence.
_INLINE_DRAWING_RE = re.compile(
    r"\[\s*(?:схема|рисунок\s+\d+|граф[^\[\]:]{0,40}|graph[^\[\]:]{0,40})\s*:[^\[\]]*\]",
    re.IGNORECASE,
)
_FRAME_OPEN_RE = re.compile(r"^\[\s*(?:в\s+)?рамк\w*\s*:?\s*(.*)$", re.IGNORECASE)
_FRAMED_ARRAY_RE = re.compile(r"\\begin\{array\}\{\|[^{}]*\|\}")
_BOXED = "\\boxed{"
# A frame round more than a dozen lines is not a frame the parser should guess
# the end of; the bracket stays text.
_MAX_FRAME_LINES = 12

# Past this a circle of vertices is unreadable, and the text is more likely to
# be prose the model mislabelled than a graph. Same for a long vertex name.
_MAX_VERTICES = 24
_MAX_VERTEX_CHARS = 12


@dataclass
class Callout:
    """A box above the record, about the record as a whole — the pages it is
    missing.

    Never anything the model wrote about the page, and never how the page was
    read: only what the pipeline stored beside the text. The caller builds
    these; this module knows nothing about where a record comes from.
    """

    title: str
    lines: list[str]
    tone: str = "info"  # "info" | "warning"


@dataclass
class Remark:
    """What a check made by code found wrong in one place of the record — an
    equality that does not hold, a matrix the graph beside it contradicts —
    set under that place.

    `anchor` is the text it belongs to, found the way an explanation's is
    (`_anchored`). One that matches nothing is not thrown away — it goes at
    the end, where it is still readable. `tone` is a callout's: "warning" for
    what is certainly wrong, "info" for what only may be.
    """

    anchor: str
    label: str
    lines: list[str]
    tone: str = "info"


@dataclass
class Explanation:
    """Something the bot adds of its own: a hard place explained, with the
    sources the search gave for it. Printed as the bot's, in a tone no other
    box has, under the line or the numbered formula it explains — the
    reference document's way with its own additions.

    `anchor` is a quote from the record or a formula's number, "(3)". One
    that anchors nowhere goes to the end rather than nowhere, like a remark.
    """

    anchor: str
    label: str
    lines: list[str]
    sources: list[tuple[str, str]]  # (title, uri)
    sources_label: str = "Источники"
    # Set before what it is anchored to rather than under it: the idea of a
    # proof is read before the proof (task 56).
    before: bool = False


@dataclass
class Summary:
    """The record summed up by the bot, set first as "Суть", the guide's one
    dark block, and marked as the bot's. It restates the record; it is not a
    source of anything.

    `label` is "what it is · whose it is": the part before the first " · " is
    set as the block's name, the rest as the note beside it."""

    label: str
    lines: list[str]


@dataclass
class Page:
    """What every page carries besides the record. The caller builds it; this
    module knows nothing about chats or bots.

    The head says which lecture a sheet is from even when it is forwarded on
    its own; the signature at the foot says where it came from and how to get
    one — the bot's name and a QR code that opens it.
    """

    subject: str = ""  # "#матан", when the record is filed under one
    date: str = ""  # "28.09.2026"
    page_word: str = ""  # "стр."
    invite: str = ""  # "Сделай такой конспект своей группе"
    bot_username: str = ""  # without the "@"; none, and there is no QR either


@dataclass
class Block:
    # heading | bullet | text | math | note | framed | gap | rule | table |
    # graph | picture | inserted | inserted_end
    kind: str
    text: str = ""
    level: int = 0
    rows: list[list[str]] = field(default_factory=list)
    header: bool = False
    caption: str = ""
    marker: str = ""  # a list item's own number, "1)" — empty for a bullet
    # A formula that matters more than the ones round it: the author framed
    # it, or the composing stage marked it as the section's result.
    main: bool = False
    # The line of the record the block was read from, so a number given to it
    # here can be written back beside it for a model to point at.
    line: int = field(default=-1, compare=False, repr=False)
    # A picture's drawing as the record keeps it — the darkness of its ink,
    # a greyscale PNG — attached by render() from what the record stored.
    image: bytes | None = field(default=None, compare=False, repr=False)


def _latex(match: re.Match) -> str:
    return (match.group(1) or match.group(2)).strip()


def boxed_contents(text: str) -> list[str]:
    """What stands inside every \\boxed{...} in `text`, braces matched.

    A regular expression cannot match nested braces, and a framed formula is
    usually a fraction or a sum — braces inside braces. An unclosed \\boxed is
    not a box and is skipped rather than guessed at.
    """
    found: list[str] = []
    start = text.find(_BOXED)
    while start != -1:
        depth, position = 1, start + len(_BOXED)
        while position < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[position], 0)
            position += 1
        if depth == 0:
            found.append(text[start + len(_BOXED) : position - 1])
        start = text.find(_BOXED, start + len(_BOXED))
    return found


def unbox(latex: str) -> tuple[str, bool]:
    """`latex` with every \\boxed{...} replaced by what it frames, and whether
    there was one. mathtext has no \\boxed; the frame is drawn by render()."""
    contents = boxed_contents(latex)
    for inner in contents:
        latex = latex.replace(f"{_BOXED}{inner}}}", inner, 1)
    return latex, bool(contents)


def _math_block(latex: str) -> Block:
    """A display formula, marked as main when the author framed it."""
    clean, boxed = unbox(latex)
    framed_array = bool(_FRAMED_ARRAY_RE.search(clean)) and "\\hline" in clean
    return Block("math", clean, main=boxed or framed_array)


def _frame_lines(lines: list[str], start: int) -> tuple[Block, int] | None:
    """A frame the author drew round several lines, which recognition wrote as
    a bracket opened on one line and closed on a later one:

        [в рамке:
        $(0, 1) = i$
        $(0, -1) = -i$
        ]

    Read line by line it printed as "[в рамке:", the formulas, and a lone "]".
    None when `start` does not open such a frame, or it is never closed.
    """
    opened = _FRAME_OPEN_RE.match(lines[start].strip())
    if opened is None or lines[start].strip().endswith("]"):
        return None
    inner = [opened.group(1).strip()]
    for end in range(start + 1, min(len(lines), start + 1 + _MAX_FRAME_LINES)):
        line = lines[end].strip()
        if not line:
            return None
        if line.endswith("]"):
            inner.append(line[:-1].strip())
            content = [part for part in inner if part]
            if not content:
                return None
            return Block("framed", "\n".join(content)), end + 1
        inner.append(line)
    return None


def _is_whole_formula(line: str) -> str | None:
    """The LaTeX of a line that is nothing but one formula, else None. Such a
    line is set on its own, centred, the way it sat on the page."""
    match = _MATH_RE.fullmatch(line.strip())
    return _latex(match) if match else None


def _display_lines(
    lines: list[str], start: int
) -> tuple[list[tuple[str, int]], int] | None:
    """A formula set between lines of "$$", the way the composing stage writes
    one, with the index just past the closing line — or None if `start` does
    not open such a block.

    Read line by line, every one of them went out as its own source: "$$",
    then the LaTeX, then "$$" again, seven times on one record. Each line
    between the dollars is a formula of its own, as on the page — except
    inside an environment, whose rows are one formula spread over lines.

    A blank line before the closing "$$" means it was never a block: the
    dollars stay text rather than swallowing the rest of the record.
    """
    first = lines[start].strip()
    if not first.startswith("$$") or _MATH_RE.fullmatch(first):
        return None
    body = [(first[2:].strip(), start)]
    for end in range(start + 1, len(lines)):
        line = lines[end].strip()
        if not line:
            return None
        if line.endswith("$$"):
            body.append((line[:-2].strip(), end))
            content = [(part, at) for part, at in body if part]
            if any("\\begin" in part for part, _ in content):
                return [(" ".join(part for part, _ in content), end)], end + 1
            return content, end + 1
        body.append((line, end))
    return None


# A formula written loosely across lines — record 47, read with recognition's
# thinking turned down, had 103 lines of it printed as source. Two shapes:
# an environment with no dollars round it at all, "\begin{array}" on a line
# of its own and "\end{array}" twelve lines later; and a "$" opened on one
# line and closed on a later one. Joined, each is one formula, and whatever
# stood before its opening or after its close on those lines stays text.
_BARE_BEGIN_RE = re.compile(r"^\\begin\{([A-Za-z]+\*?)\}")
_ENVIRONMENT_EDGE_RE = re.compile(r"\\(begin|end)\{([A-Za-z]+\*?)\}")
_DOLLAR_RE = re.compile(r"(?<!\\)\$\$?")
# Further than this, an unclosed environment or "$" is a slip of the model's,
# not a formula, and the lines stay as they are.
_MAX_LOOSE_LINES = 60
# What a span has to carry to be taken for a formula written over several
# lines rather than two stray dollars: an environment, a row break or a
# column. "5$ ... 3$" in prose carries none of them.
_LOOSE_FORMULA_HINT_RE = re.compile(r"\\begin\{|\\\\|(?<!\\)&")


def _open_dollar(line: str) -> int | None:
    """Where a single "$" opens a formula this line does not close, or None.
    Dollars pair left to right, "$$" with "$$" and "$" with "$", the way
    split_inline reads them."""
    opened: tuple[str, int] | None = None
    for found in _DOLLAR_RE.finditer(line):
        if opened is None:
            opened = (found.group(), found.start())
        elif opened[0] == found.group():
            opened = None
    return opened[1] if opened is not None and opened[0] == "$" else None


def _loose_formula(
    lines: list[str], start: int
) -> tuple[list[tuple[str, str]], int] | None:
    """A formula spread over lines from `start` as ("text"/"math", value)
    pieces in order, with the index just past it — or None."""
    first = lines[start].strip()
    last = min(len(lines), start + _MAX_LOOSE_LINES)

    bare = _BARE_BEGIN_RE.match(first)
    if bare is not None:
        depth = 0
        for end in range(start, last):
            line = lines[end].strip()
            for edge in _ENVIRONMENT_EDGE_RE.finditer(line):
                if edge.group(2) != bare.group(1):
                    continue
                depth += 1 if edge.group(1) == "begin" else -1
                if depth == 0:
                    body = " ".join(part.strip() for part in lines[start:end]) + " "
                    formula = (body + line[: edge.end()]).strip()
                    pieces = [("math", formula)]
                    if line[edge.end() :].strip():
                        pieces.append(("text", line[edge.end() :].strip()))
                    return pieces, end + 1
        return None

    opening = _open_dollar(first)
    if opening is None:
        return None
    for end in range(start + 1, last):
        line = lines[end].strip()
        if not line:
            return None
        closing = next(
            (found.start() for found in _DOLLAR_RE.finditer(line) if found.group() == "$"),
            None,
        )
        if closing is None:
            continue
        middle = [part.strip() for part in lines[start + 1 : end]]
        formula = " ".join([first[opening + 1 :], *middle, line[:closing]]).strip()
        if not _LOOSE_FORMULA_HINT_RE.search(formula):
            return None
        pieces = []
        if first[:opening].strip():
            pieces.append(("text", first[:opening].strip()))
        pieces.append(("math", formula))
        if line[closing + 1 :].strip():
            pieces.append(("text", line[closing + 1 :].strip()))
        return pieces, end + 1
    return None


def _read_table(lines: list[str], start: int) -> tuple[Block, int] | None:
    """The run of "| a | b |" lines at `start` as one block, with the index
    just past it — or None if there is no table here.

    Two rows is the minimum. A single line that happens to open and close with
    a pipe is far more often maths, `|V| \\times |E|`, than a table.
    """
    end = start
    while end < len(lines) and _ROW_RE.match(lines[end]):
        end += 1
    if end - start < 2:
        return None

    header = False
    rows: list[list[str]] = []
    for position in range(start, end):
        if _ROW_SEPARATOR_RE.match(lines[position]):
            # "|---|---|" is not a row: it says the rows above it are a header.
            # An empty "| | |" reads as a separator too, so it is a header only
            # when a row was actually read above it.
            header = bool(rows)
            continue
        rows.append(
            [cell.strip() for cell in lines[position].strip().strip("|").split("|")]
        )
    if not rows:
        return None

    # A header with nothing in it names no column: "| | |" over "|---|---|" is
    # how the composing stage opens a table it only wanted for its layout.
    if header and not any(cell for cell in rows[0]):
        rows, header = rows[1:], False
        if not rows:
            return None

    # Ragged rows would make reportlab raise. A hand-copied matrix with a cell
    # missing is still worth showing.
    width = max(len(row) for row in rows)
    for row in rows:
        row.extend([""] * (width - len(row)))
    return Block("table", rows=rows, header=header), end


def parse_graph(spec: str) -> tuple[list[str], list[tuple[str, str]], bool] | None:
    """"1-2, 2->3, 3-3" as (vertices, edges, directed), or None when it does
    not read as a graph. Vertices keep the order the model listed them in — it
    is the order they were read off the page.

    Never raises: an unparseable spec falls back to being printed, the same way
    a formula mathtext cannot read stays on the page as its own source.
    """
    vertices: list[str] = []
    edges: list[tuple[str, str]] = []
    directed = False

    for item in re.split(r"[,;\n]", spec):
        item = item.strip()
        if not item:
            continue
        pair = _DIRECTED_RE.split(item, maxsplit=1)
        if len(pair) == 2:
            directed = True
        else:
            pair = _UNDIRECTED_RE.split(item, maxsplit=1)
        if len(pair) != 2:
            # No separator at all: a vertex drawn with no edges on it. Not a
            # loop — a loop is written "3-3" and has a separator.
            if item not in vertices:
                vertices.append(item)
            continue
        tail, head = pair[0].strip(), pair[1].strip()
        if not tail or not head:
            continue
        for vertex in (tail, head):
            if vertex not in vertices:
                vertices.append(vertex)
        if (tail, head) not in edges:
            edges.append((tail, head))

    if not vertices or len(vertices) > _MAX_VERTICES:
        return None
    if any(len(vertex) > _MAX_VERTEX_CHARS for vertex in vertices):
        return None
    return vertices, edges, directed


def _lift_drawings(markdown: str) -> str:
    """Every drawing written inside a line of text moved onto a line of its
    own, between the text before it and the text after it. Done for the
    document only: the stages that number the record's lines read it as it
    is stored."""
    out: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        found = list(_INLINE_DRAWING_RE.finditer(line))
        if stripped.startswith("|") or not found or (
            len(found) == 1 and found[0].group(0) == stripped
        ):
            out.append(line)
            continue
        last = 0
        for match in found:
            before = line[last : match.start()].strip()
            if before:
                out.append(before)
            out.append(match.group(0))
            last = match.end()
        after = line[last:].strip()
        if after:
            out.append(after)
    return "\n".join(out)


def blocks(markdown: str) -> list[Block]:
    """Split a record into renderable pieces.

    Every line becomes its own block rather than being joined into flowing
    paragraphs. A lecture note is written line by line — a definition, a
    formula, a consequence — and gluing consecutive lines together produces
    sentences the author never wrote. A table is the single exception: its
    lines mean nothing apart.
    """
    out: list[Block] = []
    lines = markdown.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()

        if not stripped:
            # Collapse runs of blank lines: one gap is a gap.
            if out and out[-1].kind != "gap":
                out.append(Block("gap"))
            index += 1
            continue

        # Where a passage from another notebook begins and ends (task 63).
        if stripped == _INSERT_CLOSE:
            out.append(Block("inserted_end"))
            index += 1
            continue
        opened = _INSERT_OPEN_RE.match(stripped)
        if opened:
            out.append(Block("inserted", opened.group(1)))
            index += 1
            continue

        display = _display_lines(lines, index)
        if display is not None:
            formulas, index = display
            for formula, at in formulas:
                block = _math_block(formula)
                block.line = at
                out.append(block)
            continue

        frame = _frame_lines(lines, index)
        if frame is not None:
            block, index = frame
            block.line = index - 1
            out.append(block)
            continue

        loose = _loose_formula(lines, index)
        if loose is not None:
            pieces, end = loose
            for kind, value in pieces:
                block = _math_block(value) if kind == "math" else Block("text", value)
                block.line = index
                out.append(block)
            index = end
            continue

        table = _read_table(lines, index)
        if table is not None:
            block, end = table
            block.line = index
            index = end
            out.append(block)
            continue

        if _RULE_RE.match(stripped):
            out.append(Block("rule"))
            index += 1
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            out.append(
                Block("heading", heading.group(2).strip(), min(len(heading.group(1)), 6))
            )
            index += 1
            continue

        formula = _is_whole_formula(line)
        if formula:
            block = _math_block(formula)
            block.line = index
            out.append(block)
            index += 1
            continue

        bullet = _BULLET_RE.match(line)
        if bullet:
            out.append(Block("bullet", bullet.group(1).strip()))
            index += 1
            continue

        numbered = _NUMBERED_RE.match(line)
        if numbered:
            out.append(
                Block("bullet", numbered.group(2).strip(), marker=numbered.group(1))
            )
            index += 1
            continue

        # "[схема: граф с петлёй]" — the model's note that something on the
        # page is a drawing, and all the record has of it. "[рисунок 3: …]" is
        # one cut out of the page, which the record keeps. "[граф: 1-2, 2-3]"
        # is a drawing given as its edges, and is drawn from them.
        if stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1].strip()
            picture = _PICTURE_RE.match(inner)
            drawing = _GRAPH_RE.match(inner)
            framed = _FRAME_NOTE_RE.match(inner)
            if picture:
                out.append(
                    Block("picture", picture.group(2).strip(), marker=picture.group(1))
                )
            elif drawing:
                out.append(
                    Block("graph", drawing.group(2).strip(), caption=drawing.group(1).strip())
                )
            elif framed and framed.group(1).strip():
                out.append(Block("framed", framed.group(1).strip(), line=index))
            else:
                out.append(Block("note", inner))
            index += 1
            continue

        out.append(Block("text", stripped))
        index += 1

    while out and out[-1].kind == "gap":
        out.pop()
    return out


def _is_numbered(block: Block) -> bool:
    """Whether render gives this block a number: a main formula, or a frame
    round a formula."""
    return (block.kind == "math" and block.main) or (
        block.kind == "framed" and "$" in block.text
    )


def numbered_for_reading(markdown: str) -> str:
    """The record with each main formula's number written after it, "(3)",
    exactly as render will number it — so that a model reading the record can
    point at a formula by the number the reader sees on the page."""
    lines = markdown.splitlines()
    number = 0
    for block in blocks(markdown):
        if _is_numbered(block):
            number += 1
            if 0 <= block.line < len(lines):
                lines[block.line] = f"{lines[block.line]}   ({number})"
    return "\n".join(lines)


def split_inline(text: str) -> list[tuple[str, str]]:
    """Cut a line into ("text", s) and ("math", latex) runs, in order."""
    parts: list[tuple[str, str]] = []
    position = 0
    for match in _MATH_RE.finditer(text):
        if match.start() > position:
            parts.append(("text", text[position : match.start()]))
        parts.append(("math", _latex(match)))
        position = match.end()
    if position < len(text):
        parts.append(("text", text[position:]))
    return parts


# A title is written with its formulas — "Найти остаток от деления
# $2^{1001}$" — and three places cannot draw one: the running head, the
# file's own title and its name. Record 45 carried "$2^{1001}$" at the top of
# every page and went out as "45-Найти-остаток-от-деления-21001.pdf". Those
# places get the formula in characters instead: digits raised and lowered,
# the symbols a font has, and a command with no symbol dropped rather than
# spelled out.
_SUPERSCRIPT_OF = str.maketrans("0123456789+-=()ni", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ")
_SUBSCRIPT_OF = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
_RAISABLE = frozenset("0123456789+-=()ni")
_LOWERABLE = frozenset("0123456789+-=()")
_SCRIPT_RE = re.compile(r"([\^_])\s*(?:\{([^{}]*)\}|([^\s\\{}]))")
_WORDS_IN_FORMULA_RE = re.compile(
    r"\\(?:text|mathrm|mathbf|mathit|operatorname)\{([^{}]*)\}"
)
_PLAIN_FRACTION_RE = re.compile(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}")
_BLACKBOARD_RE = re.compile(r"\\mathbb\{([A-Z])\}")
_BLACKBOARD = {"R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "C": "ℂ"}
_PLAIN_COMMAND_RE = re.compile(r"\\([A-Za-z]+)")
_PLAIN_SYMBOLS = {
    "cdot": "·", "times": "×", "equiv": "≡", "le": "≤", "leq": "≤",
    "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠", "approx": "≈",
    "infty": "∞", "pm": "±", "to": "→", "rightarrow": "→", "Rightarrow": "⇒",
    "in": "∈", "sqrt": "√", "sum": "∑", "int": "∫", "partial": "∂",
    "nabla": "∇", "pi": "π", "alpha": "α", "beta": "β", "gamma": "γ",
    "delta": "δ", "Delta": "Δ", "varepsilon": "ε", "epsilon": "ε",
    "lambda": "λ", "mu": "μ", "sigma": "σ", "theta": "θ", "varphi": "φ",
    "phi": "φ", "psi": "ψ", "Psi": "Ψ", "omega": "ω", "Omega": "Ω",
    "pmod": "mod ", "bmod": "mod ", "mod": "mod ",
}


def _plain_script(found: re.Match) -> str:
    body = found.group(2) if found.group(2) is not None else found.group(3)
    body = body.strip()
    if found.group(1) == "^" and body and set(body) <= _RAISABLE:
        return body.translate(_SUPERSCRIPT_OF)
    if found.group(1) == "_" and body and set(body) <= _LOWERABLE:
        return body.translate(_SUBSCRIPT_OF)
    return found.group(1) + body


def _plain_formula(latex: str) -> str:
    latex = _BLACKBOARD_RE.sub(lambda found: _BLACKBOARD[found.group(1)], latex)
    latex = _PLAIN_FRACTION_RE.sub(r"\1/\2", latex)
    latex = _WORDS_IN_FORMULA_RE.sub(r"\1", latex)
    latex = _SCRIPT_RE.sub(_plain_script, latex)
    latex = _PLAIN_COMMAND_RE.sub(
        lambda found: _PLAIN_SYMBOLS.get(found.group(1), ""), latex
    )
    latex = latex.replace("{", "").replace("}", "").replace("\\", "")
    return " ".join(latex.split())


def plain(text: str) -> str:
    """A line with its formulas turned into characters, for the places that
    cannot draw one."""
    drawn = _MATH_RE.sub(lambda found: _plain_formula(_latex(found)), text)
    return " ".join(drawn.replace("\\$", "$").split())


def as_formula(fragment: str) -> str:
    """A fragment of what was read, with its LaTeX marked as formulas.

    `uncertain` quotes the page as it was transcribed, and inside a formula
    that is LaTeX with no dollars round it: «\\rho^-(v)» went out on a remark
    as its own source, and so did "похожа на греческую \\chi". A fragment
    that is all LaTeX becomes one formula. In prose — anything with Cyrillic
    in it — only the commands standing in it are marked, and every word
    stays exactly where it was.
    """
    text = fragment.strip()
    if not text or "$" in text:
        return fragment
    if not _CYRILLIC_RE.search(text) and _LATEX_HINT_RE.search(text):
        return f"${text}$"
    return _BARE_COMMAND_RE.sub(lambda found: f"${found.group()}$", fragment)


def inserted(label: str, markdown: str) -> str:
    """A passage from another notebook of the lecture, marked for render to
    set it apart under `label` (task 63)."""
    return f"⟦+ {label}⟧\n{markdown.strip()}\n{_INSERT_CLOSE}"


# ── Rendering ────────────────────────────────────────────────────────────────


def _mpl_font(name: str) -> str:
    return os.path.join(
        os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf", name
    )


_FONTS_READY = False


def _register_fonts() -> None:
    """The guide's faces from the repo, DejaVu from inside matplotlib.
    reportlab's built-in fonts are Latin only, and a page of notes is
    Cyrillic."""
    global _FONTS_READY
    if _FONTS_READY:
        return
    for name, filename in (
        (_TEXT_FONT, "Onest-Regular.ttf"),
        (_TEXT_BOLD_FONT, "Onest-SemiBold.ttf"),
        (_HEADING_FONT, "Unbounded-Bold.ttf"),
        (_HEAVY_FONT, "Unbounded-ExtraBold.ttf"),
        (_MONO_FONT, "JetBrainsMono-Regular.ttf"),
        (_MONO_BOLD_FONT, "JetBrainsMono-SemiBold.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(name, os.path.join(_FONT_DIR, filename)))
    # Every face a paragraph is set in needs a family, or a "**" inside it —
    # a bold word in a heading — is an exception inside reportlab. None of
    # them has an italic, and the record asks for none: the upright face
    # stands in for it rather than failing.
    for normal, bold in (
        (_TEXT_FONT, _TEXT_BOLD_FONT),
        (_HEADING_FONT, _HEAVY_FONT),
        (_HEAVY_FONT, _HEAVY_FONT),
        (_MONO_FONT, _MONO_BOLD_FONT),
    ):
        pdfmetrics.registerFontFamily(
            normal, normal=normal, bold=bold, italic=normal, boldItalic=bold
        )
    for name, filename in (
        ("DejaVu", "DejaVuSans.ttf"),
        ("DejaVu-Bold", "DejaVuSans-Bold.ttf"),
        ("DejaVu-Oblique", "DejaVuSans-Oblique.ttf"),
        ("DejaVu-BoldOblique", "DejaVuSans-BoldOblique.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(name, _mpl_font(filename)))
    pdfmetrics.registerFontFamily(
        "DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique",
        boldItalic="DejaVu-BoldOblique",
    )
    _FONTS_READY = True


@functools.lru_cache(maxsize=2)
def _glyphs(filename: str) -> frozenset[int]:
    """Every character a bundled face can draw. Anything else is set in
    DejaVu, which draws nearly everything."""
    return frozenset(
        TTFont(f"Coverage-{filename}", os.path.join(_FONT_DIR, filename)).face.charToGlyph
    )


def _text_glyphs() -> frozenset[int]:
    """What Onest draws — the test for running text, headings included:
    Unbounded draws at least as much of what a heading holds."""
    return _glyphs("Onest-Regular.ttf")


def _mono_glyphs() -> frozenset[int]:
    return _glyphs("JetBrainsMono-Regular.ttf")


def warm_up() -> None:
    """Build matplotlib's font cache and register the fonts ahead of the first
    request. Both are one-off costs of a few seconds; paying them at startup
    keeps them out of someone's first photo."""
    try:
        _register_fonts()
        _text_glyphs()
        _mono_glyphs()
        _formula_png("x^2", _DISPLAY_PT)
    except Exception:
        logger.exception("PDF warm-up failed; first render will be slower")


# mathtext is not LaTeX, and the model writes LaTeX. These commands are the
# ones it reaches for that mathtext rejects outright, taking the whole formula
# down with them: a page that said \sum\limits_{i=1}^p printed as its own
# source while the same sum written \sum_{i=1}^p drew perfectly. Each one
# either has no effect on how mathtext lays a formula out or has a synonym it
# does know, so dropping it costs nothing.
#
# The \big family is here for the same reason: it sizes a delimiter, mathtext
# sizes its own, and dropping the modifier leaves the bracket standing.
#
# The boundary is (?![A-Za-z]), not \b: "_" counts as a word character, so
# `limits\b` never matches `\limits_{i=1}` — and \lim and \limsup must
# survive untouched. It is what keeps \big off \bigcup, too; \bigl and
# \bigr are letters away from \big and have to be named in their own right.
_COMMAND_END = r"(?![A-Za-z])"
_UNSUPPORTED = (
    "limits", "nolimits", "displaystyle", "textstyle",
    "biggl", "biggr", "Biggl", "Biggr", "bigl", "bigr", "Bigl", "Bigr",
    "bigg", "Bigg", "big", "Big",
    # A rule across an array: record 43 used one to draw the author's frame,
    # and the whole formula went out as source. The frame is drawn by render.
    "hline",
)
# Order in the alternation does not matter and sorting it would be decoration:
# the lookahead makes a short match fail where a letter follows, so \bigl
# backtracks out of "big" into "bigl" on its own. A longest-first sort here
# survived every mutation, which is what dead sophistication looks like.
_UNSUPPORTED_RE = re.compile(
    r"\\(?:" + "|".join(_UNSUPPORTED) + rf"){_COMMAND_END}"
)
_THIN_SPACE_RE = re.compile(r"\\[,!:;]")

# An arrow with its condition written above it — most of the reactions on a
# page of biology. mathtext has no \xrightarrow and does have \overset, so the
# label survives instead of the whole formula going out as source.
#
# One level of nesting, because the label is usually \text{...}. Deeper than
# that the pattern does not match and the formula falls through to its own
# source, which is exactly what happens today.
_BRACED = r"((?:[^{}]|\{[^{}]*\})*)"
_LABELLED_ARROW_RE = re.compile(
    rf"\\x(right|left)arrow\{{{_BRACED}\}}"
)


def _labelled_arrow(found: re.Match) -> str:
    direction = "to" if found.group(1) == "right" else "leftarrow"
    return rf"\overset{{{found.group(2)}}}{{\{direction}}}"


# Congruences. mathtext has no \pmod, and a lecture on remainders is written in
# little else: 21 of record 45's 93 formulas went out as their own source for
# this one command. LaTeX sets "a \pmod n" as "a  (mod n)" after a wide space,
# "a \bmod n" as "a mod n", and amsmath's "a \mod n" as "a  mod n".
#
# \pmod takes one token, as in LaTeX — except that a run of digits is one
# token here: "\pmod 13" meant 13 on every page it was written on, and
# LaTeX's own reading of it, "(mod 1)3", never.
_PMOD_RE = re.compile(
    rf"\\pmod{_COMMAND_END}\s*(?:\{{{_BRACED}\}}|(\d+|\\[A-Za-z]+|[^\s{{}}\\]))"
)
_MOD_RE = re.compile(rf"\\(b?mod){_COMMAND_END}")


def _pmod(found: re.Match) -> str:
    argument = found.group(1) if found.group(1) is not None else found.group(2)
    return rf"\quad(\mathrm{{mod}}\ {argument.strip()})"


def _mod(found: re.Match) -> str:
    return r"\ \mathrm{mod}\ " if found.group(1) == "bmod" else r"\quad\mathrm{mod}\ "


# A line under some of an array's cells. mathtext draws no rules, so it is
# dropped from a formula that is not drawn as a ruled table (ruled_arrays);
# the rows survive, the line does not. Its argument goes with it — left
# behind, "{2-2}" printed as a stray "2-2".
_CLINE_RE = re.compile(r"\\cline\{[^{}]*\}")
# A bold or italic word in a formula — "x^n \text{ - \textbf{полином}}" in
# record 45. mathtext has no \textbf, and inside \text it reads no command at
# all: the backslash came out as an empty box and the name as letters,
# "¤extbfполином". Its \mathbf and \mathit do set Cyrillic, but only in maths,
# so the word is lifted out of the \text round it, and its spaces are kept
# as "\ " — in maths a plain space is not a space.
_TEXT_GROUP_RE = re.compile(r"\\text\{((?:[^{}]|\{[^{}]*\})*)\}")
# Inside \text, either spelling is a word to lift; outside it, only the text
# commands need translating — \mathbf there is already what mathtext reads.
_STYLED_WORDS_RE = re.compile(r"\\(textbf|textit|emph|mathbf|mathit)\{([^{}]*)\}")
_TEXT_STYLE_RE = re.compile(r"\\(textbf|textit|emph)\{([^{}]*)\}")


def _styled_words(found: re.Match) -> str:
    font = "mathbf" if found.group(1) in ("textbf", "mathbf") else "mathit"
    words = found.group(2).replace(" ", "\\ ")
    return rf"\{font}{{{words}}}"


def _lift_styles(found: re.Match) -> str:
    """One \text{...} with the styled words in it set outside it."""
    inner = found.group(1)
    if not _STYLED_WORDS_RE.search(inner):
        return found.group(0)
    pieces: list[str] = []
    position = 0
    for styled in _STYLED_WORDS_RE.finditer(inner):
        if styled.start() > position:
            pieces.append(rf"\text{{{inner[position:styled.start()]}}}")
        pieces.append(_styled_words(styled))
        position = styled.end()
    if position < len(inner):
        pieces.append(rf"\text{{{inner[position:]}}}")
    return "".join(pieces)


# Russian words inside a formula, outside any \text: mathtext set each letter
# as an italic variable and dropped the spaces, "могутбыть". Wrapped in \text
# they come out upright and spaced, the way the page wrote them. What already
# stands in a group that sets words — \text, \mathbf and its kin, \mathrm —
# is left alone; "\mathbf{полином}" is bold because it is not wrapped again.
_WORD_GROUP_RE = re.compile(
    r"\\(?:text|mathbf|mathit|mathrm|operatorname)\{(?:[^{}]|\{[^{}]*\})*\}"
)
_CYRILLIC_WORDS_RE = re.compile(r"[А-Яа-яЁё]+(?:[ .,:;!?-]+[А-Яа-яЁё]+)*\.?")


def _cyrillic_as_text(latex: str) -> str:
    def wrap(part: str) -> str:
        return _CYRILLIC_WORDS_RE.sub(lambda found: rf"\text{{{found.group()}}}", part)

    pieces: list[str] = []
    position = 0
    for group in _WORD_GROUP_RE.finditer(latex):
        pieces.append(wrap(latex[position : group.start()]))
        pieces.append(group.group())
        position = group.end()
    pieces.append(wrap(latex[position:]))
    return "".join(pieces)


# A double quote is not a character mathtext reads in a formula; inside
# \text it is. Record 45 wrote \phantom{... корня "c"} to line an arrow up
# under a word, and the whole line went out as source.
_QUOTE_RE = re.compile(r'(\\text\{[^{}]*\})|"')

# LaTeX spells each of these two ways and mathtext knows only one of them. The
# model writes the other: a page of inequalities came back with every \le and
# \ge printed as its own source, while the formulas around them drew fine.
# Cheap to get wrong in the same direction as \limits, so the same boundary
# applies — \le must not match the start of \leq or \left.
_SYNONYMS = {
    "le": "leq",
    "ge": "geq",
    "gets": "leftarrow",
    "land": "wedge",
    "lor": "vee",
    "lnot": "neg",
    "iff": "Leftrightarrow",
    "implies": "Rightarrow",
    "impliedby": "Leftarrow",
    "mbox": "text",
    # Swept out of ~120 constructs at once rather than found one broken record
    # at a time, which is how the six above were discovered.
    "textrm": "text",
    "tfrac": "frac",
    "stackrel": "overset",
    # The brace is lost and the grouping survives, which is the better half.
    "overbrace": "overline",
    "underbrace": "underline",
}
_SYNONYM_RE = re.compile(
    r"\\(" + "|".join(sorted(_SYNONYMS, key=len, reverse=True)) + rf"){_COMMAND_END}"
)

# A brace with words under or over it: "\underbrace{δ + Δ}_{\text{выберем …}}".
# The synonym above keeps the line and leaves the words an index beside it —
# record 62 printed them small and to the right; set over or under the formula
# they read as the author wrote them. Two levels of braces inside either
# group; deeper, the synonym's line is what remains.
_GROUP = r"\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}"
_BRACE_WORDS_RE = re.compile(
    r"\\(under|over)brace" + _COMMAND_END + r"\s*" + _GROUP
    + r"\s*([_^])\s*(?:" + _GROUP + r"|(\\[A-Za-z]+|[^\s{}\\]))"
)


def _brace_words(found: re.Match) -> str:
    side, body, mark = found.group(1), found.group(2), found.group(3)
    words = found.group(4) if found.group(4) is not None else found.group(5)
    if (side, mark) not in (("under", "_"), ("over", "^")):
        return found.group(0)
    line = "underline" if side == "under" else "overline"
    return f"\\{side}set{{{words}}}{{\\{line}{{{body}}}}}"


# The environments mathtext refuses outright. It has no \begin at all — but it
# does have \substack, which stacks rows at full size, and \left...\right,
# which puts a delimiter around them. Between the two, a piecewise definition
# and a matrix draw properly instead of printing as their own source.
#
# What is lost is column alignment: \substack centres each row, so a wide
# matrix comes out ragged. A ragged matrix is readable and a page of
# backslashes is not.
_ENVIRONMENT_DELIMITERS = {
    "cases": (r"\{", "."),
    "pmatrix": ("(", ")"),
    "bmatrix": ("[", "]"),
    "Bmatrix": (r"\{", r"\}"),
    "vmatrix": ("|", "|"),
    "Vmatrix": (r"\|", r"\|"),
    "matrix": (None, None),
    "smallmatrix": (None, None),
    "aligned": (None, None),
    "align": (None, None),
    "alignedat": (None, None),
    "gathered": (None, None),
    "gather": (None, None),
    "split": (None, None),
    "array": (None, None),
}
_ENVIRONMENT_RE = re.compile(
    r"\\begin\{(" + "|".join(_ENVIRONMENT_DELIMITERS) + r")\*?\}"
    r"(?:\{[^{}]*\})?"  # \begin{array}{cc} — the column spec, which we drop
    r"(.*?)"
    r"\\end\{\1\*?\}",
    re.DOTALL,
)
# & separates columns in a matrix and marks the alignment point in aligned.
# Both become \quad: mathtext knows neither, and a wide space is what each one
# looks like once the alignment is gone. Not \; — the thin-space rule below
# strips that one, and two cells of a determinant then touch.
_COLUMN_SEPARATOR_RE = re.compile(r"(?<!\\)&")
# ...except where & is not a column at all. In the aligned family it marks the
# point two lines line up on, inside one expression: "a &= 1" is "a = 1" with
# a note about where to put it. A \quad there would widen a gap that is not
# there on the page.
_ALIGNMENT_ONLY = {"aligned", "align", "alignedat", "gathered", "gather", "split"}

# A display formula that is one aligned chain and nothing else — "|x − a| < ε",
# then "−ε < x − a < ε", a row a step. Stacked by \substack its rows touch, as
# record 62's three did; drawn a row at a time on the one ground, with this
# much air between them, they read as the lines they are on the page.
_ALIGNED_RE = re.compile(
    r"\s*\\begin\{(" + "|".join(sorted(_ALIGNMENT_ONLY)) + r")\*?\}"
    r"(?:\{[^{}]*\})?(.*?)\\end\{\1\*?\}\s*",
    re.DOTALL,
)
_ALIGNED_ROW_GAP_PT = 6.0


def aligned_rows(latex: str) -> list[str] | None:
    """The rows of a display formula that is one environment of the aligned
    family and nothing else, each a formula of its own; None otherwise — and
    for one holding another environment, whose rows its \\\\ would cut."""
    found = _ALIGNED_RE.fullmatch(latex)
    if found is None or "\\begin" in found.group(2):
        return None
    rows = [
        _COLUMN_SEPARATOR_RE.sub("", re.sub(r"^\s*\[[^\]]*\]", "", row)).strip()
        for row in re.split(r"\\\\", found.group(2))
    ]
    rows = [row for row in rows if row]
    return rows if len(rows) > 1 else None


def _environment(found: re.Match) -> str:
    r"""One \begin...\end turned into a stack of rows, with its delimiters."""
    name = found.group(1)
    left, right = _ENVIRONMENT_DELIMITERS[name]
    # Doubled for re.sub's replacement template, which reads \q as an escape.
    between = "" if name in _ALIGNMENT_ONLY else r"\\quad "
    rows = [
        _COLUMN_SEPARATOR_RE.sub(between, row).strip()
        for row in re.split(r"\\\\", found.group(2))
    ]
    stacked = r"\substack{" + r" \\ ".join(row for row in rows if row) + "}"
    if left is None:
        return stacked
    return rf"\left{left}{stacked}\right{right}"


def for_mathtext(latex: str) -> str:
    """LaTeX as close to it as matplotlib's mathtext will accept."""
    latex, _ = unbox(latex)
    latex = _CLINE_RE.sub("", latex)
    latex = _ENVIRONMENT_RE.sub(_environment, latex)
    latex = _LABELLED_ARROW_RE.sub(_labelled_arrow, latex)
    latex = _PMOD_RE.sub(_pmod, latex)
    latex = _MOD_RE.sub(_mod, latex)
    latex = _TEXT_GROUP_RE.sub(_lift_styles, latex)
    latex = _TEXT_STYLE_RE.sub(_styled_words, latex)
    latex = _UNSUPPORTED_RE.sub("", latex)
    latex = _BRACE_WORDS_RE.sub(_brace_words, latex)
    latex = _SYNONYM_RE.sub(lambda found: "\\" + _SYNONYMS[found.group(1)], latex)
    latex = _cyrillic_as_text(latex)
    latex = _QUOTE_RE.sub(lambda found: found.group(1) or r'\text{"}', latex)
    return _THIN_SPACE_RE.sub(" ", latex)


# ── An array ruled inside: long division ─────────────────────────────────────
# An array with a bar between its columns, or a line under some of its cells,
# is how the model writes a polynomial divided "уголком":
#
#     \begin{array}{l|l} 4x^3 + 2x^2 - 3x + 1 & x - 1 \\ \cline{2-2}
#     -4x^3 - 4x^2 & 4x^2 + 6x + 3 \\ \cline{1-1} ...
#
# mathtext draws no rules at all, and all five in record 45 went out as their
# own source. A formula that is nothing but such arrays, with space between
# them, is drawn as tables instead — see _ruled_row.

# `tabular` is the text-mode twin: two columns of working, "I) ... & II) ...",
# with formulas inside the cells rather than cells that are formulas.
_ARRAY_RE = re.compile(
    r"\\begin\{(array|tabular)\}\{([^{}]*)\}(.*?)\\end\{\1\}", re.DOTALL
)
_BETWEEN_ARRAYS_RE = re.compile(r"(?:\s|\\q?quad(?![A-Za-z])|\\[ ,;:!]|~)*")
_RULE_COMMAND_RE = re.compile(r"\\cline\{(\d+)-(\d+)\}|\\hline(?![A-Za-z])")


@dataclass
class RuledArray:
    align: list[str]  # "l", "c" or "r", one a column
    bars: list[int]  # a bar before column i; i == len(align) is the right edge
    rows: list[list[str]]  # each cell's LaTeX, every row as wide as align
    rules: list[tuple[int, int, int]]  # a line under row r over columns a..b; r == -1 is above the first
    text: bool = False  # a tabular: each cell is text with formulas in it


def ruled_arrays(latex: str) -> list[RuledArray] | None:
    """The arrays a display formula is made of, when it is nothing but arrays
    with rules in them and space between; None for any other formula."""
    found = list(_ARRAY_RE.finditer(latex))
    if not found:
        return None
    position = 0
    for match in found:
        if not _BETWEEN_ARRAYS_RE.fullmatch(latex[position : match.start()]):
            return None
        position = match.end()
    if not _BETWEEN_ARRAYS_RE.fullmatch(latex[position:]):
        return None
    arrays = [
        _ruled(match.group(2), match.group(3), tabular=match.group(1) == "tabular")
        for match in found
    ]
    return None if any(array is None for array in arrays) else arrays


def _ruled(spec: str, body: str, tabular: bool = False) -> RuledArray | None:
    align: list[str] = []
    bars: list[int] = []
    for char in spec:
        if char in "lcr":
            align.append(char)
        elif char == "|":
            bars.append(len(align))
    if not align:
        return None

    rows: list[list[str]] = []
    rules: list[tuple[int, int, int]] = []
    for raw in re.split(r"\\\\", body):
        text = raw.strip()
        # A rule stands at the start of a row and belongs under the row before.
        while (rule := _RULE_COMMAND_RE.match(text)) is not None:
            if rule.group(1):
                first, last = int(rule.group(1)) - 1, int(rule.group(2)) - 1
            else:
                first, last = 0, len(align) - 1
            rules.append((len(rows) - 1, first, last))
            text = text[rule.end() :].strip()
        if text:
            rows.append([cell.strip() for cell in _COLUMN_SEPARATOR_RE.split(text)])

    # Without a rule an array is an ordinary one, and _environment stacks it.
    # A tabular is drawn here either way: mathtext has no text mode to set it.
    if not rows or not (bars or rules or tabular):
        return None
    width = max(len(align), *(len(row) for row in rows))
    align += ["l"] * (width - len(align))
    rows = [row + [""] * (width - len(row)) for row in rows]
    return RuledArray(align, bars, rows, rules, tabular)


# The empty margin savefig leaves round a formula, in inches and in points.
_FORMULA_PAD_IN = 0.01
_FORMULA_PAD_PT = _FORMULA_PAD_IN * 72.0
# A formula wider than the column is shrunk to fit it. At its own size a long
# chain of equalities ran past the margin and off the paper, where nobody can
# read it; smaller is readable. Inside a line it leaves room for a list item.
_INLINE_MAX_PT = _TEXT_WIDTH_PT - 30
# The kraft ground a display formula stands on is as wide as the column, and
# the formula keeps clear of its edges.
_GROUND_PAD_X = 10.0
_GROUND_PAD_Y = 5.0
_GROUND_INNER_PT = _TEXT_WIDTH_PT - 2 * _GROUND_PAD_X


def _formula_png(
    latex: str, size_pt: float, color: str = _INK
) -> tuple[bytes, float, float, float]:
    """One formula as a transparent PNG, with its width, height and depth in
    points. Raises when mathtext cannot read the LaTeX — callers fall back to
    the source text.

    The depth is how far below the bottom of the picture the formula's
    baseline sits above it. A formula set inside a line is lowered by exactly
    that much, so its baseline is the line's: a fixed fraction of the height
    lifted a subscript off the line and sank a fraction through it.

    `color` is the ink's everywhere but on the one dark block, "Суть", where
    a formula in ink would be ink on ink.
    """
    figure = plt.figure(figsize=(0.01, 0.01))
    try:
        text = figure.text(
            0, 0, f"${for_mathtext(latex)}$",
            fontsize=size_pt, math_fontfamily=_MATH_FONT, color=color,
        )
        text.set_path_effects(
            [patheffects.withStroke(linewidth=_MATH_STROKE_PT, foreground=color)]
        )
        # The box savefig crops to is this one: the text's layout, baseline at
        # y=0, so whatever lies below zero is the depth.
        extent = text.get_window_extent(figure.canvas.get_renderer())
        depth = max(0.0, -extent.y0) * 72.0 / figure.dpi + _FORMULA_PAD_PT
        buffer = io.BytesIO()
        figure.savefig(
            buffer,
            format="png",
            dpi=_DPI,
            bbox_inches="tight",
            pad_inches=_FORMULA_PAD_IN,
            transparent=True,
        )
    finally:
        plt.close(figure)
    data = buffer.getvalue()
    # Pillow is already a dependency, used here only to measure.
    from PIL import Image as PILImage

    width, height = PILImage.open(io.BytesIO(data)).size
    scale = 72.0 / _DPI
    return data, width * scale, height * scale, depth


def _loop_circle(x: float, y: float, node: float) -> tuple[float, float, float]:
    """Where a loop at (x, y) is drawn: outside its vertex, pointing away from
    the middle of the picture, so it cannot be mistaken for an edge to a
    neighbour. Centre and radius, shared by the drawing and its extent."""
    away = math.atan2(y, x) if (x or y) else math.pi / 2
    radius = node * 0.95
    reach = node + radius * 0.6
    return x + reach * math.cos(away), y + reach * math.sin(away), radius


def _graph_png(
    vertices: list[str],
    edges: list[tuple[str, str]],
    directed: bool,
    width_pt: float = _GRAPH_WIDTH_PT,
) -> tuple[bytes, float, float]:
    """A graph drawn as a picture, with its size in points. Raises on anything
    matplotlib dislikes; the caller falls back to printing the spec.

    `width_pt` is the most the picture may take across. It is drawn at the one
    scale every graph shares and shrunk only when that would not fit.
    """
    count = len(vertices)
    if count == 1:
        positions = {vertices[0]: (0.0, 0.0)}
    else:
        # Vertices on a circle. A lecture-note graph has a handful of them, and
        # a layout that is the same every time beats a prettier one that moves
        # between runs of the same page.
        placed = _placement(vertices)
        positions = {
            vertex: (
                math.cos(math.pi / 2 - 2 * math.pi * i / count),
                math.sin(math.pi / 2 - 2 * math.pi * i / count),
            )
            for i, vertex in enumerate(placed)
        }
    node = _GRAPH_NODE

    # The extent of what is actually drawn: every vertex's circle and every
    # loop, with a hair of margin so a stroke is not cut at the edge.
    xs: list[float] = []
    ys: list[float] = []
    for x, y in positions.values():
        xs += [x - node, x + node]
        ys += [y - node, y + node]
    for tail, head in edges:
        if tail == head:
            cx, cy, radius = _loop_circle(*positions[tail], node)
            xs += [cx - radius, cx + radius]
            ys += [cy - radius, cy + radius]
    margin = 0.05
    left, right = min(xs) - margin, max(xs) + margin
    bottom, top = min(ys) - margin, max(ys) + margin

    label_font = FontProperties(fname=os.path.join(_FONT_DIR, "Onest-SemiBold.ttf"), size=9)
    figure = plt.figure(
        figsize=(
            (right - left) * _GRAPH_INCHES_PER_UNIT,
            (top - bottom) * _GRAPH_INCHES_PER_UNIT,
        )
    )
    try:
        # One axes filling the figure, limits equal to the extent: the figure's
        # proportions are the drawing's, so a unit is as long in x as in y.
        axes = figure.add_axes((0, 0, 1, 1))
        axes.axis("off")
        axes.set_xlim(left, right)
        axes.set_ylim(bottom, top)
        for tail, head in edges:
            x1, y1 = positions[tail]
            x2, y2 = positions[head]
            if tail == head:
                cx, cy, radius = _loop_circle(x1, y1, node)
                axes.add_patch(
                    plt.Circle((cx, cy), radius, fill=False, lw=1.0,
                               edgecolor=_INK, zorder=1)
                )
                continue
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy) or 1.0
            # Stop the line at the circle, not at its centre, so an arrowhead
            # lands on the vertex instead of inside it.
            start = (x1 + dx / length * node, y1 + dy / length * node)
            finish = (x2 - dx / length * node, y2 - dy / length * node)
            if directed:
                axes.annotate(
                    "",
                    xy=finish,
                    xytext=start,
                    arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": _INK},
                )
            else:
                axes.plot(
                    [start[0], finish[0]], [start[1], finish[1]],
                    lw=1.0, color=_INK, zorder=1,
                )
        for vertex, (x, y) in positions.items():
            # Filled with the paper, so an edge stops at the circle and the
            # circle does not stand out as a white disc on the page.
            axes.add_patch(
                plt.Circle((x, y), node, facecolor=_PAPER, edgecolor=_INK,
                           lw=1.0, zorder=2)
            )
            axes.text(x, y, vertex, ha="center", va="center",
                      fontproperties=label_font, color=_INK, zorder=3)

        buffer = io.BytesIO()
        figure.savefig(buffer, format="png", dpi=_DPI, transparent=True)
    finally:
        plt.close(figure)

    width = (right - left) * _GRAPH_SCALE_PT
    height = (top - bottom) * _GRAPH_SCALE_PT
    if width > width_pt:
        height *= width_pt / width
        width = width_pt
    return buffer.getvalue(), width, height


def _placement(vertices: list[str]) -> list[str]:
    """The order the vertices go round the circle.

    Numbered ones go in numeric order rather than in the order the model read
    them off the page. Vertices numbered 1..n are usually numbered *along* the
    drawing, so consecutive ones are joined; putting them side by side turns
    those edges into the rim of the circle instead of a star of chords across
    the middle of it.
    """
    if all(vertex.isdigit() for vertex in vertices):
        return sorted(vertices, key=int)
    return vertices


def _text(value: str) -> str:
    """Plain text as reportlab markup: escaped, a <br> the composing stage
    wrote as a line break, and every run of characters Onest does not have
    set in DejaVu, which has them — reportlab has no fallback of its own and
    draws an empty box for a glyph its font lacks."""
    if not value:
        return ""
    known = _text_glyphs()
    out: list[str] = []
    for position, part in enumerate(_BREAK_RE.split(value)):
        if position:
            out.append("<br/>")
        run: list[str] = []
        run_known = True
        for char in part:
            char_known = ord(char) in known
            if run and char_known != run_known:
                out.append(_run(run, run_known))
                run = []
            run.append(char)
            run_known = char_known
        if run:
            out.append(_run(run, run_known))
    return "".join(out)


def _run(chars: list[str], known: bool) -> str:
    text = escape("".join(chars))
    return text if known else f'<font face="{_FALLBACK_FONT}">{text}</font>'


# **bold** and ~~struck through~~. A crossed-out word is kept and shown crossed
# out, the way it stands in the manuscript; printed with its tildes it read as
# noise, on six of twelve records.
_EMPHASIS_RE = re.compile(r"\*\*|~~")
_EMPHASIS_TAGS = {"**": "b", "~~": "strike"}


def _inline(
    runs: list[tuple[str, str]], formulas, size_pt: float, color: str = _INK
) -> str:
    """Runs of text and formulas as reportlab markup, the formulas drawn in
    `color`.

    Emphasis is paired over the whole line, not inside one run of text:
    "**Регулярный граф степени $n$**" is one bold span with a formula in the
    middle, and paired run by run it went out with its asterisks showing. A
    marker left without a partner is printed as it stands. Spans that cross —
    "**a ~~b** c~~" — are closed and reopened so the markup stays well formed,
    because malformed markup is an exception inside reportlab, and a record is
    never worth losing over its emphasis.
    """
    counts = dict.fromkeys(_EMPHASIS_TAGS, 0)
    for kind, value in runs:
        if kind == "text":
            for found in _EMPHASIS_RE.finditer(value):
                counts[found.group()] += 1
    usable = {marker: count - count % 2 for marker, count in counts.items()}
    used = dict.fromkeys(_EMPHASIS_TAGS, 0)
    open_: list[str] = []
    pieces: list[str] = []

    def toggle(marker: str) -> str:
        if marker not in open_:
            open_.append(marker)
            return f"<{_EMPHASIS_TAGS[marker]}>"
        inner = open_[open_.index(marker) + 1 :]
        open_.remove(marker)
        return (
            "".join(f"</{_EMPHASIS_TAGS[m]}>" for m in reversed(inner))
            + f"</{_EMPHASIS_TAGS[marker]}>"
            + "".join(f"<{_EMPHASIS_TAGS[m]}>" for m in inner)
        )

    drawn_before = False
    for kind, value in runs:
        if kind == "math":
            tag = (
                formulas.inline(value, size_pt * _MATH_SCALE, color)
                if formulas is not None
                else None
            )
            # Unreadable LaTeX stays visible as its own source: worse to look
            # at than a drawn formula, far better than a silently missing one.
            pieces.append(tag if tag else _text(f"${value}$"))
            drawn_before = bool(tag)
            continue
        if drawn_before and value[:1].isspace():
            # reportlab does not break a line at a space that follows an
            # image: the word after a long formula stayed on its line and ran
            # off the paper. A zero-width space is a place it will break.
            # Only where the page had a space — never between a formula and
            # its comma. Through _text, which sets it in DejaVu: Onest has no
            # glyph for it, and it printed as an empty box after every formula.
            pieces.append(_text("\u200b"))
        drawn_before = False
        position = 0
        for found in _EMPHASIS_RE.finditer(value):
            marker = found.group()
            pieces.append(_text(value[position : found.start()]))
            if used[marker] < usable[marker]:
                used[marker] += 1
                pieces.append(toggle(marker))
            else:
                pieces.append(_text(marker))
            position = found.end()
        pieces.append(_text(value[position:]))
    return "".join(pieces)


def _markup(text: str) -> str:
    """Plain text as reportlab mini-HTML. Escaping comes first: a page that
    says "A < B" would otherwise be read as a tag and swallow the rest."""
    return _inline([("text", text)], None, 0.0)


class _Formulas:
    """Renders formulas for one document, caching by (latex, size) — a symbol
    repeated down a page is drawn once — and writing the inline ones to a
    temporary directory, because reportlab's <img> tag takes a path, not bytes.
    """

    def __init__(self, directory: str):
        self._directory = directory
        self._cache: dict[tuple[str, float, str], tuple[str, float, float, float]] = {}
        self._count = 0
        self._refused_seen: set[str] = set()

    def _refused(self, latex: str, exc: Exception) -> None:
        """A formula that is about to go out as its own source.

        This was a debug line and LOG_LEVEL is INFO, so it never appeared:
        three separate rounds of "the PDF has broken symbols" were found by
        the author's eye rather than by the log, one command at a time.

        mathtext's message names the offending command — "Unknown symbol:
        \\xrightarrow" — but it opens with a blank line and a caret under the
        source, the same shape of trap as str(TimeoutError()). The last line
        is the diagnosis; the source is logged beside it anyway.

        Once per distinct formula per document: a macro the model does not
        know how to spell is usually on every page of the record.
        """
        if latex in self._refused_seen:
            return
        self._refused_seen.add(latex)
        detail = str(exc).strip().splitlines()
        logger.warning(
            "mathtext refused %r: %s",
            latex,
            detail[-1] if detail else type(exc).__name__,
        )

    def inline(self, latex: str, size_pt: float, color: str = _INK) -> str | None:
        """An <img> tag for use inside a paragraph, or None if unrenderable."""
        key = (latex, size_pt, color)
        if key not in self._cache:
            try:
                data, width, height, depth = _formula_png(latex, size_pt, color)
            except Exception as exc:
                self._refused(latex, exc)
                return None
            if width > _INLINE_MAX_PT:
                shrink = _INLINE_MAX_PT / width
                width, height, depth = _INLINE_MAX_PT, height * shrink, depth * shrink
            self._count += 1
            path = os.path.join(self._directory, f"f{self._count}.png")
            with open(path, "wb") as handle:
                handle.write(data)
            self._cache[key] = (path, width, height, depth)
        path, width, height, depth = self._cache[key]
        # Lowered by its own depth, so the formula's baseline is the line's.
        return (
            f'<img src="{path}" width="{width:.2f}" height="{height:.2f}" '
            f'valign="-{depth:.2f}"/>'
        )

    def display(
        self, latex: str, size_pt: float, max_width: float = _GROUND_INNER_PT
    ) -> Image | None:
        try:
            data, width, height, _ = _formula_png(latex, size_pt)
        except Exception as exc:
            self._refused(latex, exc)
            return None
        if width > max_width:
            height *= max_width / width
            width = max_width
        return Image(io.BytesIO(data), width=width, height=height)


def _line_markup(text: str, formulas: _Formulas, size_pt: float) -> str:
    """One line of a record as reportlab markup, formulas drawn in place."""
    return _inline(split_inline(text), formulas, size_pt)


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "body",
        fontName=_TEXT_FONT,
        fontSize=_BODY_PT,
        leading=_BODY_PT * _LEADING,
        textColor=_INK,
        spaceAfter=0,
        # A line holding a tall formula — a fraction, a sum with its limits —
        # grows to fit it instead of printing over the line above.
        autoLeading="max",
    )
    muted = ParagraphStyle(
        "muted", parent=base, fontSize=_SMALL_PT, leading=_SMALL_PT * 1.45,
        textColor=_MUTED,
    )
    return {
        "title": ParagraphStyle(
            "title", parent=base, fontName=_HEAVY_FONT, fontSize=_TITLE_PT,
            leading=_TITLE_PT * 1.25, spaceAfter=6,
        ),
        # The lecture's sections in Unbounded, as the guide sets them; a
        # subsection in the text's own face, a step above it — Unbounded at the
        # size of the text is a shout.
        **{
            f"heading{level}": ParagraphStyle(
                f"heading{level}", parent=base,
                fontName=_HEADING_FONT if level == 1 else _TEXT_BOLD_FONT,
                fontSize=size, leading=size * 1.35,
                spaceBefore=_HEADING_SPACE_BEFORE[level],
                spaceAfter=_HEADING_SPACE_AFTER[level],
            )
            for level, size in _HEADING_PT.items()
        },
        # What stands under the title: small and grey, a line of facts rather
        # than a sentence the author was saying.
        "byline": ParagraphStyle("byline", parent=muted, fontSize=10, leading=14),
        "meta": ParagraphStyle("meta", parent=muted),
        # A box is set at the size of the text it sits in. Smaller and it
        # read as small print to skip.
        "callout_body": ParagraphStyle("callout_body", parent=base),
        # "Суть": the text in the paper's colour on the ink.
        "essence": ParagraphStyle("essence", parent=base, textColor=_PAPER),
        "body": base,
        "bullet": ParagraphStyle(
            "bullet", parent=base, leftIndent=22, bulletIndent=8,
            bulletFontName=_TEXT_FONT,
        ),
        "caption": ParagraphStyle("caption", parent=muted, alignment=TA_CENTER),
        # A drawing the page had and the record could not draw: set where the
        # picture would be, the size of a caption, so it reads as a figure
        # that is missing rather than as a line of the author's text.
        "note": ParagraphStyle("note", parent=muted, alignment=TA_CENTER),
        "math": ParagraphStyle("math", parent=base, alignment=TA_CENTER),
        "framed": ParagraphStyle("framed", parent=base, alignment=TA_CENTER),
        "number": ParagraphStyle(
            "number", parent=base, fontName=_MONO_FONT, fontSize=_NUMBER_PT,
            leading=_NUMBER_PT * 1.3, textColor=_MUTED, alignment=TA_RIGHT,
        ),
        # Where an explanation comes from: names of sites, set as what serves
        # the page rather than as the lecture.
        "sources": ParagraphStyle(
            "sources", parent=muted, fontName=_MONO_FONT, fontSize=8,
            leading=8 * 1.6, spaceBefore=4,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base, fontSize=_TABLE_PT, leading=_TABLE_PT * 1.35,
            alignment=TA_CENTER,
        ),
        # A table the composing stage used for layout — two columns of lines
        # side by side — reads as text, so it is set as text.
        "layout_cell": ParagraphStyle(
            "layout_cell", parent=base, alignment=TA_LEFT,
        ),
    }


def _column_widths(rows: list[list[str]], size: float = _TABLE_PT) -> list[float]:
    """Column widths in points, measured from the content and squeezed until
    they fit the frame together.

    Left to itself reportlab spreads the columns evenly across the whole page,
    which turns an adjacency matrix of noughts and ones into a wall of empty
    boxes. A formula in a cell is drawn rather than written, so measuring its
    source overestimates — erring towards a roomy column, not a clipped one.
    """
    widths = []
    for column in range(len(rows[0])):
        longest = max(
            pdfmetrics.stringWidth(row[column], _TEXT_FONT, size) for row in rows
        )
        widths.append(min(max(longest + 10, _MIN_COLUMN_PT), _MAX_COLUMN_PT))
    total = sum(widths)
    if total > _TEXT_WIDTH_PT:
        widths = [width * _TEXT_WIDTH_PT / total for width in widths]
    return widths


def _labelled_down_the_side(rows: list[list[str]], header: bool) -> bool:
    """Whether the first column names the rows, as it does in a matrix: an
    empty corner, or short labels under a header. Such a table is ruled the
    way a matrix is written — one line under the column names, one after the
    row names — rather than as a list of records."""
    if not header or len(rows) < 2:
        return False
    if not rows[0][0].strip():
        return True
    return all(0 < len(row[0].strip()) <= 4 for row in rows[1:])


def _for_layout(rows: list[list[str]]) -> bool:
    """Whether a table is the author's two columns rather than data: lines
    stacked in a cell, or cells as long as sentences. Ruled as a table, record
    42's two columns of algebra came out as a grid of small type."""
    cells = [cell for row in rows for cell in row]
    return any(_BREAK_RE.search(cell) or len(cell) > 40 for cell in cells)


def _table(
    rows: list[list[str]],
    header: bool,
    formulas: _Formulas,
    styles: dict[str, ParagraphStyle],
) -> Table:
    """A markdown table as a drawn one.

    Ruled, not caged: a grid round every cell made a matrix of noughts and
    ones a wall of boxes, and the reference rules only what separates the
    names from the values. A table used for layout gets no rules at all.
    """
    if _for_layout(rows):
        return _layout_table(rows, formulas, styles)

    table = Table(
        [
            [
                Paragraph(_line_markup(cell, formulas, _TABLE_PT), styles["cell"])
                for cell in row
            ]
            for row in rows
        ],
        colWidths=_column_widths(rows),
        hAlign="CENTER",
    )
    # The line under a header, or after the names of the rows, belongs to the
    # table's reading and is ink; the lines between the rows of a list are
    # the guide's kraft dividers.
    rule = colors.HexColor(_INK)
    light = colors.HexColor(_KRAFT)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if _labelled_down_the_side(rows, header):
        style += [
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, rule),
            ("LINEAFTER", (0, 0), (0, -1), 0.6, rule),
        ]
    else:
        # A table of records: a line under the header when there is one, and
        # light lines between rows so a long one can be read across.
        if header:
            style.append(("LINEBELOW", (0, 0), (-1, 0), 0.6, rule))
        style += [
            ("LINEABOVE", (0, 0), (-1, 0), 0.4, light),
            ("LINEBELOW", (0, 1 if header else 0), (-1, -1), 0.4, light),
        ]
    table.setStyle(TableStyle(style))
    return table


def _layout_table(
    rows: list[list[str]], formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> Table:
    """Columns of lines side by side, at the size of the text, with nothing
    drawn between them."""
    measured = [
        [max(_BREAK_RE.split(cell), key=len) for cell in row] for row in rows
    ]
    table = Table(
        [
            [
                Paragraph(_line_markup(cell, formulas, _BODY_PT), styles["layout_cell"])
                for cell in row
            ]
            for row in rows
        ],
        colWidths=_column_widths(measured, _BODY_PT),
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 18),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


# Between two arrays set side by side — three divisions in a row, one after
# the other, as record 45 had them.
_ARRAYS_GAP_PT = 18.0
_CELL_PAD_PT = 4.0


def _ruled_table(
    array: RuledArray, formulas: _Formulas, styles: dict[str, ParagraphStyle], size_pt: float
) -> tuple[Table, float]:
    r"""One ruled array as a table, and how wide it came out.

    Every cell a formula, in its column's alignment, so the steps of a
    division stay under one another the way \phantom lined them up. A line
    under the cells a \cline or an \hline names. The bar the column spec
    asks for runs only along the rows that have something on its far side:
    in a long division that is the divisor and the quotient, and the bar
    stops where the corner does, as on the page.
    """
    columns = len(array.align)
    widths = [0.0] * columns
    cells: list[list] = []
    for row in array.rows:
        drawn: list = []
        for column, latex in enumerate(row):
            if not latex:
                drawn.append("")
                continue
            if array.text:
                # Measured as characters: the formulas in it are drawn, and
                # drawn they come out about as wide as their plain spelling.
                drawn.append(
                    Paragraph(_line_markup(latex, formulas, _BODY_PT), styles["layout_cell"])
                )
                widths[column] = max(
                    widths[column],
                    pdfmetrics.stringWidth(plain(latex), _TEXT_FONT, _BODY_PT) + 4,
                )
                continue
            image = formulas.display(latex, size_pt, max_width=_GROUND_INNER_PT)
            if image is None:
                cell = Paragraph(_markup(f"${latex}$"), styles["layout_cell"])
                width = pdfmetrics.stringWidth(f"${latex}$", _TEXT_FONT, _BODY_PT)
            else:
                cell, width = image, image.drawWidth
            drawn.append(cell)
            widths[column] = max(widths[column], width)
        cells.append(drawn)
    widths = [width + 2 * _CELL_PAD_PT for width in widths]
    if array.text and sum(widths) > _GROUND_INNER_PT:
        # Text wraps where a formula cannot: the columns share the ground.
        widths = [width * _GROUND_INNER_PT / sum(widths) for width in widths]

    ink = colors.HexColor(_INK)
    alignment = {"l": "LEFT", "c": "CENTER", "r": "RIGHT"}
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), _CELL_PAD_PT),
        ("RIGHTPADDING", (0, 0), (-1, -1), _CELL_PAD_PT),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]
    for column, side in enumerate(array.align):
        style.append(("ALIGN", (column, 0), (column, -1), alignment[side]))
    for bar in array.bars:
        far_side = min(bar, columns - 1)
        for row, cells_of_row in enumerate(array.rows):
            if not cells_of_row[far_side]:
                continue
            if bar < columns:
                style.append(("LINEBEFORE", (bar, row), (bar, row), 0.6, ink))
            else:
                style.append(("LINEAFTER", (columns - 1, row), (columns - 1, row), 0.6, ink))
    for row, first, last in array.rules:
        first, last = max(first, 0), min(last, columns - 1)
        if row < 0:
            style.append(("LINEABOVE", (first, 0), (last, 0), 0.6, ink))
        else:
            style.append(("LINEBELOW", (first, row), (last, row), 0.6, ink))

    table = Table(cells, colWidths=widths, hAlign="CENTER")
    table.setStyle(TableStyle(style))
    return table, sum(widths)


def _ruled_row(
    arrays: list[RuledArray], formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> Flowable:
    """A formula made of ruled arrays, drawn as tables side by side, kept on
    one page — a division split between two is two halves of a sum. Wider
    than the column, it is drawn again at the size that fits."""
    size = _DISPLAY_PT
    for _ in range(2):
        drawn = [_ruled_table(array, formulas, styles, size) for array in arrays]
        total = sum(width for _, width in drawn) + _ARRAYS_GAP_PT * (len(drawn) - 1)
        if total <= _GROUND_INNER_PT:
            break
        size = max(7.0, size * _GROUND_INNER_PT / total)
    if len(drawn) == 1:
        return KeepTogether([drawn[0][0]])
    gaps = [_ARRAYS_GAP_PT] * (len(drawn) - 1)
    row: list = []
    widths: list[float] = []
    for position, (table, width) in enumerate(drawn):
        row.append(table)
        widths.append(width)
        if position < len(gaps):
            row.append("")
            widths.append(gaps[position])
    side_by_side = Table([row], colWidths=widths, hAlign="CENTER")
    side_by_side.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return KeepTogether([side_by_side])


class _Label(Flowable):
    """A box's label: capitals with their letters spaced, in the monospace of
    what serves the page. A reportlab paragraph cannot space letters, so the
    label is drawn."""

    def __init__(self, text: str, color: str):
        super().__init__()
        self.text = text.upper()
        self.color = color
        self._height = _LABEL_PT * 1.8

    def wrap(self, available_width, available_height):
        return available_width, self._height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(colors.HexColor(self.color))
        line = self.canv.beginText(0, _LABEL_PT * 0.55)
        line.setFont(_MONO_BOLD_FONT, _LABEL_PT)
        line.setCharSpace(_LABEL_TRACKING)
        line.textOut(self.text)
        self.canv.drawText(line)
        self.canv.restoreState()


class _Inserted(Flowable):
    """One flowable of a passage from another notebook, with the line in the
    margin beside it (task 63). The flowable keeps the column's full width,
    and one split across two pages takes its line to both."""

    def __init__(self, child):
        super().__init__()
        self.child = child

    def wrap(self, available_width, available_height):
        width, height = self.child.wrap(available_width, available_height)
        self._column = available_width
        self._width = width
        # The space the child asks for above and below it is drawn inside,
        # so the line runs on through it.
        self._above = self.child.getSpaceBefore()
        self._below = self.child.getSpaceAfter()
        self.height = height + self._above + self._below
        return available_width, self.height

    def split(self, available_width, available_height):
        parts = self.child.split(available_width, available_height)
        return [_Inserted(part) for part in parts]

    def draw(self):
        align = str(getattr(self.child, "hAlign", "LEFT")).upper()
        x = 0.0
        if align in ("CENTER", "CENTRE"):
            x = (self._column - self._width) / 2
        elif align == "RIGHT":
            x = self._column - self._width
        self.child.drawOn(self.canv, x, self._below)
        self.canv.saveState()
        self.canv.setStrokeColor(colors.HexColor(_INSERT_BAR))
        self.canv.setLineWidth(_BAR_PT)
        self.canv.line(-_INSERT_BAR_GAP, 0, -_INSERT_BAR_GAP, self.height)
        self.canv.restoreState()


def _box(
    label: str,
    lines: list[str],
    accent: str,
    bar: str,
    body: ParagraphStyle,
    formulas: _Formulas,
    extra: list | None = None,
) -> Table:
    """The one shape every box beside the text takes: a bar down the left,
    a label in spaced capitals, the lines under it. No panel behind it.

    A callout about the whole record and a finding under one line carry the
    weight of what they say in the bar and the label; what the bot adds of its
    own is the same box in ink, named as the bot's.

    reportlab has no such flowable, so it is a table of one cell — that is
    what gives a bar on one side only.
    """
    inside: list = [_Label(label, accent)]
    inside += [
        Paragraph(_line_markup(line, formulas, _BODY_PT), body) for line in lines
    ]
    inside += extra or []
    table = Table([[inside]], colWidths=[_TEXT_WIDTH_PT], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("LINEBEFORE", (0, 0), (0, -1), _BAR_PT, colors.HexColor(bar)),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _callout(
    box: Callout, formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> Table:
    """A box at the top of the record: what the pipeline knows about how far
    the text can be trusted, in the tone of how much that matters."""
    tone = box.tone if box.tone in _CALLOUT_TONES else "info"
    return _box(
        box.title, box.lines, _CALLOUT_TONES[tone], _CALLOUT_BARS[tone],
        styles["callout_body"], formulas,
    )


def _remark(
    remark: Remark, formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> Table:
    """A finding under the line it is about, in the accent a callout of its
    weight would carry. It used to be a callout at the top of the record,
    which said what was wrong without saying where."""
    tone = remark.tone if remark.tone in _CALLOUT_TONES else "info"
    return _box(
        remark.label, remark.lines, _CALLOUT_TONES[tone], _CALLOUT_BARS[tone],
        styles["callout_body"], formulas,
    )


def _explanation(
    item: Explanation, formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> Table:
    """An explanation in the bot's own tone, its sources under it as links.
    An explanation with none is never built — explain.py drops it first."""
    links = ", ".join(
        f'<a href="{escape(uri, {chr(34): "&quot;"})}" color="{_MUTED}">{_text(title)}</a>'
        for title, uri in item.sources
    )
    extra = (
        [Paragraph(f"{_text(item.sources_label)}: {links}", styles["sources"])]
        if links
        else []
    )
    return _box(
        item.label, item.lines, _ADDED_TONE, _ADDED_TONE, styles["callout_body"],
        formulas, extra,
    )


def _star(page_canvas, x: float, y: float, radius: float, color: str) -> None:
    """The guide's star, ✦, centred on (x, y): four points, its sides curved
    in. Drawn rather than set, so it is the same star in every face and the
    amber the guide gives it."""
    tips = [(0.0, radius), (radius, 0.0), (0.0, -radius), (-radius, 0.0)]
    # Each side bows towards a point near the centre, between its two tips.
    pull = radius * 0.2
    bows = [(pull, pull), (pull, -pull), (-pull, -pull), (-pull, pull)]
    path = page_canvas.beginPath()
    path.moveTo(x, y + radius)
    for (bx, by), (tx, ty) in zip(bows, tips[1:] + tips[:1]):
        path.curveTo(x + bx, y + by, x + bx, y + by, x + tx, y + ty)
    path.close()
    page_canvas.setFillColor(colors.HexColor(color))
    page_canvas.drawPath(path, stroke=0, fill=1)


class _EssenceLabel(Flowable):
    """"✦ СУТЬ · составлено ботом по тексту записи": the star in amber, the
    block's name in the paper's colour, and whose words these are a step
    quieter — the one dark block is the bot's, and says so."""

    def __init__(self, label: str):
        super().__init__()
        name, _, note = label.partition(" · ")
        self.name = name.upper()
        self.note = note.upper()
        self._height = _LABEL_PT * 2.0

    def wrap(self, available_width, available_height):
        return available_width, self._height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        size = _LABEL_PT
        _star(canvas, size * 0.6, size * 0.95, size * 0.72, _AMBER)
        line = canvas.beginText(size * 1.8, size * 0.6)
        line.setCharSpace(_LABEL_TRACKING)
        line.setFont(_MONO_BOLD_FONT, size)
        line.setFillColor(colors.HexColor(_PAPER))
        line.textOut(self.name)
        if self.note:
            line.setFont(_MONO_FONT, size)
            line.setFillColor(colors.HexColor(_MUTED_ON_INK))
            line.textOut(f" · {self.note}")
        canvas.drawText(line)
        canvas.restoreState()


_ESSENCE_PAD_X = 16.0
_ESSENCE_PAD_Y = 12.0


def _essence(
    item: Summary, formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> Table:
    """"Суть": the record summed up, first in the document, on the page's one
    dark block — the guide's. The bot wrote it, and its label says so."""
    inside: list = [_EssenceLabel(item.label), Spacer(1, 3)]
    inside += [
        Paragraph(_inline(split_inline(line), formulas, _BODY_PT, _PAPER), styles["essence"])
        for line in item.lines
    ]
    table = Table([[inside]], colWidths=[_TEXT_WIDTH_PT], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_INK)),
                ("ROUNDEDCORNERS", [5, 5, 5, 5]),
                ("LEFTPADDING", (0, 0), (-1, -1), _ESSENCE_PAD_X),
                ("RIGHTPADDING", (0, 0), (-1, -1), _ESSENCE_PAD_X),
                ("TOPPADDING", (0, 0), (-1, -1), _ESSENCE_PAD_Y - 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), _ESSENCE_PAD_Y),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


# Spaces, dollars and the stars of bold: what a model quoting a line writes
# as it pleases, and what composition adds to a line it did not otherwise
# change.
_SQUASH_RE = re.compile(r"[\s$*]+")
_NUMBER_ANCHOR_RE = re.compile(r"\(?\s*(\d{1,3})\s*\)?")


def _squash(text: str) -> str:
    return _SQUASH_RE.sub("", text).lower()


def _reading(member: Block) -> str:
    """A block as its text: a table's rows written the way markdown writes
    them, since a table holds its text in its cells."""
    if member.kind == "table":
        return "\n".join("|" + "|".join(row) + "|" for row in member.rows)
    return member.text


def _anchored(anchor: str, members: list[Block], numbers: set[int]) -> bool:
    """Whether a box belongs under this unit — an explanation, or a finding of
    a check: its anchor is the number of a formula in it, or a quote from one
    of its lines, compared without spaces, dollars and bold. A graph's edge
    list is text nobody reads — "2" is in "1-2, 2-3" — so a graph is matched
    only by its whole spec, which is how a finding about its matrix names it.
    Three characters at least: "" is in everything."""
    found = _NUMBER_ANCHOR_RE.fullmatch(anchor.strip())
    if found:
        return int(found.group(1)) in numbers
    wanted = _squash(anchor)
    if len(wanted) < 3:
        return False
    return any(
        wanted == _squash(member.text)
        if member.kind == "graph"
        else wanted in _squash(_reading(member))
        for member in members
    )


def _opened(flowables: list) -> tuple[list, bool]:
    """A unit's flowables with a group inside them opened up, and whether
    there was one to open.

    A long division keeps itself whole with a KeepTogether of its own. Set in
    one group with the heading over it or the box under it, that was a group
    inside a group; the inner one reports an effectively infinite height, and
    reportlab sent the whole of it to the next page even where it fitted —
    the empty stretch before a division on page 4 of record 47. The unit is
    still kept whole, by the one group it is set in."""
    opened: list = []
    whole = False
    for flowable in flowables:
        if isinstance(flowable, KeepTogether):
            opened.extend(flowable._content)
            whole = True
        else:
            opened.append(flowable)
    return opened, whole


def _figure_width(count: int) -> float:
    """How wide each drawing in a row of `count` may be.

    A drawing has a natural size, and beyond a certain number per row that
    size stops fitting — the row has to give way to the page, not the other
    way round.
    """
    return min(_GRAPH_WIDTH_PT, (_TEXT_WIDTH_PT - _FIGURE_GAP_PT * count) / count)


def _row(cells: list) -> Table:
    """Drawings side by side across the column, centred on each other."""
    table = Table([cells], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), _FIGURE_GAP_PT / 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), _FIGURE_GAP_PT / 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


# Between a graph and the matrix beside it, and between "A =" and its matrix.
# The second is small on purpose: the name belongs to the matrix, not to the
# space between the two pictures.
_BESIDE_GAP_PT = 28.0
_NAME_GAP_PT = 5.0


# A drawing cut out of the page is set at about the size it had there: the
# image the model saw is 1500 px on its long side, which across a notebook's
# page comes close to this many points a pixel.
_PICTURE_PT_PER_PX = 0.45
# A drawing that would fill a page is a page of drawing, not a figure in the
# text: never taller than this.
_PICTURE_MAX_HEIGHT_PT = 300.0


def _picture(block: Block, formulas: _Formulas, styles: dict[str, ParagraphStyle]):
    """The author's drawing in the document's ink, on its paper. Without one
    — cut by nothing, or the record made before drawings were kept — the line
    that described it, as the record always printed it."""
    described = Paragraph(
        _line_markup(f"схема: {block.text}", formulas, _SMALL_PT), styles["note"]
    )
    if block.image is None:
        return described
    try:
        with PILImage.open(io.BytesIO(block.image)) as stored:
            ink = stored.convert("L")
    except Exception:
        # A drawing the record kept and cannot open is still described.
        logger.warning("a kept drawing could not be opened", exc_info=True)
        return described
    drawn = PILImage.composite(
        PILImage.new("RGB", ink.size, _INK), PILImage.new("RGB", ink.size, _PAPER), ink
    )
    buffer = io.BytesIO()
    drawn.save(buffer, format="PNG")
    buffer.seek(0)
    width = min(_TEXT_WIDTH_PT, ink.width * _PICTURE_PT_PER_PX)
    height = width * ink.height / ink.width
    if height > _PICTURE_MAX_HEIGHT_PT:
        width, height = width * _PICTURE_MAX_HEIGHT_PT / height, _PICTURE_MAX_HEIGHT_PT
    picture = Image(buffer, width=width, height=height)
    picture.hAlign = "CENTER"
    return picture


def _figure_cell(caption: str, drawn: Image, styles: dict[str, ParagraphStyle]) -> list:
    cell: list = [drawn]
    if caption:
        cell.append(Spacer(1, 4))
        cell.append(Paragraph(_markup(caption), styles["caption"]))
    return cell


def _figure_row(
    figures: list[tuple[str, str]], styles: dict[str, ParagraphStyle]
) -> list:
    """Drawings side by side, each with its caption under it.

    Three variants of one idea were drawn across the page, and that is how
    they read. Stacked one per row they become three unrelated pictures with
    half a page between them.
    """
    width = _figure_width(len(figures))
    cells: list[list] = []
    for caption, spec in figures:
        drawn = _graph(spec, width)
        if drawn is None:
            # Same bargain as an unreadable formula: worse to look at than a
            # drawing, far better than a silently missing one.
            cells.append([Paragraph(_markup(f"граф: {spec}"), styles["note"])])
            continue
        cells.append(_figure_cell(caption, drawn, styles))
    return [_row(cells)]


def _is_name(block: Block) -> bool:
    """"A =" on a line of its own: the name of the matrix written after it."""
    return (
        block.kind == "math"
        and len(block.text) <= 16
        and block.text.rstrip().endswith("=")
    )


def _beside(
    graph: Block | None,
    name: Block | None,
    table: Block,
    formulas: _Formulas,
    styles: dict[str, ParagraphStyle],
) -> list | None:
    """A graph, the name of its matrix, and the matrix, in one row — the way
    the page has them and the reference sets them. Stacked, the graph sat
    centred over half a page of nothing, "A =" alone on a line under it, and
    the matrix further down still.

    None when they do not fit across the column together, or when the graph
    or the name cannot be drawn; the caller then sets them one under another
    as before.
    """
    table_width = sum(_column_widths(table.rows))
    named = formulas.display(name.text, _DISPLAY_PT) if name is not None else None
    if name is not None and named is None:
        return None
    name_width = named.drawWidth + _NAME_GAP_PT if named is not None else 0.0
    room = _TEXT_WIDTH_PT - table_width - name_width

    # Each column exactly as wide as what it holds, the gap after it as its
    # right padding: left to itself reportlab spreads the columns over the
    # whole width, and "A =" floated halfway between its graph and its matrix.
    cells: list = []
    widths: list[float] = []
    gaps: list[float] = []
    if graph is not None:
        room -= _BESIDE_GAP_PT
        if room < _MIN_BESIDE_PT:
            return None
        drawn = _graph(graph.text, min(_GRAPH_WIDTH_PT, room))
        if drawn is None:
            return None
        cells.append(_figure_cell(graph.caption, drawn, styles))
        widths.append(drawn.drawWidth + _BESIDE_GAP_PT)
        gaps.append(_BESIDE_GAP_PT)
    elif room < 0:
        return None
    if named is not None:
        cells.append(named)
        widths.append(name_width)
        gaps.append(_NAME_GAP_PT)
    cells.append(_table(table.rows, table.header, formulas, styles))
    widths.append(table_width)
    gaps.append(0.0)

    row = Table([cells], colWidths=widths, hAlign="CENTER")
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
            + [
                ("RIGHTPADDING", (column, 0), (column, 0), gap)
                for column, gap in enumerate(gaps)
            ]
        )
    )
    return [row]


def _graph(spec: str, width_pt: float = _GRAPH_WIDTH_PT) -> Image | None:
    """A drawn graph, or None when the spec does not read as one."""
    parsed = parse_graph(spec)
    if parsed is None:
        return None
    try:
        data, width, height = _graph_png(*parsed, width_pt=width_pt)
    except Exception:
        logger.exception("could not draw the graph %r", spec)
        return None
    image = Image(io.BytesIO(data), width=width, height=height)
    image.hAlign = "CENTER"
    return image


def _hairline(
    width: str = "100%", space_before: float = 0, space_after: float = 0
) -> HRFlowable:
    """A thin line of kraft — the guide's divider. What is left of the rules
    the reference drew under its title and between its sections is the seam
    between two pages of an album; the sections are set apart by air."""
    return HRFlowable(
        width=width,
        thickness=0.8,
        hAlign="CENTER",
        color=colors.HexColor(_HAIRLINE),
        spaceBefore=space_before,
        spaceAfter=space_after,
    )


def _grounded(flowables: list) -> Table:
    """A display formula on the guide's kraft ground, as wide as the column.

    A group that keeps itself whole — a long division — is opened first: its
    KeepTogether reports an effectively infinite height to the cell it would
    sit in. The ground keeps it whole, being one cell."""
    content, _ = _opened(flowables)
    table = Table([[content]], colWidths=[_TEXT_WIDTH_PT], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_FORMULA_GROUND)),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), _GROUND_PAD_X),
                ("RIGHTPADDING", (0, 0), (-1, -1), _GROUND_PAD_X),
                ("TOPPADDING", (0, 0), (-1, -1), _GROUND_PAD_Y),
                ("BOTTOMPADDING", (0, 0), (-1, -1), _GROUND_PAD_Y),
            ]
        )
    )
    return table


_FRAME_INNER_MAX_PT = _TEXT_WIDTH_PT - 2 * _NUMBER_COLUMN_PT - 2 * _FRAME_PAD_X


def _numbered(
    content, width: float, number: int | None, styles, grounded: bool = True
) -> Table:
    """`content` in a frame centred in the column, its number at the right edge.

    The frame is a table of one cell — it is what draws a box — and the row
    round it gives the number a column of its own, so the frame stays centred
    whether it is numbered or not. A formula's row stands on the kraft ground
    the guide gives every formula; a frame round words alone does not.
    """
    frame = Table([[content]], colWidths=[width + 2 * _FRAME_PAD_X], hAlign="CENTER")
    frame.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), _FRAME_RULE_PT, colors.HexColor(_INK)),
                ("LEFTPADDING", (0, 0), (-1, -1), _FRAME_PAD_X),
                ("RIGHTPADDING", (0, 0), (-1, -1), _FRAME_PAD_X),
                ("TOPPADDING", (0, 0), (-1, -1), _FRAME_PAD_Y),
                ("BOTTOMPADDING", (0, 0), (-1, -1), _FRAME_PAD_Y),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    label = Paragraph(f"({number})", styles["number"]) if number is not None else ""
    middle = _TEXT_WIDTH_PT - 2 * _NUMBER_COLUMN_PT
    row = Table(
        [["", frame, label]],
        colWidths=[_NUMBER_COLUMN_PT, middle, _NUMBER_COLUMN_PT],
        hAlign="CENTER",
    )
    pad = _GROUND_PAD_Y + 3 if grounded else 0
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (2, 0), (2, 0), _GROUND_PAD_X if grounded else 0),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
    ]
    if grounded:
        style.append(("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_FORMULA_GROUND)))
    row.setStyle(TableStyle(style))
    row.main_number = number  # what the tests and the reader both look for
    return row


def _main_formula(
    block: Block, formulas: _Formulas, styles: dict[str, ParagraphStyle], number: int
) -> list:
    """A main formula: larger, framed, numbered."""
    image = formulas.display(block.text, _MAIN_PT, _FRAME_INNER_MAX_PT)
    if image is None:
        source = Paragraph(_markup(f"${block.text}$"), styles["framed"])
        return [_numbered(source, _FRAME_INNER_MAX_PT, number, styles)]
    return [_numbered(image, image.drawWidth, number, styles)]


def _framed(
    block: Block,
    formulas: _Formulas,
    styles: dict[str, ParagraphStyle],
    number: int | None,
) -> list:
    """What the author framed that is not one formula: a phrase, or several
    lines. Numbered when it holds a formula, since that is what a frame round
    formulas means in the notebook — and on a formula's ground then."""
    markup = "<br/>".join(
        _line_markup(line, formulas, _BODY_PT) for line in block.text.split("\n")
    )
    paragraph = Paragraph(markup, styles["framed"])
    paragraph.wrap(_FRAME_INNER_MAX_PT, 10_000)
    widths = paragraph.getActualLineWidths0() or [_FRAME_INNER_MAX_PT]
    width = min(max(widths) + 2, _FRAME_INNER_MAX_PT)
    return [
        _numbered(
            Paragraph(markup, styles["framed"]), width, number, styles,
            grounded=number is not None,
        )
    ]


def _definition(cells: list[list], gaps: list[float]) -> Table:
    """The lines a definition is stated in, with the guide's amber line down
    their left — the one mark the author's own text gets.

    A row a line, not one cell for all of them: a table splits between its
    rows, so a definition longer than what is left of a page goes on over
    the next one with its line, where one cell would not fit anywhere."""
    table = Table([[cell] for cell in cells], colWidths=[_TEXT_WIDTH_PT], hAlign="LEFT")
    style = [
        ("LINEBEFORE", (0, 0), (0, -1), _BAR_PT, colors.HexColor(_DEFINITION_BAR)),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # The line runs a little past the first and the last line of text.
        ("TOPPADDING", (0, 0), (0, 0), 2),
        ("BOTTOMPADDING", (0, -1), (0, -1), 3),
    ]
    for row, gap in enumerate(gaps):
        if row and gap:
            style.append(("TOPPADDING", (0, row), (0, row), gap))
    table.setStyle(TableStyle(style))
    return table


def _flowables(
    block: Block,
    formulas: _Formulas,
    styles: dict[str, ParagraphStyle],
    top_level: int = 1,
    numbers=None,
    sections=None,
) -> list:
    """One parsed block as reportlab flowables, with no space around them —
    the space between blocks is the rhythm's, see _space_before."""
    numbers = numbers if numbers is not None else itertools.count(1)
    sections = sections if sections is not None else itertools.count(1)
    if block.kind == "math" and block.main:
        return _main_formula(block, formulas, styles, next(numbers))

    if block.kind == "framed":
        holds_formula = "$" in block.text
        return _framed(block, formulas, styles, next(numbers) if holds_formula else None)
    if block.kind == "rule":
        # The seam between two pages of an album. A short thin line says "the
        # next page starts here" without shouting it.
        return [_hairline("35%")]

    if block.kind == "table":
        return [_table(block.rows, block.header, formulas, styles)]

    if block.kind == "heading":
        rank = _rank(block.level, top_level)
        style = styles[f"heading{rank}"]
        markup = _line_markup(block.text, formulas, style.fontSize)
        number = next(sections) if rank == 1 else None
        if number is not None:
            # The guide numbers a lecture's sections through the whole
            # record, "01", "02", in the monospace and the dark amber —
            # the base's sections only: a passage from another notebook
            # draws its heading unnumbered (task 63).
            markup = (
                f'<font face="{_MONO_BOLD_FONT}" color="{_DARK_AMBER}" '
                f'size="{style.fontSize * 0.82:.1f}">{number:02d}</font>'
                f"&nbsp;&nbsp;{markup}"
            )
        return [Paragraph(markup, style)]

    if block.kind == "bullet":
        return [
            Paragraph(
                _line_markup(block.text, formulas, _BODY_PT),
                styles["bullet"],
                bulletText=block.marker or "•",
            )
        ]

    if block.kind == "picture":
        return [_picture(block, formulas, styles)]

    if block.kind == "note":
        # A description of a drawing names its points in LaTeX as often as
        # not — "$x_0 = 1$" — and printed as markup those were source.
        return [Paragraph(_line_markup(block.text, formulas, _SMALL_PT), styles["note"])]

    if block.kind == "math":
        arrays = ruled_arrays(block.text)
        if arrays is not None:
            return [_ruled_row(arrays, formulas, styles)]
        rows = aligned_rows(block.text)
        if rows is not None:
            drawn = [formulas.display(row, _DISPLAY_PT) for row in rows]
            if None not in drawn:
                stacked: list = []
                for image in drawn:
                    image.hAlign = "CENTER"
                    if stacked:
                        stacked.append(Spacer(1, _ALIGNED_ROW_GAP_PT))
                    stacked.append(image)
                return stacked
        image = formulas.display(block.text, _DISPLAY_PT)
        if image is None:
            return [Paragraph(_markup(f"${block.text}$"), styles["math"])]
        image.hAlign = "CENTER"
        return [image]

    if block.kind == "gap":
        return []

    return [Paragraph(_line_markup(block.text, formulas, _BODY_PT), styles["body"])]


def _rank(level: int, top_level: int) -> int:
    """A heading's step on the scale, counted from the record's top level."""
    return max(1, min(level - top_level + 1, 3))


def _skip_gaps(parsed: list[Block], position: int) -> int:
    while position < len(parsed) and parsed[position].kind == "gap":
        position += 1
    return position


def _pair(
    parsed: list[Block],
    position: int,
    formulas: _Formulas,
    styles: dict[str, ParagraphStyle],
    graph: Block | None = None,
    name: Block | None = None,
) -> tuple[list[Block], int, list, str] | None:
    """A graph or a matrix name followed directly by a table, as one unit.

    Directly: a blank line may stand between them, a line of text may not.
    That is narrower than graphcheck's rule for which table a graph is about,
    on purpose — the check asks what the table describes, the layout only
    what can sit next to it without moving a word of the record.
    """
    members = [block for block in (graph, name) if block is not None]
    position = _skip_gaps(parsed, position)
    if name is None and position < len(parsed) and _is_name(parsed[position]):
        name = parsed[position]
        members.append(name)
        position = _skip_gaps(parsed, position + 1)
    if position >= len(parsed) or parsed[position].kind != "table":
        return None
    table = parsed[position]
    flowables = _beside(graph, name, table, formulas, styles)
    if flowables is None:
        return None
    return members + [table], position + 1, flowables, "figure"


# A definition, as the composing stage heads one — "### Определение", its
# rule 6 — or as a line opens one: "**Определение.** Граф называется ...".
_DEFINITION_HEADING_RE = re.compile(r"^[*\s]*определени[еяй]", re.IGNORECASE)
_DEFINITION_LEAD_RE = re.compile(r"^\*\*\s*определени[еяй]", re.IGNORECASE)
_DEFINITION_LINES = ("text", "bullet")


def _definition_end(parsed: list[Block], index: int) -> int | None:
    """Where the lines of a definition end when `index` is the first of them,
    else None: the lines right under a heading "Определение…", or a line that
    opens with a bold "Определение" and those right after it.

    Its lines only — prose and list items with no blank line between them.
    A formula, a table or a blank line ends it: the line marks what the
    definition says, and a whole section under the heading would carry its
    examples along."""
    block = parsed[index]
    if block.kind not in _DEFINITION_LINES:
        return None
    if not (block.kind == "text" and _DEFINITION_LEAD_RE.match(block.text.strip())):
        before = index - 1
        while before >= 0 and parsed[before].kind == "gap":
            before -= 1
        if before < 0 or parsed[before].kind != "heading":
            return None
        if not _DEFINITION_HEADING_RE.match(parsed[before].text):
            return None
    end = index + 1
    while end < len(parsed) and parsed[end].kind in _DEFINITION_LINES:
        end += 1
    return end


def _unit(
    parsed: list[Block],
    index: int,
    formulas: _Formulas,
    styles: dict[str, ParagraphStyle],
    top_level: int = 1,
    numbers=None,
    sections=None,
) -> tuple[list[Block], int, list, str]:
    """The next thing set on the page: the blocks it is made of, where the one
    after it starts, its flowables, and the kind the rhythm knows it by.

    Mostly one block. A run of drawings is one row, and a graph or a matrix
    name with the table right after it is one row too; so are the lines of a
    definition, beside one amber line.
    """
    block = parsed[index]

    end = _definition_end(parsed, index)
    if end is not None:
        members = parsed[index:end]
        cells: list[list] = []
        gaps: list[float] = []
        for position, member in enumerate(members):
            cells.append(
                _flowables(member, formulas, styles, top_level, numbers, sections)
            )
            gaps.append(
                _space_before(members[position - 1].kind, member.kind, False)
                if position
                else 0.0
            )
        return members, end, [_definition(cells, gaps)], "definition"

    if block.kind == "graph":
        run = [block]
        end = index + 1
        while (
            end < len(parsed)
            and parsed[end].kind == "graph"
            and len(run) < _FIGURES_PER_ROW
        ):
            run.append(parsed[end])
            end += 1
        if len(run) == 1:
            paired = _pair(parsed, end, formulas, styles, graph=block)
            if paired is not None:
                return paired
        figures = [(member.caption, member.text) for member in run]
        return run, end, _figure_row(figures, styles), "figure"

    if _is_name(block) and not block.main:
        paired = _pair(parsed, index + 1, formulas, styles, name=block)
        if paired is not None:
            return paired

    flowables = _flowables(block, formulas, styles, top_level, numbers, sections)
    if block.kind == "math" and not block.main:
        # A main formula's row draws its own ground, round its frame.
        flowables = [_grounded(flowables)]
    if block.kind == "math" and block.main:
        kind = "main"
    elif block.kind == "framed":
        kind = "main" if "$" in block.text else "frame"
    elif block.kind == "picture":
        kind = "figure" if block.image is not None else "note"
    else:
        kind = block.kind
    return [block], index + 1, flowables, kind


def _space_before(previous: str | None, kind: str, paragraph_break: bool) -> float:
    """How much space goes between a unit of kind `previous` and one of kind
    `kind`, `paragraph_break` saying whether a blank line stood between them.

    A heading carries its own space above and below it in its style: the
    space over a section is part of the heading, and a page that begins with
    one drops it rather than opening on a gap."""
    if previous is None or kind == "heading" or previous == "heading":
        return 0.0
    if kind in ("main", "frame") or previous in ("main", "frame"):
        return _MAIN_GAP
    if kind == "math" and previous == "math":
        # One run of formulas on one ground: the grounds touch.
        return 0.0
    if kind in _SET_APART or previous in _SET_APART:
        return _SET_APART_GAP
    if previous == "box":
        return _BOX_GAP
    if paragraph_break:
        return _PARAGRAPH_GAP
    if kind == "bullet" and previous == "bullet":
        return _ITEM_GAP
    return 0.0


def _width(text: str, font: str, size: float, tracking: float = 0.0) -> float:
    return pdfmetrics.stringWidth(text, font, size) + tracking * len(text)


def _fit(
    text: str, width: float, size: float, font: str = _TEXT_FONT, tracking: float = 0.0
) -> str:
    """`text` cut to `width` points, with an ellipsis where it was cut."""
    if _width(text, font, size, tracking) <= width:
        return text
    while text and _width(text + "…", font, size, tracking) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _draw_runs(
    page_canvas,
    x: float,
    y: float,
    text: str,
    size: float,
    font: str = _TEXT_FONT,
    tracking: float = 0.0,
) -> float:
    """drawString with the fallback a paragraph gets from _text: a run of
    characters the face lacks — "⇒", "ℝ" in a title turned plain — is set in
    DejaVu rather than printed as empty boxes. Where the text ended."""
    known = _mono_glyphs() if font in (_MONO_FONT, _MONO_BOLD_FONT) else _text_glyphs()
    for in_face, run in itertools.groupby(text, key=lambda char: ord(char) in known):
        run = "".join(run)
        face = font if in_face else _FALLBACK_FONT
        page_canvas.setFont(face, size)
        page_canvas.drawString(x, y, run, charSpace=tracking)
        x += _width(run, face, size, tracking)
    return x


# ── The furniture: the head of every page and the signature at its foot ──────
_HEAD_BASELINE_PT = 12 * mm
_WORDMARK = "SUM"
_WORDMARK_PT = 14.0
_TAGLINE = "AI · КОНСПЕКТЫ"
_TAGLINE_PT = 6.0
_TAGLINE_TRACKING = 0.22 * _TAGLINE_PT  # the guide's 0.22 em
_INVITE_PT = 8.0
_HANDLE_PT = 9.5
# 18 mm is the guide's size, 15 its least. At 18 in a band of 22 the last row
# of modules came to 3 mm off the paper's edge, where a printer does not
# print; at 16 it stands 5 mm clear, and the signature's line 1.5 mm above it.
_QR_PT = 16 * mm
_QR_BOTTOM_PT = 4.5 * mm
_QR_BORDER_MODULES = 2


def _draw_head(
    page_canvas, number: int, total: int, page: Page, running_title: str
) -> None:
    """The head of a page: which lecture this is, even on a sheet forwarded
    alone — the subject, the date, the page — in the monospace, in capitals,
    in grey ink. From the second page on the record's title stands in it too,
    since the title itself is on the first.

    The page is "стр. 2/5", never "с. 2": inside a record "с. 2" means the
    second photographed page, which is what a missing page's box names. A
    record of one page has no page number."""
    width, height = A4
    left, right = _MARGIN_PT, width - _MARGIN_PT
    facts = [page.date] if page.date else []
    if total > 1:
        facts.append(f"{page.page_word} {number}/{total}".strip())
    at_right = " · ".join(facts).upper()
    named = [page.subject] if page.subject else []
    if number > 1 and running_title:
        named.append(running_title)
    at_left = " · ".join(named).upper()

    page_canvas.saveState()
    page_canvas.setFillColor(colors.HexColor(_MUTED))
    size, tracking = _FURNITURE_PT, _FURNITURE_TRACKING
    y = height - _HEAD_BASELINE_PT
    right_width = _width(at_right, _MONO_FONT, size, tracking)
    if at_right:
        _draw_runs(
            page_canvas, right - right_width, y, at_right, size, _MONO_FONT, tracking
        )
    if at_left:
        room = right - left - right_width - (16 if at_right else 0)
        _draw_runs(
            page_canvas, left, y, _fit(at_left, room, size, _MONO_FONT, tracking),
            size, _MONO_FONT, tracking,
        )
    page_canvas.restoreState()


def _draw_qr(page_canvas, value: str, x: float, y: float, size: float) -> None:
    """A QR code in ink on the paper, as the guide asks: not inverted, not in
    amber, no star in its middle — each of those costs a scanner its read."""
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing

    widget = QrCodeWidget(value, barLevel="M", barBorder=_QR_BORDER_MODULES)
    widget.barWidth = size
    widget.barHeight = size
    widget.barFillColor = colors.HexColor(_INK)
    drawing = Drawing(size, size)
    drawing.add(widget)
    renderPDF.draw(drawing, page_canvas, x, y)


def _draw_signature(page_canvas, page: Page) -> None:
    """The foot of every page, the last one included: the SUM sign, the
    invitation with the bot's name, and a QR code that opens the bot. A
    screenshot of one page has to lead to it too — the guide's reason for
    putting it on every page rather than once at the end.

    Nothing of it without the bot's name but the sign: an invitation to a bot
    it cannot name is an invitation to nothing."""
    width, _ = A4
    left, right = _MARGIN_PT, width - _MARGIN_PT
    page_canvas.saveState()
    page_canvas.setStrokeColor(colors.HexColor(_KRAFT))
    page_canvas.setLineWidth(0.5)
    page_canvas.line(left, _SIGNATURE_PT, right, _SIGNATURE_PT)

    # The sign: SUM in ink and the star in amber, "AI · конспекты" under it.
    baseline = 12.9 * mm
    page_canvas.setFillColor(colors.HexColor(_INK))
    page_canvas.setFont(_HEAVY_FONT, _WORDMARK_PT)
    page_canvas.drawString(left, baseline, _WORDMARK)
    after = left + pdfmetrics.stringWidth(_WORDMARK, _HEAVY_FONT, _WORDMARK_PT)
    radius = _WORDMARK_PT * 0.34
    _star(page_canvas, after + 2.5 + radius, baseline + _WORDMARK_PT * 0.5, radius, _AMBER)
    page_canvas.setFillColor(colors.HexColor(_MUTED))
    _draw_runs(
        page_canvas, left + 0.5, baseline - 3.6 * mm, _TAGLINE, _TAGLINE_PT,
        _MONO_FONT, _TAGLINE_TRACKING,
    )

    if page.bot_username:
        handle = f"@{page.bot_username}"
        middle = width / 2
        if page.invite:
            page_canvas.setFillColor(colors.HexColor(_MUTED))
            invite_width = _width(page.invite, _TEXT_FONT, _INVITE_PT)
            _draw_runs(
                page_canvas, middle - invite_width / 2, 14.6 * mm, page.invite, _INVITE_PT
            )
        page_canvas.setFillColor(colors.HexColor(_INK))
        handle_width = _width(handle, _MONO_BOLD_FONT, _HANDLE_PT)
        _draw_runs(
            page_canvas, middle - handle_width / 2, 9.6 * mm, handle, _HANDLE_PT,
            _MONO_BOLD_FONT,
        )
        _draw_qr(
            page_canvas, f"https://t.me/{page.bot_username}", right - _QR_PT,
            _QR_BOTTOM_PT, _QR_PT,
        )
    page_canvas.restoreState()


def _draw_furniture(
    page_canvas, number: int, total: int, page: Page, running_title: str
) -> None:
    """What a page carries besides the record: its head and its signature."""
    _draw_head(page_canvas, number, total, page, running_title)
    _draw_signature(page_canvas, page)


def _draw_paper(page_canvas, _document=None) -> None:
    """The page's paper, under everything drawn on it — never white."""
    width, height = A4
    page_canvas.saveState()
    page_canvas.setFillColor(colors.HexColor(_PAPER))
    page_canvas.rect(0, 0, width, height, stroke=0, fill=1)
    page_canvas.restoreState()


class _PagedCanvas(rl_canvas.Canvas):
    """A canvas that holds every page back until the last one is known.

    reportlab finishes a page the moment its frame is full, and "2 / 5" needs
    the 5 — so each page's state is kept, and the furniture is drawn over all
    of them when the document is saved.
    """

    def __init__(self, *args, page: Page | None = None, running_title: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._page = page or Page()
        self._running_title = running_title
        self._held: list[dict] = []

    def showPage(self):  # noqa: N802 — reportlab's name
        self._held.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._held)
        for number, state in enumerate(self._held, 1):
            self.__dict__.update(state)
            _draw_furniture(self, number, total, self._page, self._running_title)
            rl_canvas.Canvas.showPage(self)
        rl_canvas.Canvas.save(self)


def render(
    title: str,
    markdown: str,
    subtitle: str | None = None,
    callouts: Sequence[Callout] = (),
    byline: str | None = None,
    remarks: Sequence[Remark] = (),
    explanations: Sequence[Explanation] = (),
    summary: Summary | None = None,
    page: Page | None = None,
    figures: Mapping[int, bytes] | None = None,
) -> bytes:
    """A record as PDF bytes. Never raises on the content of the record.
    `figures` are the drawings the record keeps, by the N of "[рисунок N: …]"."""
    _register_fonts()
    styles = _styles()
    buffer = io.BytesIO()
    page = page or Page()

    # A first heading repeating the title is the commonest shape a page takes:
    # the record is called "Графы" and the page is headed "Графы". Printing
    # both says nothing twice.
    wanted = title.strip().casefold()
    parsed = [
        block
        for block in blocks(_lift_drawings(markdown))
        if not (block.kind == "heading" and block.text.strip().casefold() == wanted)
    ]
    for block in parsed:
        if block.kind == "picture" and figures:
            block.image = figures.get(int(block.marker))
    levels = [block.level for block in parsed if block.kind == "heading"]
    top_level = min(levels) if levels else 1

    with tempfile.TemporaryDirectory(prefix="conspectium-pdf-") as directory:
        formulas = _Formulas(directory)
        story: list = [
            # With its formulas drawn: "$2^{1001}$" stood in record 45's title.
            # Not through _line_markup, which sets the lines of the record.
            Paragraph(
                _inline(split_inline(title), formulas, styles["title"].fontSize),
                styles["title"],
            ),
        ]
        # What was written in the margin — whose lecture, which date — and
        # then the facts of the record. Under the title, where a reader looks
        # for them, not in the body, where they read as the author speaking.
        facts = [(byline, "byline"), (subtitle, "meta")]
        for line, style in facts:
            if line:
                story.append(Paragraph(_markup(line), styles[style]))
        story.append(Spacer(1, 14))

        # The guide's one thought on top: what the lecture was, in the bot's
        # words, before the lecture itself. It is about the whole record, and
        # it is where a reader deciding whether to read on looks first.
        if summary is not None and summary.lines:
            story.append(_essence(summary, formulas, styles))
            story.append(Spacer(1, 14))

        for box in callouts:
            # Above the record, not below it: these say how far the text that
            # follows can be trusted, and that is worth knowing first.
            story.append(_callout(box, formulas, styles))
            story.append(Spacer(1, 10))
        if callouts:
            story.append(Spacer(1, 4))

        pending = list(remarks)
        unexplained = list(explanations)
        # The number each numbered block will carry, known before the loop so
        # an explanation anchored on "(3)" finds the unit that holds it.
        numbered: dict[int, int] = {}
        inside = False
        for block in parsed:
            if block.kind in ("inserted", "inserted_end"):
                inside = block.kind == "inserted"
            elif _is_numbered(block) and not inside:
                numbered[id(block)] = len(numbered) + 1
        previous: str | None = None
        paragraph_break = False
        # Headings waiting for what they head. A heading is never the last
        # line of a page — "Пример" at the foot of page three, its graph on
        # four, reads as a heading over nothing — so it is held back and set
        # in one group with the unit after it.
        #
        # The groups are built here and flat, never left to reportlab's
        # keepWithNext: that wraps a heading and the next flowable in a
        # KeepTogether, and when the next flowable is itself a KeepTogether —
        # a line with its remark, a whole table — the inner one reports its
        # height as effectively infinite and the heading stays behind anyway.
        held: list = []
        # Main formulas are numbered in the order they stand, through the
        # whole record, and so are its sections.
        numbers = itertools.count(1)
        sections = itertools.count(1)
        # Inside a passage from another notebook (task 63) nothing is
        # numbered: the numbers are the base's, an explanation points at
        # them, and a passage set in before one would move them all.
        inserting = False
        unnumbered = itertools.repeat(None)

        def mark(flowable):
            return _Inserted(flowable) if inserting else flowable

        index = 0
        while index < len(parsed):
            if parsed[index].kind == "gap":
                paragraph_break = True
                index += 1
                continue
            if parsed[index].kind in ("inserted", "inserted_end"):
                story.extend(held)
                held = []
                inserting = parsed[index].kind == "inserted"
                if inserting:
                    # The label is held like a heading: never the last line
                    # of a page with its passage on the next.
                    story.append(Spacer(1, _SET_APART_GAP))
                    held = [_Inserted(_Label(parsed[index].text, _INSERT_LABEL))]
                    previous = None
                else:
                    previous = "box"
                paragraph_break = False
                index += 1
                continue

            members, index, flowables, kind = _unit(
                parsed, index, formulas, styles, top_level,
                unnumbered if inserting else numbers,
                unnumbered if inserting else sections,
            )
            space = _space_before(previous, kind, paragraph_break)
            paragraph_break = False

            unit_numbers = {numbered[id(m)] for m in members if id(m) in numbered}
            attached = [
                remark
                for remark in pending
                if _anchored(remark.anchor, members, unit_numbers)
            ]
            group, whole = _opened(flowables)
            for remark in attached:
                # A finding stays with the line it is about: never the first
                # thing on a page whose line was the last on the one before.
                pending.remove(remark)
                group += [Spacer(1, 4), _remark(remark, formulas, styles)]
            explained = [
                item for item in unexplained
                if _anchored(item.anchor, members, unit_numbers)
            ]
            lead: list = []
            for item in explained:
                unexplained.remove(item)
                if item.before:
                    lead += [_explanation(item, formulas, styles), Spacer(1, 6)]
                    continue
                # After the findings: first what is wrong with the line, then
                # what the bot has to add to it.
                group += [Spacer(1, 6), _explanation(item, formulas, styles)]
            group = [mark(flowable) for flowable in lead + group]
            attached = attached + explained

            if held:
                group = held + ([mark(Spacer(1, space))] if space else []) + group
                held = []
            elif space:
                story.append(mark(Spacer(1, space)))

            previous = "box" if attached else kind
            if kind == "heading":
                held = group
                continue
            # A table is kept whole as well: split across two pages, a matrix
            # loses its column names on the second.
            if len(group) > 1 or kind == "table" or whole:
                story.append(KeepTogether(group))
            else:
                story.extend(group)

        # A heading with nothing after it has nothing to be kept with.
        story.extend(held)

        # A finding whose anchor was never found is still worth reading; it
        # goes at the end rather than nowhere. So does an explanation.
        for remark in pending:
            story.append(Spacer(1, _SET_APART_GAP))
            story.append(_remark(remark, formulas, styles))
        for item in unexplained:
            story.append(Spacer(1, _SET_APART_GAP))
            story.append(_explanation(item, formulas, styles))

        SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=_MARGIN_PT - _FRAME_PADDING_PT,
            rightMargin=_MARGIN_PT - _FRAME_PADDING_PT,
            topMargin=_TOP_PT - _FRAME_PADDING_PT,
            bottomMargin=_BOTTOM_PT - _FRAME_PADDING_PT,
            title=plain(title),
            author=_WORDMARK,
            creator=_WORDMARK,
            subject=page.subject,
        ).build(
            story,
            onFirstPage=_draw_paper,
            onLaterPages=_draw_paper,
            canvasmaker=functools.partial(
                _PagedCanvas, page=page, running_title=plain(title)
            ),
        )

    return buffer.getvalue()
