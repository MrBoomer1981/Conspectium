r"""A drawing that is data (task 94): what its line says, whether the runs
read it alike, and how it reads where it is not drawn.

Record 97 printed «схема: график параболы $y = x^2$ …», «схема: числовая
прямая … множествами X, Y и точкой c» and «схема: отображение множества A в
B со стрелками», and its author read them as the bot failing to draw the
drawings. Much of what a lecture draws is data, and data is drawn by code, the
way a graph is drawn from its edges (`[граф: 1-2]`) and was never a picture
of the model's. From `prompts-v10.md` on, recognition writes three kinds of
drawing as data, each on a line of its own:

- `[график: y = x^2; x от -2 до 2]` — a function's graph by its formula; a
  sequence, `x_n = …`, as its points; a constant as a level, dashed;
- `[прямая: 0, c, X = [0; c), (c; +\infty)]` — a number line: its points
  from left to right, its intervals and rays, «множество X» for a set whose
  ends the drawing does not name;
- `[отображение: A -> B; 1 -> a, 2 -> a, 3 -> b, c]` — a mapping: its
  arrows, an element of B no arrow comes to, «3 ->» for one of A with none
  going out, «•1» for a dot with no name.

Everything else a page draws stays `[схема: …]`, the words it always was.

What is drawn is what the data says, and the data is a reading: an invented
point or arrow is drawn as confidently as a real one, and nothing in the
picture tells them apart. So a drawing is drawn only when another run read
the same data (`agreed`) — the one signal that has proved reliable, as for
where a lecture begins — and otherwise goes into the record as the words
`[схема: …]`, which is what it was before. The runs' ranges are not
compared: where a curve is drawn from is the author's choice, what it is is
not.

This module reads; `pdf.py` draws, under its lock. Nothing here raises on
what a model wrote: a line that does not read is None, and the document
prints its words.
"""

from __future__ import annotations

import math
import random
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from app.services import algebracheck

PLOT = "plot"
LINE = "line"
MAPPING = "mapping"

# The words a drawing of data opens with. «Ось» and «числовая прямая» are
# what a reading may write for «прямая» — the model's own words for it, as
# record 97's descriptions show.
_KIND_OF = {
    "график": PLOT,
    "прямая": LINE,
    "числовая прямая": LINE,
    "числовая ось": LINE,
    "ось": LINE,
    "отображение": MAPPING,
}
_WORDS = r"график|числовая\s+прямая|числовая\s+ось|прямая|ось|отображение"
# «график функции:», «график последовательности:» — a reading's words for
# what it is, which say nothing the data does not.
_QUALIFIER = r"(?:\s+(?:функции|последовательности))?"
_TAG_RE = re.compile(rf"\[\s*(?P<word>{_WORDS}){_QUALIFIER}\s*:", re.IGNORECASE)
_INNER_RE = re.compile(
    rf"^\s*(?P<word>{_WORDS}){_QUALIFIER}\s*:\s*(?P<spec>.*?)\s*$", re.IGNORECASE | re.DOTALL
)
# How a drawing that is not drawn reads in the record: as the drawing it is,
# in words, as a description always was.
_DESCRIBED = {PLOT: "график", LINE: "числовая прямая", MAPPING: "отображение"}

# What stands in a chart's place while the composer works: it keeps
# «[схема: …]» as it is (rule of prompts-compose-v4.md), and a number in it is
# one the numbers guard counts, so a composition that drops it is refused.
_HELD = "[схема: рисунок данными {}]"

# Past these a drawing is unreadable, or the line is not what it says.
_MAX_POINTS = 12
_MAX_ELEMENTS = 8
_MAX_LABEL_CHARS = 24
_MAX_CURVES = 4
_MAX_SPAN = 1e4
_MAX_TERMS = 40

# Where a graph is drawn when its line does not say: a function round the
# origin, a sequence from its first term.
DEFAULT_RANGE = (-3.0, 3.0)
DEFAULT_TERMS = 10
# Letters that name a sequence's index rather than a function's argument.
_INDICES = frozenset("nkm")
# Where two curves are compared: the same formula comes to the same numbers
# there whichever way it was written, x^2 or x \cdot x.
_PROBES = (-2.31, -1.17, -0.43, 0.61, 1.39, 2.53)
_TERM_PROBES = (1, 2, 3, 4, 6, 9)


@dataclass
class Curve:
    label: str  # the left side as written, "y", "f(x)", "x_n"
    formula: str  # the right side as written
    tree: tuple = field(repr=False, compare=False, default=())
    level: bool = False  # a constant: a level, drawn dashed


@dataclass
class Plot:
    curves: list[Curve]
    variable: str
    low: float
    high: float
    terms: bool  # a sequence: drawn at whole numbers, as points


@dataclass
class Point:
    label: str  # "" for an end the drawing does not name
    value: float | None = None


@dataclass
class Interval:
    left: int | None  # a point's index; None: from −∞
    right: int | None  # None: to +∞
    closed_left: bool
    closed_right: bool
    name: str = ""


@dataclass
class NumberLine:
    points: list[Point]  # left to right
    intervals: list[Interval]
    scaled: bool  # every point a number: placed by its value


@dataclass
class Mapping:
    name: str  # "f", or ""
    domain: str  # "A", or ""
    codomain: str
    left: list[str]  # top to bottom; "•1" is a dot with no name
    right: list[str]
    arrows: list[tuple[int, int]]


Chart = Plot | NumberLine | Mapping


# ── Where a chart stands in a text ──────────────────────────────────────────


def spans(text: str) -> list[tuple[int, int, str]]:
    """Every chart in `text`: where it begins, where it ends, and its kind.

    Its brackets are counted, since an interval's are its own — «X = [0; c)»
    inside «[прямая: …]» — so a closing one is the chart's only at depth
    zero. A chart never crosses a line; one whose brackets do not balance
    ends at the last «]» of its line, or is no chart."""
    found: list[tuple[int, int, str]] = []
    for match in _TAG_RE.finditer(text):
        if found and match.start() < found[-1][1]:
            continue
        depth, index, end = 1, match.end(), None
        while index < len(text) and text[index] != "\n":
            char = text[index]
            if char in "([":
                depth += 1
            elif char in ")]":
                depth -= 1
                if depth == 0:
                    end = index + 1 if char == "]" else None
                    break
            index += 1
        if end is None:
            line_end = text.find("\n", match.end())
            line_end = len(text) if line_end == -1 else line_end
            close = text.rfind("]", match.end(), line_end)
            if close == -1:
                continue
            end = close + 1
        found.append((match.start(), end, _kind(match.group("word"))))
    return found


def _kind(word: str) -> str:
    return _KIND_OF[" ".join(word.lower().split())]


def read(inner: str) -> tuple[str, str] | None:
    """A bracketed line's inside as (kind, spec), when it is a chart."""
    found = _INNER_RE.match(inner)
    if found is None:
        return None
    return _kind(found.group("word")), found.group("spec")


def count(markdown: str) -> int:
    """How many charts a record carries — `note_processed.charts`."""
    return len(spans(markdown))


def blanked(text: str) -> str:
    """`text` with every chart taken out, its line left in place: a chart's
    data is not the lecture's arithmetic, and «y = x^2» in it is no equality
    a check should count."""
    out, last = [], 0
    for start, end, _kind_ in spans(text):
        out.append(text[last:start])
        last = end
    out.append(text[last:])
    return "".join(out)


# ── While the composer works ────────────────────────────────────────────────


def held(markdown: str) -> tuple[str, list[str]]:
    """The text with every chart replaced by a line the composer keeps, and
    the charts in their order. The composer never sees a chart's data: it
    sets out text, and a formula in a chart is the drawing's, which rule 4 of
    the composing prompt would set apart as the lecture's."""
    charts: list[str] = []
    out, last = [], 0
    for start, end, _kind_ in spans(markdown):
        charts.append(markdown[start:end])
        out.append(markdown[last:start])
        out.append(_HELD.format(len(charts)))
        last = end
    out.append(markdown[last:])
    return "".join(out), charts


def lost(composed: str, charts: Sequence[str]) -> bool:
    """Whether a composition lost the place of a chart, changed it, or
    wrote it twice — the second would stay in the record as its words."""
    return any(
        composed.count(_HELD.format(number)) != 1 for number in range(1, len(charts) + 1)
    )


def restored(markdown: str, charts: Sequence[str]) -> str:
    """The charts back in their places."""
    for number, chart in enumerate(charts, 1):
        markdown = markdown.replace(_HELD.format(number), chart, 1)
    return markdown


# ── Reading a chart ─────────────────────────────────────────────────────────


def parse(kind: str, spec: str) -> Chart | None:
    """A chart's data, or None when it does not read as one. Never raises."""
    try:
        if kind == PLOT:
            return _plot(spec)
        if kind == LINE:
            return _number_line(spec)
        if kind == MAPPING:
            return _mapping(spec)
    except Exception:
        return None
    return None


_OPENING = "([{"
_CLOSING = ")]}"


def _split(text: str, separators: str) -> list[str]:
    """`text` cut at every separator outside brackets: an interval's «;» and
    a set's «,» are their own."""
    parts: list[str] = []
    depth, start = 0, 0
    for index, char in enumerate(text):
        if char in _OPENING:
            depth += 1
        elif char in _CLOSING:
            depth = max(0, depth - 1)
        elif char in separators and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return [part.strip() for part in parts if part.strip()]


def _bare(text: str) -> str:
    """A piece of a chart without the dollars a reading may put round it."""
    return text.replace("$", "").strip()


# The LaTeX a graph's formula is written in, made what algebracheck reads.
_PLAIN_FORMULA = (
    (re.compile(r"\\left\s*\||\\right\s*\||\\[lr]vert|\\vert|\\mid"), "|"),
    (re.compile(r"\\left\s*([(\[])|\\right\s*([)\]])"), r"\1\2"),
    (re.compile(r"\\(?:left|right)\s*\.?"), ""),
    (re.compile(r"\\(?:times|ast)(?![A-Za-z])"), r"\\cdot"),
    (re.compile(r"(\d)\{,\}(\d)"), r"\1.\2"),
    (re.compile(r"\\operatorname\{(\w+)\}"), r"\\\1"),
    (re.compile(r"[−–]"), "-"),
)
# What a graph's formula may call, by the name it is written with.
_FUNCTIONS = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan, "tg": np.tan,
    "cot": lambda v: 1 / np.tan(v), "ctg": lambda v: 1 / np.tan(v),
    "arcsin": np.arcsin, "arccos": np.arccos, "arctan": np.arctan, "arctg": np.arctan,
    "ln": np.log, "log": np.log, "lg": np.log10, "exp": np.exp,
    "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh, "sh": np.sinh, "ch": np.cosh,
    "sgn": np.sign, "abs": np.abs,
}


class _Reader(algebracheck._Reader):
    """algebracheck's reading of one side of an equality, and what a graph's
    formula has besides: |x|, more functions, \\sin^2 x, «sin x» written
    without its backslash. The tree is algebracheck's."""

    def __init__(self, tokens):
        super().__init__(tokens)
        self.bars = 0

    def _function(self, token) -> str | None:
        if token.kind == "command" and token.text[1:] in _FUNCTIONS:
            return token.text[1:]
        if token.kind == "word" and token.text in _FUNCTIONS:
            return token.text
        return None

    def starts_atom(self, token) -> bool:
        if token.text == "|":
            return self.bars == 0
        if self._function(token) is not None:
            return True
        return super().starts_atom(token)

    def atom(self):
        token = self.peek()
        if token is not None and token.text == "|" and self.bars == 0:
            self.take()
            self.bars += 1
            inner = self.sum()
            self.expect("|")
            self.bars -= 1
            return ("fn", "abs", inner)
        if token is not None:
            name = self._function(token)
            if name is not None:
                self.take()
                following = self.peek()
                if following is not None and following.text == "^":
                    self.take()
                    power = self.exponent()
                    return ("pow", ("fn", name, self.power()), power)
                return ("fn", name, self.power())
        return super().atom()


def _tree(latex: str):
    """A formula read into algebracheck's tree, or None."""
    for pattern, put in _PLAIN_FORMULA:
        latex = pattern.sub(put, latex)
    try:
        return _Reader(algebracheck._tokens(latex)).whole()
    except Exception:
        return None


def _letters(node) -> set[str]:
    kind = node[0]
    if kind == "num":
        return set()
    if kind == "sym":
        return {node[1]}
    if kind == "fn":
        return _letters(node[2])
    return set().union(*(_letters(part) for part in node[1:]))


def _evaluate(node, letters: dict, like):
    """The tree counted with every letter at its values in `letters`, NaN
    where it is not defined; `like` is the shape a constant takes. «e» not
    given is Euler's number."""
    kind = node[0]
    if kind == "num":
        return float(node[1]) + 0 * like
    if kind == "sym":
        if node[1] in letters:
            return letters[node[1]]
        if node[1] == "e":
            return math.e + 0 * like
        raise ValueError(f"a letter with no value: {node[1]}")
    if kind == "neg":
        return -_evaluate(node[1], letters, like)
    if kind == "fn":
        return _FUNCTIONS[node[1]](_evaluate(node[2], letters, like))
    if kind == "root":
        degree = _evaluate(node[1], letters, like)
        radicand = _evaluate(node[2], letters, like)
        odd = np.isclose(degree % 2, 1)
        return np.where(
            odd,
            np.sign(radicand) * np.abs(radicand) ** (1 / degree),
            np.where(radicand >= 0, np.abs(radicand) ** (1 / degree), np.nan),
        )
    a = _evaluate(node[1], letters, like)
    b = _evaluate(node[2], letters, like)
    if kind == "add":
        return a + b
    if kind == "sub":
        return a - b
    if kind == "mul":
        return a * b
    if kind == "div":
        return np.where(b == 0, np.nan, a / np.where(b == 0, 1, b))
    if kind == "pow":
        return np.power(a, b)
    raise ValueError(kind)


def values(curve: Curve, variable: str, at) -> np.ndarray:
    """A curve counted at `at`: NaN where it is undefined or infinite."""
    at = np.asarray(at, dtype=float)
    with np.errstate(all="ignore"):
        try:
            counted = np.asarray(_evaluate(curve.tree, {variable: at}, at), dtype=float)
        except (ValueError, KeyError, TypeError, ArithmeticError):
            return np.full(at.shape, np.nan)
    counted = np.broadcast_to(counted, at.shape).copy()
    counted[~np.isfinite(counted)] = np.nan
    return counted


def _number(text: str) -> float | None:
    """A label's value when it is a number — «0», «-2», «\\frac{1}{2}», «\\pi»."""
    text = _bare(text)
    if not text:
        return None
    tree = _tree(text)
    if tree is None or _letters(tree):
        return None
    with np.errstate(all="ignore"):
        try:
            value = float(_evaluate(tree, {}, np.zeros(1))[0])
        except (ValueError, KeyError, TypeError, ArithmeticError):
            return None
    return value if math.isfinite(value) else None


_RANGE_RE = re.compile(
    r"^(?P<variable>[A-Za-z])\s*(?:от|from)\s+(?P<low>.+?)\s+(?:до|to)\s+(?P<high>.+)$",
    re.IGNORECASE,
)
_RANGE_IN_RE = re.compile(
    r"^(?P<variable>[A-Za-z])\s*(?:\\in|∈)\s*[\[(]\s*(?P<low>[^;,]+?)\s*[;,]\s*(?P<high>[^;,]+?)\s*[\])]$"
)
_BOUNDS_RE = re.compile(
    r"^(?P<low>[^<≤⩽\\]+?)\s*(?:<|≤|⩽|\\le(?:q|qslant)?)\s*(?P<variable>[A-Za-z])\s*"
    r"(?:<|≤|⩽|\\le(?:q|qslant)?)\s*(?P<high>.+)$"
)
# A sequence's term named by its index, «x_n», «a_{k}».
_TERM_LABEL_RE = re.compile(r"^[A-Za-z]_\{?([nkm])\}?$")


def _bound(text: str) -> float | None | bool:
    """A range's end: its number, None for an infinity — the default on that
    side — or False when it is neither."""
    text = _bare(text)
    if _INFINITY_RE.match(text):
        return None
    value = _number(text)
    return False if value is None else value


def _plot(spec: str) -> Plot | None:
    curves: list[Curve] = []
    variable: str | None = None
    low = high = None
    for piece in _split(_bare(spec), ";,"):
        bounds = None
        for pattern in (_RANGE_RE, _RANGE_IN_RE, _BOUNDS_RE):
            bounds = pattern.match(piece)
            if bounds is not None:
                break
        if bounds is not None:
            variable = bounds.group("variable")
            low, high = _bound(bounds.group("low")), _bound(bounds.group("high"))
            if low is False or high is False:
                return None
            continue
        if "=" not in piece:
            return None
        label, _, formula = piece.rpartition("=")
        label, formula = label.strip(), formula.strip()
        tree = _tree(formula)
        if not label or tree is None:
            return None
        curves.append(Curve(label, formula, tree))
    if not curves or len(curves) > _MAX_CURVES:
        return None

    letters = set().union(*(_letters(curve.tree) for curve in curves)) - {"e"}
    if variable is None:
        if len(letters) != 1:
            return None
        variable = next(iter(letters))
    elif not letters <= {variable}:
        return None
    for curve in curves:
        curve.level = variable not in _letters(curve.tree)
    if all(curve.level for curve in curves):
        return None

    terms = variable in _INDICES or any(
        _TERM_LABEL_RE.match(curve.label.replace(" ", "")) for curve in curves
    )
    if terms:
        low = 1.0 if low is None else math.ceil(low)
        high = low + DEFAULT_TERMS - 1 if high is None else math.floor(high)
        high = min(high, low + _MAX_TERMS - 1)
    elif low is not None and high is None:
        high = low + (DEFAULT_RANGE[1] - DEFAULT_RANGE[0])
    elif low is None and high is not None:
        low = high - (DEFAULT_RANGE[1] - DEFAULT_RANGE[0])
    elif low is None and high is None:
        low, high = DEFAULT_RANGE
        drawn = [curve for curve in curves if not curve.level]
        everywhere = np.linspace(low, high, 61)
        undefined = np.mean(
            [np.isnan(values(curve, variable, everywhere)).mean() for curve in drawn]
        )
        # A root or a logarithm is drawn where it is defined, not on a page
        # of nothing left of zero.
        if undefined > 0.4:
            low, high = 0.0, 4.0
    if not (math.isfinite(low) and math.isfinite(high)) or high <= low:
        return None
    if high - low > _MAX_SPAN:
        return None
    return Plot(curves, variable, float(low), float(high), terms)


_INFINITY_RE = re.compile(r"^([+-]?)\s*(?:\\infty|∞)$")
# A set whose ends the drawing does not name, written where it stands among
# the points: «множество X», and «отрезок X», «интервал X» as a reading may
# put it — one run of three wrote «отрезок X, c, отрезок Y» for the others'
# «множество X, c, множество Y».
_SET_RE = re.compile(
    r"^(?:множество|мн-во|отрезок|интервал|промежуток)\s+(?P<name>\S.{0,15})$", re.IGNORECASE
)
_INTERVAL_RE = re.compile(
    r"^(?:(?P<name>[^=:\[\]()]{1,16}?)\s*[=:]\s*)?(?P<open>[\[(])(?P<inside>.*)(?P<close>[\])])$"
)


def _end(text: str) -> str | None:
    """An interval's end as written, or None for an infinity."""
    text = _bare(text)
    return None if _INFINITY_RE.match(text) else text


def _number_line(spec: str) -> NumberLine | None:
    listed: list[str] = []  # the labels written as points
    raw: list[tuple] = []  # ("point", label) | ("interval", ...) | ("set", name)
    for item in _split(_bare(spec), ",;"):
        named_set = _SET_RE.match(item)
        if named_set is not None:
            raw.append(("set", _bare(named_set.group("name"))))
            continue
        interval = _INTERVAL_RE.match(item)
        if interval is not None:
            ends = _split(interval.group("inside"), ";")
            if len(ends) != 2:
                ends = _split(interval.group("inside"), ",")
            if len(ends) != 2:
                return None
            left, right = _end(ends[0]), _end(ends[1])
            if left == "" or right == "":
                return None
            raw.append(
                (
                    "interval",
                    left,
                    right,
                    interval.group("open") == "[",
                    interval.group("close") == "]",
                    _bare(interval.group("name") or ""),
                )
            )
            continue
        label = _bare(item)
        if not label or len(label) > _MAX_LABEL_CHARS:
            return None
        raw.append(("point", label))
        listed.append(label)

    # Where the points stand: in the order written, left to right, a set's
    # two unnamed ends where the set is written. An interval's end that is
    # not listed is a reading's slip when other points are — a nested
    # segment's end put after the rest would draw the segments apart — and
    # stands where it comes only when no point is listed at all, or when it
    # is a number.
    order: list[str] = []
    for number, item in enumerate(raw):
        if item[0] == "point":
            if item[1] not in order:
                order.append(item[1])
        elif item[0] == "set":
            order += [f"\0{number}<", f"\0{number}>"]
        else:
            for end in item[1:3]:
                if end is None or end in order or end in listed:
                    continue
                if listed and _number(end) is None:
                    return None
                order.append(end)
    if not order or len(order) > _MAX_POINTS:
        return None
    intervals: list[Interval] = []
    for number, item in enumerate(raw):
        if item[0] == "set":
            intervals.append(
                Interval(order.index(f"\0{number}<"), order.index(f"\0{number}>"), True, True, item[1])
            )
        elif item[0] == "interval":
            _, left, right, closed_left, closed_right, name = item
            intervals.append(
                Interval(
                    None if left is None else order.index(left),
                    None if right is None else order.index(right),
                    closed_left and left is not None,
                    closed_right and right is not None,
                    name,
                )
            )
    points = [
        Point("", None) if label.startswith("\0") else Point(label, _number(label))
        for label in order
    ]

    named = [point for point in points if point.label]
    scaled = (
        len(named) >= 2
        and len(named) == len(points)
        and all(point.value is not None for point in points)
        and len({point.value for point in points}) == len(points)
    )
    if scaled:
        # Numbers stand where their values put them, whatever order a
        # reading listed them in.
        moved = sorted(range(len(points)), key=lambda index: points[index].value)
        where = {old: new for new, old in enumerate(moved)}
        points = [points[old] for old in moved]
        for interval in intervals:
            interval.left = None if interval.left is None else where[interval.left]
            interval.right = None if interval.right is None else where[interval.right]
    for interval in intervals:
        if (
            interval.left is not None
            and interval.right is not None
            and interval.left >= interval.right
        ):
            return None
        if interval.left is None and interval.right is None:
            return None
    return NumberLine(points, intervals, scaled)


_ARROW_RE = re.compile(r"\s*(?:->|→|↦|\\mapsto|\\to(?![A-Za-z])|\\rightarrow|\\longmapsto)\s*")
_HEAD_RE = re.compile(
    r"^(?:(?P<name>[^:]{1,8}?)\s*(?::|\\colon)\s*)?(?P<domain>.+?)"
    r"(?:->|→|\\to(?![A-Za-z])|\\rightarrow|\\longrightarrow)(?P<codomain>.+)$"
)
_ELEMENTS_RE = re.compile(r"^(?P<name>[^=]*?)\s*=?\s*\\?\{(?P<elements>.*)\\?\}$")


def _side(text: str) -> tuple[str, list[str]]:
    """A set as the head names it — «A», or «A = \\{1, 2\\}» with its
    elements."""
    text = _bare(text)
    found = _ELEMENTS_RE.match(text)
    if found is None:
        return text, []
    elements = [_bare(element) for element in _split(found.group("elements").rstrip("\\"), ",")]
    return _bare(found.group("name")), [element for element in elements if element]


def _mapping(spec: str) -> Mapping | None:
    parts = _split(_bare(spec), ";")
    if not parts:
        return None
    name = domain = codomain = ""
    left: list[str] = []
    right: list[str] = []
    head = _HEAD_RE.match(parts[0])
    if head is not None:
        if len(parts) == 1 and "{" not in parts[0]:
            # «A -> B» and nothing more: which elements, and which arrows,
            # the line does not say — two dots and an arrow would be a
            # picture the page did not have.
            return None
        name = _bare(head.group("name") or "")
        domain, left = _side(head.group("domain"))
        codomain, right = _side(head.group("codomain"))
        parts = parts[1:]
    arrows: list[tuple[str, str]] = []
    for part in parts:
        for item in _split(part, ","):
            pair = _ARROW_RE.split(item, maxsplit=1)
            if len(pair) == 1:
                element = _bare(pair[0])
                if element and element not in right:
                    right.append(element)
                continue
            tail, head_ = _bare(pair[0]), _bare(pair[1])
            if tail and tail not in left:
                left.append(tail)
            if head_ and head_ not in right:
                right.append(head_)
            if tail and head_:
                arrows.append((tail, head_))
    labels = left + right + [domain, codomain, name]
    if (
        not arrows
        or not 0 < len(left) <= _MAX_ELEMENTS
        or not 0 < len(right) <= _MAX_ELEMENTS
        or any(len(label) > _MAX_LABEL_CHARS for label in labels)
    ):
        return None
    pairs = []
    for tail, head_ in arrows:
        pair = (left.index(tail), right.index(head_))
        if pair not in pairs:
            pairs.append(pair)
    return Mapping(name, domain, codomain, left, right, pairs)


def unnamed(label: str) -> bool:
    """A dot the drawing gives no name: «•1», «\\bullet 2», «·»."""
    return bool(re.match(r"^(?:•|·|\\bullet|\\cdot)", label))


# ── Whether two runs read one chart ─────────────────────────────────────────


_NORMALS = (
    (re.compile(r"\\(?:var)?epsilon|ϵ"), "ε"),
    (re.compile(r"\\infty"), "∞"),
    (re.compile(r"[−–—]"), "-"),
    (re.compile(r"\\(?:left|right|displaystyle)(?![A-Za-z])|\\[,;:! ]|\s+"), ""),
    (re.compile(r"\{([^{}])\}"), r"\1"),
)


def _normal(label: str) -> str:
    label = _bare(label)
    for pattern, put in _NORMALS:
        label = pattern.sub(put, label)
    return label


def _shown(value: float) -> str:
    return "–" if math.isnan(value) else f"{value:.3g}"


def _signature(plot: Plot) -> tuple:
    """What a graph is, whichever way a reading wrote it: each curve the
    numbers it comes to at a few points — x^2 and x \\cdot x are one curve —
    and not its range, which a reading estimates."""
    probes = _TERM_PROBES if plot.terms else _PROBES
    return (
        plot.terms,
        tuple(
            sorted(
                (curve.level, tuple(_shown(v) for v in values(curve, plot.variable, probes)))
                for curve in plot.curves
            )
        ),
    )


# Where two names are counted to see whether they are one expression.
_ALIKE_POINTS = 3


def _alike(one: str, other: str) -> bool:
    """Whether two readings name one point, element or set: written alike,
    or one expression however written — «\\frac{1}{2}» and «0.5», «1 -
    \\frac{1}{n}» and «1-1/n» — counted at the same random numbers, the way
    algebracheck counts an equality's sides."""
    if _normal(one) == _normal(other):
        return True
    if not one or not other or unnamed(one) or unnamed(other):
        return False
    first, second = _tree(_bare(one)), _tree(_bare(other))
    if first is None or second is None or _letters(first) != _letters(second):
        return False
    chance = random.Random(94)
    like = np.zeros(_ALIKE_POINTS)
    at = {
        letter: np.array([chance.uniform(1.3, 2.9) for _ in range(_ALIKE_POINTS)])
        for letter in sorted(_letters(first))
    }
    with np.errstate(all="ignore"):
        try:
            a = np.asarray(_evaluate(first, at, like), dtype=float)
            b = np.asarray(_evaluate(second, at, like), dtype=float)
        except (ValueError, KeyError, TypeError, ArithmeticError):
            return False
    return bool(np.all(np.isfinite(a)) and np.allclose(a, b, rtol=1e-9, atol=1e-12))


def _matched(ones: list[str], others: list[str]) -> list[int] | None:
    """Which of `others` each of `ones` is, each taken once; None when they
    are not the same elements."""
    if len(ones) != len(others):
        return None
    taken: set[int] = set()
    found: list[int] = []
    for label in ones:
        for index, other in enumerate(others):
            if index not in taken and _alike(label, other):
                taken.add(index)
                found.append(index)
                break
        else:
            return None
    return found


def alike(one: Chart, other: Chart) -> bool:
    """Whether two readings of a drawing read the same data. A number line
    is its points in order — a name alike, an unnamed end on both — and
    what each interval spans and holds; a mapping, its arrows between
    elements that are alike, whatever order the arrows were written in."""
    if type(one) is not type(other):
        return False
    if isinstance(one, Plot):
        return _signature(one) == _signature(other)
    if isinstance(one, NumberLine):
        if len(one.points) != len(other.points):
            return False
        if not all(
            _alike(p.label, q.label) if p.label and q.label else p.label == q.label
            for p, q in zip(one.points, other.points)
        ):
            return False
        if len(one.intervals) != len(other.intervals):
            return False

        def placed(line: NumberLine) -> list[tuple]:
            """Each interval by what it spans, its name with it: X left of c
            and Y right of it are not Y left and X right."""
            return sorted(
                (
                    -1 if interval.left is None else interval.left,
                    -1 if interval.right is None else interval.right,
                    interval.closed_left,
                    interval.closed_right,
                    interval.name,
                )
                for interval in line.intervals
            )

        return all(
            a[:4] == b[:4] and (a[4] == b[4] == "" or _alike(a[4], b[4]))
            for a, b in zip(placed(one), placed(other))
        )
    if not (
        (one.domain == other.domain == "" or _alike(one.domain, other.domain))
        and (one.codomain == other.codomain == "" or _alike(one.codomain, other.codomain))
    ):
        return False
    left, right = _matched(one.left, other.left), _matched(one.right, other.right)
    if left is None or right is None:
        return False
    return {(left[tail], right[head]) for tail, head in one.arrows} == set(other.arrows)


# A drawing a reading described in words, its brackets nested once — the
# words of a chart not drawn, «[схема: числовая прямая: $X = [0; c)$]».
_DESCRIBED_RE = re.compile(
    r"\[\s*схема\s*:(?:[^\[\]\n]|\[[^\[\]\n]*[\])])*\]", re.IGNORECASE
)


@dataclass
class _Slot:
    """One drawing of a reading, in its order on the page: a chart with its
    data, or a drawing described in words (`kind` None)."""

    start: int
    end: int
    kind: str | None
    chart: Chart | None
    text: str


def _slots(markdown: str) -> list[_Slot]:
    found = []
    for start, end, kind in spans(markdown):
        inside = read(markdown[start + 1 : end - 1])
        chart = parse(kind, inside[1]) if inside else None
        found.append(_Slot(start, end, kind, chart, markdown[start:end]))
    for match in _DESCRIBED_RE.finditer(markdown):
        if not any(slot.start < match.end() and match.start() < slot.end for slot in found):
            found.append(_Slot(match.start(), match.end(), None, None, match.group(0)))
    return sorted(found, key=lambda slot: slot.start)


@dataclass
class Agreement:
    """What the runs' charts came to: the chosen run's text with its charts
    settled, how many charts each run wrote, how many the text keeps, and
    how many of those it took from the other runs."""

    markdown: str
    by_run: list[int]
    kept: int
    taken: int


def agreed(markdowns: list[str], chosen: int) -> Agreement:
    """The chosen run's text with every chart settled by the runs together.

    A chart the chosen run wrote stays when another run read it alike, at
    its place when the runs' drawings line up one for one, anywhere when
    they do not. A drawing the chosen run described in words, or read
    otherwise, is drawn as two other runs read it alike at its place: the
    run the text came from was chosen for its text, not for its drawings.
    Anything else is written as the words it stands for — one run alone
    keeps no chart, nobody having read it a second time."""
    slots = [_slots(markdown) for markdown in markdowns]
    mine = slots[chosen]
    others = [found for index, found in enumerate(slots) if index != chosen]
    lined_up = bool(others) and all(len(found) == len(mine) for found in others)
    elsewhere = [slot.chart for found in others for slot in found if slot.chart is not None]
    text = markdowns[chosen]
    out, last, kept, taken = [], 0, 0, 0
    for place, slot in enumerate(mine):
        out.append(text[last : slot.start])
        last = slot.end
        here = [found[place] for found in others] if lined_up else []
        if slot.chart is not None and (
            any(other.chart is not None and alike(slot.chart, other.chart) for other in here)
            if lined_up
            else any(alike(slot.chart, other) for other in elsewhere)
        ):
            kept += 1
            out.append(slot.text)
            continue
        theirs = [other for other in here if other.chart is not None]
        two = next(
            (
                one
                for index, one in enumerate(theirs)
                if any(alike(one.chart, other.chart) for other in theirs[index + 1 :])
            ),
            None,
        )
        if two is not None:
            kept += 1
            taken += 1
            out.append(two.text)
        elif slot.kind is not None:
            inside = read(slot.text[1:-1])
            out.append(described(slot.kind, inside[1] if inside else slot.text[1:-1]))
        else:
            out.append(slot.text)
    out.append(text[last:])
    by_run = [sum(slot.kind is not None for slot in found) for found in slots]
    return Agreement("".join(out), by_run, kept, taken)


# ── A chart in words ────────────────────────────────────────────────────────


_RANGE_WORDS_RE = re.compile(r"^(\S+)\s+от\s+(.+?)\s+до\s+(.+)$", re.IGNORECASE)
_WORDED_RE = re.compile(r"^(множество|мн-во)\s+(.+)$", re.IGNORECASE)


def _dollared(item: str) -> str:
    item = _ARROW_RE.sub(r" \\to ", _bare(item)).strip().replace("•", r"\bullet ")
    if not item:
        return item
    ranged = _RANGE_WORDS_RE.match(item)
    if ranged is not None:
        return f"${ranged.group(1)}$ от ${ranged.group(2)}$ до ${ranged.group(3)}$"
    worded = _WORDED_RE.match(item)
    if worded is not None:
        return f"{worded.group(1)} ${worded.group(2)}$"
    return f"${item}$"


def described(kind: str, spec: str) -> str:
    """A chart as the words «[схема: …]» it stands for, its formulas in
    dollars so the document draws them as formulas."""
    items = []
    for part in _split(spec, ";"):
        pieces = _split(part, ",")
        items.append(", ".join(_dollared(piece) for piece in pieces))
    return f"[схема: {_DESCRIBED[kind]}: {'; '.join(items)}]"
