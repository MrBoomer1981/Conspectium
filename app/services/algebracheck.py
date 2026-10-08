r"""An equality that does not hold, found by code (task 84).

Two of the ten errors the CEO found in records 88 and 89 were equalities that
do not hold — «(−x)(−x) = x», «c − h = c² − 2ch + h²» — and that is the one
kind of a lecture's error code can prove. mathcheck compares numbers; this
compares the two sides of an «=» that carry letters, by counting both at
numbers picked at random: an identity holds at every point, and two sides
that differ at three of them do not hold as written.

It stays quiet when the page does not settle it, as graphcheck does — a
confident wrong finding costs more than silence:

- only an «=» whose sides carry the same letters is checked. An equation,
  «x + a = b», a claim about one number, «c² = 2», a contradiction reached on
  purpose, «1 = 0», carry different letters, or none;
- «h = …», a letter alone on the left, is a definition and is never checked:
  what the lecture defined is put in its place in the formulas after it
  («положим h = b/3c»), the latest definition of a letter the one used. Not
  «x = y», a conclusion, nor what a line solving an equation finds;
- a line that solves, supposes or argues the contrary is left alone, and so
  is a lecture on logic, where «x + x = x» holds;
- whatever the code does not read — a set, a sum, a limit, a vector, a
  function's value f(x), arg z, an absolute value — is left alone, and so
  is a formula of analysis, with \lim, \to or \infty in it;
- a capital letter — a set, a matrix, an ideal, where (A + B)ᵀ = Aᵀ + Bᵀ
  and x + J + J = x + J hold — and i or j, the imaginary unit, where
  (a + ib)(c + id) = ac − bd + i(ad + bc) holds, leave their «=» alone;
- in a lecture on limits, an «=» that holds as the letters grow —
  n⁴(…)/n³(…) = n/(−1) — is the limit's notation, not an error. Only there:
  elsewhere (x + 1)² = x² + 1 grows alike as well, and is wrong.

Measured over every record in the database on 2026-10-08, the CEO's word
given to read them: 30 equalities found before these last three rules —
complex numbers, ideals, a transpose, arg z, a limit — and 7 after, every
one an equality that does not hold as the record reads it.

Pure code: no model, no library this project did not have, no database.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from fractions import Fraction

# $…$ and $$…$$ on one line, as the document reads them (pdf._MATH_RE).
_FORMULA_RE = re.compile(
    r"(?<!\\)\$\$([^$\n]+?)(?<!\\)\$\$|(?<!\\)\$([^$\n]+?)(?<!\\)\$"
)
_STRUCK_RE = re.compile(r"(?<!~)~~(?!~)[^~\n]+?(?<!~)~~(?!~)")

_TOKEN_RE = re.compile(
    r"(?P<number>\d+(?:[.,]\d+)?)"
    r"|(?P<command>\\[A-Za-z]+|\\.)"
    r"|(?P<letter>[A-Za-z])"
    r"|(?P<space>\s+)"
    r"|(?P<char>.)"
)

# Where one statement of a formula ends and the next begins.
_SEPARATORS = {
    ",", ";", ":", "|", "\\quad", "\\qquad", "\\Rightarrow", "\\Leftarrow",
    "\\Leftrightarrow", "\\iff", "\\implies", "\\impliedby", "\\to", "\\mid",
    "\\text", "\\mbox", "\\textrm", "\\textit", "\\textbf", "\\forall",
    "\\exists", "\\land", "\\lor", "\\wedge", "\\vee", "\\neg",
}
# Relations between the sides of a statement; only «=» is checked.
_RELATIONS = {
    "=", "<", ">", "\\le", "\\leq", "\\leqslant", "\\ge", "\\geq", "\\geqslant",
    "\\ne", "\\neq", "\\approx", "\\sim", "\\equiv", "\\in", "\\notin",
    "\\subset", "\\subseteq", "\\supset", "\\supseteq", "\\simeq", "\\cong",
}
_IGNORED = {"\\,", "\\;", "\\!", "\\ ", "\\:", "\\displaystyle", "\\limits"}
_GREEK = {
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
    "theta", "vartheta", "kappa", "lambda", "mu", "nu", "xi", "rho", "sigma",
    "tau", "upsilon", "phi", "varphi", "chi", "psi", "omega",
}
_FUNCTIONS = {"sin": math.sin, "cos": math.cos, "tan": math.tan, "ln": math.log, "exp": math.exp}
# A formula of analysis, whose «=» may hold only in a limit: left alone whole.
_ANALYSIS = {
    "\\lim", "\\to", "\\infty", "\\sum", "\\prod", "\\int", "\\oint",
    "\\partial", "\\nabla", "\\sup", "\\inf", "\\max", "\\min", "\\rightarrow",
}
# A function written in letters without its backslash — «arg z», «sin x» —
# which read letter by letter would be a product.
_WORDS = (
    "arg", "sin", "cos", "tg", "ctg", "tan", "cot", "ln", "lg", "log", "exp",
    "lim", "max", "min", "sup", "inf", "det", "deg", "dim", "mod", "sgn", "rank",
)
# Letters that are no number: i and j, the imaginary unit.
_UNITS = {"i", "j"}
# How large the letters are made to see whether two sides agree as they grow.
_LARGE = 1e6
# A lecture where «=» may stand for agreement in the limit.
_LIMITS_RE = re.compile(r"\\lim|\\to\b|\\infty|предел")

# A line that solves an equation, supposes or argues the contrary: what it
# says need not hold (lower case, by the start of the word).
_CONTEXT_RE = re.compile(
    r"уравнен|реши|решен|найд|найти|корн|предполож|допуст|противн|систем"
)
# A lecture on logic or on structures where x + x = x holds: left alone whole.
_SUBJECT_RE = re.compile(
    r"булев|логическ|алгебр\w* логик|дизъюнк|конъюнк|идемпотент|решётк|решетк"
)

# Three points, each letter a number in a range with no 0 and no 1 — where
# x² = x would hold — and the same three every time.
_POINTS = 3
_LOW, _HIGH = 1.3, 2.9
_TOLERANCE = 1e-9
# The numbers a reader can count with, tried for the example the box gives.
_SMALL = (2, 3, 5, 7, 11, 13)
_MAX_DEPTH = 6
# Whole powers up to this are counted exactly.
_MAX_POWER = 64


class _Unread(Exception):
    """What this module does not read. The statement is left alone."""


@dataclass
class Failure:
    """An equality that does not hold: its two sides as written, and a point
    where they differ — the letters the reader counts with, and what each
    side comes to there."""

    left: str
    right: str
    point: list[tuple[str, str]]
    left_value: str
    right_value: str

    @property
    def anchor(self) -> str:
        return f"{self.left} = {self.right}"


@dataclass
class _Token:
    kind: str
    text: str
    start: int
    end: int


def _tokens(latex: str) -> list[_Token]:
    found = []
    for match in _TOKEN_RE.finditer(latex):
        kind = match.lastgroup
        if kind == "space":
            continue
        if kind == "command" and match.group() in _IGNORED:
            continue
        found.append(_Token(kind, match.group(), match.start(), match.end()))
    # A run of letters written together that opens with a function's name is
    # that function, not a product: «arg z». Not «2ch», which is 2·c·h.
    index = 0
    while index < len(found):
        end = index
        while (
            end + 1 < len(found)
            and found[end].kind == found[end + 1].kind == "letter"
            and found[end].end == found[end + 1].start
        ):
            end += 1
        run = "".join(token.text for token in found[index : end + 1])
        if found[index].kind == "letter" and run.startswith(_WORDS):
            found[index : end + 1] = [
                _Token("word", run, found[index].start, found[end].end)
            ]
        index += 1
    return found


def _statements(tokens: list[_Token]) -> list[list[tuple[str, list[_Token]]]]:
    """A formula's statements, each a chain of sides and the relations
    between them: «a = b < c» is [("", a), ("=", b), ("<", c)]. Split only
    outside brackets; a \\text{…} ends a statement and is skipped whole."""
    statements: list[list[tuple[str, list[_Token]]]] = []
    chain: list[tuple[str, list[_Token]]] = []
    side: list[_Token] = []
    relation = ""
    depth = 0
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.text in ("(", "{", "[") or token.text == "\\left":
            depth += 1
        elif token.text in (")", "}", "]") or token.text == "\\right":
            depth -= 1
        if (
            depth == 0
            and token.text == ":"
            and index + 1 < len(tokens)
            and tokens[index + 1].text == "="
        ):
            chain.append((relation, side))
            side, relation = [], ":="
            index += 2
            continue
        if depth == 0 and token.text in _SEPARATORS:
            if token.text.startswith("\\text") or token.text == "\\mbox":
                # The words in braces after it go with it.
                index += 1
                if index < len(tokens) and tokens[index].text == "{":
                    level = 0
                    while index < len(tokens):
                        level += {"{": 1, "}": -1}.get(tokens[index].text, 0)
                        if level == 0:
                            break
                        index += 1
            chain.append((relation, side))
            statements.append(chain)
            chain, side, relation = [], [], ""
            index += 1
            continue
        if depth == 0 and token.text in _RELATIONS:
            chain.append((relation, side))
            side, relation = [], token.text
            index += 1
            continue
        side.append(token)
        index += 1
    chain.append((relation, side))
    statements.append(chain)
    return statements


class _Reader:
    """One side of a statement read into a tree of tuples:
    ("num", Fraction | float), ("sym", name), ("neg", a), ("add" | "sub" |
    "mul" | "div" | "pow", a, b), ("root", degree, a), ("fn", name, a)."""

    def __init__(self, tokens: list[_Token]):
        self.tokens = tokens
        self.index = 0

    def peek(self) -> _Token | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self) -> _Token:
        token = self.peek()
        if token is None:
            raise _Unread
        self.index += 1
        return token

    def expect(self, text: str) -> None:
        if self.take().text != text:
            raise _Unread

    def whole(self):
        if not self.tokens:
            raise _Unread
        node = self.sum()
        if self.peek() is not None:
            raise _Unread
        return node

    def sum(self):
        node = self.product()
        while self.peek() is not None and self.peek().text in ("+", "-"):
            sign = self.take().text
            node = ("add" if sign == "+" else "sub", node, self.product())
        return node

    def product(self):
        node = self.signed()
        while True:
            token = self.peek()
            if token is None:
                return node
            if token.text in ("\\cdot", "*"):
                self.take()
                node = ("mul", node, self.signed())
            elif token.text in ("/", "\\div"):
                self.take()
                node = ("div", node, self.signed())
            elif self.starts_atom(token):
                node = ("mul", node, self.power())
            else:
                return node

    def signed(self):
        token = self.peek()
        if token is not None and token.text == "-":
            self.take()
            return ("neg", self.signed())
        if token is not None and token.text == "+":
            self.take()
            return self.signed()
        return self.power()

    def starts_atom(self, token: _Token) -> bool:
        if token.kind in ("number", "letter"):
            return True
        if token.text in ("(", "{"):
            return True
        name = token.text[1:]
        return token.kind == "command" and (
            name in ("frac", "dfrac", "tfrac", "sqrt", "left", "pi")
            or name in _GREEK
            or name in _FUNCTIONS
        )

    def power(self):
        base = self.atom()
        token = self.peek()
        if token is not None and token.text == "^":
            self.take()
            return ("pow", base, self.exponent())
        return base

    def exponent(self):
        token = self.take()
        if token.text == "{":
            node = self.sum()
            self.expect("}")
            return node
        if token.kind == "number":
            # "x^23" is x² times 3: a bare exponent is one character.
            if len(token.text) > 1:
                rest = token.text[1:]
                if not rest.isdigit():
                    raise _Unread
                self.tokens.insert(
                    self.index, _Token("number", rest, token.start + 1, token.end)
                )
            return ("num", Fraction(int(token.text[0])))
        if token.kind == "letter":
            return ("sym", token.text)
        if token.kind == "command" and token.text[1:] in _GREEK:
            return ("sym", token.text[1:])
        raise _Unread

    def group(self):
        self.expect("{")
        node = self.sum()
        self.expect("}")
        return node

    def subscript(self) -> str:
        """A letter's index, as part of its name: a_1, a_{n+1}."""
        token = self.take()
        if token.text != "{":
            if token.kind in ("number", "letter"):
                return token.text
            raise _Unread
        parts = []
        level = 1
        while True:
            token = self.take()
            level += {"{": 1, "}": -1}.get(token.text, 0)
            if level == 0:
                return "{" + "".join(parts) + "}"
            parts.append(token.text)

    def atom(self):
        token = self.take()
        if token.kind == "number":
            text = token.text.replace(",", ".")
            return ("num", Fraction(text))
        if token.kind == "letter" or (
            token.kind == "command" and token.text[1:] in _GREEK
        ):
            name = token.text.lstrip("\\")
            following = self.peek()
            if following is not None and following.text == "_":
                self.take()
                name = f"{name}_{self.subscript()}"
                following = self.peek()
            if following is not None and following.text in ("'", "!"):
                raise _Unread
            # f(x) is a function's value, not f times x.
            if following is not None and following.text == "(" and following.start == token.end:
                raise _Unread
            return ("sym", name)
        if token.text in ("(", "{"):
            node = self.sum()
            self.expect(")" if token.text == "(" else "}")
            return node
        if token.text == "\\left":
            if self.take().text != "(":
                raise _Unread
            node = self.sum()
            self.expect("\\right")
            self.expect(")")
            return node
        name = token.text[1:] if token.kind == "command" else ""
        if name in ("frac", "dfrac", "tfrac"):
            top = self.group()
            return ("div", top, self.group())
        if name == "sqrt":
            degree = ("num", Fraction(2))
            following = self.peek()
            if following is not None and following.text == "[":
                self.take()
                degree = self.sum()
                self.expect("]")
            return ("root", degree, self.group())
        if name == "pi":
            return ("num", math.pi)
        if name in _FUNCTIONS:
            following = self.peek()
            if following is not None and following.text == "^":
                raise _Unread  # \sin^2 x
            return ("fn", name, self.power())
        raise _Unread


def _read(tokens: list[_Token]):
    return _Reader(list(tokens)).whole()


def _letters(node, definitions: dict, depth: int = 0) -> set[str]:
    """The letters a side depends on once what the lecture defined is put in."""
    kind = node[0]
    if kind == "num":
        return set()
    if kind == "sym":
        defined = definitions.get(node[1])
        if defined is not None and depth < _MAX_DEPTH:
            return _letters(defined, definitions, depth + 1)
        return {node[1]}
    if kind == "fn":
        return _letters(node[2], definitions, depth)
    return set().union(*(_letters(part, definitions, depth) for part in node[1:]))


def _value(node, values: dict, definitions: dict, depth: int = 0):
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "sym":
        defined = definitions.get(node[1])
        if defined is not None and depth < _MAX_DEPTH:
            return _value(defined, values, definitions, depth + 1)
        return values[node[1]]
    if kind == "neg":
        return -_value(node[1], values, definitions, depth)
    if kind == "fn":
        return _FUNCTIONS[node[1]](float(_value(node[2], values, definitions, depth)))
    if kind == "root":
        degree = _value(node[1], values, definitions, depth)
        radicand = float(_value(node[2], values, definitions, depth))
        if radicand < 0:
            raise ValueError
        return radicand ** (1 / float(degree))
    a = _value(node[1], values, definitions, depth)
    b = _value(node[2], values, definitions, depth)
    if kind == "add":
        return a + b
    if kind == "sub":
        return a - b
    if kind == "mul":
        return a * b
    if kind == "div":
        if b == 0:
            raise ZeroDivisionError
        return a / b
    if kind == "pow":
        if isinstance(b, Fraction) and b.denominator == 1 and abs(b) <= _MAX_POWER:
            return a ** int(b)
        if float(a) <= 0:
            raise ValueError
        return float(a) ** float(b)
    raise _Unread


def _differ(a, b) -> bool:
    a, b = float(a), float(b)
    return abs(a - b) > _TOLERANCE * max(1.0, abs(a), abs(b))


def _shown(number) -> str:
    """A number as the box writes it: whole, a fraction, or three figures."""
    if isinstance(number, Fraction):
        if number.denominator == 1:
            return str(number.numerator)
        sign = "-" if number < 0 else ""
        return f"{sign}\\frac{{{abs(number.numerator)}}}{{{number.denominator}}}"
    value = float(number)
    if abs(value) >= 1000:
        return str(round(value))
    return f"{value:.3g}"


def _refuted(left, right, definitions: dict, letters: list[str]) -> list[dict] | None:
    """The points where the two sides differ, if they differ at every one of
    _POINTS random points; None when they agree anywhere, or cannot be
    counted. Seeded, so a record gives the same finding every time."""
    chance = random.Random(84)
    points = []
    for _ in range(_POINTS):
        values = {letter: chance.uniform(_LOW, _HIGH) for letter in letters}
        try:
            if not _differ(
                _value(left, values, definitions), _value(right, values, definitions)
            ):
                return None
        except (ArithmeticError, ValueError, TypeError):
            return None
        points.append(values)
    return points


def _example(left, right, definitions: dict, letters: list[str]):
    """Small whole numbers the two sides differ at, and their values there,
    counted exactly where they can be; None when none of the few tried do."""
    for offset in range(len(_SMALL)):
        values = {
            letter: Fraction(_SMALL[(offset + place) % len(_SMALL)])
            for place, letter in enumerate(letters)
        }
        try:
            a = _value(left, values, definitions)
            b = _value(right, values, definitions)
        except (ArithmeticError, ValueError, TypeError):
            continue
        if _differ(a, b):
            return values, a, b
    return None


def _formulas(markdown: str) -> list[tuple[str, str]]:
    """Every formula of the record with the line it stands on, in order — a
    working broken over two lines, «… + h^2 =» over «= c^2 - …», joined."""
    found: list[tuple[str, str]] = []
    for line in markdown.splitlines():
        line = _STRUCK_RE.sub("", line)
        for match in _FORMULA_RE.finditer(line):
            latex = (match.group(1) or match.group(2) or "").strip()
            if not latex:
                continue
            if (
                found
                and found[-1][0].endswith("=")
                and latex.startswith("=")
            ):
                found[-1] = (found[-1][0] + " " + latex[1:].lstrip(), found[-1][1] + " " + line)
                continue
            found.append((latex, line))
    return found


def _numbers_only(letters: set[str]) -> bool:
    """Whether every letter stands for a number: none a capital — a set, a
    matrix, an ideal — and none the imaginary unit."""
    for letter in letters:
        base = letter.partition("_")[0]
        if base in _UNITS or (len(base) == 1 and base.isupper()):
            return False
    return True


def _grows_alike(left, right, definitions: dict, letters: list[str]) -> bool:
    """Whether two sides agree as the letters grow: an «=» of a limit's
    working, which holds in the limit and nowhere else."""
    values = {letter: _LARGE * (1 + place / 10) for place, letter in enumerate(letters)}
    try:
        a = float(_value(left, values, definitions))
        b = float(_value(right, values, definitions))
    except (ArithmeticError, ValueError, TypeError):
        return False
    return b != 0 and abs(a / b - 1) < 1e-3


def failures(markdown: str) -> list[Failure]:
    """Every equality of the record that does not hold, in order."""
    if _SUBJECT_RE.search(markdown.lower()):
        return []
    definitions: dict = {}
    out: list[Failure] = []
    previous_line = ""
    limits = bool(_LIMITS_RE.search(markdown.lower()))
    for latex, line in _formulas(markdown):
        quiet = bool(_CONTEXT_RE.search((previous_line + " " + line).lower()))
        previous_line = line
        tokens = _tokens(latex)
        if any(token.text in _ANALYSIS for token in tokens):
            continue
        for chain in _statements(tokens):
            sides = []
            for relation, tokens in chain:
                try:
                    sides.append((relation, tokens, _read(tokens)))
                except (_Unread, ValueError, ZeroDivisionError, IndexError):
                    sides.append((relation, tokens, None))
            for (_, before, left), (relation, after, right) in zip(sides, sides[1:]):
                if relation not in ("=", ":="):
                    continue
                if left is not None and left[0] == "sym" and right is not None:
                    # A letter alone on the left is defined, never checked —
                    # but not by itself, by another letter alone, «то x = y»,
                    # or by the solution a quiet line finds.
                    if (
                        not quiet
                        and right[0] != "sym"
                        and left[1] not in _letters(right, {})
                    ):
                        definitions[left[1]] = right
                    continue
                if relation != "=" or quiet or left is None or right is None:
                    continue
                letters = _letters(left, definitions)
                if not letters or letters != _letters(right, definitions):
                    continue
                if not _numbers_only(_letters(left, {}) | _letters(right, {}) | letters):
                    continue
                ordered = sorted(letters)
                if _refuted(left, right, definitions, ordered) is None:
                    continue
                if limits and _grows_alike(left, right, definitions, ordered):
                    continue
                example = _example(left, right, definitions, ordered)
                if example is None:
                    continue
                values, a, b = example
                written = latex
                out.append(
                    Failure(
                        left=written[before[0].start : before[-1].end].strip(),
                        right=written[after[0].start : after[-1].end].strip(),
                        point=_point(left, right, definitions, values),
                        left_value=_shown(a),
                        right_value=_shown(b),
                    )
                )
    return out


def _point(left, right, definitions: dict, values: dict) -> list[tuple[str, str]]:
    """The letters as the equality writes them and what each was counted as:
    the ones picked, and the ones the lecture defined, worked out."""
    written = sorted(_letters(left, {}) | _letters(right, {}))
    shown = []
    for letter in written:
        try:
            value = _value(("sym", letter), values, definitions)
        except (ArithmeticError, ValueError, TypeError, KeyError):
            continue
        shown.append((_name(letter), _shown(value)))
    return shown


def _name(letter: str) -> str:
    """A letter as LaTeX writes it: a Greek one with its backslash."""
    base, _, index = letter.partition("_")
    head = f"\\{base}" if base in _GREEK else base
    return f"{head}_{index}" if index else head
