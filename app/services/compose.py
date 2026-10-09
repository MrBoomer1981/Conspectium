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
import difflib
import logging
import re
import time
from collections import Counter
from collections.abc import Iterable
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
# a heading or a bold label — "1))" too, as the reading wrote record 86's first
# case, and a bare number before a capitalised word: the author numbered record
# 87's theorem «1 Существование», «2 Число не является рациональным», the
# composer made them the list they are, and both numbers seemed to vanish —
# the record went out uncomposed twice. Before a lower-case word a number is a
# value: «2 мн-ва» written «два множества» is refused. A bullet may stand
# before the number: record 88's items became «* 2) …» and «* 1 База
# индукции», the composer's list over the author's, and seemed gained ...
_LIST_MARKER_RE = re.compile(
    r"^([ \t]*(?:[-*+•][ \t]+)?(?:#{1,6}[ \t]+)?(?:\*\*|__)?)"
    r"\d+(?:\.|\)+|(?=[ \t]+[A-ZА-ЯЁ]))[ \t]+",
    re.MULTILINE,
)
# ... or follows, inside a line, the colon or semicolon that introduces it.
# Record 59 lost its whole composition, headings and all, to "Примеры: 1) …"
# made into the list it was: the 1 counted inside the line and not at its
# start, so a number seemed to vanish. Inside a line only "1)": "Ответ: 2."
# ends on a value, and the value is what this guard is for.
_INLINE_MARKER_RE = re.compile(r"(?<=[:;][ \t])\d+\)(?=[ \t])")
# ... and a run of numbers in order, 1, 2, 3, each opening a line — or the
# first after the colon that introduces them — is a list whatever follows
# each (task 88). Records 91 and 92 numbered a metric's axioms «1
# тождественность», «2 симметричность», a corollary's parts «Следствие 2: 1
# …» and «2 …» on the next line: values to the rule above, and gone once the
# composer made the list they are — sixteen numbers of record 91, four of
# 92, and both went out uncomposed. A number alone stays a value: «2 мн-ва».
# Seen the same way on both sides, however the composer sets the item —
# «**1.** Тождественность», «### 2. …», «(3) …» — so that a list read as one
# in the source is read as one in the composition.
_ITEM_NUMBER_RE = re.compile(
    r"^[ \t]*(?:[-*+•][ \t]+)?(?:#{1,6}[ \t]+)?(?:\*\*|__)?\(?(?P<opening>\d+)"
    r"(?:\.|\)+)?(?:\*\*|__)?(?=[ \t]+\S)"
    r"|(?<=[:;][ \t])(?P<first>1)(?=[ \t]+\S)"
    r"|(?<=[ \t])(?P<inline>\d+)\)(?=[ \t]+\S)",
    re.MULTILINE,
)
# Space set by \phantom{…} draws nothing: record 92 kept a column aligned with
# «\phantom{\forall \varepsilon > 0 …}», and its 0 was no value to lose.
_PHANTOM_RE = re.compile(r"\\[hv]?phantom\{(?:[^{}]|\{[^{}]*\})*\}")
# How far one item's number may stand from the next: a line of its own each,
# or a formula of their own between them.
_ITEM_REACH = 6
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
# What the author struck out, as recognition read it. Its numbers are not the
# lecture's: record 88's «~~3.1 Строгое~~», a section number given up, was
# dropped by the composer and seemed lost — and hid the «1)» after it from
# the markers, which only look at the start of a line. Over two or three
# lines too (task 88).
_STRUCK_RE = re.compile(r"(?<!~)~~(?!~)(?:[^~\n]+\n){0,2}[^~\n]+?(?<!~)~~(?!~)")
# How alike a changed formula has to be to the source's to be put back as it
# was read: four-fifths of the characters, spaces aside. Record 89's
# $(c-h)^2 = c^2 - 2ch + h^2 =$ against the $c-h = …$ it was read as is 0.89;
# $I_3$ against $I_2$ is 0.67, and a formula that short has too many
# neighbours to tell which it was.
_RESTORE_SIMILARITY = 0.8
# The most lines of a working the composer is taken to make one formula of.
_MAX_JOINED = 4
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
    # Formulas the composer changed a number in, put back as they were read
    # (task 82).
    restored: int = 0
    # Whether the guards refused the first composition and a second was asked
    # for — what note_processed reports, so how often it saves a record is a
    # query.
    retried: bool = False
    stats: list[CallStats] = field(default_factory=list)


def _inline_marker(match: re.Match) -> str:
    """An inline item marker dropped — unless its bracket closes one opened
    before it on the line: "(0; 1)" is an interval, and its 1 is a value."""
    text = match.string
    line = text[text.rfind("\n", 0, match.start()) + 1 : match.start()]
    if match.group(0).endswith(")") and line.count("(") > line.count(")"):
        return match.group(0)
    return ""


def _items(markdown: str) -> str:
    """The text without the numbers of its numbered runs: 1, 2, 3 in order,
    each within _ITEM_REACH lines of the one before, two numbers at least
    (task 88). An item opens a line; the first may follow a colon inside
    its line, and a later one may stand inside a line as «3)» — «верно 3)
    …», record 91 — unless its bracket closes one opened before it, as
    «(0; 1)» and «[1; 2)» do."""
    found: list[tuple[int, int, str, re.Match]] = []
    for match in _ITEM_NUMBER_RE.finditer(markdown):
        kind = match.lastgroup
        line_start = markdown.rfind("\n", 0, match.start()) + 1
        before = markdown[line_start : match.start()]
        # «(0; 1)» and «[1; 2)» are intervals, their numbers values.
        opened = before.count("(") + before.count("[")
        if kind == "inline" and opened > before.count(")") + before.count("]"):
            continue
        found.append(
            (markdown.count("\n", 0, match.start()), int(match.group(kind)), kind, match)
        )
    items: set[int] = set()
    for position, (_, number, _, _) in enumerate(found):
        if number != 1:
            continue
        run = [position]
        for later in range(position + 1, len(found)):
            last_line, last_number, _, _ = found[run[-1]]
            next_line, next_number, kind, _ = found[later]
            if next_line - last_line > _ITEM_REACH:
                break
            if next_number == last_number + 1 and (
                next_line > last_line or kind == "inline"
            ):
                run.append(later)
        if len(run) > 1:
            items.update(run)
    out, last = [], 0
    for position in sorted(items):
        _, _, kind, match = found[position]
        out.append(markdown[last : match.start(kind)])
        last = match.end(kind)
    return "".join(out) + markdown[last:]


def _unstruck(markdown: str, struck: Iterable[str]) -> str:
    """`markdown` without the spans the source carries struck out, and
    without what \\phantom only measures (task 88)."""
    for span in struck:
        markdown = markdown.replace(span, "", 1)
    return _PHANTOM_RE.sub("", markdown)


def _numbers(markdown: str, struck: Iterable[str] = ()) -> Counter[str]:
    """The values a text carries: every number but an item's, and but those
    of `struck` — the spans the source carries struck out."""
    markdown = _unstruck(markdown, struck)
    unmarked = _INLINE_MARKER_RE.sub(
        _inline_marker, _LIST_MARKER_RE.sub(r"\1", _items(markdown))
    )
    return Counter(_NUMBER_RE.findall(unmarked))


def _counts(source: str, composed: str) -> tuple[Counter[str], Counter[str]]:
    """The numbers of the source and of the composition as the guard compares
    them: what the author struck out left out of both, so the composer may
    drop it (task 82). A struck span the composer adds is counted."""
    struck = _STRUCK_RE.findall(source)
    return _numbers(source, struck), _numbers(composed, struck)


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
    before, after = _counts(source, composed)
    if before != after:
        return "numbers"
    # What the author struck out may go, its marks and its length with it:
    # record 91's struck passage held one mark (task 88).
    struck = _STRUCK_RE.findall(source)
    if _unstruck(source, struck).count(_UNREADABLE) != _unstruck(
        composed, struck
    ).count(_UNREADABLE):
        return "unreadable marks"
    if len(composed) < len(_unstruck(source, struck)) * _MIN_LENGTH_RATIO:
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


def _inner(match: re.Match) -> str:
    """The LaTeX of a formula pdf draws, without its dollars."""
    return match.group(1) if match.group(1) is not None else match.group(2)


def _alike(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _joined(first: str, second: str) -> str:
    """Two lines of a working as one formula. The author writes the sign that
    breaks a line again at the start of the next — record 89's «h^2 =» over
    «= c^2 - …» — and inside one formula it stands once."""
    head, tail = first.rstrip(), second.lstrip()
    if head and tail and head[-1] == tail[0] and head[-1] in "=+-<>":
        tail = tail[1:].lstrip()
    return f"{head} {tail}"


def _workings(source: str) -> list[tuple[str, ...]]:
    """What a formula of the composition may have been read as: one formula
    of the source, or up to _MAX_JOINED of them standing one after another
    with nothing but space between — the lines of one working, which the
    composer makes one formula."""
    found = list(pdf._MATH_RE.finditer(source))
    workings = []
    for start, first in enumerate(found):
        run = [first]
        workings.append((_inner(first),))
        for later in found[start + 1 : start + _MAX_JOINED]:
            if source[run[-1].end() : later.start()].strip():
                break
            run.append(later)
            workings.append(tuple(_inner(match) for match in run))
    return workings


def _restore_formulas(source: str, composed: str) -> tuple[str, int]:
    """Put back, as recognition read it, every formula the composer changed a
    number in, and count them (task 82).

    The composer corrects what does not add up: record 89 reads
    $c-h = c^2 - 2ch + h^2 =$, where the working needs $(c-h)^2$, and its
    compositions came back squared nine times of fourteen. The guard refused
    them, rightly — a formula changed is the author corrected — and the
    record lost every heading for one exponent. A repair rather than a
    refusal, as for a heading: what the source read stands where the
    composer set its own formula, and the guards then judge the whole as
    before. A formula the composition carries as it was read is never
    touched, and each one of the source is put back once.

    The composer also makes one formula of a working's lines, and record
    89's square came that way: «$c-h = … + h^2 =$» over «$= c^2 - … = 2$»,
    made «$(c-h)^2 = … = 2$». So a changed formula is matched against runs
    of the source's formulas as well as single ones (_workings), the closest
    put back if four-fifths of its characters are alike — and only where
    that brings the numbers closer to the source's. One changed without its
    numbers — a frame, a space, a command spelled another way — is markup
    and stays; and a working put back as one of its lines would lose the
    others' numbers.
    """
    target, now = _counts(source, composed)

    def distance(counts: Counter[str]) -> int:
        return sum(((target - counts) + (counts - target)).values())

    pool = Counter(_bare(_inner(match)) for match in pdf._MATH_RE.finditer(source))
    changed = []
    for match in pdf._MATH_RE.finditer(composed):
        bare = _bare(_inner(match))
        if pool[bare] > 0:
            pool[bare] -= 1
        else:
            changed.append(match)
    workings = _workings(source)
    pieces: list[str] = []
    end = restored = 0
    for match in changed:
        bare = _bare(_inner(match))
        free = [
            working
            for working in workings
            if all(
                pool[line] >= count
                for line, count in Counter(map(_bare, working)).items()
            )
        ]
        closest = max(free, key=lambda w: _alike(bare, _bare("".join(w))), default=None)
        if closest is None or _alike(bare, _bare("".join(closest))) < _RESTORE_SIMILARITY:
            continue
        read = closest[0]
        for line in closest[1:]:
            read = _joined(read, line)
        after = (
            now
            - Counter(_NUMBER_RE.findall(_inner(match)))
            + Counter(_NUMBER_RE.findall(read))
        )
        if distance(after) >= distance(now):
            continue
        now = after
        pool -= Counter(map(_bare, closest))
        group = 1 if match.group(1) is not None else 2
        pieces += [composed[end : match.start(group)], read]
        end = match.end(group)
        restored += 1
    pieces.append(composed[end:])
    return "".join(pieces), restored


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
                        automatic_function_calling=vision.NO_AFC,
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


async def _sample(markdown: str, all_stats: list[CallStats]) -> str | None:
    """One composition asked for, a call that failed asked again on
    _ATTEMPTS' terms; None when no call came back. Every attempt's stats go
    into `all_stats`."""
    for attempt in range(_ATTEMPTS):
        composed, stats, retryable = await _one_call(markdown)
        all_stats.append(stats)  # rule 4: a call that failed was still a call
        if composed is not None:
            return composed
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
            return None
        await asyncio.sleep(_RETRY_PAUSE_S)
    return None


def _checked(markdown: str, composed: str) -> Composition:
    """One composition through the repairs and the guards: the composed
    document when they accept it, the source and the reason when not."""
    # Before the guards, so that what they checked is what gets stored.
    composed, demoted = _demote_invented_headings(composed)
    composed, unmarked = _cap_marks(markdown, composed)
    # Only where the numbers would refuse it: a formula the composer changed
    # with every number kept is markup, its own business.
    restored = 0
    before, after = _counts(markdown, composed)
    if before != after:
        composed, restored = _restore_formulas(markdown, composed)
        before, after = _counts(markdown, composed)
    refused = _refusal(markdown, composed)
    drift = _drift(markdown, composed)
    # How many numbers went and came, never which: they are the page's.
    # Record 59's refusal took two paid calls in the container to explain.
    logger.info(
        "compose: %s, %d -> %d chars, word drift %d, numbers %d lost %d gained, "
        "%d headings demoted, %d marks taken back, %d formulas put back, model %s",
        f"refused ({refused})" if refused else "accepted",
        len(markdown),
        len(composed),
        drift,
        sum((before - after).values()),
        sum((after - before).values()),
        demoted,
        unmarked,
        restored,
        settings.COMPOSE_MODEL,
    )
    return Composition(
        markdown if refused else composed,
        refused=refused,
        drift=drift,
        demoted=demoted,
        unmarked=unmarked,
        restored=restored,
    )


async def compose(markdown: str) -> Composition:
    """Format a trusted transcription. Never touches the database."""
    if not settings.COMPOSE_ENABLED:
        return Composition(markdown)

    all_stats: list[CallStats] = []
    composed = await _sample(markdown, all_stats)
    if composed is None:
        return Composition(markdown, refused="call failed", stats=all_stats)

    result = _checked(markdown, composed)
    if result.refused:
        # A refusal is one sample's. Record 66's composition was refused in
        # production for three numbers it gained, and asked for six times
        # again in the container it was accepted six times; a record that
        # loses its composition loses its headings. So a refused one is asked
        # for once more — one call more, on about one record in thirty — and
        # the guards judge the second as they judged the first.
        again = await _sample(markdown, all_stats)
        if again is not None:
            result = _checked(markdown, again)
        result.retried = True
    result.stats = all_stats
    return result
