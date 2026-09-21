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
_GRAPH_WIDTH_PT = 150.0
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
_GRAPH_RE = re.compile(r"^(?:граф|graph)\s*:\s*(.*)$", re.IGNORECASE)
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
class Block:
    kind: str  # heading | bullet | text | math | note | gap | rule | table | graph
    text: str = ""
    level: int = 0
    rows: list[list[str]] = field(default_factory=list)
    header: bool = False


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
                Block("graph", drawing.group(1).strip())
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


# mathtext is not LaTeX, and the model writes LaTeX. These four commands are
# the ones it reaches for that mathtext rejects outright, taking the whole
# formula down with them: a page that said \sum\limits_{i=1}^p printed as its
# own source while the same sum written \sum_{i=1}^p drew perfectly. Each one
# either has no effect on how mathtext lays a formula out or has a synonym it
# does know, so dropping it costs nothing.
#
# The boundary is (?![A-Za-z]), not \b: "_" counts as a word character, so
# `limits\b` never matches `\limits_{i=1}` — and \lim and \limsup must
# survive untouched.
_COMMAND_END = r"(?![A-Za-z])"
_UNSUPPORTED_RE = re.compile(
    rf"\\(?:limits|nolimits|displaystyle|textstyle){_COMMAND_END}"
)
_MBOX_RE = re.compile(rf"\\mbox{_COMMAND_END}")
_THIN_SPACE_RE = re.compile(r"\\[,!:;]")


def for_mathtext(latex: str) -> str:
    """LaTeX as close to it as matplotlib's mathtext will accept."""
    latex = _UNSUPPORTED_RE.sub("", latex)
    latex = _MBOX_RE.sub(r"\\text", latex)
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
    vertices: list[str], edges: list[tuple[str, str]], directed: bool
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
    scale = _GRAPH_WIDTH_PT / width
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

    def inline(self, latex: str, size_pt: float) -> str | None:
        """An <img> tag for use inside a paragraph, or None if unrenderable."""
        key = (latex, size_pt)
        if key not in self._cache:
            try:
                data, width, height = _formula_png(latex, size_pt)
            except Exception:
                logger.debug("mathtext could not render %r", latex)
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
        except Exception:
            logger.debug("mathtext could not render %r", latex)
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
        leading=_BODY_PT * 1.6,
        spaceAfter=1,
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
            "bullet", parent=base, leftIndent=10, bulletIndent=2, spaceAfter=1
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


def _graph(spec: str) -> Image | None:
    """A drawn graph, or None when the spec does not read as one."""
    parsed = parse_graph(spec)
    if parsed is None:
        return None
    try:
        data, width, height = _graph_png(*parsed)
    except Exception:
        logger.exception("could not draw the graph %r", spec)
        return None
    image = Image(io.BytesIO(data), width=width, height=height)
    image.hAlign = "CENTER"
    return image


def render(
    title: str,
    markdown: str,
    subtitle: str | None = None,
    callouts: Sequence[Callout] = (),
) -> bytes:
    """A record as PDF bytes. Never raises on the content of the record."""
    _register_fonts()
    styles = _styles()
    buffer = io.BytesIO()

    with tempfile.TemporaryDirectory(prefix="conspectium-pdf-") as directory:
        formulas = _Formulas(directory)
        story: list = [Paragraph(_markup(title), styles["title"])]
        if subtitle:
            story.append(Paragraph(_markup(subtitle), styles["note"]))
            story.append(Spacer(1, 6))
        for box in callouts:
            # Above the record, not below it: these say how far the text that
            # follows can be trusted, and that is worth knowing first.
            story.append(_callout(box, formulas, styles))
            story.append(Spacer(1, 8))

        for block in blocks(markdown):
            if block.kind == "gap":
                story.append(Spacer(1, 5))
            elif block.kind == "rule":
                # The seam between two pages of an album. A thin short line
                # says "the next page starts here" without shouting it.
                story.append(Spacer(1, 7))
                story.append(
                    HRFlowable(
                        width="35%", thickness=0.6, hAlign="CENTER",
                        color=colors.HexColor("#cccccc"),
                    )
                )
                story.append(Spacer(1, 7))
            elif block.kind == "table":
                story.append(Spacer(1, 4))
                story.append(_table(block.rows, block.header, formulas, styles))
                story.append(Spacer(1, 6))
            elif block.kind == "graph":
                image = _graph(block.text)
                if image is not None:
                    story.append(Spacer(1, 4))
                    story.append(image)
                    story.append(Spacer(1, 6))
                else:
                    # Same bargain as an unreadable formula: worse to look at
                    # than a drawing, far better than a silently missing one.
                    story.append(
                        Paragraph(_markup(f"граф: {block.text}"), styles["note"])
                    )
            elif block.kind == "heading":
                style = styles[f"heading{max(1, min(block.level, 3))}"]
                story.append(
                    Paragraph(
                        _line_markup(block.text, formulas, style.fontSize), style
                    )
                )
            elif block.kind == "bullet":
                story.append(
                    Paragraph(
                        _line_markup(block.text, formulas, _BODY_PT),
                        styles["bullet"],
                        bulletText="•",
                    )
                )
            elif block.kind == "note":
                story.append(Paragraph(_markup(block.text), styles["note"]))
            elif block.kind == "math":
                image = formulas.display(block.text, _BODY_PT + 1.5)
                if image is not None:
                    image.hAlign = "CENTER"
                    story.append(Spacer(1, 7))
                    story.append(image)
                    story.append(Spacer(1, 7))
                else:
                    story.append(
                        Paragraph(_markup(f"${block.text}$"), styles["math"])
                    )
            else:
                story.append(
                    Paragraph(
                        _line_markup(block.text, formulas, _BODY_PT), styles["body"]
                    )
                )

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
