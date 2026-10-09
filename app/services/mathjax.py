"""Formulas drawn by MathJax 4, inside the process (task 99).

mathtext, which drew every formula until then, is not LaTeX: it has no
matrix — pdf.for_mathtext stacks an environment's rows, each a centred
string, and record 102's determinants printed with their columns apart and
their dots between the entries — and each record brought the next command it
lacked, printed as its source. MathJax is the engine the LaTeX the model
writes is written for. Over the 3 118 distinct formulas of the database it
drew every one the document hands an engine, in about 3 ms each against
mathtext's 13.

The bundle, `app/assets/mathjax/tex2svg.js`, built from `entry.js` beside it,
runs in V8 through mini-racer, and its SVG is rasterised by resvg: two pip
wheels, no Node. pdf._formula_png asks here first and mathtext when this
raises, so a deploy that lost either wheel draws as before and says so at
startup.

One V8 context for the process, behind one lock: pdf draws one document at
a time anyway (pdf._DRAWING), and the context is not to be entered by two
threads at once.
"""

from __future__ import annotations

import logging
import os
import re
import threading

logger = logging.getLogger(__name__)

VERSION = "4.1.3"
_BUNDLE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "mathjax", "tex2svg.js"
)
# One formula takes milliseconds; a call that has not come back in this long
# never will, and the formula goes to mathtext.
_CALL_TIMEOUT_S = 10.0
# A width for a formula that is not to be broken: wider than any page.
_UNBROKEN_EM = 1000.0
# An SVG's lengths are thousandths of an em.
_UNITS_PER_EM = 1000.0


class Refused(Exception):
    """MathJax will not draw this formula: a command it does not know, a
    character its bundled font lacks."""


class Unavailable(Refused):
    """MathJax cannot run here at all — a wheel missing, the bundle, V8 —
    which the startup log has said once already."""


_lock = threading.Lock()
_context = None
_unavailable: str | None = None


def _ready():
    """The V8 context with the bundle in it, made on first use; None, with
    the reason kept, if it cannot be made here."""
    global _context, _unavailable
    if _context is None and _unavailable is None:
        try:
            from py_mini_racer import MiniRacer
            import resvg_py  # noqa: F401 — the raster needs it as much

            context = MiniRacer()
            with open(_BUNDLE, encoding="utf-8") as handle:
                context.eval(handle.read())
            _context = context
        except Exception as exc:  # an import, a missing file, V8 itself
            _unavailable = f"{type(exc).__name__}: {exc}"[:200]
            logger.warning(
                "MathJax unavailable, mathtext draws every formula: %s", _unavailable
            )
    return _context


def describe() -> str:
    """The engine, for the startup log: what a deploy draws its formulas by."""
    with _lock:
        ready = _ready() is not None
    if ready:
        return f"MathJax {VERSION} in V8, mathtext behind it"
    return f"mathtext only, MathJax unavailable ({_unavailable})"


# mini-racer's message is the error's line followed by the minified source
# round where it was thrown; the line is the diagnosis.
_JS_ERROR_RE = re.compile(r"Error: ([^\n]*)")
_VIEWBOX_RE = re.compile(r'viewBox="([-\d.e ]+)"')
_ATTRIBUTE_RE = re.compile(r'="([^"]*)"')


def _diagnosis(exc: Exception) -> str:
    found = _JS_ERROR_RE.search(str(exc))
    return found.group(1).strip() if found else f"{type(exc).__name__}"


def _escaped(found: re.Match) -> str:
    # MathJax keeps each node's LaTeX in a data-latex attribute with its "<"
    # unescaped, which HTML reads and an SVG parser refuses.
    return '="' + found.group(1).replace("<", "&lt;").replace(">", "&gt;") + '"'


def png(
    latex: str,
    size_pt: float,
    color: str,
    display: bool,
    width_pt: float | None,
    dpi: int,
    stroke_pt: float,
    pad_pt: float,
) -> tuple[bytes, float, float, float]:
    """The formula as a transparent PNG with its width, height and depth in
    points — the shape mathtext's pictures have in pdf._formula_png.

    `display` sets it as a formula set apart, `width_pt` the width a display
    formula is broken to when it is wider. The depth is how far above the
    picture's bottom the baseline runs; the picture always holds its
    baseline, as mathtext's does — a minus sign alone sits above it, and a
    depth below zero would lift the line's text — and `pad_pt` round it, so
    the stroke is never clipped. `stroke_pt` is the outline mathtext's
    formulas are given to weigh as the text does (pdf._MATH_STROKE_PT).
    """
    width_em = width_pt / size_pt if width_pt else _UNBROKEN_EM
    with _lock:
        context = _ready()
        if context is None:
            raise Unavailable(_unavailable or "MathJax unavailable")
        try:
            svg = context.call(
                "tex2svg", latex, display, width_em, timeout_sec=_CALL_TIMEOUT_S
            )
        except Exception as exc:
            raise Refused(_diagnosis(exc)) from None
    try:
        return _rasterised(svg, size_pt, color, dpi, stroke_pt, pad_pt)
    except Refused:
        raise
    except Exception as exc:  # whatever the SVG does to resvg
        raise Refused(f"{type(exc).__name__}: {exc}"[:200]) from None


def _rasterised(
    svg: str, size_pt: float, color: str, dpi: int, stroke_pt: float, pad_pt: float
) -> tuple[bytes, float, float, float]:
    if 'data-mml-node="merror"' in svg:
        raise Refused("MathJax drew an error")
    if "<text" in svg:
        # A character none of the bundled font's ranges has: MathJax sets it
        # as text, and the raster is given no font, so it would be a blank.
        raise Refused("a character outside the bundled font")
    box = _VIEWBOX_RE.search(svg)
    if box is None:
        raise Refused("no viewBox")
    left, top, wide, high = (float(value) for value in box.group(1).split())
    if top + high < 0:
        high = -top
    pad = pad_pt / size_pt * _UNITS_PER_EM
    left, top, wide, high = left - pad, top - pad, wide + 2 * pad, high + 2 * pad
    points = size_pt / _UNITS_PER_EM
    pixels = dpi / 72.0
    svg = _ATTRIBUTE_RE.sub(_escaped, svg)
    svg = _VIEWBOX_RE.sub(f'viewBox="{left:.1f} {top:.1f} {wide:.1f} {high:.1f}"', svg, count=1)
    svg = re.sub(r'width="[-\d.]+ex"', f'width="{wide * points * pixels:.2f}"', svg, count=1)
    svg = re.sub(r'height="[-\d.]+ex"', f'height="{high * points * pixels:.2f}"', svg, count=1)
    svg = svg.replace("currentColor", color)
    # The first stroke-width is the whole formula's, at zero.
    svg = svg.replace(
        'stroke-width="0"', f'stroke-width="{stroke_pt / points:.1f}"', 1
    )
    import resvg_py

    data = bytes(resvg_py.svg_to_bytes(svg_string=svg, skip_system_fonts=True))
    return data, wide * points, high * points, (top + high) * points
