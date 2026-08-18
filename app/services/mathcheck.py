"""
Детерминированная проверка распознанного конспекта.

Две независимые проверки, обе без обращения к модели:
  1. check_constants  — сверка физических констант со справочником
  2. check_chains     — сходимость цепочек вычислений вида  A = B = C

Обе работают на тексте, который вернула модель. Модель к проверке
не привлекается: она ошибается в арифметике и склонна молча
"починить" несходящееся.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────────
# Справочник констант. Значения CODATA.
# ─────────────────────────────────────────────────────────────

CONSTANTS = {
    "h":   (6.62607015e-34, "постоянная Планка",        "Дж·с"),
    "c":   (2.99792458e8,   "скорость света",           "м/с"),
    "e":   (1.602176634e-19,"элементарный заряд",       "Кл"),
    "m_e": (9.1093837e-31,  "масса электрона",          "кг"),
    "m_p": (1.67262192e-27, "масса протона",            "кг"),
    "k":   (1.380649e-23,   "постоянная Больцмана",     "Дж/К"),
    "N_A": (6.02214076e23,  "число Авогадро",           "1/моль"),
    "R":   (8.31446262,     "универсальная газовая",    "Дж/(моль·К)"),
    "G":   (6.67430e-11,    "гравитационная постоянная","Н·м²/кг²"),
    "g":   (9.80665,        "ускорение свободного падения", "м/с²"),
}

# Ниже этого порога считаем, что человек просто округлил, и молчим.
CONST_QUIET = 0.005             # 0.5%
# Выше 2% — это уже не округление, а ошибка.
CONST_TOLERANCE = 0.02          # 2%
# Выше этого порога считаем, что буква обозначает вообще другую величину,
# а не испорченную константу. R = 0,02 в задаче — это радиус, а не
# универсальная газовая постоянная 8,31, и предупреждать тут не о чем.
CONST_DIFFERENT_QUANTITY = 0.10 # 10%

# Буквы, которые в школьной и вузовской физике почти всегда означают
# что-то своё (радиус, заряд, скорость, ускорение), а не константу.
# Их проверяем только при попадании в узкий коридор вокруг табличного
# значения — то есть когда человек явно целился в константу.
AMBIGUOUS = {"R", "e", "k", "g", "c"}


# ─────────────────────────────────────────────────────────────
# Разбор чисел и LaTeX
# ─────────────────────────────────────────────────────────────

_SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")


def _strip_noise(s: str) -> str:
    """Убрать оформительский LaTeX, не влияющий на значение."""
    s = re.sub(r"\\text\{[^}]*\}", "", s)
    s = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", s)
    s = s.replace("\\,", " ").replace("\\;", " ").replace("\\!", "")
    s = s.replace("\\left", "").replace("\\right", "")
    s = s.replace("$", "")
    return s


def _match_brace(s: str, i: int) -> int:
    """Вернуть индекс '}', парного открывающей '{' в позиции i."""
    assert s[i] == "{"
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError("незакрытая скобка")


def _expand_frac(s: str) -> str:
    """\\frac{A}{B} -> ((A)/(B)), рекурсивно, с корректным учётом вложенности."""
    while True:
        m = re.search(r"\\[dt]?frac\s*\{", s)
        if not m:
            return s
        open1 = s.index("{", m.start())
        close1 = _match_brace(s, open1)
        rest = s[close1 + 1:]
        off = len(s) - len(rest)
        m2 = re.match(r"\s*\{", rest)
        if not m2:
            raise ValueError("у \\frac нет второго аргумента")
        open2 = off + m2.end() - 1
        close2 = _match_brace(s, open2)
        num = s[open1 + 1:close1]
        den = s[open2 + 1:close2]
        s = f"{s[:m.start()]}(({num})/({den})){s[close2 + 1:]}"


def latex_to_python(s: str) -> str:
    """LaTeX-выражение -> строка, которую можно вычислить.

    Поддерживает то, что реально встречается в студенческом конспекте:
    \\frac, \\cdot, степени, скобки, десятичную запятую, надстрочные знаки.
    """
    s = _strip_noise(s)
    # надстрочные знаки: 10⁻¹⁹ -> 10^{-19}, до всякой другой обработки
    s = re.sub(
        r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+",
        lambda m: "^{" + m.group(0).translate(_SUPERSCRIPT) + "}",
        s,
    )
    s = _expand_frac(s)
    s = s.replace("\\cdot", "*").replace("\\times", "*").replace("·", "*")
    s = s.replace("\\sqrt", "sqrt")
    # степени: ^{-19} -> **(-19), ^2 -> **2
    s = re.sub(r"\^\s*\{([^}]*)\}", r"**(\1)", s)
    s = re.sub(r"\^\s*(-?\d+)", r"**(\1)", s)
    # десятичная запятая только между цифрами
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)
    # неразрывные пробелы и остатки разметки
    s = s.replace("\u00a0", " ").replace("{", "(").replace("}", ")")
    return s.strip()


_NUMERIC_ONLY = re.compile(r"^[\d\.\s\+\-\*/\(\)]*$")


def eval_numeric(latex: str) -> float | None:
    """Вычислить выражение, если оно полностью числовое. Иначе None."""
    try:
        py = latex_to_python(latex)
    except Exception:
        return None
    if not py or not _NUMERIC_ONLY.match(py.replace("**", "")):
        return None
    if not re.search(r"\d", py):
        return None
    try:
        # eval без builtins: на вход попадают только цифры и операторы,
        # это проверено регуляркой выше
        return float(eval(py, {"__builtins__": {}}, {}))
    except Exception:
        return None


def split_top_level(s: str, sep: str = "=") -> list[str]:
    """Разбить по знаку, игнорируя вхождения внутри скобок."""
    parts, depth, buf = [], 0, []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in "{([":
            depth += 1
        elif ch in "})]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


# ─────────────────────────────────────────────────────────────
# Результаты
# ─────────────────────────────────────────────────────────────

@dataclass
class Issue:
    kind: str              # "constant" | "chain" | "parse"
    severity: str          # "critical" | "warning"
    message: str
    detail: str = ""
    suggestion: str = ""


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "critical" for i in self.issues)

    def render(self) -> str:
        if not self.issues:
            return "✅ Расхождений не найдено"
        out = []
        for i in self.issues:
            mark = "❌" if i.severity == "critical" else "⚠️"
            out.append(f"{mark} {i.message}")
            if i.detail:
                out.append(f"     {i.detail}")
            if i.suggestion:
                out.append(f"     → {i.suggestion}")
        return "\n".join(out)


# ─────────────────────────────────────────────────────────────
# Проверка 1. Константы
# ─────────────────────────────────────────────────────────────

_ASSIGN = re.compile(
    r"(?<![A-Za-zА-Яа-я_])([A-Za-z](?:_\{?[A-Za-z0-9]+\}?)?)\s*=\s*"
    r"([\d,\.]+\s*(?:\\cdot|·|\*)\s*10\s*\^?\s*\{?-?\d+\}?|[\d,\.]+)"
)


def check_constants(markdown: str) -> list[Issue]:
    """Найти присваивания вида `h = ...` и сверить со справочником."""
    issues = []
    seen = set()
    for m in _ASSIGN.finditer(markdown):
        name_raw, value_raw = m.group(1), m.group(2)
        name = name_raw.replace("{", "").replace("}", "")
        if name not in CONSTANTS:
            continue
        val = eval_numeric(value_raw)
        if val is None or val == 0:
            continue
        ref, title, unit = CONSTANTS[name]
        rel = abs(val - ref) / abs(ref)
        if rel <= CONST_QUIET:
            continue
        # Слишком далеко от табличного -> это другая величина, не константа
        if rel > CONST_DIFFERENT_QUANTITY:
            continue
        if name in AMBIGUOUS and rel > CONST_TOLERANCE:
            continue
        key = (name, round(val, 12))
        if key in seen:
            continue
        seen.add(key)

        # Не спутана ли константа с другой из справочника?
        confused = None
        for other, (oref, otitle, _u) in CONSTANTS.items():
            if other == name:
                continue
            om, oe = f"{oref:e}".split("e")
            vm, ve = f"{val:e}".split("e")
            if abs(float(om) - float(vm)) / abs(float(om)) < 0.01:
                confused = (other, oref, otitle)
                break

        sev = "critical" if confused else "warning"
        det = f"в записи {val:.6g}, табличное {ref:.6g} {unit} (расхождение {rel*100:.1f}%)"
        sug = f"похоже на {confused[2]} {confused[0]} = {confused[1]:.6g}" if confused else ""
        issues.append(Issue("constant", sev, f"{title} ({name}) записана неверно", det, sug))
    return issues


# ─────────────────────────────────────────────────────────────
# Проверка 2. Сходимость цепочек
# ─────────────────────────────────────────────────────────────

CHAIN_TOLERANCE = 0.02          # 2% — запас на округления автора


def check_chains(markdown: str) -> list[Issue]:
    """Для каждой строки с несколькими '=' сравнить числовые звенья."""
    issues = []
    for lineno, line in enumerate(markdown.splitlines(), 1):
        if line.count("=") < 2:
            continue
        parts = split_top_level(_strip_noise(line), "=")
        values: list[tuple[int, str, float]] = []
        for idx, p in enumerate(parts):
            v = eval_numeric(p)
            if v is not None and math.isfinite(v):
                values.append((idx, p.strip(), v))
        for (i1, s1, v1), (i2, s2, v2) in zip(values, values[1:]):
            if v1 == 0 and v2 == 0:
                continue
            base = max(abs(v1), abs(v2))
            if base == 0:
                continue
            rel = abs(v1 - v2) / base
            if rel <= CHAIN_TOLERANCE:
                continue
            ratio = v2 / v1 if v1 else float("inf")
            hint = ""
            if abs(ratio) > 1e-12:
                lg = math.log10(abs(ratio))
                if abs(lg - round(lg)) < 0.02 and round(lg) != 0:
                    hint = f"расхождение ровно в 10^{round(lg):+d} — вероятно, потерян показатель степени"
            issues.append(Issue(
                "chain", "critical",
                f"строка {lineno}: звенья цепочки не сходятся",
                f"{_short(s1)} = {v1:.6g}   ⟶   {_short(s2)} = {v2:.6g}"
                f"   (отличие в {ratio:.4g} раз)",
                hint,
            ))
    return issues


def _short(s: str, n: int = 46) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


# ─────────────────────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────────────────────

def check(markdown: str) -> Report:
    return Report(check_constants(markdown) + check_chains(markdown))
