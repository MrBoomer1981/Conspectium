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
import os
import re
import tempfile
from dataclasses import dataclass
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")  # no display on a server; must precede pyplot
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

logger = logging.getLogger(__name__)

# Rendered at this DPI, then scaled to points. High enough that a formula
# stays sharp when the PDF is zoomed on a phone.
_DPI = 300
_BODY_PT = 10.5

# ── Parsing ──────────────────────────────────────────────────────────────────

# $...$ with no newline inside. A backslash-escaped \$ is left alone: it is a
# literal dollar sign, not the start of a formula.
_MATH_RE = re.compile(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^\s*[-*•]\s+(.*)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


@dataclass
class Block:
    kind: str  # "heading" | "bullet" | "text" | "math" | "note" | "gap"
    text: str = ""
    level: int = 0


def _is_whole_formula(line: str) -> str | None:
    """The LaTeX of a line that is nothing but one formula, else None. Such a
    line is set on its own, centred, the way it sat on the page."""
    stripped = line.strip()
    if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
        return stripped[2:-2].strip()
    match = _MATH_RE.fullmatch(stripped)
    return match.group(1).strip() if match else None


def blocks(markdown: str) -> list[Block]:
    """Split a record into renderable pieces.

    Every line becomes its own block rather than being joined into flowing
    paragraphs. A lecture note is written line by line — a definition, a
    formula, a consequence — and gluing consecutive lines together produces
    sentences the author never wrote.
    """
    out: list[Block] = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            # Collapse runs of blank lines: one gap is a gap.
            if out and out[-1].kind != "gap":
                out.append(Block("gap"))
            continue

        heading = _HEADING_RE.match(line.strip())
        if heading:
            out.append(
                Block("heading", heading.group(2).strip(), min(len(heading.group(1)), 6))
            )
            continue

        formula = _is_whole_formula(line)
        if formula:
            out.append(Block("math", formula))
            continue

        bullet = _BULLET_RE.match(line)
        if bullet:
            out.append(Block("bullet", bullet.group(1).strip()))
            continue

        stripped = line.strip()
        # "[схема: граф с петлёй]" — the model's note that something on the
        # page is a drawing. We never store photos, so it stays a remark.
        if stripped.startswith("[") and stripped.endswith("]"):
            out.append(Block("note", stripped[1:-1].strip()))
            continue

        out.append(Block("text", stripped))

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


def _formula_png(latex: str, size_pt: float) -> tuple[bytes, float, float]:
    """One formula as a transparent PNG, with its size in points. Raises when
    mathtext cannot read the LaTeX — callers fall back to the source text."""
    figure = plt.figure(figsize=(0.01, 0.01))
    try:
        figure.text(0, 0, f"${latex}$", fontsize=size_pt)
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
            "title", parent=base, fontName="DejaVu-Bold", fontSize=16,
            leading=20, spaceAfter=10,
        ),
        "heading": ParagraphStyle(
            "heading", parent=base, fontName="DejaVu-Bold", fontSize=12.5,
            leading=17, spaceBefore=8, spaceAfter=3,
        ),
        "body": base,
        "bullet": ParagraphStyle(
            "bullet", parent=base, leftIndent=10, bulletIndent=2, spaceAfter=1
        ),
        "note": ParagraphStyle(
            "note", parent=base, fontName="DejaVu-Oblique", textColor="#666666"
        ),
        "math": ParagraphStyle("math", parent=base, alignment=TA_CENTER),
    }


def render(title: str, markdown: str, subtitle: str | None = None) -> bytes:
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

        for block in blocks(markdown):
            if block.kind == "gap":
                story.append(Spacer(1, 5))
            elif block.kind == "heading":
                story.append(
                    Paragraph(
                        _line_markup(block.text, formulas, 12.5), styles["heading"]
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
                    story.append(Spacer(1, 3))
                    story.append(image)
                    story.append(Spacer(1, 3))
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
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=title,
        ).build(story)

    return buffer.getvalue()
