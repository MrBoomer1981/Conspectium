"""A record rendered as a PDF, formulas included.

Recognised lecture notes are full of LaTeX — `$\\sum_{i=1}^{p} \\rho(v_i) = 2q$`
reads as noise until it is drawn. Formulas go through matplotlib's mathtext,
the surrounding text through reportlab.

Two halves on purpose. `blocks()` is a pure parser with no rendering in it, so
the reading of a page can be pinned down exactly by tests; `render()` turns
those blocks into a document. Neither ever raises on bad input: a formula
mathtext cannot read stays on the page as its own source, the same way
parse_response returns None rather than exploding.
"""

from __future__ import annotations

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
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    HRFlowable,
    Image,
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
_BODY_PT = 10.5
_MARGIN_MM = 18
_TEXT_WIDTH_PT = A4[0] - 2 * _MARGIN_MM * mm
_INK = "#333333"
_GRAPH_WIDTH_PT = 135.0
_TABLE_PT = 9.0
# Four steps, so a section is told from a subsection at a glance. The level
# blocks() reads was being parsed and thrown away: every heading printed at
# one size, which made "#" and "###" the same thing on the page.
_HEADING_PT = {1: 14.0, 2: 12.5, 3: 11.0}
_HEADING_SPACE_BEFORE = {1: 15, 2: 11, 3: 9}
# background, and the accent used for the left edge and the title
_CALLOUT_TONES = {
    "info": ("#eef3fa", "#3f6f9f"),
    "warning": ("#fdf4e6", "#a8742c"),
}
_HAIRLINE = "#d5d5d5"
_REMARK_ACCENT = "#9aa5b1"
# More than three drawings in a row and none of them is readable.
_FIGURES_PER_ROW = 3
# Padding either side of a drawing inside its cell of the row.
_FIGURE_GAP_PT = 16.0
_MIN_COLUMN_PT = 20.0
_MAX_COLUMN_PT = 120.0

# ── Parsing ──────────────────────────────────────────────────────────────────

# $...$ with no newline inside. A backslash-escaped \$ is left alone: it is a
# literal dollar sign, not the start of a formula.
_MATH_RE = re.compile(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^\s*[-*•]\s+(.*)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# The seam _assemble writes between two pages of an album.
_RULE_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})$")
# A markdown table row, and the "|---|:--|" line that marks the row above it
# as a header rather than data.
_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_ROW_SEPARATOR_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
# "[граф: 1-2, 2-3]" inside the square brackets of a note.
# "[граф: 1-2]", or "[граф Ориентированный: 1->2]" with a caption.
_GRAPH_RE = re.compile(
    r"^(?:граф|graph)\s*([^:]{0,40}?)\s*:\s*(.*)$", re.IGNORECASE
)
_DIRECTED_RE = re.compile(r"\s*(?:-+>|→)\s*")
_UNDIRECTED_RE = re.compile(r"\s*[-–—]\s*")

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


def _is_whole_formula(line: str) -> str | None:
    """The LaTeX of a line that is nothing but one formula, else None. Such a
    line is set on its own, centred, the way it sat on the page."""
    stripped = line.strip()
    if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
        return stripped[2:-2].strip()
    match = _MATH_RE.fullmatch(stripped)
    return match.group(1).strip() if match else None


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
            header = position > start
            continue
        rows.append(
            [cell.strip() for cell in lines[position].strip().strip("|").split("|")]
        )
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
        parts.append(("math", match.group(1).strip()))
        position = match.end()
    if position < len(text):
        parts.append(("text", text[position:]))
    return parts


# ── Rendering ────────────────────────────────────────────────────────────────


def _font_path(name: str) -> str:
    return os.path.join(
        os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf", name
    )


_FONTS_READY = False


def _register_fonts() -> None:
    """Cyrillic needs a real TTF — reportlab's built-ins are Latin only.
    DejaVu ships inside matplotlib, so nothing has to live in the repo."""
    global _FONTS_READY
    if _FONTS_READY:
        return
    pdfmetrics.registerFont(TTFont("DejaVu", _font_path("DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", _font_path("DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Oblique", _font_path("DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFontFamily(
        "DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique"
    )
    _FONTS_READY = True


def warm_up() -> None:
    """Build matplotlib's font cache and register the fonts ahead of the first
    request. Both are one-off costs of a few seconds; paying them at startup
    keeps them out of someone's first photo."""
    try:
        _register_fonts()
        _formula_png("x^2", _BODY_PT)
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


def _formula_png(latex: str, size_pt: float) -> tuple[bytes, float, float]:
    """One formula as a transparent PNG, with its size in points. Raises when
    mathtext cannot read the LaTeX — callers fall back to the source text."""
    figure = plt.figure(figsize=(0.01, 0.01))
    try:
        figure.text(0, 0, f"${for_mathtext(latex)}$", fontsize=size_pt)
        buffer = io.BytesIO()
        figure.savefig(
            buffer,
            format="png",
            dpi=_DPI,
            bbox_inches="tight",
            pad_inches=0.01,
            transparent=True,
        )
    finally:
        plt.close(figure)
    data = buffer.getvalue()
    # Pillow is already a dependency, used here only to measure.
    from PIL import Image as PILImage

    width, height = PILImage.open(io.BytesIO(data)).size
    scale = 72.0 / _DPI
    return data, width * scale, height * scale


def _graph_png(
    vertices: list[str],
    edges: list[tuple[str, str]],
    directed: bool,
    width_pt: float = _GRAPH_WIDTH_PT,
) -> tuple[bytes, float, float]:
    """A graph drawn as a picture, with its size in points. Raises on anything
    matplotlib dislikes; the caller falls back to printing the spec."""
    count = len(vertices)
    if count == 1:
        positions = {vertices[0]: (0.0, 0.0)}
    else:
        # Vertices on a circle. A lecture-note graph has a handful of them, and
        # a layout that is the same every time beats a prettier one that moves
        # between runs of the same page.
        #
        placed = _placement(vertices)
        positions = {
            vertex: (
                math.cos(math.pi / 2 - 2 * math.pi * i / count),
                math.sin(math.pi / 2 - 2 * math.pi * i / count),
            )
            for i, vertex in enumerate(placed)
        }
    node = 0.17

    figure, axes = plt.subplots(figsize=(2.4, 2.4))
    try:
        axes.set_aspect("equal")
        axes.axis("off")
        for tail, head in edges:
            x1, y1 = positions[tail]
            x2, y2 = positions[head]
            if tail == head:
                _draw_loop(axes, x1, y1, node)
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
                    arrowprops={"arrowstyle": "-|>", "lw": 1.1, "color": _INK},
                )
            else:
                axes.plot(
                    [start[0], finish[0]], [start[1], finish[1]],
                    lw=1.1, color=_INK, zorder=1,
                )
        for vertex, (x, y) in positions.items():
            axes.add_patch(
                plt.Circle((x, y), node, facecolor="white", edgecolor=_INK,
                           lw=1.1, zorder=2)
            )
            axes.text(x, y, vertex, ha="center", va="center",
                      fontsize=9, color=_INK, zorder=3)
        axes.set_xlim(-1.6, 1.6)
        axes.set_ylim(-1.6, 1.6)

        buffer = io.BytesIO()
        figure.savefig(
            buffer, format="png", dpi=_DPI, bbox_inches="tight",
            pad_inches=0.02, transparent=True,
        )
    finally:
        plt.close(figure)

    from PIL import Image as PILImage

    data = buffer.getvalue()
    width, height = PILImage.open(io.BytesIO(data)).size
    scale = width_pt / width
    return data, width * scale, height * scale


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


def _draw_loop(axes, x: float, y: float, node: float) -> None:
    """A loop sits outside its vertex, pointing away from the middle of the
    picture, so it cannot be mistaken for an edge to a neighbour."""
    away = math.atan2(y, x) if (x or y) else math.pi / 2
    loop = node * 0.95
    axes.add_patch(
        plt.Circle(
            (x + (node + loop * 0.6) * math.cos(away),
             y + (node + loop * 0.6) * math.sin(away)),
            loop, fill=False, lw=1.1, edgecolor=_INK, zorder=1,
        )
    )


def _markup(text: str) -> str:
    """Plain text as reportlab mini-HTML. Escaping comes first: a page that
    says "A < B" would otherwise be read as a tag and swallow the rest."""
    return _BOLD_RE.sub(r"<b>\1</b>", escape(text))


class _Formulas:
    """Renders formulas for one document, caching by (latex, size) — a symbol
    repeated down a page is drawn once — and writing the inline ones to a
    temporary directory, because reportlab's <img> tag takes a path, not bytes.
    """

    def __init__(self, directory: str):
        self._directory = directory
        self._cache: dict[tuple[str, float], tuple[str, float, float]] = {}
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
                data, width, height = _formula_png(latex, size_pt)
            except Exception as exc:
                self._refused(latex, exc)
                return None
            self._count += 1
            path = os.path.join(self._directory, f"f{self._count}.png")
            with open(path, "wb") as handle:
                handle.write(data)
            self._cache[key] = (path, width, height)
        path, width, height = self._cache[key]
        # Nudged below the baseline so the formula sits on the line of text
        # rather than floating above it.
        return (
            f'<img src="{path}" width="{width:.2f}" height="{height:.2f}" '
            f'valign="-{height * 0.22:.2f}"/>'
        )

    def display(self, latex: str, size_pt: float) -> Image | None:
        try:
            data, width, height = _formula_png(latex, size_pt)
        except Exception as exc:
            self._refused(latex, exc)
            return None
        return Image(io.BytesIO(data), width=width, height=height)


def _line_markup(text: str, formulas: _Formulas, size_pt: float) -> str:
    """One line of a record as reportlab markup, formulas drawn in place."""
    pieces: list[str] = []
    for kind, value in split_inline(text):
        if kind == "text":
            pieces.append(_markup(value))
            continue
        tag = formulas.inline(value, size_pt)
        # Unreadable LaTeX stays visible as its own source: worse to look at
        # than a drawn formula, far better than a silently missing one.
        pieces.append(tag if tag else _markup(f"${value}$"))
    return "".join(pieces)


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "body",
        fontName="DejaVu",
        fontSize=_BODY_PT,
        leading=_BODY_PT * 1.7,
        # Rule 8 of the prompt joins lines that continue a sentence, so a text
        # block is now a paragraph rather than one written line. Paragraphs
        # need air between them; written lines did not.
        spaceAfter=4,
    )
    return {
        "title": ParagraphStyle(
            "title", parent=base, fontName="DejaVu-Bold", fontSize=17,
            leading=21, spaceAfter=12,
        ),
        **{
            f"heading{level}": ParagraphStyle(
                f"heading{level}", parent=base, fontName="DejaVu-Bold",
                fontSize=size, leading=size * 1.35,
                spaceBefore=_HEADING_SPACE_BEFORE[level], spaceAfter=size * 0.3,
            )
            for level, size in _HEADING_PT.items()
        },
        "byline": ParagraphStyle(
            "byline", parent=base, fontName="DejaVu-Oblique",
            fontSize=_BODY_PT, textColor="#555555", spaceAfter=2,
        ),
        "callout_title": ParagraphStyle(
            "callout_title", parent=base, fontName="DejaVu-Bold",
            fontSize=_BODY_PT, spaceAfter=4,
        ),
        "callout_body": ParagraphStyle(
            "callout_body", parent=base, fontSize=_BODY_PT - 0.5,
            leading=(_BODY_PT - 0.5) * 1.45, spaceAfter=1,
        ),
        "body": base,
        "bullet": ParagraphStyle(
            "bullet", parent=base, leftIndent=16, bulletIndent=5, spaceAfter=3
        ),
        "remark_label": ParagraphStyle(
            "remark_label", parent=base, fontName="DejaVu-Bold",
            fontSize=_BODY_PT - 2.5, leading=(_BODY_PT - 2.5) * 1.3, spaceAfter=2,
        ),
        "remark_body": ParagraphStyle(
            "remark_body", parent=base, fontSize=_BODY_PT - 1,
            leading=(_BODY_PT - 1) * 1.45, textColor="#5a6570", spaceAfter=1,
        ),
        "caption": ParagraphStyle(
            "caption", parent=base, fontSize=_BODY_PT - 1.5,
            leading=(_BODY_PT - 1.5) * 1.3, alignment=TA_CENTER,
            textColor="#555555", spaceAfter=0,
        ),
        "note": ParagraphStyle(
            "note", parent=base, fontName="DejaVu-Oblique", textColor="#666666"
        ),
        "math": ParagraphStyle("math", parent=base, alignment=TA_CENTER),
        "cell": ParagraphStyle(
            "cell", parent=base, fontSize=_TABLE_PT, leading=_TABLE_PT * 1.25,
            alignment=TA_CENTER, spaceAfter=0,
        ),
    }


def _column_widths(rows: list[list[str]]) -> list[float]:
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
            pdfmetrics.stringWidth(row[column], "DejaVu", _TABLE_PT) for row in rows
        )
        widths.append(min(max(longest + 10, _MIN_COLUMN_PT), _MAX_COLUMN_PT))
    total = sum(widths)
    if total > _TEXT_WIDTH_PT:
        widths = [width * _TEXT_WIDTH_PT / total for width in widths]
    return widths


def _table(
    rows: list[list[str]],
    header: bool,
    formulas: _Formulas,
    styles: dict[str, ParagraphStyle],
) -> Table:
    """A markdown table as a drawn one."""
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
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8c8c8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")))
    table.setStyle(TableStyle(style))
    return table


def _callout(
    box: Callout, formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> Table:
    """One box: a tinted panel with a coloured edge down its left side.

    reportlab has no such flowable, so it is a table of one cell — that is
    what gives a background and a rule on one side only.
    """
    background, accent = _CALLOUT_TONES.get(box.tone, _CALLOUT_TONES["info"])
    inside: list = [
        Paragraph(
            f'<font color="{accent}">{_markup(box.title)}</font>',
            styles["callout_title"],
        )
    ]
    inside += [
        Paragraph(_line_markup(line, formulas, _BODY_PT - 0.5), styles["callout_body"])
        for line in box.lines
    ]
    table = Table([[inside]], colWidths=[_TEXT_WIDTH_PT], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(background)),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor(accent)),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _figure_width(count: int) -> float:
    """How wide each drawing in a row of `count` may be.

    A drawing has a natural size, and beyond a certain number per row that
    size stops fitting — the row has to give way to the page, not the other
    way round.
    """
    return min(_GRAPH_WIDTH_PT, (_TEXT_WIDTH_PT - _FIGURE_GAP_PT * count) / count)


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
        cell: list = [drawn]
        if caption:
            cell.append(Spacer(1, 3))
            cell.append(Paragraph(_markup(caption), styles["caption"]))
        cells.append(cell)

    table = Table([cells], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), _FIGURE_GAP_PT / 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), _FIGURE_GAP_PT / 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [Spacer(1, 6), table, Spacer(1, 8)]


def _remark(
    remark: Remark, formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> Table:
    """A note set beside the line it belongs to: a rule down the left and grey
    text, with no panel behind it. Anything louder and a page of ordinary
    reading becomes a page of warnings."""
    inside: list = [
        Paragraph(
            f'<font color="{_REMARK_ACCENT}">{_markup(remark.label)}</font>',
            styles["remark_label"],
        )
    ]
    inside += [
        Paragraph(_line_markup(line, formulas, _BODY_PT - 1), styles["remark_body"])
        for line in remark.lines
    ]
    table = Table([[inside]], colWidths=[_TEXT_WIDTH_PT - 14], hAlign="RIGHT")
    table.setStyle(
        TableStyle(
            [
                ("LINEBEFORE", (0, 0), (0, -1), 1.6, colors.HexColor(_REMARK_ACCENT)),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


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


def _hairline(width: str = "100%") -> HRFlowable:
    """The thin rule the target layout puts under a title and under each
    top-level heading. Quiet enough to separate without being furniture."""
    return HRFlowable(
        width=width,
        thickness=0.5,
        hAlign="CENTER",
        color=colors.HexColor(_HAIRLINE),
        spaceBefore=0,
        spaceAfter=0,
    )


def _flowables(
    block: Block, formulas: _Formulas, styles: dict[str, ParagraphStyle]
) -> list:
    """One parsed block as reportlab flowables. Graphs are not here: they are
    gathered into rows by the caller, which needs to see several at once."""
    if block.kind == "gap":
        return [Spacer(1, 5)]

    if block.kind == "rule":
        # The seam between two pages of an album. A short thin line says "the
        # next page starts here" without shouting it.
        return [Spacer(1, 7), _hairline("35%"), Spacer(1, 7)]

    if block.kind == "table":
        return [
            Spacer(1, 4),
            _table(block.rows, block.header, formulas, styles),
            Spacer(1, 6),
        ]

    if block.kind == "heading":
        level = max(1, min(block.level, 3))
        style = styles[f"heading{level}"]
        out = [Paragraph(_line_markup(block.text, formulas, style.fontSize), style)]
        if level == 1:
            out += [_hairline(), Spacer(1, 6)]
        return out

    if block.kind == "bullet":
        return [
            Paragraph(
                _line_markup(block.text, formulas, _BODY_PT),
                styles["bullet"],
                bulletText="•",
            )
        ]

    if block.kind == "note":
        return [Paragraph(_markup(block.text), styles["note"])]

    if block.kind == "math":
        image = formulas.display(block.text, _BODY_PT + 1.5)
        if image is None:
            return [Paragraph(_markup(f"${block.text}$"), styles["math"])]
        image.hAlign = "CENTER"
        return [Spacer(1, 7), image, Spacer(1, 7)]

    return [Paragraph(_line_markup(block.text, formulas, _BODY_PT), styles["body"])]


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

    with tempfile.TemporaryDirectory(prefix="conspectium-pdf-") as directory:
        formulas = _Formulas(directory)
        story: list = [Paragraph(_markup(title), styles["title"]), _hairline()]
        if byline:
            # What was written in the margin rather than in the note: whose
            # lecture it was, which date, which page. Under the title, where a
            # reader looks for it — not in the body, where it reads as
            # something the author was saying.
            story.append(Spacer(1, 5))
            story.append(Paragraph(_markup(byline), styles["byline"]))
        if subtitle:
            if not byline:
                story.append(Spacer(1, 5))
            story.append(Paragraph(_markup(subtitle), styles["note"]))
        story.append(Spacer(1, 10))

        for box in callouts:
            # Above the record, not below it: these say how far the text that
            # follows can be trusted, and that is worth knowing first.
            story.append(_callout(box, formulas, styles))
            story.append(Spacer(1, 8))

        pending = list(remarks)
        index = 0
        while index < len(parsed):
            if parsed[index].kind == "graph":
                figures: list[tuple[str, str]] = []
                while (
                    index < len(parsed)
                    and parsed[index].kind == "graph"
                    and len(figures) < _FIGURES_PER_ROW
                ):
                    figures.append((parsed[index].caption, parsed[index].text))
                    index += 1
                story.extend(_figure_row(figures, styles))
                continue

            block = parsed[index]
            story.extend(_flowables(block, formulas, styles))
            for remark in [r for r in pending if r.anchor and r.anchor in block.text]:
                story.append(_remark(remark, formulas, styles))
                story.append(Spacer(1, 4))
                pending.remove(remark)
            index += 1

        # A remark whose anchor was never found is still worth reading; it
        # goes at the end rather than nowhere.
        for remark in pending:
            story.append(Spacer(1, 4))
            story.append(_remark(remark, formulas, styles))

        SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=_MARGIN_MM * mm,
            rightMargin=_MARGIN_MM * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=title,
        ).build(story)

    return buffer.getvalue()
