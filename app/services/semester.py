"""A subject's whole semester as one study version (task 63; task 52 in the
new form the CEO gave it on 2026-10-12, its shape decided on 2026-10-13).

Not the lectures one after another: every lecture's text, as its document
draws it, set out by the semester's topics — each piece under its
lecture's day, «О чём тема» under every topic, questions to check oneself
at the end. A study version of the subject (study.py), built the same way:
the model answers with an order — the lectures' units by number, through
the semester — and with its own texts; code moves the units, so not a word
of the authors' changes and every unit stands once. None of the bot's boxes
the lectures carry, the CEO's: the author's text and the semester's own.

Never touches the database; the caller kept the arrangement on the subject
(`subjects.semester`) by its fingerprint.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

from app.services import pdf, study, vision

SEMESTER_PROMPT_FILE = "prompts-semester-v1.md"
SEMESTER_PROMPT = vision.load_prompt(SEMESTER_PROMPT_FILE)
SEMESTER_PROMPT_WORDS = len(SEMESTER_PROMPT.split())

# The prompt asks for three to twelve topics and five to ten questions;
# these are where "at most" is kept.
_MAX_TOPICS = 14
_MAX_QUESTIONS = 10
# What a fingerprint is taken of besides the lectures: the rule of putting
# them together. Raised when that changes, so a kept arrangement is built
# again.
_CUT_VERSION = "1"
# What separates the units while their formulas are numbered as the
# document numbers them, as study._for_reading does.
_SEPARATOR = "\n\n⟦⟧\n\n"


@dataclass
class Lecture:
    """One lecture of the semester: the day it was given, its title, and
    its text as its document draws it — the base with what other notebooks
    add, its drawings numbered through the semester."""

    day: date
    title: str
    markdown: str


def head(lecture: Lecture) -> str:
    """The line a run of one lecture's units stands under: its day and its
    title, in characters — a heading draws no formula."""
    return f"Лекция от {lecture.day:%d.%m} — {pdf.plain(lecture.title)}"


def _pieces(lectures: list[Lecture]) -> tuple[list[str], dict[int, int]]:
    """Every lecture's units, in the semester's order, and the lecture each
    unit is from, by its number from 1."""
    pieces: list[str] = []
    owner: dict[int, int] = {}
    for index, lecture in enumerate(lectures):
        for piece in study.units(lecture.markdown):
            pieces.append(piece)
            owner[len(pieces)] = index
    return pieces, owner


def _reading(lectures: list[Lecture], pieces: list[str], owner: dict[int, int]) -> str:
    """The units as the model reads them: numbered through the semester,
    each lecture's opened by its day and title, every main formula with the
    number the document gives it."""
    numbered = pdf.numbered_for_reading(_SEPARATOR.join(pieces)).split(_SEPARATOR)
    blocks: list[str] = []
    for number, piece in enumerate(numbered, 1):
        if number == 1 or owner[number] != owner[number - 1]:
            lecture = lectures[owner[number]]
            blocks.append(f"ЛЕКЦИЯ от {lecture.day:%d.%m.%Y} — {pdf.plain(lecture.title)}")
        blocks.append(f"[{number}] {piece}")
    return "\n\n".join(blocks)


def fingerprint(lectures: list[Lecture]) -> str:
    """The lectures an arrangement was built from, the way they were put
    together and the prompt that arranged them: a lecture added or a
    notebook joining one, and it is built again."""
    whole = "\n".join(
        f"{lecture.day.isoformat()}\n{lecture.title}\n{lecture.markdown}" for lecture in lectures
    )
    return hashlib.sha1(
        f"{_CUT_VERSION}\n{SEMESTER_PROMPT_FILE}\n{whole}".encode()
    ).hexdigest()[:16]


async def build(lectures: list[Lecture]) -> study.Study:
    """The semester's arrangement, one call over every lecture's units.
    Never touches the database."""
    pieces, owner = _pieces(lectures)
    if len(lectures) < 2 or len(pieces) < 2:
        return study.Study(refused="one lecture")
    return await study.arrange(
        pieces,
        _reading(lectures, pieces, owner),
        fingerprint(lectures),
        prompt=SEMESTER_PROMPT,
        kind="semester",
        most_topics=_MAX_TOPICS,
        most_questions=_MAX_QUESTIONS,
    )


def layout(lectures: list[Lecture], version: study.Study) -> study.Layout:
    """The semester for render: each topic, its «О чём тема», and under it
    the runs of its units each under its lecture's day; the questions at the
    end, their answers on a page of their own."""
    pieces, owner = _pieces(lectures)
    heads = {number: head(lectures[index]) for number, index in owner.items()}
    return study.layout_of(pieces, version, heads)
