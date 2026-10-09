"""A lecture's study version (task 80): the record set out by topic.

The CEO's of 2026-10-08. The record is what a group trusts and what
everything else is made from; a study version is built from it when somebody
asks, for someone who was not at the lecture — the author's text moved whole
into topics, and between them, under the bot's label, what each topic is
about and its key notions; at the end, questions to check oneself, their
answers on the last page.

The model never gives the author's text back. It answers with an order — the
record's units by number — and with its own texts, and code moves the units:
not a word of the author's can change, and every unit stands once. What the
bot writes may state no number the record does not carry, the summary's
guard, and an answer's working is checked as a teacher's example is. Like
the stages before it, this never touches the database.

What is not the lecture's subject — the course's organisation, the CEO's of
2026-10-09 (task 93) — the model names and code leaves out, never a line
that holds the subject: the record keeps every line, and its own document.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from dataclasses import asdict, dataclass, field

from google.genai import types

from app.core.config import settings
from app.services import explain, pdf, vision
from app.services.vision import CallStats

logger = logging.getLogger(__name__)

STUDY_PROMPT_FILE = "prompts-study-v2.md"
STUDY_PROMPT = vision.load_prompt(STUDY_PROMPT_FILE)
STUDY_PROMPT_WORDS = len(STUDY_PROMPT.split())

# The prompt asks for two to six topics and three to five questions; these
# are where "at most" is kept.
_MAX_TOPICS = 8
_MAX_QUESTIONS = 5
# A unit the model left out is put back after the one before it, so nothing
# of the author's is lost; past a quarter of the record left out, what came
# back is not an arrangement of it.
_MAX_MISSING_SHARE = 0.25
# The course's organisation is a few lines of a lecture: past a fifth of the
# record named so, the model took the lecture for it, and nothing goes.
_MAX_OFF_TOPIC_SHARE = 0.2
# The explaining call's policy, for its reasons: a call over the whole
# record, where a timeout means it was working.
_ATTEMPTS = 2
_RETRY_PAUSE_S = 2

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+\S")
_RULE_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,}|~{3,})$")
_DOLLAR_RE = re.compile(r"(?<!\\)\$")
# With the formula written right against it: record 90's «$\varepsilon$**-
# окрестностью точки**» lost its ε among the key notions (task 86).
_BOLD_RE = re.compile(r"(\$[^$\n]+\$)?\*\*([^*\n]+?)\*\*")
# A bold label is not a notion: «**Определение.**», «**Теорема 2**».
_LABEL_RE = re.compile(
    r"^(?:определени\w*|теорем\w*|лемм\w*|доказательств\w*|док-во|следстви\w*"
    r"|пример\w*|замечани\w*|утверждени\w*|свойств\w*|задач\w*|решени\w*"
    r"|ответ\w*|итог\w*)\W*\d*\W*$",
    re.IGNORECASE,
)
_MAX_NOTIONS = 8
_MAX_NOTION_WORDS = 6
# What makes a paragraph the lecture's whatever the model says of it (task
# 93): a formula — its dollars, a command, a sign — a drawing, or a word of
# what a lecture states or is about, as the notebook shortens it too, a
# problem and homework included. A paragraph of the organisation that has
# one stays: kept, it costs a line; left out, a line of the lecture would go
# — record 92's «Мн-во наз-ся полным, если …» has no formula.
_SUBJECT_RE = re.compile(
    r"[$\\∀∃∈∉⊂⊃⊆⊇∪∩⇒⇐⇔→←↦≤≥≠≈≡∞∑∏∫√±×÷∅ℕℤℚℝℂα-ωΑ-Ω]"
    r"|\[(?:схема|рисунок|граф)"
    r"|определ|теорем|лемм|доказ|док-в|аксиом|следстви|утвержд|свойств|замечани"
    r"|пример(?!н)|наз(?:ыва|-)|пусть|положим|верн"
    r"|множеств|мн-|функци|отображ|чис(?:л|ел)|последовательн|пос-ть|пространств|пр-в|точк"
    r"|задач|упражнен|домашн|\bдз\b|№|§",
    re.IGNORECASE,
)


@dataclass
class Topic:
    title: str
    units: list[int]  # the record's units by number, from 1, in reading order
    about: str | None = None


@dataclass
class Study:
    """What the caller stores and draws, whether or not the call worked."""

    topics: list[Topic] = field(default_factory=list)
    questions: list[dict] = field(default_factory=list)  # {"question", "answer"}
    # The text it was built from, as a fingerprint (`fingerprint`): a kept
    # version is drawn only over the same text cut the same way — a second
    # notebook joining the lecture, or a later rule of cutting, and it is
    # built again rather than set one topic's numbers over another's units.
    source: str = ""
    # Why nothing usable came back: None when it did.
    refused: str | None = None
    # The units it leaves out as the course's organisation, whole or their
    # paragraphs before the subject begins (`trimmed`): kept, so it is drawn
    # again the same way.
    off_topic: list[int] = field(default_factory=list)
    # Units the model left out and code put back, units it named twice, and
    # units it named as the organisation that code kept whole.
    missing: int = 0
    repeated: int = 0
    off_topic_kept: int = 0
    # The bot's texts a check of code threw away.
    abouts_dropped: int = 0
    questions_dropped: int = 0
    stats: list[CallStats] = field(default_factory=list)

    def stored(self) -> dict:
        """What `notes.study` keeps."""
        return {
            "topics": [asdict(topic) for topic in self.topics],
            "questions": list(self.questions),
            "off_topic": list(self.off_topic),
            "source": self.source,
        }


def from_stored(data: object) -> Study | None:
    """A study version kept with its record, or None when what is kept is
    not one this version can draw. Never raises."""
    if not isinstance(data, dict) or not isinstance(data.get("topics"), list):
        return None
    topics: list[Topic] = []
    for item in data["topics"]:
        if not isinstance(item, dict) or not isinstance(item.get("units"), list):
            return None
        units = [unit for unit in item["units"] if isinstance(unit, int)]
        about = item.get("about")
        topics.append(
            Topic(str(item.get("title", "")), units, about if isinstance(about, str) else None)
        )
    questions = [
        {"question": str(q.get("question", "")), "answer": str(q.get("answer", ""))}
        for q in data.get("questions") or []
        if isinstance(q, dict)
    ]
    off_topic = [
        unit
        for unit in data.get("off_topic") or []
        if isinstance(unit, int) and not isinstance(unit, bool)
    ]
    source = data.get("source")
    if not topics or not isinstance(source, str):
        return None
    return Study(topics=topics, questions=questions, source=source, off_topic=off_topic)


# What a fingerprint is taken of besides the text: the rule of cutting it.
# Raised when units() or trimmed() cuts differently, so every kept version is
# built again.
_CUT_VERSION = "1"


def fingerprint(markdown: str) -> str:
    """The text a study version is built from, the way it is cut and the
    prompt that arranged it, in sixteen characters: a version kept from an
    earlier prompt is built again by the next (task 93), so a record brought
    back is set out as a new one is."""
    return hashlib.sha1(
        f"{_CUT_VERSION}\n{STUDY_PROMPT_FILE}\n{markdown}".encode()
    ).hexdigest()[:16]


def units(markdown: str) -> list[str]:
    """The record cut into the pieces a study version moves whole: its
    paragraphs, a heading always beginning one and going with what follows it.

    A seam between two pages goes: a study version is not paged by the
    notebook. Nor is a formula ever cut: a unit whose dollars or environments
    do not close runs on into the next, so a formula set loosely across a
    blank line stays one."""
    pieces: list[list[str]] = []
    current: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or _RULE_RE.fullmatch(stripped):
            if current:
                pieces.append(current)
                current = []
            continue
        if _HEADING_RE.match(stripped) and current:
            pieces.append(current)
            current = []
        current.append(line.rstrip())
    if current:
        pieces.append(current)

    out: list[str] = []
    carried: list[str] = []
    for piece in pieces:
        carried += piece if not carried else [""] + piece
        text = "\n".join(carried)
        heading_only = all(_HEADING_RE.match(line.strip()) for line in carried)
        if heading_only or not _closed(text):
            continue
        out.append(text)
        carried = []
    if carried:
        out.append("\n".join(carried))

    # A formula or a drawing set apart goes with the text before it, which
    # leads up to it: «… значит» and the framed result under it are one
    # thought, and moved apart they would be two halves of a sentence.
    glued: list[str] = []
    for piece in out:
        if glued and _figure_only(piece):
            glued[-1] = f"{glued[-1]}\n\n{piece}"
        else:
            glued.append(piece)
    return glued


# What a unit made only of these is: a formula set apart, a drawing, a note
# about one — never a thought of its own.
_FIGURE_KINDS = frozenset({"math", "picture", "graph", "note", "gap"})


def _figure_only(piece: str) -> bool:
    return {block.kind for block in pdf.blocks(piece)} <= _FIGURE_KINDS


def _closed(text: str) -> bool:
    """Whether every formula opened in `text` closes in it, and every passage
    another notebook adds to a lecture (pdf.inserted) — moved apart, its
    label would stand in one topic and its end in another."""
    lines = [line.strip() for line in text.splitlines()]
    opened = sum(1 for line in lines if line.startswith("⟦+") and line != pdf.INSERT_CLOSE)
    return (
        len(_DOLLAR_RE.findall(text)) % 2 == 0
        and text.count("\\begin{") == text.count("\\end{")
        and opened == lines.count(pdf.INSERT_CLOSE)
    )


def _paragraphs(piece: str) -> list[str]:
    """A unit's paragraphs, as units() joined them: a formula never cut."""
    out: list[str] = []
    carried: list[str] = []
    for paragraph in piece.split("\n\n"):
        carried.append(paragraph)
        text = "\n\n".join(carried)
        if _closed(text):
            out.append(text)
            carried = []
    if carried:
        out.append("\n\n".join(carried))
    return out


def trimmed(piece: str) -> tuple[str, str]:
    """A unit named as the course's organisation, cut where the subject
    begins: what goes — its paragraphs before the first that holds the
    subject (`_SUBJECT_RE`) — and what stays. Record 97's points and test
    dates stood in one unit with the set equality under them, which a
    formula set apart goes with (task 93)."""
    paragraphs = _paragraphs(piece)
    first = next(
        (index for index, paragraph in enumerate(paragraphs) if _SUBJECT_RE.search(paragraph)),
        len(paragraphs),
    )
    # The headings right above the subject head it, and stay with it: record
    # 90's «## Супремум и инфимум» over its definition.
    while 0 < first < len(paragraphs) and all(
        _HEADING_RE.match(line.strip()) for line in paragraphs[first - 1].splitlines()
    ):
        first -= 1
    return "\n\n".join(paragraphs[:first]), "\n\n".join(paragraphs[first:])


def _for_reading(pieces: list[str]) -> str:
    """The units as the model reads them: numbered, each main formula with
    the number the document gives it, so "(3)" in an answer is "(3)" on the
    page."""
    numbered = pdf.numbered_for_reading("\n\n⟦⟧\n\n".join(pieces)).split("\n\n⟦⟧\n\n")
    return "\n\n".join(f"[{number}] {piece}" for number, piece in enumerate(numbered, 1))


def _answer_of(response: object) -> dict | None:
    return explain._answer(vision._response_text(response))


async def _call(text: str) -> tuple[object | None, CallStats, bool]:
    """The one call: the arrangement and the bot's texts, as strict JSON."""
    started = time.monotonic()
    model = settings.EXPLAIN_MODEL
    try:
        async with vision._API_SLOTS:
            response = await asyncio.wait_for(
                vision._client.aio.models.generate_content(
                    model=model,
                    contents=[STUDY_PROMPT, text],
                    config=types.GenerateContentConfig(
                        temperature=1.0,
                        max_output_tokens=vision.MAX_OUTPUT_TOKENS,
                        response_mime_type="application/json",
                        automatic_function_calling=vision.NO_AFC,
                    ),
                ),
                timeout=settings.EXPLAIN_CALL_TIMEOUT_S,
            )
    except Exception as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        retryable = vision._should_retry(exc) and not isinstance(exc, TimeoutError)
        return None, CallStats(
            kind="study", model=model, tokens_in=None, tokens_out=None,
            tokens_thought=None, cost_usd=None, latency_ms=latency_ms,
            success=False, error=vision._short_error(exc),
        ), retryable
    tokens_in, tokens_out, tokens_thought = vision._usage(response)
    answered = bool(vision._response_text(response).strip())
    return response, CallStats(
        kind="study", model=model, tokens_in=tokens_in, tokens_out=tokens_out,
        tokens_thought=tokens_thought,
        cost_usd=vision._cost_usd(model, tokens_in, tokens_out, tokens_thought),
        latency_ms=int((time.monotonic() - started) * 1000),
        success=answered, error=None if answered else "empty model response",
    ), False


def _arranged(
    topics: list[dict], count: int, named: list[int], aside: dict[int, str]
) -> tuple[list[Topic], int, int] | None:
    """The topics with every unit placed once — a unit named twice keeps its
    first place, one left out goes back after the unit before it — and how
    many were left out and repeated. None when too much was left out.

    `named` are the units the model named as the course's organisation, and
    `aside` those code leaves out, each with what is left of it: that stands
    where the model put the unit, else goes back as a unit left out does, and
    so does a unit named that code keeps whole; a unit with nothing left
    stands nowhere."""
    seen: set[int] = set()
    arranged: list[Topic] = []
    repeated = 0
    for item in topics[:_MAX_TOPICS]:
        placed: list[int] = []
        for unit in item["units"]:
            if unit in seen:
                repeated += 1
                continue
            seen.add(unit)
            if unit in aside and not aside[unit]:
                continue
            placed.append(unit)
        if placed:
            arranged.append(Topic(item["title"], placed, item["about"]))
    missing = [unit for unit in range(1, count + 1) if unit not in seen and unit not in named]
    if not arranged or len(missing) > count * _MAX_MISSING_SHARE:
        return None
    back = {unit for unit in named if unit not in seen and (unit not in aside or aside[unit])}
    for unit in sorted(back.union(missing)):
        # After the unit nearest before it on the page that stands somewhere,
        # wherever that went — the one just before may be the organisation,
        # gone; with none, first.
        for before in range(unit - 1, 0, -1):
            topic = next((topic for topic in arranged if before in topic.units), None)
            if topic is not None:
                topic.units.insert(topic.units.index(before) + 1, unit)
                break
        else:
            arranged[0].units.insert(0, unit)
    return arranged, len(missing), repeated


def _named_aside(data: dict, count: int) -> list[int]:
    """The units the answer names as the course's organisation. Never raises."""
    named = data.get("organization")
    if not isinstance(named, list):
        return []
    return list(
        dict.fromkeys(
            unit
            for unit in named
            if isinstance(unit, int) and not isinstance(unit, bool) and 1 <= unit <= count
        )
    )


def _aside(pieces: list[str], named: list[int]) -> tuple[dict[int, str], int]:
    """The units left out as the organisation, each with what is left of it,
    and how many of those named are kept whole: a unit that opens on the
    subject loses nothing, and past a fifth of the record nothing goes."""
    aside: dict[int, str] = {}
    gone = 0
    for unit in named:
        cut, kept = trimmed(pieces[unit - 1])
        if cut:
            aside[unit] = kept
            gone += len(cut)
    if gone > sum(len(piece) for piece in pieces) * _MAX_OFF_TOPIC_SHARE:
        logger.warning(
            "study: %d units named as the course's organisation hold more than a "
            "fifth of the record; none is left out",
            len(aside),
        )
        return {}, len(named)
    return aside, len(named) - len(aside)


def _topics_of(data: dict, count: int) -> list[dict]:
    """The answer's topics, each with a title, its units as numbers within
    the record and what it is about. Never raises."""
    found: list[dict] = []
    for item in data.get("topics") or []:
        if not isinstance(item, dict) or not isinstance(item.get("units"), list):
            continue
        numbers = [
            unit
            for unit in item["units"]
            if isinstance(unit, int) and not isinstance(unit, bool) and 1 <= unit <= count
        ]
        about = item.get("about")
        found.append(
            {
                "title": " ".join(str(item.get("title", "")).split())[:100],
                "units": numbers,
                "about": about.strip() if isinstance(about, str) and about.strip() else None,
            }
        )
    return found


def _fair(text: str, carried: set[str]) -> bool:
    """Whether a text of the bot's may be printed: it states no number the
    record does not carry and does not judge the record."""
    return set(_NUMBER_RE.findall(text)) <= carried and not explain.judges_the_record("", text)


async def build(markdown: str) -> Study:
    """The record's study version. Never touches the database."""
    pieces = units(markdown)
    if len(pieces) < 2:
        return Study(refused="one unit")

    all_stats: list[CallStats] = []
    response = None
    data = None
    text = _for_reading(pieces)
    for attempt in range(_ATTEMPTS):
        last = attempt == _ATTEMPTS - 1
        response, stats, retryable = await _call(text)
        all_stats.append(stats)  # rule 4: a call that failed was still a call
        if response is not None:
            data = _answer_of(response)
            if data is not None:
                break
            # Record 91's came back whole and would not parse; the press of
            # its button asked again, and the second parsed (task 87). Asked
            # again here, as recognition's answers are — never after a
            # refusal or our own ceiling — and its row says why (rule 7).
            stats.success = False
            stats.error = vision._unparseable(response)
            again = not last and vision._worth_asking_again(response)
            logger.warning(
                "study attempt %d/%d did not parse as the JSON asked for, %s: %s",
                attempt + 1,
                _ATTEMPTS,
                "asking again" if again else "no retry",
                stats.error,
            )
            if not again:
                break
            continue
        logger.warning(
            "study attempt %d/%d failed, %s: %s",
            attempt + 1,
            _ATTEMPTS,
            "retrying" if retryable and not last else "no retry",
            stats.error,
        )
        if last or not retryable:
            break
        await asyncio.sleep(_RETRY_PAUSE_S)
    if data is None:
        return Study(
            refused="call failed" if response is None else "unparseable", stats=all_stats
        )
    named = _named_aside(data, len(pieces))
    aside, off_topic_kept = _aside(pieces, named)
    arranged = _arranged(_topics_of(data, len(pieces)), len(pieces), named, aside)
    if arranged is None:
        logger.warning("study: the answer left out too much of the record")
        return Study(refused="units missing", stats=all_stats)
    topics, missing, repeated = arranged

    carried = set(_NUMBER_RE.findall(markdown))
    abouts_dropped = 0
    for number, topic in enumerate(topics, 1):
        if not topic.title or explain.judges_the_record(topic.title, ""):
            topic.title = f"Тема {number}"
        if topic.about is not None and not _fair(topic.about, carried):
            topic.about = None
            abouts_dropped += 1

    questions: list[dict] = []
    questions_dropped = 0
    for item in (data.get("questions") or [])[:_MAX_QUESTIONS]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if not question or not answer:
            continue
        if (
            not _fair(question, carried)
            or not _fair(answer, carried)
            or explain._working_fails(answer)
        ):
            questions_dropped += 1
            continue
        questions.append({"question": question, "answer": answer})

    logger.info(
        "study: %d topics over %d units, %d left out and put back, %d repeated, "
        "%d the course's organisation left out, %d named so and kept whole, "
        "%d abouts dropped, %d questions kept, %d dropped, model %s",
        len(topics), len(pieces), missing, repeated, len(aside), off_topic_kept,
        abouts_dropped, len(questions), questions_dropped, settings.EXPLAIN_MODEL,
    )
    return Study(
        topics=topics,
        questions=questions,
        source=fingerprint(markdown),
        off_topic=sorted(aside),
        missing=missing,
        repeated=repeated,
        off_topic_kept=off_topic_kept,
        abouts_dropped=abouts_dropped,
        questions_dropped=questions_dropped,
        stats=all_stats,
    )


def notions(text: str) -> list[str]:
    """The key notions of a topic, the author's own words: what the record
    sets in bold, a bold label like «Определение» left out."""
    found: list[str] = []
    for match in _BOLD_RE.finditer(text):
        notion = " ".join(match.group(2).split()).strip(" .,:;")
        if match.group(1) and notion.startswith("-"):
            notion = match.group(1) + notion
        if (
            not notion
            or _LABEL_RE.match(notion)
            or len(notion.split()) > _MAX_NOTION_WORDS
            or notion.casefold() in (seen.casefold() for seen in found)
        ):
            continue
        found.append(notion)
    return found[:_MAX_NOTIONS]


@dataclass
class Layout:
    """A study version as render takes it: the arranged record with a line
    where each of the bot's boxes stands, the boxes in that order — each a
    kind and what it holds — and the numbers the record's formulas carry, in
    the order they stand now; and what it leaves out as the course's
    organisation, where a box anchored there would stand."""

    markdown: str
    boxes: list[dict]
    formula_numbers: list[int]
    left_out: str = ""


def _demoted(piece: str) -> str:
    """A unit with its headings a level down: the topics are the document's
    first level now, and the author's sections stand under them."""
    return "\n".join(
        f"#{line.lstrip()}"
        if _HEADING_RE.match(line.strip()) and not line.lstrip().startswith("######")
        else line
        for line in piece.splitlines()
    )


def layout(markdown: str, version: Study) -> Layout:
    """The arranged record for render: each topic a first-level heading, the
    box of what it is about under it, its units in order; the questions at
    the end, their answers on a page of their own."""
    pieces = units(markdown)
    # The numbers the record's formulas carry, unit by unit, in the record's
    # order — kept, so an explanation's "(3)" still names its formula.
    counts = [pdf.numbered_formulas(piece) for piece in pieces]
    starts = [sum(counts[:index]) + 1 for index in range(len(pieces))]
    # What is left of the units the version leaves out as the organisation;
    # a formula is never left out, so no number moves.
    aside = {
        unit: trimmed(pieces[unit - 1]) for unit in version.off_topic if 0 < unit <= len(pieces)
    }
    drawn = [aside[unit][1] if unit in aside else piece for unit, piece in enumerate(pieces, 1)]

    lines: list[str] = []
    boxes: list[dict] = []
    numbers: list[int] = []
    for topic in version.topics:
        lines += [f"# {topic.title}", ""]
        held = notions(
            "\n\n".join(drawn[unit - 1] for unit in topic.units if 0 < unit <= len(pieces))
        )
        if topic.about or held:
            lines += [pdf.placed_mark(len(boxes)), ""]
            boxes.append({"kind": "about", "text": topic.about, "notions": held})
        for unit in topic.units:
            if not 0 < unit <= len(pieces) or not drawn[unit - 1]:
                continue
            lines += [_demoted(drawn[unit - 1]), ""]
            count = pdf.numbered_formulas(drawn[unit - 1]) if unit in aside else counts[unit - 1]
            numbers += range(starts[unit - 1], starts[unit - 1] + count)
    lines += [pdf.TEXT_END, ""]
    if version.questions:
        lines += [pdf.placed_mark(len(boxes)), ""]
        boxes.append({"kind": "questions", "items": [q["question"] for q in version.questions]})
        lines += [pdf.PAGE_BREAK, pdf.placed_mark(len(boxes)), ""]
        boxes.append({"kind": "answers", "items": [q["answer"] for q in version.questions]})
    left_out = "\n\n".join(cut for cut, _ in aside.values())
    return Layout("\n".join(lines).rstrip() + "\n", boxes, numbers, left_out)
