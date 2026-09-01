"""
Самосогласованность: несколько независимых прогонов транскрипции
одной и той же страницы сравниваются между собой.

Зачем. Модель уверена в каждом отдельном прочтении и не помечает
неоднозначные глифы (единица, написанная как семёрка, — типовой случай).
Расхождение между прогонами такие места находит, потому что при разных
сэмплах неоднозначный символ читается по-разному.

Цена. Страница стоит около $0,0004, поэтому три прогона — $0,0012.
Это дешевле одного проверочного вызова и надёжнее его.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from app.services.mathcheck import eval_numeric

# Числовой литерал: 4,42·10⁻¹⁹ / 4,42 \cdot 10^{-19} / 0,02 / 960
NUM_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:\\cdot|·|\*)\s*10\s*(?:\^\s*\{?-?\d+\}?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)"
    r"|\d+(?:[.,]\d+)?"
)


def extract_numbers(markdown: str) -> list[tuple[str, float]]:
    """Все числовые литералы в порядке появления, с вычисленным значением."""
    out = []
    for m in NUM_RE.finditer(markdown):
        raw = " ".join(m.group(0).split())
        val = eval_numeric(raw)
        if val is not None:
            out.append((raw, val))
    return out


@dataclass
class Divergence:
    position: int
    variants: dict[str, int]        # значение -> сколько прогонов за него
    context: str = ""

    @property
    def majority(self) -> str:
        return max(self.variants.items(), key=lambda kv: kv[1])[0]

    @property
    def unanimous(self) -> bool:
        return len(self.variants) == 1


@dataclass
class ConsensusReport:
    runs: int
    total_positions: int
    divergences: list[Divergence] = field(default_factory=list)

    @property
    def agreement(self) -> float:
        if not self.total_positions:
            return 1.0
        return 1 - len(self.divergences) / self.total_positions

    def render(self) -> str:
        lines = [
            f"Прогонов: {self.runs}   "
            f"числовых позиций: {self.total_positions}   "
            f"согласие: {self.agreement*100:.0f}%"
        ]
        if not self.divergences:
            lines.append("✅ Все прогоны совпали — доверяем транскрипции")
            return "\n".join(lines)
        lines.append(f"⚠️ Расхождений: {len(self.divergences)}")
        for d in self.divergences:
            variants = ", ".join(
                f"{v} ({n}/{self.runs})"
                for v, n in sorted(d.variants.items(), key=lambda kv: -kv[1])
            )
            lines.append(f"   позиция {d.position}: {variants}")
            lines.append(f"      большинство: {d.majority}  → пометить как спорное")
        return "\n".join(lines)


def _words(text: str) -> list[str]:
    """Слова в нижнем регистре, без разметки и пунктуации."""
    t = re.sub(r"\$[^$]*\$", " ", text)          # выкинуть формулы
    t = re.sub(r"\[[^\]]*\]", " ", t)            # выкинуть [схема: ...]
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return t.split()


@dataclass
class TextConsensus:
    runs: int
    similarity: float                # 0..1, среднее попарное совпадение
    verdict: str
    explanation: str

    def render(self) -> str:
        bar = "█" * int(self.similarity * 20) + "░" * (20 - int(self.similarity * 20))
        return (f"Совпадение текста между прогонами: {self.similarity*100:.0f}%  {bar}\n"
                f"{self.verdict}\n{self.explanation}")


def compare_text(runs: list[str]) -> TextConsensus:
    """Сравнить прогоны на уровне СЛОВ, а не чисел.

    Зачем отдельно от compare(). На странице сплошного текста чисел нет,
    и числовое сравнение бесполезно. При этом именно текстовые страницы
    опаснее всего: если модель не смогла прочитать мелкий почерк, но узнала
    тему по заголовку, она сгенерирует правдоподобный учебниковый пересказ
    и не пометит его как сомнительный.

    Отличить чтение от пересказа можно так: при чтении разные прогоны дают
    почти одинаковый текст, при генерации — разные формулировки одной мысли.
    """
    from difflib import SequenceMatcher

    seqs = [_words(r) for r in runs]
    scores = []
    for i in range(len(seqs)):
        for j in range(i + 1, len(seqs)):
            scores.append(SequenceMatcher(a=seqs[i], b=seqs[j], autojunk=False).ratio())
    sim = sum(scores) / len(scores) if scores else 1.0

    if sim >= 0.90:
        verdict = "✅ Прогоны почти идентичны — модель читает страницу"
        expl = "Расхождения на уровне отдельных слов. Транскрипции можно доверять."
    elif sim >= 0.70:
        verdict = "⚠️ Заметные расхождения — часть страницы прочитана плохо"
        expl = "Пометить запись как требующую проверки. Карточки не генерировать."
    else:
        verdict = "❌ ОПАСНО: прогоны рассказывают одно и то же разными словами"
        expl = ("Это подпись генерации, а не чтения: модель узнала тему и\n"
                "пересказывает её по памяти. Отклонить фотографию и попросить\n"
                "переснять крупнее. Ничего не сохранять.")
    return TextConsensus(len(runs), sim, verdict, expl)


def _align(ref: list[str], other: list[str]) -> dict[int, str | None]:
    """Сопоставить позиции `other` позициям `ref`.

    Наивное сравнение по индексу разваливается, как только один прогон
    потерял или добавил число: все последующие позиции съезжают и дают
    лавину ложных расхождений. Поэтому выравниваем последовательности
    так же, как diff выравнивает строки файла.
    """
    from difflib import SequenceMatcher

    mapping: dict[int, str | None] = {i: None for i in range(len(ref))}
    sm = SequenceMatcher(a=ref, b=other, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("equal", "replace"):
            for k in range(i2 - i1):
                mapping[i1 + k] = other[j1 + k] if j1 + k < j2 else None
        elif tag == "delete":
            for k in range(i1, i2):
                mapping[k] = None
    return mapping


def compare(runs: list[str]) -> ConsensusReport:
    """Сравнить N независимых прогонов транскрипции одной страницы."""
    seqs = [extract_numbers(r) for r in runs]
    keys = [[f"{v:.10g}" for _raw, v in s] for s in seqs]

    # Опорный прогон — самый длинный: в нём меньше всего потерь
    ref_i = max(range(len(keys)), key=lambda i: len(keys[i]))
    ref = keys[ref_i]

    mappings = [
        {i: ref[i] for i in range(len(ref))} if i_run == ref_i
        else _align(ref, keys[i_run])
        for i_run in range(len(runs))
    ]

    report = ConsensusReport(runs=len(runs), total_positions=len(ref))
    for i in range(len(ref)):
        votes = Counter()
        for mp in mappings:
            votes[mp[i] if mp[i] is not None else "— (пропущено)"] += 1
        if len(votes) > 1:
            report.divergences.append(Divergence(
                position=i,
                variants=dict(votes),
                context=seqs[ref_i][i][0],
            ))
    return report


def pick_representative(runs: list[str]) -> int:
    """Индекс прогона, наиболее близкого ко всем остальным.

    Голосование большинством работает для отдельных чисел, но за основной
    текст записи надо взять целый прогон — тот, который меньше всех
    отклоняется от остальных. Склеивать куски разных прогонов нельзя:
    получится текст, которого не выдавала ни одна модель.
    """
    from difflib import SequenceMatcher

    if len(runs) == 1:
        return 0
    seqs = [_words(r) for r in runs]
    best_i, best_score = 0, -1.0
    for i in range(len(seqs)):
        score = sum(
            SequenceMatcher(a=seqs[i], b=seqs[j], autojunk=False).ratio()
            for j in range(len(seqs)) if j != i
        )
        if score > best_score:
            best_i, best_score = i, score
    return best_i
