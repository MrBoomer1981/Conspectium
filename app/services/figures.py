"""A drawing cut out of the page it was drawn on.

Recognition describes a drawing it cannot write down as data as one line,
"[схема: …]", and from prompts-v8.md on it names the drawing's frame on the
photograph as well. This module cuts the drawing out of the compressed image
the model saw, keeps the darkness of its ink and nothing else of the
photograph, and after the composing stage sets it back at the line that
describes it. Nothing here calls a model or touches the database.

Why the page and not a redrawing: a sketch redrawn from what the model says
about it is the model's picture of the topic rather than the author's — the
very place it invents. A graph, which is data, is still drawn from the data
(pdf.blocks).
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

# "[схема: …]": a drawing recognition could only describe. Its words may run
# over several lines; a bracket never nests inside them.
_SCHEME_RE = re.compile(r"\[\s*схема\s*:\s*([^\[\]]*?)\s*\]", re.IGNORECASE)

# A frame is widened by this share of the photo's long side before it is cut:
# the model draws its frames tight, and a stroke cut in half is worse than a
# margin of paper.
_MARGIN = 0.015
# Narrower than this share of a side, a frame holds a symbol rather than a
# drawing; larger than this share of the page, it holds the text round the
# drawing as well, and the record would print the page twice.
_MIN_SIDE = 0.04
_MAX_AREA = 0.6

# The page's tones as a share of the paper's own light at the spot. Darker
# than _INK is ink, lighter than _PAPER is paper, and between them — a
# notebook's grid, a faint stroke — a smooth step, so a grid stays faint
# rather than breaking into dashes. Set on the notebook of the CEO's
# reference lecture, squared paper lit and in a hand's shadow: there the grid
# could be told from the ink neither by its colour nor by its width, only
# kept faint.
_INK = 0.30
_PAPER = 0.78
# A stroke: what the drawing is trimmed to, with _PAD_PX of the page round it.
_STROKE = 0.6
_PAD_PX = 16
# The cut-out fades into the page over its last pixels, so it does not stand
# on the document as a pasted rectangle of squared paper.
_FADE_PX = 12
# Fewer stroke pixels than this, and there is no drawing in the frame.
_MIN_STROKE_PX = 40


@dataclass
class Cutout:
    """A drawing cut out of a page: the words of the line that described it,
    and the darkness of its ink as a greyscale PNG, 255 the darkest. Colour is
    the document's to give it."""

    words: str
    png: bytes


def _words(text: str) -> str:
    return " ".join(text.split())


def count(markdown: str) -> int:
    """How many drawings the text only describes."""
    return len(_SCHEME_RE.findall(markdown))


def cut(image_bytes: bytes, markdown: str, frames: list) -> list[Cutout]:
    """The drawings of one page, cut out of the image the model saw.

    `frames` pairs with the "[схема: …]" lines of `markdown` in order — the
    prompt asks for one frame a line. When the two counts differ the pairing
    would be a guess, and a drawing at the wrong line is worse than none, so
    nothing is cut. Never raises: a drawing that cannot be cut stays the line
    that describes it."""
    lines = _SCHEME_RE.findall(markdown)
    if not lines or not frames:
        return []
    if len(lines) != len(frames):
        logger.info(
            "figures: %d drawings described, %d frames given, none cut",
            len(lines),
            len(frames),
        )
        return []
    try:
        with Image.open(io.BytesIO(image_bytes)) as opened:
            page = opened.convert("L")
    except Exception:
        logger.warning("figures: the page could not be opened", exc_info=True)
        return []
    out: list[Cutout] = []
    for words, frame in zip(lines, frames):
        try:
            png = _cut_one(page, frame)
        except Exception:
            logger.warning("figures: a drawing could not be cut", exc_info=True)
            png = None
        if png is not None:
            out.append(Cutout(_words(words), png))
    return out


def place(markdown: str, cutouts: list[Cutout]) -> tuple[str, list[tuple[int, bytes]]]:
    """Each cut-out set back at the line that describes it: the first
    "[схема: …]" with its words becomes "[рисунок N: …]", N through the whole
    record in order. Matched by the words rather than by position, because the
    composing stage stands between the cutting and the placing: a line it
    reworded keeps no drawing, so a picture can go missing but never lands at
    the wrong line."""
    remaining = list(cutouts)
    placed: list[tuple[int, bytes]] = []

    def put(match: re.Match) -> str:
        words = _words(match.group(1))
        for position, cutout in enumerate(remaining):
            if cutout.words == words:
                del remaining[position]
                placed.append((len(placed) + 1, cutout.png))
                return f"[рисунок {len(placed)}: {words}]"
        return match.group(0)

    if not remaining:
        return markdown, []
    return _SCHEME_RE.sub(put, markdown), placed


def _box(size: tuple[int, int], frame) -> tuple[int, int, int, int] | None:
    """The frame in pixels, widened by the margin and kept on the page; None
    for a frame too small to hold a drawing or too large to hold only one."""
    if frame is None:
        return None
    width, height = size
    top, left, bottom, right = frame
    if bottom - top < _MIN_SIDE * 1000 or right - left < _MIN_SIDE * 1000:
        return None
    if (bottom - top) * (right - left) > _MAX_AREA * 1000 * 1000:
        return None
    margin = _MARGIN * max(width, height)
    return (
        max(0, round(left / 1000 * width - margin)),
        max(0, round(top / 1000 * height - margin)),
        min(width, round(right / 1000 * width + margin)),
        min(height, round(bottom / 1000 * height + margin)),
    )


def _paper_light(gray: Image.Image) -> Image.Image:
    """The paper's own light at every point, a shadow across it included: the
    strokes taken out by a maximum filter on a quarter-size copy, then
    smoothed. Divided by it, the page keeps its ink and loses its lighting."""
    width, height = gray.size
    small = gray.resize(
        (max(1, width // 4), max(1, height // 4)), Image.Resampling.BILINEAR
    )
    size = 2 * (max(3, max(small.size) // 40) // 2) + 1
    small = small.filter(ImageFilter.MaxFilter(size)).filter(
        ImageFilter.GaussianBlur(size)
    )
    return small.resize((width, height), Image.Resampling.BILINEAR)


def _density(gray: Image.Image) -> np.ndarray:
    """How much ink stands at every point, 0 for paper and 1 for ink."""
    tone = np.asarray(gray, dtype=np.float32) / np.maximum(
        np.asarray(_paper_light(gray), dtype=np.float32), 1.0
    )
    step = np.clip((tone - _INK) / (_PAPER - _INK), 0.0, 1.0)
    return 1.0 - step * step * (3.0 - 2.0 * step)


def _fade(height: int, width: int) -> np.ndarray:
    def ramp(length: int) -> np.ndarray:
        edge = np.minimum(np.arange(length), np.arange(length)[::-1])
        return np.clip((edge + 1) / _FADE_PX, 0.0, 1.0)

    return np.minimum.outer(ramp(height), ramp(width))


def _cut_one(page: Image.Image, frame) -> bytes | None:
    box = _box(page.size, frame)
    if box is None:
        return None
    ink = _density(page.crop(box))
    strokes = np.argwhere(ink > _STROKE)
    if len(strokes) < _MIN_STROKE_PX:
        return None
    (top, left), (bottom, right) = strokes.min(axis=0), strokes.max(axis=0)
    ink = ink[
        max(0, top - _PAD_PX) : bottom + _PAD_PX + 1,
        max(0, left - _PAD_PX) : right + _PAD_PX + 1,
    ]
    ink = ink * _fade(*ink.shape)
    buffer = io.BytesIO()
    Image.fromarray(np.round(ink * 255).astype(np.uint8), "L").save(
        buffer, format="PNG", optimize=True
    )
    return buffer.getvalue()
