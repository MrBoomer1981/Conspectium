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
than left to reportlab's defaults, and it is copied from one file: the
author's `матан 24.09.2026.pdf`. Lato for the text and Computer Modern for the
formulas, its sizes, its greys, its one kind of box beside the text — the
values below were read out of that PDF, not chosen by eye.
"""

from __future__ import annotations

import functools
import io
import logging
import math
import os
import re
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")  # no display on a server; must precede pyplot
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import patheffects  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
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

logger = logging.getLogger(__name__)

# Rendered at this DPI, then scaled to points. High enough that a formula
# stays sharp when the PDF is zoomed on a phone.
_DPI = 300

# ── The fonts ────────────────────────────────────────────────────────────────
# Lato 2, which has Cyrillic — the Lato Google serves does not — bundled in the
# repo under its OFL licence. DejaVu, which ships inside matplotlib, stays as
# the face for the glyphs Lato lacks: ∀, ∈, ⇒, ►, ℝ in running text would
# otherwise print as empty boxes.
_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
_TEXT_FONT = "Lato"
_HEAVY_FONT = "Lato-Black"
_FALLBACK_FONT = "DejaVu"
# Formulas in Computer Modern, as the reference's KaTeX draws them. It has no
# Cyrillic, and mathtext sets a \text{кольца} in a serif of its own instead —
# which is exactly what the reference does with its own Cyrillic in formulas.
_MATH_FONT = "cm"
# Computer Modern's hairlines, drawn as pixels and smoothed, came out a pale
# grey beside the text: KaTeX in the reference is vector and as dark as Lato.
# A quarter-point stroke round every glyph brings the weight back to the
# reference's; half a point was already bold.
_MATH_STROKE_PT = 0.25

# ── The scale, read out of the reference ─────────────────────────────────────
_BODY_PT = 12.0
_LEADING = 1.6
_TITLE_PT = 24.0
# Levels are counted from the top one the record uses, so a record whose
# sections are "##" looks like one whose sections are "#". The level blocks()
# reads was once thrown away altogether, which made "#" and "###" the same.
_HEADING_PT = {1: 18.0, 2: 14.0, 3: 12.0}
_HEADING_SPACE_BEFORE = {1: 20, 2: 16, 3: 12}
_HEADING_SPACE_AFTER = {1: 3, 2: 5, 3: 3}
# KaTeX sets its formulas a little larger than the text round them: Computer
# Modern's x-height is smaller than Lato's.
_MATH_SCALE = 1.06
_DISPLAY_PT = _BODY_PT * _MATH_SCALE
_TABLE_PT = 11.0
_SMALL_PT = 10.0
_LABEL_PT = 8.5
_LABEL_TRACKING = 0.9
_FURNITURE_PT = 8.0

# ── The rhythm ───────────────────────────────────────────────────────────────
# The space between two blocks depends on what both of them are. Lines of one
# paragraph sit at the leading and nothing more: a lecture note is written
# line by line, and space under every line made a page of them read as
# double-spaced. A blank line in the record is a paragraph. A display
# formula, a table and a drawing are set apart, and a run of display formulas
# is one block, the way a chain of equalities is one thing on paper.
_PARAGRAPH_GAP = 9.0
_SET_APART_GAP = 10.0
_STACK_GAP = 3.0
_ITEM_GAP = 3.0
_BOX_GAP = 8.0
_SET_APART = {"math", "table", "figure", "note", "rule"}

# ── The page ─────────────────────────────────────────────────────────────────
# The reference's column: 66 pt either side of an A4 page, 463 pt of text.
_MARGIN_PT = 66.0
_TOP_PT = 60.0
_BOTTOM_PT = 56.0
_TEXT_WIDTH_PT = A4[0] - 2 * _MARGIN_PT
# reportlab's frame pads its content by 6 pt on every side, inside the page
# margins. Unaccounted for, the column was 12 pt narrower than every width
# computed from it, and a box as wide as the column ran past its right edge.
_FRAME_PADDING_PT = 6.0

# ── The reference's tones, and the two accents the callouts already had ────
_INK = "#24292f"
_MUTED = "#6b7480"
_HAIRLINE = "#d8dee4"  # under the title and a section heading, 0.8 pt
_SECTION_RULE = "#e6e8eb"  # between two sections, 1.5 pt
_BAR = "#d0d7de"  # down the side of a remark, 3 pt
# A callout differs from a remark in its accent alone: the bar and the label.
_CALLOUT_TONES = {
    "info": "#3f6f9f",
    "warning": "#a8742c",
}

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
# The seam _assemble writes between two pages of an album.
_RULE_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})$")
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

# Past this a circle of vertices is unreadable, and the text is more likely to
# be prose the model mislabelled than a graph. Same for a long vertex name.
_MAX_VERTICES = 24
_MAX_VERTEX_CHARS = 12


@dataclass
class Callout:
    """A box above the record saying how far the transcription can be trusted.

    Never anything the model wrote about the page: only what the pipeline
    already stored beside the text — unreadable spots, arithmetic it could not
    make add up, numbers the three runs read differently. The caller builds
    these; this module knows nothing about where a record comes from.
    """

    title: str
    lines: list[str]
    tone: str = "info"  # "info" | "warning"


@dataclass
class Remark:
    """A note about how one place in the record was read, set beside it.

    `anchor` is the text it belongs to: whichever block contains that text
    gets the remark under it. One that matches nothing is not thrown away —
    it goes at the end, where it is still readable. Like a Callout, it says
    only what the pipeline already knows.
    """

    anchor: str
    label: str
    lines: list[str]


@dataclass
class Block:
    kind: str  # heading | bullet | text | math | note | gap | rule | table | graph
    text: str = ""
    level: int = 0
    rows: list[list[str]] = field(default_factory=list)
    header: bool = False
    caption: str = ""
    marker: str = ""  # a list item's own number, "1)" — empty for a bullet


def _latex(match: re.Match) -> str:
    return (match.group(1) or match.group(2)).strip()


def _is_whole_formula(line: str) -> str | None:
    """The LaTeX of a line that is nothing but one formula, else None. Such a
    line is set on its own, centred, the way it sat on the page."""
    match = _MATH_RE.fullmatch(line.strip())
    return _latex(match) if match else None


def _display_lines(lines: list[str], start: int) -> tuple[list[str], int] | None:
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
    body = [first[2:].strip()]
    for end in range(start + 1, len(lines)):
        line = lines[end].strip()
        if not line:
            return None
        if line.endswith("$$"):
            body.append(line[:-2].strip())
            content = [part for part in body if part]
            if any("\\begin" in part for part in content):
                return [" ".join(content)], end + 1
            return content, end + 1
        body.append(line)
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

        display = _display_lines(lines, index)
        if display is not None:
            formulas, index = display
            out.extend(Block("math", formula) for formula in formulas)
            continue

        table = _read_table(lines, index)
        if table is not None:
            block, index = table
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
            out.append(Block("math", formula))
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
        # page is a drawing. We never store photos, so it stays a remark.
        # "[граф: 1-2, 2-3]" is that same note with the edges in it, and is
        # drawn instead of described.
        if stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1].strip()
            drawing = _GRAPH_RE.match(inner)
            out.append(
                Block(
                    "graph",
                    drawing.group(2).strip(),
                    caption=drawing.group(1).strip(),
                )
                if drawing
                else Block("note", inner)
            )
            index += 1
            continue

        out.append(Block("text", stripped))
        index += 1

    while out and out[-1].kind == "gap":
        out.pop()
    return out


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


# ── Rendering ────────────────────────────────────────────────────────────────


def _mpl_font(name: str) -> str:
    return os.path.join(
        os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf", name
    )


_FONTS_READY = False


def _register_fonts() -> None:
    """Lato from the repo, DejaVu from inside matplotlib. reportlab's built-in
    fonts are Latin only, and a page of notes is Cyrillic."""
    global _FONTS_READY
    if _FONTS_READY:
        return
    for name, filename in (
        ("Lato", "Lato-Regular.ttf"),
        ("Lato-Italic", "Lato-Italic.ttf"),
        ("Lato-Bold", "Lato-Bold.ttf"),
        ("Lato-BoldItalic", "Lato-BoldItalic.ttf"),
        ("Lato-Black", "Lato-Black.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(name, os.path.join(_FONT_DIR, filename)))
    pdfmetrics.registerFontFamily(
        "Lato", normal="Lato", bold="Lato-Bold", italic="Lato-Italic",
        boldItalic="Lato-BoldItalic",
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


@functools.lru_cache(maxsize=1)
def _lato_glyphs() -> frozenset[int]:
    """Every character Lato can draw. Anything else in running text is set in
    DejaVu, which draws nearly everything."""
    return frozenset(
        TTFont("LatoCoverage", os.path.join(_FONT_DIR, "Lato-Regular.ttf")).face.charToGlyph
    )


def warm_up() -> None:
    """Build matplotlib's font cache and register the fonts ahead of the first
    request. Both are one-off costs of a few seconds; paying them at startup
    keeps them out of someone's first photo."""
    try:
        _register_fonts()
        _lato_glyphs()
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
    latex = _ENVIRONMENT_RE.sub(_environment, latex)
    latex = _LABELLED_ARROW_RE.sub(_labelled_arrow, latex)
    latex = _UNSUPPORTED_RE.sub("", latex)
    latex = _SYNONYM_RE.sub(lambda found: "\\" + _SYNONYMS[found.group(1)], latex)
    return _THIN_SPACE_RE.sub(" ", latex)


# The empty margin savefig leaves round a formula, in inches and in points.
_FORMULA_PAD_IN = 0.01
_FORMULA_PAD_PT = _FORMULA_PAD_IN * 72.0
# A formula wider than the column is shrunk to fit it. At its own size a long
# chain of equalities ran past the margin and off the paper, where nobody can
# read it; smaller is readable. Inside a line it leaves room for a list item.
_INLINE_MAX_PT = _TEXT_WIDTH_PT - 30


def _formula_png(latex: str, size_pt: float) -> tuple[bytes, float, float, float]:
    """One formula as a transparent PNG, with its width, height and depth in
    points. Raises when mathtext cannot read the LaTeX — callers fall back to
    the source text.

    The depth is how far below the bottom of the picture the formula's
    baseline sits above it. A formula set inside a line is lowered by exactly
    that much, so its baseline is the line's: a fixed fraction of the height
    lifted a subscript off the line and sank a fraction through it.
    """
    figure = plt.figure(figsize=(0.01, 0.01))
    try:
        text = figure.text(
            0, 0, f"${for_mathtext(latex)}$",
            fontsize=size_pt, math_fontfamily=_MATH_FONT, color=_INK,
        )
        text.set_path_effects(
            [patheffects.withStroke(linewidth=_MATH_STROKE_PT, foreground=_INK)]
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

    label_font = FontProperties(fname=os.path.join(_FONT_DIR, "Lato-Bold.ttf"), size=9)
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
            axes.add_patch(
                plt.Circle((x, y), node, facecolor="white", edgecolor=_INK,
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
    wrote as a line break, and every run of characters Lato does not have set
    in DejaVu, which has them — reportlab has no fallback of its own and draws
    an empty box for a glyph its font lacks."""
    if not value:
        return ""
    known = _lato_glyphs()
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


def _inline(runs: list[tuple[str, str]], formulas, size_pt: float) -> str:
    """Runs of text and formulas as reportlab markup.

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
                formulas.inline(value, size_pt * _MATH_SCALE)
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
            # its comma.
            pieces.append("\u200b")
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
        self._cache: dict[tuple[str, float], tuple[str, float, float, float]] = {}
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

    def inline(self, latex: str, size_pt: float) -> str | None:
        """An <img> tag for use inside a paragraph, or None if unrenderable."""
        key = (latex, size_pt)
        if key not in self._cache:
            try:
                data, width, height, depth = _formula_png(latex, size_pt)
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

    def display(self, latex: str, size_pt: float) -> Image | None:
        try:
            data, width, height, _ = _formula_png(latex, size_pt)
        except Exception as exc:
            self._refused(latex, exc)
            return None
        if width > _TEXT_WIDTH_PT:
            height *= _TEXT_WIDTH_PT / width
            width = _TEXT_WIDTH_PT
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
            leading=_TITLE_PT * 1.2, spaceAfter=9,
        ),
        **{
            f"heading{level}": ParagraphStyle(
                f"heading{level}", parent=base, fontName=_HEAVY_FONT,
                fontSize=size, leading=size * 1.3,
                spaceBefore=_HEADING_SPACE_BEFORE[level],
                spaceAfter=_HEADING_SPACE_AFTER[level],
            )
            for level, size in _HEADING_PT.items()
        },
        # What stands under the title: small and grey, a line of facts rather
        # than a sentence the author was saying.
        "byline": ParagraphStyle("byline", parent=muted),
        "meta": ParagraphStyle("meta", parent=muted),
        "callout_body": ParagraphStyle("callout_body", parent=base),
        # A remark is set at the size of the text it sits in, in grey — the
        # reference's "ЗАМЕЧАНИЕ". Smaller and it read as small print to skip.
        "remark_body": ParagraphStyle(
            "remark_body", parent=base, textColor=_MUTED,
        ),
        "body": base,
        "bullet": ParagraphStyle(
            "bullet", parent=base, leftIndent=26, bulletIndent=10,
            bulletFontName=_TEXT_FONT,
        ),
        "caption": ParagraphStyle("caption", parent=muted, alignment=TA_CENTER),
        # A drawing the page had and the record could not draw: set where the
        # picture would be, the size of a caption, so it reads as a figure
        # that is missing rather than as a line of the author's text.
        "note": ParagraphStyle(
            "note", parent=muted, fontName="Lato-Italic", alignment=TA_CENTER,
        ),
        "math": ParagraphStyle("math", parent=base, alignment=TA_CENTER),
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
    rule = colors.HexColor(_INK)
    light = colors.HexColor(_HAIRLINE)
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


class _Label(Flowable):
    """A box's label: small capitals with their letters spaced, the way the
    reference sets "ЗАМЕЧАНИЕ". A reportlab paragraph cannot space letters,
    so the label is drawn."""

    def __init__(self, text: str, color: str):
        super().__init__()
        self.text = text.upper()
        self.color = color
        self._height = _LABEL_PT * 1.55

    def wrap(self, available_width, available_height):
        return available_width, self._height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(colors.HexColor(self.color))
        line = self.canv.beginText(0, _LABEL_PT * 0.45)
        line.setFont(_HEAVY_FONT, _LABEL_PT)
        line.setCharSpace(_LABEL_TRACKING)
        line.textOut(self.text)
        self.canv.drawText(line)
        self.canv.restoreState()


def _box(
    label: str,
    lines: list[str],
    accent: str,
    bar: str,
    body: ParagraphStyle,
    formulas: _Formulas,
) -> Table:
    """The one shape every box beside the text takes: a bar down the left,
    a label in spaced capitals, the lines under it. No panel behind it.

    A callout about the whole record and a remark about one line differ in
    their colours alone — a remark is the reference's "ЗАМЕЧАНИЕ", grey bar
    and grey text; a callout carries its accent in the bar and the label.
    Whatever the bot adds of its own later is the same box in a tone of its
    own.

    reportlab has no such flowable, so it is a table of one cell — that is
    what gives a bar on one side only.
    """
    inside: list = [_Label(label, accent)]
    inside += [
        Paragraph(_line_markup(line, formulas, _BODY_PT), body) for line in lines
    ]
    table = Table([[inside]], colWidths=[_TEXT_WIDTH_PT], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(bar)),
                ("LEFTPADDING", (0, 0), (-1, -1), 18),
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
    accent = _CALLOUT_TONES.get(box.tone, _CALLOUT_TONES["info"])
    return _box(box.title, box.lines, accent, accent, styles["callout_body"], formulas)


def _remark(
    remark: Remark, formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> Table:
    """A box under the line it belongs to, in the quietest tone. Anything
    louder and a page of ordinary reading becomes a page of warnings."""
    return _box(
        remark.label, remark.lines, _MUTED, _BAR, styles["remark_body"], formulas,
    )


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
    """The thin rule the reference puts under its title and under each section
    heading. Quiet enough to separate without being furniture."""
    return HRFlowable(
        width=width,
        thickness=0.8,
        hAlign="CENTER",
        color=colors.HexColor(_HAIRLINE),
        spaceBefore=space_before,
        spaceAfter=space_after,
    )


def _section_rule() -> HRFlowable:
    """The broader, paler rule the reference sets between two sections."""
    return HRFlowable(
        width="100%",
        thickness=1.5,
        hAlign="CENTER",
        color=colors.HexColor(_SECTION_RULE),
        spaceBefore=8,
        spaceAfter=4,
    )


def _flowables(
    block: Block,
    formulas: _Formulas,
    styles: dict[str, ParagraphStyle],
    top_level: int = 1,
) -> list:
    """One parsed block as reportlab flowables, with no space around them —
    the space between blocks is the rhythm's, see _space_before."""
    if block.kind == "rule":
        # The seam between two pages of an album. A short thin line says "the
        # next page starts here" without shouting it.
        return [_hairline("35%")]

    if block.kind == "table":
        return [_table(block.rows, block.header, formulas, styles)]

    if block.kind == "heading":
        rank = _rank(block.level, top_level)
        style = styles[f"heading{rank}"]
        out = [Paragraph(_line_markup(block.text, formulas, style.fontSize), style)]
        if rank == 1:
            out.append(_hairline(space_before=3, space_after=8))
        return out

    if block.kind == "bullet":
        return [
            Paragraph(
                _line_markup(block.text, formulas, _BODY_PT),
                styles["bullet"],
                bulletText=block.marker or "•",
            )
        ]

    if block.kind == "note":
        return [Paragraph(_markup(block.text), styles["note"])]

    if block.kind == "math":
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


def _unit(
    parsed: list[Block],
    index: int,
    formulas: _Formulas,
    styles: dict[str, ParagraphStyle],
    top_level: int = 1,
) -> tuple[list[Block], int, list, str]:
    """The next thing set on the page: the blocks it is made of, where the one
    after it starts, its flowables, and the kind the rhythm knows it by.

    Mostly one block. A run of drawings is one row, and a graph or a matrix
    name with the table right after it is one row too.
    """
    block = parsed[index]

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

    if _is_name(block):
        paired = _pair(parsed, index + 1, formulas, styles, name=block)
        if paired is not None:
            return paired

    flowables = _flowables(block, formulas, styles, top_level)
    return [block], index + 1, flowables, block.kind


def _space_before(previous: str | None, kind: str, paragraph_break: bool) -> float:
    """How much space goes between a unit of kind `previous` and one of kind
    `kind`, `paragraph_break` saying whether a blank line stood between them.

    A heading carries its own space above and below it in its style: the
    space over a section is part of the heading, and a page that begins with
    one drops it rather than opening on a gap."""
    if previous is None or kind == "heading" or previous == "heading":
        return 0.0
    if kind == "math" and previous == "math":
        return _STACK_GAP
    if kind in _SET_APART or previous in _SET_APART:
        return _SET_APART_GAP
    if previous == "box":
        return _BOX_GAP
    if paragraph_break:
        return _PARAGRAPH_GAP
    if kind == "bullet" and previous == "bullet":
        return _ITEM_GAP
    return 0.0


def _fit(text: str, width: float, size: float) -> str:
    """`text` cut to `width` points, with an ellipsis where it was cut."""
    if pdfmetrics.stringWidth(text, _TEXT_FONT, size) <= width:
        return text
    while text and pdfmetrics.stringWidth(text + "…", _TEXT_FONT, size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _draw_furniture(page_canvas, number: int, total: int, running_title: str) -> None:
    """What a page carries besides the record.

    From the second page on, the record's title over the text: a printed page
    four has to say which lecture it belongs to. On every page of a record
    longer than one, its number — as "2 / 5" and not "с. 2", because inside a
    record "с. 2" already means the second photographed page, which is what a
    remark or a callout points at. A one-page record carries none of it.
    """
    if total < 2:
        return
    width, height = A4
    left, right = _MARGIN_PT, width - _MARGIN_PT
    page_canvas.saveState()
    page_canvas.setFont(_TEXT_FONT, _FURNITURE_PT)
    page_canvas.setFillColor(colors.HexColor(_MUTED))
    if number > 1 and running_title:
        baseline = height - 12 * mm
        page_canvas.drawString(
            left, baseline, _fit(running_title, right - left, _FURNITURE_PT)
        )
        page_canvas.setStrokeColor(colors.HexColor(_HAIRLINE))
        page_canvas.setLineWidth(0.8)
        page_canvas.line(left, baseline - 2.2 * mm, right, baseline - 2.2 * mm)
    page_canvas.drawCentredString(width / 2, 10 * mm, f"{number} / {total}")
    page_canvas.restoreState()


class _PagedCanvas(rl_canvas.Canvas):
    """A canvas that holds every page back until the last one is known.

    reportlab finishes a page the moment its frame is full, and "2 / 5" needs
    the 5 — so each page's state is kept, and the furniture is drawn over all
    of them when the document is saved.
    """

    def __init__(self, *args, running_title: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._running_title = running_title
        self._held: list[dict] = []

    def showPage(self):  # noqa: N802 — reportlab's name
        self._held.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._held)
        for number, state in enumerate(self._held, 1):
            self.__dict__.update(state)
            _draw_furniture(self, number, total, self._running_title)
            rl_canvas.Canvas.showPage(self)
        rl_canvas.Canvas.save(self)


def render(
    title: str,
    markdown: str,
    subtitle: str | None = None,
    callouts: Sequence[Callout] = (),
    byline: str | None = None,
    remarks: Sequence[Remark] = (),
) -> bytes:
    """A record as PDF bytes. Never raises on the content of the record."""
    _register_fonts()
    styles = _styles()
    buffer = io.BytesIO()

    # A first heading repeating the title is the commonest shape a page takes:
    # the record is called "Графы" and the page is headed "Графы". Printing
    # both says nothing twice.
    wanted = title.strip().casefold()
    parsed = [
        block
        for block in blocks(markdown)
        if not (block.kind == "heading" and block.text.strip().casefold() == wanted)
    ]
    levels = [block.level for block in parsed if block.kind == "heading"]
    top_level = min(levels) if levels else 1

    with tempfile.TemporaryDirectory(prefix="conspectium-pdf-") as directory:
        formulas = _Formulas(directory)
        story: list = [
            Paragraph(_markup(title), styles["title"]),
            _hairline(space_after=0),
        ]
        # What was written in the margin — whose lecture, which date — and
        # then the facts of the record. Under the title, where a reader looks
        # for them, not in the body, where they read as the author speaking.
        facts = [(byline, "byline"), (subtitle, "meta")]
        if any(line for line, _ in facts):
            story.append(Spacer(1, 7))
        for line, style in facts:
            if line:
                story.append(Paragraph(_markup(line), styles[style]))
        story.append(Spacer(1, 16))

        for box in callouts:
            # Above the record, not below it: these say how far the text that
            # follows can be trusted, and that is worth knowing first.
            story.append(_callout(box, formulas, styles))
            story.append(Spacer(1, 10))
        if callouts:
            story.append(Spacer(1, 4))

        pending = list(remarks)
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
        index = 0
        while index < len(parsed):
            if parsed[index].kind == "gap":
                paragraph_break = True
                index += 1
                continue

            members, index, flowables, kind = _unit(
                parsed, index, formulas, styles, top_level
            )
            space = _space_before(previous, kind, paragraph_break)
            paragraph_break = False

            # A graph's spec is not text a reader sees: an anchor "2" found in
            # "1-2, 2-3" pinned a remark about a word to a drawing.
            attached = [
                remark
                for remark in pending
                if remark.anchor
                and any(m.kind != "graph" and remark.anchor in m.text for m in members)
            ]
            group = list(flowables)
            for remark in attached:
                # A remark stays with the line it explains: never the first
                # thing on a page whose line was the last on the one before.
                pending.remove(remark)
                group += [Spacer(1, 4), _remark(remark, formulas, styles)]

            # A new top-level section after something else is set off by the
            # broader rule the reference puts between two of its sections.
            if (
                kind == "heading"
                and previous is not None
                and not held
                and _rank(members[0].level, top_level) == 1
            ):
                group = [_section_rule()] + group

            if held:
                group = held + ([Spacer(1, space)] if space else []) + group
                held = []
            elif space:
                story.append(Spacer(1, space))

            previous = "box" if attached else kind
            if kind == "heading":
                held = group
                continue
            # A table is kept whole as well: split across two pages, a matrix
            # loses its column names on the second.
            if len(group) > 1 or kind == "table":
                story.append(KeepTogether(group))
            else:
                story.extend(group)

        # A heading with nothing after it has nothing to be kept with.
        story.extend(held)

        # A remark whose anchor was never found is still worth reading; it
        # goes at the end rather than nowhere.
        for remark in pending:
            story.append(Spacer(1, _SET_APART_GAP))
            story.append(_remark(remark, formulas, styles))

        SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=_MARGIN_PT - _FRAME_PADDING_PT,
            rightMargin=_MARGIN_PT - _FRAME_PADDING_PT,
            topMargin=_TOP_PT - _FRAME_PADDING_PT,
            bottomMargin=_BOTTOM_PT - _FRAME_PADDING_PT,
            title=title,
        ).build(
            story,
            canvasmaker=functools.partial(_PagedCanvas, running_title=title),
        )

    return buffer.getvalue()
