"""A sketch drawn again from its page: the pen's strokes traced off the
photograph as lines, the notebook's grid taken away, the labels set in type
(task 101).

A sketch — a set, a ball, a neighbourhood, a graph with no formula — is no
data (charts.py), and words about it told a student who missed the lecture
nothing. Cut out of the photograph as it was (task 54), it came out faint,
the grid standing over a light hand's strokes, and the CEO read the
document as worse. Asked for the drawing's geometry, the model put circles
of the wrong size where the author drew four balls and a whole grid where
he drew three lines — and each run differently: the place it invents. So
the lines here are the photograph's, every one where the pen left it, and
the model gives only what it reads well: where the drawing is, and what
its labels say (sketches.py). Nothing here calls a model or touches the
database, and redraw() never raises: a drawing that cannot be redrawn, or
comes out in pieces, stays the words that describe it.

The way, as `docs/FINDINGS.md` → "Sketches drawn from the page" measured it:

- the paper's own light divided out, as figures.py does — a hand's shadow
  across the page is no ink;
- the grid found as a lattice: its period and slant read off the spectrum,
  where a squared page's grid is the strongest periodic thing on it; its
  lines put where a comb of that period stands on the most darkness, then
  each fitted to the paper locally, for the photograph's perspective — and
  under the drawing too, where nothing else could find it;
- each grid line's own darkness taken off, line by line: darkness adds
  where ink lies over a printed line, so a stroke crossing the grid or
  drawn along it keeps what it adds itself;
- the strokes found by an oriented filter, which sums a line's darkness
  along its own direction and so lifts a light hand's stroke out of the
  paper's grain, where a threshold pixel by pixel lost it; a ridge along a
  grid line no stronger than the grid beside it is the grid;
- the ridges' crests as centre lines, joined across the gaps a crossing or
  a faint stretch leaves, a stroke traced twice kept once, straight where
  the author drew it straight, smoothed where not;
- the labels the runs read alike set in type where the handwriting stood,
  and the handwriting gone; a point a dot.

Set on record 106's album (the compactness lecture, light blue ballpoint on
a squared notebook, Telegram's 960 × 1280 photographs). What another hand,
another pen or another notebook does is measured on the next albums: the
gate below refuses what comes out in pieces, so the worst it does is leave
the words.
"""

from __future__ import annotations

import io
import logging
import math
import warnings
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

# ── Sizes, as shares of the page ─────────────────────────────────────────────
# A handwritten letter's height, about, as a share of the photograph's long
# side: the unit every distance below is measured in, so a photograph taken
# closer or further reads the same.
_LETTER = 0.02
# The strokes are traced this many letters round the model's frame: its
# frames are tight, and a drawing cut at one is worse than a margin — the
# ball round four others lost its left side at 0.6 of a letter; at three, the
# page's own top edge came in.
_REACH_LETTERS = 2.0
# The grid is found over this much more round the frame, so its lines are
# measured past the drawing that covers them.
_CONTEXT_LETTERS = 2.0
# A frame narrower than this share of a side holds a symbol, not a drawing;
# one larger than this share of the page holds the text round it as well.
_MIN_SIDE = 0.04
_MAX_AREA = 0.6

# ── The lattice ──────────────────────────────────────────────────────────────
# A notebook's square, in pixels of a photograph of 1000 to 1500 on its long
# side: 17 to 24 measured on record 106's pages. Wider than this both ways,
# so a page photographed close or far still finds its grid.
_MIN_PERIOD, _MAX_PERIOD = 12.0, 45.0
# A grid's peak stands this many times over the spectrum round it, and
# _GRID_SHARP times over the frequencies beside it; a page with no grid —
# plain paper — has none, and nothing is taken away.
_GRID_PEAK = 6.0
_GRID_SHARP = 3.0
# Darker than this share of the paper's light is no grid line's darkness —
# record 106's grid measured 0.1 to 0.3 against its paper, a light hand's
# ink 0.3 to 0.6: the grid is found with every stroke clipped to it.
_GRID_CLIP = 0.2
# A grid shows along at least this share of the places its comb puts its
# lines: record 106's, under its drawings and words, 0.6 to 0.9.
_GRID_COVERS = 0.45
# A grid line keeps to the place its order gives it within this share of a
# square; one further off was measured on a stroke lying beside it.
_GRID_STRAY = 0.33
# Along a line, its darkness is measured in pieces this long, to follow the
# photograph's perspective; a piece where the line does not show — under
# the drawing — leaves the line where the comb puts it.
_GRID_SEGMENT = 36
_GRID_SHOWS = 0.012
# How far either side of a grid line its own darkness is taken off.
_GRID_REACH = 4

# ── The strokes ──────────────────────────────────────────────────────────────
# The oriented filter: across a stroke about a ballpoint's width, along it
# three times that, at sixteen directions.
_ACROSS, _ALONG, _DIRECTIONS = 1.1, 3.0, 16
# A crest counts from _LOW times the paper's own spread of the filter, and a
# stroke needs a stretch above _HIGH somewhere along it: a stroke is kept
# whole down to its faintest, and the paper's grain never starts one. The
# spread is never taken below _MIN_SPREAD: record 106's paper measured 0.004
# to 0.006, and a page lit flat next to nothing.
_LOW, _HIGH = 3.0, 8.0
_MIN_SPREAD = 0.003
# A ridge running along a grid line, within this angle of it, is the grid's
# unless it stands twice the strength of the grid lines beside it.
_GRID_ANGLE = math.radians(16)
# A path no longer than this, from a fork to a loose end, is the thinning's
# spur, not a stroke; a lone one this short is a speck.
_SPUR_PX, _SPECK_PX = 4.0, 5.0
# A loose end is joined to another facing it, or to a line it runs into,
# across at most this many letters.
_GAP_LETTERS = 0.7
# A straight path lying this close to a grid line is the grid unless it is
# half as dark again as the grid lines beside it.
_ON_GRID_PX = 1.8
_DARKER_THAN_GRID = 1.5
# A mark this many letters long or less, at the frame's edge and touching
# nothing long, is the text round the drawing: a letter «о» of the line
# above, closed on itself, ran 1.8.
_EDGE_MARK_LETTERS = 2.2
# Ink along a line: at least this share of the drawing's darkest stroke, and
# above the paper's grain.
_INK_SHARE = 0.1
# A stretch of a stroke with less than this share of the stroke's own ink is
# a gap in it.
_OWN_INK = 0.33
# A turn sharper than this, about 55 degrees, is a corner a stroke is cut at
# before it is judged.
_CORNER_COS = 0.57
# A stroke traced twice: the second pass lies within this many pixels of
# the first along this share of its length.
_TWICE_PX, _TWICE_SHARE = 2.5, 0.7
# Straight when the author's line keeps this close to its chord, in pixels
# or as a share of its length; smoothed along its length otherwise.
_STRAIGHT_PX, _STRAIGHT_SHARE = 1.3, 0.012
_SMOOTH_PX = 2.2

# ── The gate ─────────────────────────────────────────────────────────────────
# A drawing redrawn in pieces is worse than its words. Over record 106's six,
# with every run's frames and with production's: the drawings that read as
# their photographs had at most 0.37 of their length in open strokes shorter
# than a letter, and at most 0.14 in straight pieces along the page's axes
# shorter than three letters; the plane drawn along the grid, 0.43 to 0.46
# and 0.24 to 0.43 — the author's lines and the notebook's in squares no
# code can tell apart; at 0.25 production drew it once, from the page as
# compressed, the text beside it with it. An axis is one long straight line and is not counted.
# Measured on six, said so, and watched on the next. A drawing half of
# which lies along the grid is the grid's as much as the author's.
_MAX_SHORT = 0.45
_MAX_SHORT_STRAIGHT = 0.2
_MAX_ALONG_GRID = 0.5
_MIN_LENGTH_LETTERS = 3.0
# A frame more than a quarter ink holds no line drawing; nor does one that
# traces into more pieces than this — record 106's busiest drawing made 640.
_MOSTLY_INK = 0.25
_MAX_PATHS = 2500

# ── The drawing as printed ───────────────────────────────────────────────────
# A notebook page's long side in points: pdf._PICTURE_PT_PER_PX × 1500, the
# scale cut-outs were set at, so a drawing prints at about its size on the
# page whatever the photograph's pixels.
_PAGE_PT = 675.0
# The document's chart weights (pdf._CHART_RULE_PT, _CHART_NAME_PT): a
# drawing redrawn sits beside a chart drawn from its data.
_LINE_PT = 0.9
_DOT_PT = 1.4
_LABEL_PT = 10.0
# Pixels a point keeps after its ink is eroded by one: a dot drawn 5 px
# across keeps 9, a stroke's dark stretch two or three.
_DOT_PX = 5
_DPI = 300


@dataclass
class Label:
    """A label the runs read alike: its text in LaTeX and its box,
    (top, left, bottom, right) in thousandths of the photograph."""

    text: str
    box: tuple[int, int, int, int]


@dataclass
class Sketch:
    """Where one drawing is, as the runs agree: `frame` takes in every run's
    frame that agreed, `inner` only what they all hold — the stretch a small
    mark is counted in — and the labels read alike."""

    frame: tuple[int, int, int, int]
    inner: tuple[int, int, int, int]
    labels: list[Label] = field(default_factory=list)


@dataclass
class Redrawn:
    """A drawing drawn again: its darkness as a greyscale PNG, 255 the
    ink, carrying the resolution it was drawn at so the document sets it at
    its size; or None with why not, for the log."""

    png: bytes | None
    reason: str
    labels: int = 0


# ── The page ─────────────────────────────────────────────────────────────────


def _paper_light(gray: Image.Image) -> np.ndarray:
    """The paper's own light at every point, a shadow included: figures.py's
    estimate — the strokes taken out by a maximum filter on a quarter-size
    copy, then smoothed."""
    width, height = gray.size
    small = gray.resize((max(1, width // 4), max(1, height // 4)), Image.Resampling.BILINEAR)
    size = 2 * (max(3, max(small.size) // 40) // 2) + 1
    small = small.filter(ImageFilter.MaxFilter(size)).filter(ImageFilter.GaussianBlur(size))
    return np.asarray(small.resize((width, height), Image.Resampling.BILINEAR), np.float32)


def _box_mean(a: np.ndarray, r: int) -> np.ndarray:
    """The mean over a (2r+1)² window at every point, edges clamped."""
    p = np.pad(a.astype(np.float64), r + 1, mode="edge")
    c = p.cumsum(0).cumsum(1)
    k = 2 * r + 1
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return (s / (k * k))[: a.shape[0], : a.shape[1]].astype(np.float32)


# Paper is within this share of the light at the page's middle — a hand's
# shadow measured 0.55 to 0.7 of it on record 106's pages — and no warmer
# than the middle by this much of red over blue.
_PAPER_LIGHT = 0.45
_PAPER_WARM = 22


class Page:
    """A photograph's tones, worked out once for all its drawings: its
    darkness against the paper's own light, and where the paper is — not
    far darker than the page's middle and not the table's warm colour."""

    def __init__(self, image_bytes: bytes):
        with Image.open(io.BytesIO(image_bytes)) as opened:
            photo = opened.convert("RGB")
        self.width, self.height = photo.size
        rgb = np.asarray(photo, np.float32)
        gray = photo.convert("L")
        light = _paper_light(gray)
        self.darkness = np.clip(1 - np.asarray(gray, np.float32) / np.maximum(light, 1), 0, 1)
        h, w = light.shape
        middle = (slice(h // 4, 3 * h // 4), slice(w // 4, 3 * w // 4))
        warm = _box_mean(rgb[..., 0] - rgb[..., 2], 12)
        # a shadow across the page is paper still, divided out above; what
        # is not is far darker than the page's middle, or the table's warm
        # colour (record 106's: R - B some 30 above the page's)
        self.paper = (light > _PAPER_LIGHT * float(np.median(light[middle]))) & (
            warm < float(np.median(warm[middle])) + _PAPER_WARM
        )


# ── The lattice ──────────────────────────────────────────────────────────────


def _smooth_along(a: np.ndarray, r: int, axis: int) -> np.ndarray:
    """The mean over 2r+1 along one axis, edges clamped."""
    a = np.moveaxis(a, axis, -1)
    pad = np.concatenate(
        [np.repeat(a[..., :1], r + 1, -1), a, np.repeat(a[..., -1:], r, -1)], -1
    ).astype(np.float64)
    c = pad.cumsum(-1)
    k = 2 * r + 1
    return np.moveaxis(((c[..., k:] - c[..., :-k]) / k).astype(np.float32), -1, axis)


def _grid_lines(darkness: np.ndarray) -> tuple[list[np.ndarray], float]:
    """The near-horizontal lines of a squared page's grid in a window, each
    a quadratic y(x), and their period at the window's middle; ([], 0)
    where the window has none.

    The period and slant are the spectrum's sharpest peak in the band a
    notebook's square falls in; the lines stand where a comb of that period
    covers the most darkness at the window's middle. Perspective shrinks
    the square across a wide window, so the comb's places are only a start:
    each line is measured in pieces along it, and where lines stand and how
    they slant is fitted over their order — the period and the slant each
    changing smoothly from line to line, as perspective changes them. A
    line hidden under the drawing, or one whose own fit strays towards a
    neighbour, takes the place and slant that fit gives it."""
    h, w = darkness.shape
    if h < 2 * _MIN_PERIOD or w < 2 * _MIN_PERIOD:
        return [], 0.0
    # every stroke as dark as a grid line at most: three dark dashed levels
    # forty pixels apart outweighed a faint grid of twenty-two, and were taken
    # for it; clipped, the grid's many lines outweigh a drawing's few
    darkness = np.minimum(darkness, _GRID_CLIP)
    windowed = (darkness - darkness.mean()) * np.outer(np.hanning(h), np.hanning(w))
    spectrum = np.abs(np.fft.fft2(windowed))
    spectrum[0, 0] = 0
    ky = np.fft.fftfreq(h)[:, None]
    kx = np.fft.fftfreq(w)[None, :]
    band = (ky >= 1 / _MAX_PERIOD) & (ky <= 1 / _MIN_PERIOD)
    candidates = band & (np.abs(kx) <= 0.22 * ky)
    if not candidates.any():
        return [], 0.0
    found = np.where(candidates, spectrum, 0)
    iy, ix = np.unravel_index(int(np.argmax(found)), found.shape)
    ring = np.broadcast_to((np.abs(ky) >= 1 / _MAX_PERIOD) & (np.abs(ky) <= 1 / _MIN_PERIOD), spectrum.shape)
    # a blank window has no peak at all: nothing stands above nothing; and a
    # grid's peak is sharp — it stands over the frequencies just beside it in
    # its column, where one long line, an axis on plain paper, makes a ridge
    # along the whole column and no peak in it
    beside = [
        spectrum[(iy + k) % h, ix] for k in (-6, -5, -4, -3, -2, 2, 3, 4, 5, 6)
    ]
    if (
        not candidates[iy, ix]
        or found[iy, ix] <= 0
        or found[iy, ix] < _GRID_PEAK * float(np.median(spectrum[ring]))
        or found[iy, ix] < _GRID_SHARP * float(np.median(beside))
    ):
        return [], 0.0
    fy, fx = float(ky[iy, 0]), float(kx[0, ix])
    period = 1 / math.hypot(fy, fx)
    slope = -fx / fy
    smooth = _smooth_along(darkness, 12, axis=1)
    xs = np.arange(w)
    middle = w / 2
    rows = np.floor(np.arange(h)[:, None] - slope * (xs[None, :] - middle)).astype(int)
    low = int(rows.min())
    profile = np.bincount((rows - low).ravel(), weights=smooth.ravel())
    counts = np.bincount((rows - low).ravel())
    profile = profile / np.maximum(counts, 1)
    positions = np.arange(len(profile))

    def comb(phase: float) -> float:
        return float(np.interp(np.arange(phase, len(profile), period), positions, profile).mean())

    phase = max(np.arange(0, period, 0.25), key=comb)
    starts = [c for c in np.arange(phase, len(profile), period) + low if -period <= c <= h + period]
    if len(starts) < 3:
        return [], 0.0

    tried, shown = [0], [0]

    def measure(centre: float, line_slope: float, reach: float, nearest: bool) -> np.ndarray | None:
        """A line measured in pieces along it, near where it is expected:
        at the darkest crest in reach while only the comb says where, at the
        crest nearest the place once the lines' order does."""
        mx, my = [], []
        for x0 in range(0, w, _GRID_SEGMENT):
            xm = (x0 + min(w, x0 + _GRID_SEGMENT)) / 2
            yp = centre + line_slope * (xm - middle)
            ya, yb = int(math.floor(yp - reach)), int(math.ceil(yp + reach))
            if ya < 0 or yb >= h:
                continue
            tried[0] += 1
            column = smooth[ya : yb + 1, int(xm)]
            base = float(np.median(column))
            # the crest nearest where the line is expected, not the darkest:
            # a stroke drawn beside a grid line, a dashed level four pixels
            # off it, drew the darkest one to itself
            crests = [
                k for k in range(1, len(column) - 1)
                if column[k] >= column[k - 1] and column[k] >= column[k + 1] and column[k] - base > _GRID_SHOWS
            ]
            if crests:
                k = min(crests, key=lambda k: abs(ya + k - yp)) if nearest else max(crests, key=lambda k: column[k])
                shown[0] += 1
                mx.append(xm)
                my.append(ya + k)
        if len(mx) < 3:
            return None
        mx_, my_ = np.array(mx), np.array(my, float)
        coef = np.polyfit(mx_, my_, 1 if len(mx_) < 6 else 2)
        keep = np.abs(np.polyval(coef, mx_) - my_) < 2.0
        if keep.sum() < 3:
            return None
        coef = np.polyfit(mx_[keep], my_[keep], 1 if keep.sum() < 6 else 2)
        return np.pad(coef, (3 - len(coef), 0))

    # first pass: each line near the comb's place, the window's own slant
    first = [measure(c, slope, 0.35 * period, nearest=False) for c in starts]
    known = [(i, c) for i, c in enumerate(first) if c is not None]
    # a notebook's grid runs across the whole window, under the drawing
    # too; a drawing's own parallel lines — dashed levels, an axis on plain
    # paper — make a periodic spectrum as well, but show along few of the
    # comb's places, and taken for a grid they took the axis with them
    if not known or shown[0] < _GRID_COVERS * max(tried[0], 1):
        return [], 0.0
    # where the lines stand and how they slant, over their order: smooth in
    # it, as perspective is
    order = np.array([i for i, _ in known], float)
    at_middle = np.array([np.polyval(c, middle) for _, c in known])
    slants = np.array([c[1] + 2 * c[0] * middle for _, c in known])
    degree = 2 if len(known) >= 6 else 1 if len(known) >= 2 else 0
    place_fit = np.polyfit(order, at_middle, degree) if degree else np.array([period, at_middle[0] - order[0] * period])
    if degree == 0:
        slant_fit = np.array([slants[0]])
    else:
        slant_fit = np.polyfit(order, slants, 1)
    residual = np.abs(np.polyval(place_fit, order) - at_middle)
    if degree and np.any(residual > 0.3 * period):
        good = residual <= 0.3 * period
        if good.sum() >= 3:
            place_fit = np.polyfit(order[good], at_middle[good], min(degree, 2 if good.sum() >= 6 else 1))
            slant_fit = np.polyfit(order[good], slants[good], 1)
    lines: list[np.ndarray] = []
    count = len(starts)
    for i in range(-2, count + 2):
        centre = float(np.polyval(place_fit, i))
        if centre < -period or centre > h + period:
            continue
        local_period = abs(float(np.polyval(np.polyder(place_fit), i))) if degree else period
        local_period = min(max(local_period, _MIN_PERIOD * 0.8), _MAX_PERIOD * 1.2)
        line_slope = float(np.polyval(slant_fit, i))
        coef = measure(centre, line_slope, 0.3 * local_period, nearest=True)
        predicted = np.array([0.0, line_slope, centre - line_slope * middle])
        if coef is None:
            lines.append(predicted)
            continue
        # a line's own fit that strays a third of a square from where its
        # order puts it is following a stroke, not the paper; less is the
        # lens bending the paper's lines, which the fit has to follow
        probe = np.linspace(0, w - 1, 9)
        if np.max(np.abs(np.polyval(coef, probe) - np.polyval(predicted, probe))) > _GRID_STRAY * local_period:
            lines.append(predicted)
        else:
            lines.append(coef)
    return lines, period


def _take_grid_off(od: np.ndarray, lines: list[np.ndarray]) -> np.ndarray:
    """Each grid line's own darkness taken off: its shape across, the
    median of all its columns, and its strength along, a running median the
    strokes crossing it hardly move. Darkness adds where ink lies over a
    printed line, so a stroke keeps what it adds itself."""
    h, w = od.shape
    out = od.copy()
    xs = np.arange(w)
    offsets = np.arange(-_GRID_REACH, _GRID_REACH + 1)
    for coef in lines:
        yc = np.polyval(coef, xs.astype(float))
        ys = yc[:, None] + offsets[None, :]
        valid = (ys[:, 0] >= 0) & (ys[:, -1] <= h - 1)
        if valid.sum() < 10:
            continue
        y0 = np.clip(np.floor(ys).astype(int), 0, h - 1)
        f = ys - np.floor(ys)
        prof = od[y0, xs[:, None]] * (1 - f) + od[np.clip(y0 + 1, 0, h - 1), xs[:, None]] * f
        base = np.minimum(prof[:, 0], prof[:, -1])
        rel = prof - base[:, None]
        shape = np.clip(np.median(rel[valid], axis=0), 0, None)
        if shape.max() <= 1e-4:
            continue
        shape = shape / shape.max()
        peak = np.where(valid, rel[:, _GRID_REACH - 1 : _GRID_REACH + 2].max(1), np.nan)
        # the strength along the line: a running median over 41 columns
        padded = np.concatenate([np.full(20, np.nan), peak, np.full(20, np.nan)])
        with warnings.catch_warnings():
            # a window wholly off the photograph is all NaN: no strength there
            warnings.simplefilter("ignore", RuntimeWarning)
            strength = np.nan_to_num(
                np.nanmedian(np.lib.stride_tricks.sliding_window_view(padded, 41), axis=1)
            )
        # every pixel of the band at once: no two lines' bands meet, a
        # period being three times the reach
        columns = np.where(valid)[0]
        base_row = np.floor(yc[columns]).astype(int)
        for k in range(-_GRID_REACH, _GRID_REACH + 2):
            row = base_row + k
            offset = row - yc[columns]
            ok = (np.abs(offset) <= _GRID_REACH) & (row >= 0) & (row < h)
            x, y = columns[ok], row[ok]
            out[y, x] = np.maximum(0.0, out[y, x] - strength[x] * np.interp(offset[ok], offsets, shape))
    return out


# ── The strokes ──────────────────────────────────────────────────────────────


def _filters() -> tuple[list[np.ndarray], int]:
    r = int(math.ceil(3 * max(_ACROSS, _ALONG)))
    y, x = np.mgrid[-r : r + 1, -r : r + 1].astype(np.float64)
    kernels = []
    for i in range(_DIRECTIONS):
        theta = math.pi * i / _DIRECTIONS
        u = x * math.cos(theta) + y * math.sin(theta)
        v = -x * math.sin(theta) + y * math.cos(theta)
        g = np.exp(-0.5 * (u**2 / _ACROSS**2 + v**2 / _ALONG**2))
        k = (1 - u**2 / _ACROSS**2) * g
        k -= k.mean()
        kernels.append(k / np.abs(k).sum())
    return kernels, r


_KERNELS, _KERNEL_R = _filters()


def _ridges(od: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The oriented filter's strongest answer at every point, in the paper's
    own spread of it, and the direction across the ridge it answered at."""
    h, w = od.shape
    r = _KERNEL_R
    fh = 1 << int(math.ceil(math.log2(h + 2 * r)))
    fw = 1 << int(math.ceil(math.log2(w + 2 * r)))
    pad = np.zeros((fh, fw))
    pad[r : r + h, r : r + w] = od
    pad[:r, r : r + w] = od[0]
    pad[r + h : r + h + r, r : r + w] = od[-1]
    pad[:, :r] = pad[:, r : r + 1]
    pad[:, r + w : r + w + r] = pad[:, r + w - 1 : r + w]
    spectrum = np.fft.rfft2(pad)
    best = np.full((h, w), -np.inf)
    direction = np.zeros((h, w), np.int8)
    size = _KERNELS[0].shape[0]
    for i, k in enumerate(_KERNELS):
        kp = np.zeros((fh, fw))
        kp[:size, :size] = k
        kp = np.roll(np.roll(kp, -r, 0), -r, 1)
        answer = np.fft.irfft2(spectrum * np.fft.rfft2(kp), s=(fh, fw))[r : r + h, r : r + w]
        better = answer > best
        best[better] = answer[better]
        direction[better] = i
    spread = 1.4826 * float(np.median(np.abs(best - np.median(best))))
    # paper with no grain of its own — a scan, a page lit flat — has next to
    # no spread, and JPEG's ripples would stand above it as strokes
    return (best / max(spread, _MIN_SPREAD)).astype(np.float32), direction


def _grid_bands(shape, lines: list[np.ndarray], transpose: bool) -> list[np.ndarray]:
    """The pixels within two of each grid line, as (row, column) pairs."""
    h, w = shape if not transpose else shape[::-1]
    xs = np.arange(w)
    bands = []
    for coef in lines:
        yc = np.round(np.polyval(coef, xs.astype(float))).astype(int)
        pts = []
        for o in (-2, -1, 0, 1, 2):
            y = yc + o
            ok = (y >= 0) & (y < h)
            pts.append(np.stack([y[ok], xs[ok]], 1))
        band = np.concatenate(pts)
        bands.append(band[:, ::-1] if transpose else band)
    return bands


def _silence_grid(z, direction, lines, transpose):
    """Ridges along a grid line, no stronger than twice the grid lines beside
    it, are the grid's. The neighbours, not the line itself: an axis drawn
    along a grid line end to end made that line's own median its own height
    and silenced itself."""
    bands = _grid_bands(z.shape, lines, transpose)
    medians, aligned = [], []
    for band in bands:
        if len(band) == 0:
            medians.append(None)
            aligned.append(None)
            continue
        across = direction[band[:, 0], band[:, 1]].astype(float) * math.pi / _DIRECTIONS
        along = across + math.pi / 2
        runs_with = (np.abs(np.cos(along)) if transpose else np.abs(np.sin(along))) < math.sin(_GRID_ANGLE)
        aligned.append(runs_with)
        values = z[band[:, 0], band[:, 1]][runs_with]
        medians.append(float(np.median(values)) if len(values) >= 10 else None)
    for i, band in enumerate(bands):
        if aligned[i] is None or aligned[i].sum() < 10:
            continue
        near = [medians[j] for j in range(max(0, i - 3), min(len(bands), i + 4)) if j != i and medians[j] is not None]
        if not near:
            continue
        values = z[band[:, 0], band[:, 1]]
        quiet = aligned[i] & (values < 2.0 * float(np.median(near)) + _LOW)
        z[band[quiet, 0], band[quiet, 1]] = 0
    return z


def _crests(z: np.ndarray, direction: np.ndarray) -> np.ndarray:
    """The ridges' crests — a point no lower than its two neighbours across
    the ridge — above _LOW, kept where a stretch of them rises above _HIGH."""
    h, w = z.shape
    across = direction.astype(float) * math.pi / _DIRECTIONS
    dx, dy = np.cos(across), np.sin(across)
    yy, xx = np.mgrid[0:h, 0:w]

    def at(ox, oy):
        return z[np.clip(np.round(yy + oy).astype(int), 0, h - 1), np.clip(np.round(xx + ox).astype(int), 0, w - 1)]

    crest = (z >= at(dx, dy)) & (z >= at(-dx, -dy)) & (z > _LOW)
    labels, _ = _components(crest)
    strong = np.unique(labels[crest & (z > _HIGH)])
    keep = np.zeros(int(labels.max()) + 1, bool)
    keep[strong] = True
    keep[0] = False
    return keep[labels]


def _components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """8-connected components of a mask: labels from 1, and how many."""
    h, w = mask.shape
    labels = np.zeros((h, w), np.int32)
    n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if labels[y0, x0]:
            continue
        n += 1
        labels[y0, x0] = n
        stack = [(y0, x0)]
        while stack:
            y, x = stack.pop()
            for yy in (y - 1, y, y + 1):
                if 0 <= yy < h:
                    for xx in (x - 1, x, x + 1):
                        if 0 <= xx < w and mask[yy, xx] and not labels[yy, xx]:
                            labels[yy, xx] = n
                            stack.append((yy, xx))
    return labels, n


def _pieces(labels: np.ndarray) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """Each component's rows and columns."""
    ys, xs = np.nonzero(labels)
    if len(ys) == 0:
        return {}
    ids = labels[ys, xs]
    order = np.argsort(ids, kind="stable")
    ids, ys, xs = ids[order], ys[order], xs[order]
    cuts = np.flatnonzero(np.diff(ids)) + 1
    return {int(i[0]): (y, x) for i, y, x in zip(np.split(ids, cuts), np.split(ys, cuts), np.split(xs, cuts))}


def _ink(od: np.ndarray) -> tuple[np.ndarray, float] | None:
    """The ink as blobs — a letter, a point — between two levels set from
    the drawing's own darkest ink, so a light hand and a heavy one are cut
    alike; and that level. None when more than a quarter of the frame is
    ink: no line drawing is, and walking it pixel by pixel would hold an
    image thread for seconds."""
    smooth = od
    for _ in range(3):
        smooth = _smooth_along(_smooth_along(smooth, 1, 0), 1, 1)
    level = float(np.percentile(smooth, 99.3))
    weak = smooth > 0.2 * level
    if weak.mean() > _MOSTLY_INK:
        return None
    labels, n = _components(weak)
    strong = np.unique(labels[(smooth > 0.42 * level) & weak])
    sizes = np.bincount(labels.ravel(), minlength=n + 1)
    keep = np.zeros(n + 1, bool)
    keep[strong] = True
    keep[0] = False
    keep &= sizes >= 6
    return keep[labels], level


# ── Lines out of crests ──────────────────────────────────────────────────────


def _thin(mask: np.ndarray) -> np.ndarray:
    """Zhang and Suen's thinning with Lü and Wang's condition, three
    neighbours at least: the plain one erases a stroke two pixels thick on a
    diagonal outright — the segments from x₁ went missing that way."""
    img = np.pad(mask.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            p2, p3, p4 = img[:-2, 1:-1], img[:-2, 2:], img[1:-1, 2:]
            p5, p6, p7 = img[2:, 2:], img[2:, 1:-1], img[2:, :-2]
            p8, p9 = img[1:-1, :-2], img[:-2, :-2]
            centre = img[1:-1, 1:-1]
            ring = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            count = sum(r.astype(np.int16) for r in ring[:8])
            steps = sum(((ring[i] == 0) & (ring[i + 1] == 1)).astype(np.int16) for i in range(8))
            if step == 0:
                first, second = (p2 * p4 * p6) == 0, (p4 * p6 * p8) == 0
            else:
                first, second = (p2 * p4 * p8) == 0, (p2 * p6 * p8) == 0
            gone = (centre == 1) & (count >= 3) & (count <= 6) & (steps == 1) & first & second
            if gone.any():
                centre[gone] = 0
                changed = True
        if not changed:
            return img[1:-1, 1:-1].astype(bool)


_AROUND = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


def _branches(skeleton: np.ndarray) -> np.ndarray:
    """Branches leaving each skeleton pixel: its 0→1 steps round its eight
    neighbours. A staircase on a diagonal has three neighbours and two
    branches; counting neighbours took every step for a fork."""
    p = np.pad(skeleton.astype(np.int8), 1)
    h, w = skeleton.shape
    ring = [p[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w] for dy, dx in _AROUND]
    steps = sum(((ring[i] == 0) & (ring[(i + 1) % 8] == 1)).astype(np.int8) for i in range(8))
    return steps * skeleton


def _paths(skeleton: np.ndarray) -> tuple[list[list[tuple[int, int]]], np.ndarray]:
    """The skeleton as paths between its ends and forks, and its closed
    loops; with each pixel's branch count."""
    h, w = skeleton.shape
    branches = _branches(skeleton)
    p = np.pad(skeleton.astype(np.int8), 1)
    neighbours = sum(p[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w] for dy, dx in _AROUND)
    node = skeleton & ((branches != 2) | (neighbours > 4))
    seen = np.zeros_like(skeleton)
    walked: set = set()
    paths = []

    def around(y, x):
        for dy, dx in _AROUND:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and skeleton[yy, xx]:
                yield yy, xx

    for y0, x0 in zip(*np.nonzero(node)):
        start_node = (int(y0), int(x0))
        for first in around(*start_node):
            if node[first]:
                key = tuple(sorted([start_node, first]))
                if key not in walked:
                    walked.add(key)
                    paths.append([start_node, first])
                continue
            if seen[first]:
                continue
            seen[first] = True
            path = [start_node, first]
            previous, current = start_node, first
            while True:
                options = [q for q in around(*current) if q != previous and (not seen[q] or node[q])]
                if not options:
                    break
                ends = [q for q in options if node[q] and (q != start_node or len(path) > 3)]
                if ends:
                    path.append(min(ends, key=lambda q: abs(q[0] - current[0]) + abs(q[1] - current[1])))
                    break
                nxt = min(options, key=lambda q: abs(q[0] - current[0]) + abs(q[1] - current[1]))
                seen[nxt] = True
                path.append(nxt)
                previous, current = current, nxt
            paths.append(path)
    for y0, x0 in zip(*np.nonzero(skeleton & ~node & ~seen)):
        if seen[y0, x0]:
            continue
        path = [(int(y0), int(x0))]
        seen[y0, x0] = True
        previous, current = None, path[0]
        while True:
            options = [q for q in around(*current) if q != previous and not seen[q]]
            if not options:
                break
            nxt = min(options, key=lambda q: abs(q[0] - current[0]) + abs(q[1] - current[1]))
            seen[nxt] = True
            path.append(nxt)
            previous, current = current, nxt
        if len(path) > 2:
            path.append(path[0])
            paths.append(path)
    return paths, branches


def _length(points: np.ndarray) -> float:
    return float(np.sum(np.hypot(*np.diff(points, axis=0).T))) if len(points) > 1 else 0.0


def _bridges(paths: list[np.ndarray], branches: np.ndarray, skeleton: np.ndarray, reach: float) -> list[np.ndarray]:
    """Gaps closed: a loose end joined to another facing it, else to a line
    it runs into, along its own direction. Each end looks only within reach
    of itself, so a page of many strokes costs what a page of few does."""
    ends = []
    for i, path in enumerate(paths):
        if len(path) < 3:
            continue
        for at_start in (True, False):
            end = path[0] if at_start else path[-1]
            if branches[int(end[0]), int(end[1])] != 1:
                continue
            back = path[min(6, len(path) - 1)] if at_start else path[-1 - min(6, len(path) - 1)]
            heading = end - back
            norm = float(np.hypot(*heading))
            if norm:
                ends.append((i, end, heading / norm))
    if not ends:
        return []
    facing_cos = math.cos(math.radians(45))
    at = np.array([e[1] for e in ends])
    pairs = []
    order = np.argsort(at[:, 0])
    for k, a in enumerate(order):
        for b in order[k + 1 :]:
            if at[b, 0] - at[a, 0] > reach:
                break
            gap = at[b] - at[a]
            d = float(np.hypot(*gap))
            if d == 0 or d > reach:
                continue
            ca, cb = float(ends[a][2] @ (gap / d)), float(ends[b][2] @ (-gap / d))
            if ca > facing_cos and cb > facing_cos:
                pairs.append((d * (2 - ca) * (2 - cb), int(a), int(b)))
    bridges, used = [], set()
    for _, a, b in sorted(pairs):
        if a in used or b in used:
            continue
        used.update((a, b))
        bridges.append(np.array([ends[a][1], ends[b][1]]))
    h, w = skeleton.shape
    r = int(math.ceil(reach))
    running_cos = math.cos(math.radians(25))
    for a, (i, end, heading) in enumerate(ends):
        if a in used:
            continue
        y0, x0 = int(end[0]), int(end[1])
        top, left = max(0, y0 - r), max(0, x0 - r)
        local = np.argwhere(skeleton[top : y0 + r + 1, left : x0 + r + 1]).astype(float)
        if not len(local):
            continue
        local += (top, left)
        gap = local - end
        d = np.hypot(gap[:, 0], gap[:, 1])
        near = (d > 2.5) & (d <= reach)
        if not near.any():
            continue
        ahead = (gap[near] @ heading) / d[near] > running_cos
        if not ahead.any():
            continue
        target = local[near][ahead][int(np.argmin(d[near][ahead]))]
        if float(np.min(np.hypot(*(paths[i] - target).T))) < 1.5:
            continue
        used.add(a)
        bridges.append(np.array([end, target]))
    return bridges


def _strokes(pieces: list[np.ndarray], join: float = 1.5) -> list[tuple[np.ndarray, bool]]:
    """Paths and bridges as one graph walked through its nodes of two
    branches: each stroke a polyline, and whether it closes."""
    ends = [(i, side, piece[0] if side == 0 else piece[-1]) for i, piece in enumerate(pieces) for side in (0, 1)]
    parent = list(range(len(ends)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    points = np.array([e[2] for e in ends]) if ends else np.zeros((0, 2))
    order = np.argsort(points[:, 0]) if len(points) else []
    for ii, a in enumerate(order):
        for b in order[ii + 1 :]:
            if points[b, 0] - points[a, 0] > join:
                break
            if abs(points[b, 1] - points[a, 1]) <= join:
                parent[find(a)] = find(b)
    node = [find(k) for k in range(len(ends))]
    incident: dict[int, list[tuple[int, int]]] = {}
    for k, (i, side, _) in enumerate(ends):
        incident.setdefault(node[k], []).append((i, side))
    used = [False] * len(pieces)
    out = []
    for start in range(len(pieces)):
        if used[start]:
            continue
        used[start] = True
        chain = [pieces[start]]
        for side in (1, 0):
            at = node[2 * start + side]
            while len(incident.get(at, [])) == 2:
                free = [(i, s) for i, s in incident[at] if not used[i]]
                if not free:
                    break
                i, s = free[0]
                used[i] = True
                piece = pieces[i] if s == 0 else pieces[i][::-1]
                if side == 1:
                    chain.append(piece)
                else:
                    chain.insert(0, piece[::-1])
                at = node[2 * i + (1 - s)]
        joined = [chain[0]]
        for piece in chain[1:]:
            last = joined[-1][-1]
            if np.hypot(*(piece[0] - last)) > np.hypot(*(piece[-1] - last)):
                piece = piece[::-1]
            joined.append(piece)
        line = np.concatenate(joined)
        out.append((line, len(line) > 8 and float(np.hypot(*(line[0] - line[-1]))) <= join + 1))
    return out


def _disc(radius: float) -> np.ndarray:
    r = int(math.ceil(radius))
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    return np.argwhere(yy**2 + xx**2 <= radius * radius) - r


def _stamp(mask: np.ndarray, line: np.ndarray, disc: np.ndarray) -> None:
    """Every point of a line marked on a mask with the disc round it."""
    h, w = mask.shape
    points = np.round(line).astype(int)
    for dy, dx in disc:
        ys, xs = points[:, 0] + dy, points[:, 1] + dx
        ok = (ys >= 0) & (ys < h) & (xs >= 0) & (xs < w)
        mask[ys[ok], xs[ok]] = True


def _marked(mask: np.ndarray, line: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    points = np.round(line).astype(int)
    ys, xs = np.clip(points[:, 0], 0, h - 1), np.clip(points[:, 1], 0, w - 1)
    return mask[ys, xs]


def _ink_at(line: np.ndarray, od: np.ndarray) -> np.ndarray:
    """The darkness at each point of a line, the most within a pixel of it."""
    h, w = od.shape
    points = np.round(line).astype(int)
    best = np.zeros(len(points), np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ys = np.clip(points[:, 0] + dy, 0, h - 1)
            xs = np.clip(points[:, 1] + dx, 0, w - 1)
            best = np.maximum(best, od[ys, xs])
    return best


def _inked_runs(paths, od: np.ndarray, floor: float):
    """Each path cut where the ink itself is gone for more than two pixels
    running: the oriented filter sums a line along its length, and so runs
    a dashed line's dashes into one stroke over the paper between them.
    Gone is below the floor, or below a third of the path's own darkness —
    JPEG's halo round a dark dash lies over the paper between two."""
    for path in paths:
        if len(path) < 6:
            yield path
            continue
        along = _ink_at(np.array(path, float), od)
        inked = along >= max(floor, _OWN_INK * float(np.median(along)))
        start, gap = 0, 0
        cut = False
        for i, here in enumerate(inked):
            if here:
                if gap > 2:
                    if i - gap - start >= 3:
                        yield path[start : i - gap]
                    start = i
                    cut = True
                gap = 0
            else:
                gap += 1
        if not cut:
            yield path
        elif len(path) - gap - start >= 3:
            yield path[start : len(path) - gap]


def _inked_share(segment: np.ndarray, od: np.ndarray, floor: float) -> float:
    """The share of a gap's middle where there is ink — above the floor
    and a third of the ink at the gap's two ends: a gap is closed where a
    crossing or a faint stretch left one, never across paper."""
    a, b = segment[0], segment[-1]
    n = max(3, int(np.hypot(*(b - a))))
    t = np.linspace(0.2, 0.8, n)[:, None]
    ends = _ink_at(np.array([a, b]), od)
    return float(np.mean(_ink_at(a + (b - a) * t, od) >= max(floor, _OWN_INK * float(ends.min()))))


def _dashes(strokes: list[tuple[np.ndarray, bool]], letter: float) -> set[int]:
    """The strokes that are dashes of a dashed line: three or more short
    straight pieces on one line, a few of their own lengths apart."""
    pieces = []
    for i, (line, closed) in enumerate(strokes):
        if closed:
            continue
        length = _length(line)
        a, b = line[0], line[-1]
        chord = float(np.hypot(*(b - a)))
        if length >= letter or chord < 2:
            continue
        normal = np.array([-(b - a)[1], (b - a)[0]]) / chord
        if float(np.abs((line - a) @ normal).max()) > 1.5:
            continue
        pieces.append((i, a, b, (b - a) / chord, chord))
    parent = {p[0]: p[0] for p in pieces}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for x in range(len(pieces)):
        i, a, b, u, la = pieces[x]
        for y in range(x + 1, len(pieces)):
            j, c, d, v, lb = pieces[y]
            if abs(float(u @ v)) < math.cos(math.radians(12)):
                continue
            normal = np.array([-u[1], u[0]])
            if abs(float((c - a) @ normal)) > 2.0 or abs(float((d - a) @ normal)) > 2.0:
                continue
            # the gap between the two along their line
            ta, tb = sorted([float((a - a) @ u), float((b - a) @ u)])
            tc, td = sorted([float((c - a) @ u), float((d - a) @ u)])
            gap = max(tc - tb, ta - td)
            if 0 < gap <= 2.5 * max(la, lb):
                parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i, _, _, _, _ in pieces:
        groups.setdefault(find(i), []).append(i)
    return {i for members in groups.values() if len(members) >= 3 for i in members}


def _at_corners(line: np.ndarray, closed: bool) -> list[tuple[np.ndarray, bool]]:
    """A stroke cut where it turns sharply: a grid line's stub that met an
    arc's end was one stroke with it, and no straight one. A curve's flat
    stretch has no corner, and stays the curve's."""
    if closed or len(line) < 9:
        return [(line, closed)]
    ahead = line[6:] - line[3:-3]
    behind = line[3:-3] - line[:-6]
    na, nb = np.hypot(*ahead.T), np.hypot(*behind.T)
    ok = (na > 0) & (nb > 0)
    cos = np.ones(len(ahead))
    cos[ok] = np.einsum("ij,ij->i", ahead[ok], behind[ok]) / (na[ok] * nb[ok])
    corners = [i + 3 for i in range(1, len(cos) - 1) if cos[i] < _CORNER_COS and cos[i] <= cos[i - 1] and cos[i] <= cos[i + 1]]
    pieces, start = [], 0
    for c in corners:
        if c - start >= 3:
            pieces.append((line[start : c + 1], False))
            start = c
    pieces.append((line[start:], False))
    return [piece for piece in pieces if len(piece[0]) >= 2]


def _once(strokes: list[tuple[np.ndarray, bool]], shape: tuple[int, int]) -> list[tuple[np.ndarray, bool]]:
    """A stroke traced twice kept once: the longest stand, and one whose
    points mostly lie within reach of those is a second pass."""
    standing = np.zeros(shape, bool)
    disc = _disc(_TWICE_PX)
    kept = []
    for line, closed in sorted(strokes, key=lambda s_: -len(s_[0])):
        if _marked(standing, line).mean() >= _TWICE_SHARE:
            continue
        kept.append((line, closed))
        _stamp(standing, line, disc)
    return kept


def _shaped(line: np.ndarray, closed: bool) -> np.ndarray:
    """Straight where the author's line keeps to its chord; smoothed along
    its length otherwise, round when it closes."""
    steps = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(line, axis=0).T))])
    if steps[-1] >= 1:
        t = np.arange(0, steps[-1], 1.0)
        line = np.stack([np.interp(t, steps, line[:, 0]), np.interp(t, steps, line[:, 1])], 1)
    if len(line) < 4:
        return line
    if not closed:
        a, b = line[0], line[-1]
        chord = float(np.hypot(*(b - a)))
        if chord > 6:
            normal = np.array([-(b - a)[1], (b - a)[0]]) / chord
            if float(np.abs((line - a) @ normal).max()) <= max(_STRAIGHT_PX, _STRAIGHT_SHARE * chord):
                return np.array([a, b])
    r = int(3 * _SMOOTH_PX)
    kernel = np.exp(-0.5 * (np.arange(-r, r + 1) / _SMOOTH_PX) ** 2)
    kernel /= kernel.sum()
    if closed:
        core = line[:-1]
        if len(core) <= 2 * r:
            return line
        ring = np.concatenate([core[-r:], core, core[:r]])
        smooth = np.stack([np.convolve(ring[:, i], kernel, mode="valid") for i in (0, 1)], 1)
        return np.concatenate([smooth, smooth[:1]])
    if len(line) <= 2 * r:
        return line
    padded = np.concatenate([np.repeat(line[:1], r, 0), line, np.repeat(line[-1:], r, 0)])
    smooth = np.stack([np.convolve(padded[:, i], kernel, mode="valid") for i in (0, 1)], 1)
    weight = np.clip(np.minimum(np.arange(len(line)), np.arange(len(line))[::-1]) / r, 0, 1)[:, None]
    return line * (1 - weight) + smooth * weight


def _straight_family(line: np.ndarray) -> str | None:
    """"h" or "v" for a straight path along the page's axes, else None."""
    a, b = line[0], line[-1]
    chord = float(np.hypot(*(b - a)))
    if chord < 3:
        return None
    normal = np.array([-(b - a)[1], (b - a)[0]]) / chord
    if float(np.abs((line - a) @ normal).max()) > 1.6:
        return None
    angle = math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 180
    if min(angle, 180 - angle) < 8:
        return "h"
    if abs(angle - 90) < 8:
        return "v"
    return None


def _from_grid(line: np.ndarray, coefs: list[np.ndarray], family: str) -> float:
    """How far a path lies from the nearest grid line of its family."""
    if not coefs:
        return math.inf
    y, x = (line[:, 0], line[:, 1]) if family == "h" else (line[:, 1], line[:, 0])
    d = np.abs(np.stack([np.polyval(c, x) for c in coefs]) - y[None, :])
    return float(np.median(d.min(0)))


def _line_darkness(coef: np.ndarray, family: str, raw: np.ndarray) -> float | None:
    h, w = raw.shape
    n, limit = (w, h) if family == "h" else (h, w)
    t = np.arange(n)
    at = np.round(np.polyval(coef, t.astype(float))).astype(int)
    ok = (at >= 1) & (at < limit - 1)
    if ok.sum() < 10:
        return None
    if family == "h":
        values = np.max(np.stack([raw[at[ok] + o, t[ok]] for o in (-1, 0, 1)]), 0)
    else:
        values = np.max(np.stack([raw[t[ok], at[ok] + o] for o in (-1, 0, 1)]), 0)
    return float(np.median(values))


def _darker_than_grid(line: np.ndarray, coefs: list[np.ndarray], family: str, raw: np.ndarray) -> float:
    """How much darker a path is than the grid lines beside the one it lies
    on — its neighbours, since the line itself may be the author's axis."""
    h, w = raw.shape
    y, x = (line[:, 0], line[:, 1]) if family == "h" else (line[:, 1], line[:, 0])
    nearest = int(np.argmin(np.median(np.abs(np.stack([np.polyval(c, x) for c in coefs]) - y[None, :]), 1)))
    middle = (w if family == "h" else h) / 2
    order = sorted(range(len(coefs)), key=lambda j: float(np.polyval(coefs[j], middle)))
    place = order.index(nearest)
    values = [
        v
        for v in (_line_darkness(coefs[order[j]], family, raw) for j in range(max(0, place - 3), min(len(order), place + 4)) if j != place)
        if v is not None
    ]
    if not values:
        return math.inf
    here = []
    for py, px in line.astype(int):
        rows = [py - 1, py, py + 1] if family == "h" else [py]
        cols = [px] if family == "h" else [px - 1, px, px + 1]
        here.append(max(raw[min(max(a, 0), h - 1), min(max(b, 0), w - 1)] for a in rows for b in cols))
    return float(np.mean(here)) / max(float(np.median(values)), 1e-3)


# ── One drawing ──────────────────────────────────────────────────────────────


def redraw(page: Page, sketch: Sketch) -> Redrawn:
    """One drawing drawn again from the page. Never raises: whatever fails
    leaves the drawing to its words."""
    try:
        return _redraw(page, sketch)
    except Exception:
        logger.warning("strokes: a drawing could not be drawn again", exc_info=True)
        return Redrawn(None, "failed")


def _redraw(page: Page, sketch: Sketch) -> Redrawn:
    width, height = page.width, page.height
    t, l, b, r = sketch.frame
    if b - t < _MIN_SIDE * 1000 or r - l < _MIN_SIDE * 1000:
        return Redrawn(None, "frame too small")
    if (b - t) * (r - l) > _MAX_AREA * 1000 * 1000:
        return Redrawn(None, "frame too large")
    letter = _LETTER * max(width, height)

    def px(frame):
        return (frame[0] / 1000 * height, frame[1] / 1000 * width, frame[2] / 1000 * height, frame[3] / 1000 * width)

    # the strokes are traced over the frame and a few letters round it, so
    # one running past a tight frame is traced whole; the grid over a wider
    # window still, so its lines are measured past the drawing
    outer = px(sketch.frame)
    reach, context = int(_REACH_LETTERS * letter), int(_CONTEXT_LETTERS * letter)
    region = (
        max(0, int(outer[1]) - reach), max(0, int(outer[0]) - reach),
        min(width, int(outer[3]) + reach), min(height, int(outer[2]) + reach),
    )
    around = (
        max(0, region[0] - context), max(0, region[1] - context),
        min(width, region[2] + context), min(height, region[3] + context),
    )
    window = (slice(around[1], around[3]), slice(around[0], around[2]))
    paper = page.paper[window]
    darkness = page.darkness[window] * paper
    raw = (-np.log(np.clip(1 - darkness, 0.02, 1))).astype(np.float32)
    across_rows, period_rows = _grid_lines(darkness)
    across_cols, period_cols = _grid_lines(darkness.T)
    periods = [p for p in (period_rows, period_cols) if p]
    period = float(np.mean(periods)) if periods else 0.0
    od = _take_grid_off(raw, across_rows)
    od = _take_grid_off(od.T, across_cols).T
    z, direction = _ridges(od)
    z = _silence_grid(z, direction, across_rows, transpose=False)
    z = _silence_grid(z, direction, across_cols, transpose=True)
    off_paper = np.asarray(Image.fromarray(((~paper) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)), bool)
    z[off_paper] = 0
    crests = _crests(z, direction)
    oy, ox = region[1] - around[1], region[0] - around[0]
    hr, wr = region[3] - region[1], region[2] - region[0]
    cut = (slice(oy, oy + hr), slice(ox, ox + wr))
    crests, od, raw = crests[cut], od[cut], raw[cut]

    # the grid in the region's own coordinates: x and y shifted in each quadratic
    def shifted(c, dx, dy):
        return np.array([c[0], c[1] + 2 * c[0] * dx, c[2] + c[1] * dx + c[0] * dx * dx - dy])

    rows = [shifted(c, ox, oy) for c in across_rows]
    cols = [shifted(c, oy, ox) for c in across_cols]
    found = _ink(od)
    if found is None:
        return Redrawn(None, "mostly ink")
    blobs, level = found
    blob_labels, _ = _components(blobs)
    # what counts as ink along a line: above the paper's own grain, and a
    # tenth of the drawing's darkest stroke — the filter that finds a faint
    # stroke also runs on across a dashed line's gaps, where there is none
    paper_od = od[~np.asarray(Image.fromarray((blobs * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)), bool)]
    grain = 1.4826 * float(np.median(np.abs(paper_od - np.median(paper_od)))) if paper_od.size else 0.0
    ink_floor = max(3.0 * grain, _INK_SHARE * level)
    blob_pieces = list(_pieces(blob_labels).values())

    def local(frame, slack):
        top, left, bottom, right = px(frame)
        return (top - region[1] - slack, left - region[0] - slack, bottom - region[1] + slack, right - region[0] + slack)

    framed = local(sketch.frame, 0.3 * letter)
    inner = local(sketch.inner, 0.3 * letter)

    def within(box_, y, x):
        return box_[0] <= y <= box_[2] and box_[1] <= x <= box_[3]

    # the labels the runs read alike: the handwriting under each goes — its
    # letters, not the strokes that pass through its box — and the label is
    # set where it stood; never where nothing is written
    gone = np.zeros(crests.shape, bool)
    placed: list[tuple[str, float, float]] = []
    for label in sketch.labels:
        top, left, bottom, right = px(label.box)
        y0, x0 = max(0, int(round(top - region[1]))), max(0, int(round(left - region[0])))
        y1, x1 = min(hr - 1, int(round(bottom - region[1]))), min(wr - 1, int(round(right - region[0])))
        if y1 <= y0 or x1 <= x0:
            continue
        written = blobs[y0 : y1 + 1, x0 : x1 + 1]
        if written.sum() < 6:
            continue
        gy, gx = np.nonzero(written)
        e = 0.25 * (y1 - y0) + 1
        letters = np.zeros(crests.shape, bool)
        for ys, xs in blob_pieces:
            share = float(np.mean((ys >= y0 - e) & (ys <= y1 + e) & (xs >= x0 - e) & (xs <= x1 + e)))
            if share >= 0.6 and ys.max() - ys.min() <= 2.0 * (y1 - y0 + 2 * e):
                letters[ys, xs] = True
        if written.sum() > letters[y0 : y1 + 1, x0 : x1 + 1].sum():
            # a letter written against a stroke is one piece with it: the box
            # goes, and the label's patch of paper covers the stroke there
            letters[y0 : y1 + 1, x0 : x1 + 1] = True
        gone |= letters
        anchor = (y0 + (gy.min() + gy.max()) / 2, x0 + (gx.min() + gx.max()) / 2)
        # one place holds one label: the same one twice, or two the runs
        # read differently there, never
        if any(
            math.hypot(y - anchor[0], x - anchor[1]) < (1.5 if text == label.text else 0.8) * letter
            for text, y, x in placed
        ):
            continue
        placed.append((label.text, anchor[0], anchor[1]))
    gone = np.asarray(Image.fromarray((gone * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)), bool)
    crests &= ~gone

    # points: a spot of ink thicker and rounder than a stroke
    dots = []
    if blobs.any():
        dense = od > 0.8 * float(np.percentile(od[blobs], 90))
        dense = np.asarray(Image.fromarray((dense * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)), bool)
        dense_labels, _ = _components(dense)
        for ys, xs in _pieces(dense_labels).values():
            tall, wide = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
            cy, cx = float(ys.mean()), float(xs.mean())
            # a point survives the erosion as a spot of five pixels at least;
            # a dark stretch of a stroke, as a sliver
            if (
                len(ys) >= _DOT_PX
                and max(tall, wide) <= 0.35 * letter
                and max(tall, wide) <= 1.6 * min(tall, wide) + 1
                and not gone[int(cy), int(cx)]
                and within(inner, cy, cx)
            ):
                dots.append((cy, cx))
        # the point is drawn as a dot: the crests its blot left go
        for cy, cx in dots:
            r = int(round(0.2 * letter))
            crests[max(0, int(cy) - r) : int(cy) + r + 1, max(0, int(cx) - r) : int(cx) + r + 1] = False

    skeleton = _thin(crests)
    paths, branches = _paths(skeleton)
    if len(paths) > _MAX_PATHS:
        return Redrawn(None, f"{len(paths)} pieces of line")
    kept: list[np.ndarray] = []
    for path in _inked_runs(paths, od, ink_floor):
        line = np.array(path, float)
        length = _length(line)
        first, last = branches[path[0]], branches[path[-1]]
        if length < _SPUR_PX and ((first == 1 and last >= 3) or (last == 1 and first >= 3)):
            continue
        if length < _SPECK_PX and first <= 1 and last <= 1:
            continue
        # a long path is the drawing's when most of it lies in a frame some
        # two runs gave; a short mark only inside what they all hold — past
        # that it is the text round the drawing
        if length >= 2 * letter:
            inside = (line[:, 0] >= framed[0]) & (line[:, 0] <= framed[2]) & (line[:, 1] >= framed[1]) & (line[:, 1] <= framed[3])
            if inside.mean() < 0.5:
                continue
        elif not within(inner, float(line[:, 0].mean()), float(line[:, 1].mean())):
            continue
        kept.append(line)
    bridges = [
        bridge for bridge in _bridges(kept, branches, skeleton, _GAP_LETTERS * letter)
        if _inked_share(bridge, od, ink_floor) >= 0.5
    ]
    strokes = [
        piece
        for line, closed in _strokes(kept + bridges)
        for piece in _at_corners(line, closed)
    ]
    dashed = _dashes(strokes, letter)

    # whole strokes judged: straight along a grid line and no darker than the
    # grid beside it is the grid; a lone straight dash along the page's axes
    # shorter than a square is too; and a small mark at the frame's edge,
    # touching nothing long, is the text round it. A curve's flat stretch is
    # no stroke of its own, so it is never judged alone.
    near_long = np.zeros((hr, wr), bool)
    disc = _disc(3.0)
    for line, _ in strokes:
        if _length(line) >= 2 * letter:
            _stamp(near_long, line, disc)
    judged = []
    for index, (line, closed) in enumerate(strokes):
        length = _length(line)
        family = None if closed else _straight_family(line)
        if family is not None:
            coefs = rows if family == "h" else cols
            if _from_grid(line, coefs, family) <= _ON_GRID_PX and _darker_than_grid(line, coefs, family, raw) < _DARKER_THAN_GRID:
                continue
            if period and length < period and not _touches(line, near_long) and index not in dashed:
                continue
            # a straight edge mostly past what every run framed: the page's
            # edge, a rule under the text — the drawing's own axes and
            # segments stand inside it
            outside = ~((line[:, 0] >= inner[0]) & (line[:, 0] <= inner[2]) & (line[:, 1] >= inner[1]) & (line[:, 1] <= inner[3]))
            if outside.mean() > 0.5:
                continue
        if length < _EDGE_MARK_LETTERS * letter and near_long.any() and not _touches(line, near_long):
            cy, cx = float(line[:, 0].mean()), float(line[:, 1].mean())
            if min(cy - inner[0], inner[2] - cy, cx - inner[1], inner[3] - cx) < 0.6 * letter:
                continue
        judged.append((line, closed, index in dashed))
    # a dash is known by its array: _once passes the strokes it keeps through
    dash_ids = {id(line) for line, _, dash in judged if dash}
    strokes = _once([(line, closed) for line, closed, _ in judged], (hr, wr))

    def is_dash(line):
        return id(line) in dash_ids

    total = sum(_length(line) for line, _ in strokes)
    if total < _MIN_LENGTH_LETTERS * letter:
        return Redrawn(None, "too little drawn")
    # a dashed line's dashes are the author's pattern, not pieces
    short = sum(
        _length(line) for line, closed in strokes if not closed and _length(line) < letter and not is_dash(line)
    )
    short_straight = sum(
        _length(line)
        for line, closed in strokes
        if not closed and _length(line) < 3 * letter and _straight_family(line) is not None and not is_dash(line)
    )
    along = sum(
        _length(line)
        for line, closed in strokes
        if not closed
        and (family := _straight_family(line)) is not None
        and _from_grid(line, rows if family == "h" else cols, family) <= _ON_GRID_PX
    )
    if short / total > _MAX_SHORT:
        return Redrawn(None, f"in pieces, {short / total:.2f}")
    if short_straight / total > _MAX_SHORT_STRAIGHT:
        return Redrawn(None, f"in square pieces, {short_straight / total:.2f}")
    if along / total > _MAX_ALONG_GRID:
        return Redrawn(None, f"along the grid, {along / total:.2f}")

    # the picture is what was drawn, wherever the frame stood
    shaped = [_shaped(line, closed) for line, closed in strokes]
    ys = np.concatenate([line[:, 0] for line in shaped] + [np.array([y for y, _ in dots] + [y for _, y, _ in placed])])
    xs = np.concatenate([line[:, 1] for line in shaped] + [np.array([x for _, x in dots] + [x for _, _, x in placed])])
    pad = 0.6 * letter
    top, left = max(0.0, float(ys.min()) - pad), max(0.0, float(xs.min()) - pad)
    bottom, right = min(float(hr), float(ys.max()) + pad), min(float(wr), float(xs.max()) + pad)
    shift = np.array([top, left])
    png = _drawn(
        [line - shift for line in shaped],
        [(y - top, x - left) for y, x in dots],
        [(text, y - top, x - left) for text, y, x in placed],
        (bottom - top, right - left),
        _PAGE_PT / max(width, height),
    )
    return Redrawn(png, "drawn", len(placed))


def _touches(line: np.ndarray, near_long: np.ndarray) -> bool:
    """Whether a stroke comes within three pixels of a long one, marked."""
    return bool(_marked(near_long, line).any())


def _drawn(lines, dots, labels, size, points_per_px) -> bytes:
    """The drawing as the document prints it: its darkness, 255 the ink, at
    the size it had on the page, its resolution written into the PNG so the
    document sets it at that size. One document's formulas at a time: the
    labels go through matplotlib's one parser (pdf._DRAWING)."""
    from app.services import pdf

    import matplotlib.pyplot as plt

    h, w = size
    buffer = io.BytesIO()
    # A label mathtext will not draw is written in characters rather than
    # costing the drawing, as a chart's name is.
    for plain in (False, True):
        with pdf._DRAWING:
            figure = plt.figure(figsize=(w * points_per_px / 72, h * points_per_px / 72), dpi=_DPI)
            try:
                axes = figure.add_axes((0, 0, 1, 1))
                axes.set_xlim(0, w)
                axes.set_ylim(h, 0)
                axes.axis("off")
                for line in lines:
                    axes.plot(
                        line[:, 1], line[:, 0], color="black", lw=_LINE_PT,
                        solid_capstyle="round", solid_joinstyle="round",
                    )
                for y, x in dots:
                    axes.add_patch(plt.Circle((x, y), _DOT_PT / points_per_px, color="black", lw=0))
                for text, y, x in labels:
                    pdf.chart_label(axes, x, y, text, _LABEL_PT, plain=plain)
                buffer = io.BytesIO()
                figure.savefig(buffer, format="png", dpi=_DPI, facecolor="white")
                break
            except Exception:
                if plain:
                    raise
                logger.info("strokes: a label mathtext would not draw, written in characters")
            finally:
                plt.close(figure)
    with Image.open(io.BytesIO(buffer.getvalue())) as rendered:
        darkness = Image.fromarray(255 - np.asarray(rendered.convert("L")))
    out = io.BytesIO()
    darkness.save(out, format="PNG", optimize=True, dpi=(_DPI, _DPI))
    return out.getvalue()
