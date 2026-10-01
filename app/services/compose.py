"""Stage two: the trusted transcription, formatted.

This call never sees the photograph. That is the whole point of separating it
from recognition, not an implementation detail: the worst failure this project
has reproduced — a page photographed from a distance coming back as a fluent
textbook retelling with `unreadable_count: 0` — needs an image to invent from.
Here there is none. What arrives is text three independent runs already agreed
on, and the only job is markup.

The other half of the separation is that the result is checkable *by code*.
CLAUDE.md records that a verification model call does not work, and it does
not: that one compared text against a photograph, which is perception again,
and it invented a discrepancy that was not there. These guards compare text
against text. A number that changed, a mark that vanished, a document that
came back shorter — none of that is a matter of opinion.

Refused or failed, the record still goes out: the caller ships the text it
already had. The worst case of this stage is the output without it.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field

from google.genai import types

from app.core.config import settings
from app.services import pdf, vision
from app.services.vision import CallStats

logger = logging.getLogger(__name__)

COMPOSE_PROMPT = vision.load_prompt(settings.COMPOSE_PROMPT_FILE)
COMPOSE_PROMPT_WORDS = len(COMPOSE_PROMPT.split())

# A composed document is longer than its source — markup only adds. Anything
# that comes back materially shorter lost something, and the numbers guard
# only catches that when the lost part had numbers in it.
_MIN_LENGTH_RATIO = 0.8

# "1. " and "2) " that count items are markdown, not values on the page. Rule 8
# lets the composer turn a run of lines into a list, which renumbers them, and
# that must not read as arithmetic being rewritten. Such a marker opens a line,
# a heading or a bold label ...
_LIST_MARKER_RE = re.compile(
    r"^([ \t]*(?:#{1,6}[ \t]+)?(?:\*\*|__)?)\d+[.)][ \t]+", re.MULTILINE
)
# ... or follows, inside a line, the colon or semicolon that introduces it.
# Record 59 lost its whole composition, headings and all, to "Примеры: 1) …"
# made into the list it was: the 1 counted inside the line and not at its
# start, so a number seemed to vanish. Inside a line only "1)": "Ответ: 2."
# ends on a value, and the value is what this guard is for.
_INLINE_MARKER_RE = re.compile(r"(?<=[:;][ \t])\d+\)(?=[ \t])")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
# Letters only. Digits are the numbers guard's business and punctuation is
# markup's, so neither belongs in a count of words.
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

_UNREADABLE = "[неразборчиво]"

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
# A line that continues the heading as a list is a list under a heading, which
# is what rule 8 asks for. Only prose running on in lower case is the failure.
_LIST_RE = re.compile(r"^([-*•]|\d+[.)])\s")
_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)

# How many formulas a section may have this stage mark as main. Emphasis on
# everything is emphasis on nothing, and what a section's result is, is the
# composer's reading of the page — interpretation, capped like a heading is.
_MAX_MARKS_PER_SECTION = 2
_SPACE_RE = re.compile(r"\s+")

# Two attempts, one pause. Recognition takes three because a lost page costs
# the whole album; here a lost call costs the markup of a record that is
# delivered either way, so the second attempt is insurance against a 429 or a
# 503 and not a machine for getting an answer out of the model.
_ATTEMPTS = 2
_RETRY_PAUSE_S = 2


@dataclass
class Composition:
    """What the caller stores, whether or not the stage ran.

    `markdown` is always usable: the composed document when it was accepted,
    the untouched source when composition was off, failed, or was refused.
    """

    markdown: str
    refused: str | None = None
    # Words added or dropped, reported and never refused on. Rule 6 of the
    # prompt asks for "### Определение" over a definition, so a word the page
    # does not carry is *requested* — a guard here would refuse by design.
    # Measure the size of the drift first; decide what to do about it on data.
    drift: int = 0
    # Headings the stage wrote and the repair took back. Reported for the same
    # reason drift is: it is the size of a liberty, and nobody has decided yet
    # what a large number here should mean.
    demoted: int = 0
    # Main-formula marks past two in a section, taken back the same way.
    unmarked: int = 0
    stats: list[CallStats] = field(default_factory=list)


def _inline_marker(match: re.Match) -> str:
    """An inline item marker dropped — unless its bracket closes one opened
    before it on the line: "(0; 1)" is an interval, and its 1 is a value."""
    text = match.string
    line = text[text.rfind("\n", 0, match.start()) + 1 : match.start()]
    if match.group(0).endswith(")") and line.count("(") > line.count(")"):
        return match.group(0)
    return ""


def _numbers(markdown: str) -> Counter[str]:
    unmarked = _INLINE_MARKER_RE.sub(_inline_marker, _LIST_MARKER_RE.sub(r"\1", markdown))
    return Counter(_NUMBER_RE.findall(unmarked))


def _words(markdown: str) -> Counter[str]:
    return Counter(word.lower() for word in _WORD_RE.findall(markdown))


def _drift(source: str, composed: str) -> int:
    """How many words the composer added or dropped, in either direction."""
    before, after = _words(source), _words(composed)
    return sum(((before - after) + (after - before)).values())


def _refusal(source: str, composed: str) -> str | None:
    """The guard that refuses this composition, or None to accept it.

    Named in the order they are worth hearing about: a changed number is
    invisible to a reader and fatal, a lost mark hides a hole in the page,
    and a document that shrank lost something neither of those two caught.
    """
    if not composed.strip():
        return "empty"
    if _numbers(source) != _numbers(composed):
        return "numbers"
    if source.count(_UNREADABLE) != composed.count(_UNREADABLE):
        return "unreadable marks"
    if len(composed) < len(source) * _MIN_LENGTH_RATIO:
        return "too short"
    return None


def _invented_heading(text: str, following: str) -> bool:
    """Is this heading a section the page had, or one the composer decided on?

    Three shapes, all of them found in the corpus before this existed. A
    heading with no letters in it ("4.") is a number the composer promoted and
    a topic nobody can search by. One that does not start with a word or a
    number started as a formula line. And one whose next line of prose begins
    in lower case is the first half of a sentence — the composer itself writes
    that content correctly elsewhere, as a bold term and a colon, which is how
    we know it is the markup and not the page that is wrong.
    """
    bare = text.replace("*", "").replace("_", "").strip()
    if not _LETTER_RE.search(bare):
        return True
    if not bare[0].isalnum():
        return True
    if not following or following.startswith("#") or _LIST_RE.match(following):
        return False
    first = _LETTER_RE.search(following)
    # The letter has to be the first thing on the line: "**Принцип**: если мы"
    # opens with markup and is a sentence of its own, not a continuation.
    return (
        first is not None
        and first.group().islower()
        and following[: first.start()].strip("*_ ") == ""
    )


def _demote_invented_headings(composed: str) -> tuple[str, int]:
    """Take the marker off every heading that is not one, and count them.

    A repair rather than a refusal, and that is the whole decision here. One
    invented heading in a document with ten good ones would cost all ten if it
    refused, and the corpus says the ratio is about one in ten (11 headings of
    111 on 2026-09-23). What is removed is markup the stage added; every word
    stays on its line, so the numbers, the marks and the length the guards
    below compare are untouched by construction.

    It matters more than a tidy document: topics are read off headings, so an
    invented section becomes a word the corpus is searched by — the one part
    of the pipeline that interprets, feeding the part that has to be literal.
    """
    lines = composed.split("\n")
    demoted = 0
    for index, line in enumerate(lines):
        found = _HEADING_RE.match(line)
        if not found:
            continue
        following = next(
            (later.strip() for later in lines[index + 1:] if later.strip()), ""
        )
        if _invented_heading(found.group(2), following):
            lines[index] = found.group(2)  # the words stay, the marker goes
            demoted += 1
    return "\n".join(lines), demoted


def _bare(latex: str) -> str:
    return _SPACE_RE.sub("", latex)


def _cap_marks(source: str, composed: str) -> tuple[str, int]:
    """Take the frame off every main-formula mark past two in a section, and
    count them.

    A frame the source already had is the author's: drawn on the page, read
    by recognition as \\boxed{...}. It is never taken off and never counted —
    only the marks this stage added are its liberty. What is removed is the
    frame and nothing else, so the formula stays where it was and the numbers,
    marks and length the guards compare cannot move.
    """
    authors = Counter(_bare(inner) for inner in pdf.boxed_contents(source))
    lines = composed.split("\n")
    kept = 0
    removed = 0
    for index, line in enumerate(lines):
        if _HEADING_RE.match(line):
            kept = 0
            continue
        for inner in pdf.boxed_contents(line):
            if authors[_bare(inner)] > 0:
                authors[_bare(inner)] -= 1
                continue
            if kept < _MAX_MARKS_PER_SECTION:
                kept += 1
                continue
            lines[index] = lines[index].replace(f"\\boxed{{{inner}}}", inner, 1)
            removed += 1
    return "\n".join(lines), removed


async def _one_call(markdown: str) -> tuple[str | None, CallStats, bool]:
    """One call, and whether the failure that ended it is worth another.

    None means the call itself never came back. An answer that arrived empty
    is returned as the empty string: the call happened, it was billed, and
    "empty" is a different thing to see in the log than "call failed"."""
    started = time.monotonic()
    model = settings.COMPOSE_MODEL
    try:
        async with vision._API_SLOTS:
            response = await asyncio.wait_for(
                vision._client.aio.models.generate_content(
                    model=model,
                    contents=[COMPOSE_PROMPT, markdown],
                    # No response_mime_type: the answer is markdown, not JSON,
                    # so there is nothing here to parse and nothing to fail.
                    config=types.GenerateContentConfig(
                        temperature=1.0,
                        max_output_tokens=vision.MAX_OUTPUT_TOKENS,
                        thinking_config=vision.thinking_config(
                            settings.COMPOSE_THINKING_LEVEL
                        ),
                    ),
                ),
                timeout=settings.COMPOSE_CALL_TIMEOUT_S,
            )
    except Exception as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        # A timeout is the one transient failure not worth calling again, and
        # vision._should_retry says the opposite — rightly, for a page: there
        # the ceiling is tens of seconds and a hung connection is the usual
        # cause. Here the ceiling is minutes and sized for the whole record, so
        # a call that reached it was working rather than hanging. Waiting the
        # same minutes again buys the same answer and doubles the window in
        # which a deploy cancels the background task holding the record.
        retryable = vision._should_retry(exc) and not isinstance(exc, TimeoutError)
        return None, CallStats(
            kind="compose",
            model=model,
            tokens_in=None,
            tokens_out=None,
            tokens_thought=None,
            cost_usd=None,
            latency_ms=latency_ms,
            success=False,
            error=vision._short_error(exc),
        ), retryable

    tokens_in, tokens_out, tokens_thought = vision._usage(response)
    text = vision._response_text(response).strip()
    latency_ms = int((time.monotonic() - started) * 1000)
    return text, CallStats(
        kind="compose",
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tokens_thought=tokens_thought,
        cost_usd=vision._cost_usd(model, tokens_in, tokens_out, tokens_thought),
        latency_ms=latency_ms,
        success=bool(text),
        error=None if text else "empty model response",
    ), False


async def compose(markdown: str) -> Composition:
    """Format a trusted transcription. Never touches the database."""
    if not settings.COMPOSE_ENABLED:
        return Composition(markdown)

    all_stats: list[CallStats] = []
    composed: str | None = None
    for attempt in range(_ATTEMPTS):
        composed, stats, retryable = await _one_call(markdown)
        all_stats.append(stats)  # rule 4: a call that failed was still a call
        if composed is not None:
            break
        last = attempt == _ATTEMPTS - 1
        # stats.error and not the exception, for the reason vision.transcribe
        # gives: str(TimeoutError()) is "", and the line used to end in a colon.
        logger.warning(
            "compose attempt %d/%d failed, %s: %s",
            attempt + 1,
            _ATTEMPTS,
            "retrying" if retryable and not last else "no retry",
            stats.error,
        )
        if last or not retryable:
            break
        await asyncio.sleep(_RETRY_PAUSE_S)

    if composed is None:
        return Composition(markdown, refused="call failed", stats=all_stats)

    # Before the guards, so that what they checked is what gets stored.
    composed, demoted = _demote_invented_headings(composed)
    composed, unmarked = _cap_marks(markdown, composed)
    refused = _refusal(markdown, composed)
    drift = _drift(markdown, composed)
    # How many numbers went and came, never which: they are the page's.
    # Record 59's refusal took two paid calls in the container to explain.
    before, after = _numbers(markdown), _numbers(composed)
    logger.info(
        "compose: %s, %d -> %d chars, word drift %d, numbers %d lost %d gained, "
        "%d headings demoted, %d marks taken back, model %s",
        f"refused ({refused})" if refused else "accepted",
        len(markdown),
        len(composed),
        drift,
        sum((before - after).values()),
        sum((after - before).values()),
        demoted,
        unmarked,
        settings.COMPOSE_MODEL,
    )
    if refused:
        return Composition(
            markdown, refused=refused, drift=drift, demoted=demoted,
            unmarked=unmarked, stats=all_stats,
        )
    return Composition(
        composed, drift=drift, demoted=demoted, unmarked=unmarked, stats=all_stats
    )
