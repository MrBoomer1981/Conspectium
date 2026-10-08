"""Stage three: hard places explained, and the record summed up.

The group's reader was not at the lecture, and the record is exactly what the
author wrote — steps skipped, notation never introduced, the lecturer's
context left unsaid. This stage adds what a classmate who was there would
add. Everything it writes is the bot's own and is printed as the bot's, in a
box of its own tone: adding is not forbidden, adding unmarked is.

It runs over the text the runs agreed on and the composer marked up, and like
the composer it never sees the photograph — the worst failure this project
has reproduced needs an image to invent from.

Two steps, because one did not work. Asked to explain and search in a single
call, the model searched for nothing: it knows complex numbers and said so
from memory, and asked for a quote from a found source it wrote plausible
textbook quotes without a single search behind them. A short question of its
own — "find a source for this" — it does search. So the first call writes the
explanations and the summary, and each explanation then gets a call of its
own with Google Search switched on.

What may be printed is held by two guards, both in code:

- An explanation carries the sources its own search call returned, read from
  that call's grounding metadata — never from anything the model writes about
  its sources. One whose search returned nothing is not printed. The reader
  cannot check a claim, so the page has to say where it is from.
- The summary restates the record and may not state a number the record does
  not carry: a new number there would be the model inventing inside the one
  box that claims to say what the lecture said.

Failed, refused or off, the record goes out without the stage: its worst case
is the document it would have been anyway.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
from dataclasses import dataclass, field

from google.genai import types

from app.core.config import GROUNDING_USD_PER_QUERY, settings
from app.services import mathcheck, pdf, vision
from app.services.vision import CallStats

logger = logging.getLogger(__name__)

EXPLAIN_PROMPT = vision.load_prompt(settings.EXPLAIN_PROMPT_FILE)
EXPLAIN_PROMPT_WORDS = len(EXPLAIN_PROMPT.split())
# Whether the prompt asks for the teacher's boxes as well (v2 on, task 56):
# read from the prompt, as recognition's switches are, and printed at start.
PROMPT_ASKS_ELEMENTS = '"elements"' in EXPLAIN_PROMPT
# The question each explanation is searched with. Short on purpose: a short,
# direct request to find something is what makes the model actually search.
SOURCE_PROMPT = vision.load_prompt("prompts-explain-source-v2.md")

# The prompt asks for one or two a section and eight at most; this is where
# "at most" is kept.
_MAX_EXPLANATIONS = 8
# The teacher's boxes (task 56): the plan of a proof, set before it; what a
# condition is for and what breaks without it; an example the lecture did not
# give. Reasoning about the lecture rather than facts from books, so no search
# can source one: each is printed without a source, under a label that says
# whose it is, and checked by code wherever there is something to check.
ELEMENT_KINDS = ("idea", "condition", "example")
# The model writes a kind in Russian as often as not.
_KIND_NAMES = {
    "идея": "idea",
    "условие": "condition",
    "зачем условие": "condition",
    "пример": "example",
    "контрпример": "example",
}
# The prompt asks for one before every proof, one at every condition and one
# at every new notion — the reference notebook's density, sixteen remarks in
# fourteen pages; this is the ceiling, not the aim.
_MAX_ELEMENTS = 12
# Three links under an explanation say where it is from; more is a list.
_MAX_SOURCES = 3
# One search over one short claim. The whole-record ceiling would let a hung
# call hold its slot for minutes.
_SOURCE_TIMEOUT_S = 90
# The composer's retry policy, for the composer's reasons: a call over the
# whole record, where a timeout means it was working and a second wait buys
# the same answer.
_ATTEMPTS = 2
_RETRY_PAUSE_S = 2

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")
# A LaTeX command written into a JSON string with one backslash instead of
# two. "\varphi" is an escape JSON does not have and the whole answer failed
# to parse, while "\frac", "\rho", "\text" and "\nu" are escapes it does
# have — a form feed, a carriage return, a tab, a newline — and parsed into
# garbage without a word. A lone backslash before two or more Latin letters
# is a command, not an escape, and is doubled; one before any other character
# JSON does not know is doubled too. The strict JSON mode the first call asks
# for should make this rare; the parser does not rely on it.
_LONE_COMMAND_RE = re.compile(r"(?<!\\)\\(?=[A-Za-z]{2,})")
_BAD_ESCAPE_RE = re.compile(r'(?<!\\)\\(?![\\"/bfnrtu])')


@dataclass
class Source:
    title: str
    uri: str


# Where a source stands, most trusted first. A search returns what it returns
# — a university's course beside a shop's page — and an explanation shows
# three links, so which three, and in what order, is decided here: science,
# then encyclopedias, then study sites, then everything else. Nothing is
# dropped for being everyday; it only stands behind what is better (the
# author's decision, 2026-09-25). The lists are kept by hand and short on
# purpose: a site nobody listed is "everything else" and keeps the search's
# own order, so a name missing here costs a place, never a source — a forum
# excepted, which is no source at all (_NOT_SOURCES, 2026-10-01). The Gemini
# API names a site by its registered domain — "wolfram.com", never
# "mathworld.wolfram.com" — so that is the form a name is listed in.
_TIERS = (
    re.compile(
        r"(^|\.)edu(\.[a-z]{2})?$|\.ac\.[a-z]{2}$|univ(ersit|-|\.)"
        r"|(^|\.)(msu|spbu|nsu|nsc|mipt|hse|bmstu|mephi|itmo|urfu|kpfu|tsu|spbstu|"
        r"misis|rudn|tpu|susu|nstu|unn|teach-in|ras|imath|mccme|mathnet|math-net|elibrary|"
        r"cyberleninka|arxiv|springer|sciencedirect|jstor|ams|ieee|nature|nih|"
        r"wiley|tandfonline|cambridge|oup)\."
    ),
    re.compile(
        r"(^|\.)(wikipedia\.org|bigenc\.ru|britannica\.com|encyclopediaofmath\.org|"
        r"scholarpedia\.org|wolfram\.com|academic\.ru|ncatlab\.org|"
        r"planetmath\.org)$"
    ),
    re.compile(
        r"(^|\.)(stepik\.org|coursera\.org|edx\.org|khanacademy\.org|libretexts\.org|"
        r"intuit\.ru|foxford\.ru|problems\.ru|libelli\.ru|mathprofi\.ru|"
        r"studfile\.net|studme\.org|studopedia\.ru)$"
    ),
)


# A forum, a social network or a video is not a source, whatever else stands
# under the explanation: record 59 printed reddit.com beside ucdavis.edu, and
# record 62 the mathematical forum dxdy.ru and askfilo.com's homework answers.
# Its page is dropped, and an explanation left with none is dropped with it,
# by the rule that already holds (`explain_unsourced`). Registered domains,
# the form the Gemini API names a site in — see _TIERS.
_NOT_SOURCES = re.compile(
    r"(^|\.)(reddit\.com|quora\.com|mail\.ru|pikabu\.ru|vk\.com|vk\.ru|ok\.ru|"
    r"facebook\.com|instagram\.com|x\.com|twitter\.com|t\.me|tiktok\.com|"
    r"youtube\.com|youtu\.be|rutube\.ru|dzen\.ru|stackexchange\.com|"
    r"stackoverflow\.com|mathoverflow\.net|answers\.com|brainly\.(com|ru)|"
    r"znanija\.com|dxdy\.ru|askfilo\.com)$"
)


def not_a_source(site: str) -> bool:
    """A forum, a social network or a video, by the site's name. Asked when a
    search returns its pages, and again when a stored record is drawn."""
    return bool(_NOT_SOURCES.search(site.strip().lower().removeprefix("www.")))


# An explanation that judges the record — calls a line of it a slip of the
# pen, a typo, the author's mistake. The prompt says «Не исправляй автора»,
# and record 62 printed «В конспекте допущена опечатка» over a union both of
# its readings agree on: what the bot cannot tell is whether the author wrote
# it so or the reading saw it so, and a reader cannot tell either. Such an
# explanation is dropped (`explain_judged`), in a stored record too.
_JUDGES_RE = re.compile(
    r"опечатк|описк|ошибочно\s+(?:записан|написан|указан)|"
    r"ошибк\w*\s+(?:в\s+)?(?:автор|конспект|записи)|"
    r"(?:в|у)\s+(?:конспект|записи|записях|автор)\w*[\s,]+(?:[\w-]+[\s,]+){0,3}?ошибк|"
    r"автор\w*[\s,]+(?:[\w-]+[\s,]+){0,3}?(?:ошиб|перепута)",
    re.IGNORECASE,
)


def judges_the_record(title: str, text: str) -> bool:
    """Whether an explanation calls something in the record an error of its
    author's. Asked when the stage writes it, and when a stored record is
    drawn."""
    return bool(_JUDGES_RE.search(f"{title} {text}"))


def _tier(site: str) -> int:
    """0 for a scientific site, 1 an encyclopedia, 2 a study site, 3 the rest."""
    site = site.strip().lower().removeprefix("www.")
    for tier, pattern in enumerate(_TIERS):
        if pattern.search(site):
            return tier
    return len(_TIERS)


@dataclass
class Explanation:
    anchor: str
    title: str
    text: str
    sources: list[Source] = field(default_factory=list)


@dataclass
class Element:
    kind: str  # one of ELEMENT_KINDS
    anchor: str
    title: str
    text: str


@dataclass
class Explaining:
    """What the caller stores, whether or not the stage ran."""

    explanations: list[Explanation] = field(default_factory=list)
    summary: str | None = None
    # Why nothing came back: None when the stage ran and its answer was read.
    refused: str | None = None
    # Explanations whose search found nothing, and so were not printed.
    unsourced: int = 0
    # Explanations that judged the record, and so were not searched for.
    judged: int = 0
    # A summary thrown away for stating a number the record does not carry.
    summary_refused: bool = False
    # The teacher's boxes kept, and those a check of code threw away.
    elements: list[Element] = field(default_factory=list)
    elements_dropped: int = 0
    stats: list[CallStats] = field(default_factory=list)


def _answer(text: str) -> dict | None:
    """The answer as the JSON object asked for, or None. Never raises."""
    stripped = _FENCE_RE.sub("", text.strip())
    start, end = stripped.find("{"), stripped.rfind("}")
    if start == -1 or end <= start:
        return None
    body = _LONE_COMMAND_RE.sub(r"\\\\", stripped[start : end + 1])
    body = _BAD_ESCAPE_RE.sub(r"\\\\", body)
    try:
        # A line break written raw inside a string is still the string's,
        # not a reason to lose the answer (task 87).
        data = json.loads(body, strict=False)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def parse(text: str) -> tuple[list[dict], str | None] | None:
    """The answer's explanations and summary, or None when it is not the JSON
    asked for. Never raises — rule 7, the same as recognition's answers."""
    data = _answer(text)
    if data is None:
        return None
    items = data.get("explanations", [])
    if not isinstance(items, list):
        return None
    explanations = [
        {
            "anchor": str(item.get("anchor", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "text": str(item.get("text", "")).strip(),
        }
        for item in items
        if isinstance(item, dict) and str(item.get("text", "")).strip()
    ]
    summary = data.get("summary")
    summary = summary.strip() if isinstance(summary, str) and summary.strip() else None
    return explanations, summary


def elements_of(text: str) -> list[dict]:
    """The teacher's boxes the answer holds, each with a kind it knows, a
    place and a text — none under a prompt that asks for none. Never raises."""
    data = _answer(text)
    items = data.get("elements") if data is not None else None
    if not isinstance(items, list):
        return []
    found: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "")).strip().lower()
        kind = _KIND_NAMES.get(kind, kind)
        box = {
            "kind": kind,
            "anchor": str(item.get("anchor", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "text": str(item.get("text", "")).strip(),
        }
        if kind in ELEMENT_KINDS and box["anchor"] and box["text"]:
            found.append(box)
    return found


# A formula inside an explanation's text, between its dollars.
_FORMULA_RE = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$", re.DOTALL)


def _working_fails(text: str) -> bool:
    """Whether an example's working holds an equality whose numeric sides
    differ. mathcheck compares a chain of two "=" or more and leaves a single
    one alone — on a lecture page mostly a definition — but in an example the
    bot wrote, a single "2 + 2 = 5" is exactly what is to be caught. So every
    "=" is compared here, with mathcheck's own reading of a number and its
    tolerance; a side that is not a number is passed over, as it does. Each
    formula is read on its own: a word before one would make its left side no
    number at all."""
    formulas = [a or b for a, b in _FORMULA_RE.findall(text)] or text.splitlines()
    for formula in formulas:
        if "=" not in formula:
            continue
        sides = mathcheck.split_top_level(mathcheck._strip_noise(formula), "=")
        values = [
            value
            for value in (mathcheck.eval_numeric(side) for side in sides)
            if value is not None and math.isfinite(value)
        ]
        for first, second in zip(values, values[1:]):
            base = max(abs(first), abs(second))
            if base and abs(first - second) / base > mathcheck.CHAIN_TOLERANCE:
                return True
    return False


def _element_refused(box: dict, carried: set[str]) -> str | None:
    """Why a teacher's box may not be printed, or None. An example brings its
    own numbers, so its arithmetic is what is checked; an idea or a
    condition talks about the record, so it may state no number the record
    does not carry — the summary's guard."""
    if judges_the_record(box["title"], box["text"]):
        return "judged"
    if box["kind"] == "example":
        if _working_fails(box["text"]) or any(
            f.severity == "critical" for f in vision.findings(box["text"])
        ):
            return "arithmetic"
        return None
    if not set(_NUMBER_RE.findall(box["text"])) <= carried:
        return "numbers"
    return None


def _sources(response: object) -> list[Source]:
    """The pages a search call returned, from its grounding metadata, the
    most trusted first — see _TIERS. Empty when the call did not search.
    Never raises."""
    try:
        meta = response.candidates[0].grounding_metadata
    except Exception:
        return []
    found: list[tuple[int, Source]] = []
    sites: set[str] = set()
    for chunk in (getattr(meta, "grounding_chunks", None) or []) if meta else []:
        web = getattr(chunk, "web", None)
        uri = getattr(web, "uri", None) if web else None
        if not uri:
            continue
        title = getattr(web, "title", None) or getattr(web, "domain", None) or uri
        # The link is Google's redirect and says nothing about where it
        # leads; the site is named by the chunk itself, and on the Gemini API
        # its title is that name. One link a site: a second page of it is
        # printed under the same name and reads as the first one twice.
        site = str(getattr(web, "domain", None) or title).strip().lower().removeprefix("www.")
        if site in sites or not_a_source(site):
            continue
        sites.add(site)
        found.append((_tier(site), Source(title=title, uri=uri)))
    # sorted() is stable: within a tier the search's own order stands.
    return [source for _, source in sorted(found, key=lambda pair: pair[0])][:_MAX_SOURCES]


def _search_queries(response: object) -> int:
    """How many Google searches a call ran, which is what a Gemini 3 model is
    billed for. The grounding metadata lists them; a call that returned pages
    and listed no query still searched once. Never raises."""
    try:
        meta = response.candidates[0].grounding_metadata
    except Exception:
        return 0
    if not meta:
        return 0
    queries = len(getattr(meta, "web_search_queries", None) or [])
    return queries or (1 if _sources(response) else 0)


def _stats(
    kind: str, response: object | None, started: float, exc: Exception | None = None
) -> CallStats:
    model = settings.EXPLAIN_MODEL
    latency_ms = int((time.monotonic() - started) * 1000)
    if response is None:
        return CallStats(
            kind=kind, model=model, tokens_in=None, tokens_out=None,
            tokens_thought=None, cost_usd=None, latency_ms=latency_ms,
            success=False, error=vision._short_error(exc) if exc else "no response",
        )
    tokens_in, tokens_out, tokens_thought = vision._usage(response)
    cost = vision._cost_usd(model, tokens_in, tokens_out, tokens_thought)
    # A search is billed per query it ran, on top of the tokens, and the
    # daily cap has to see it.
    if cost is not None:
        cost += GROUNDING_USD_PER_QUERY * _search_queries(response)
    answered = bool(vision._response_text(response).strip())
    return CallStats(
        kind=kind, model=model, tokens_in=tokens_in, tokens_out=tokens_out,
        tokens_thought=tokens_thought, cost_usd=cost, latency_ms=latency_ms,
        success=answered, error=None if answered else "empty model response",
    )


async def _write(text: str) -> tuple[object | None, CallStats, bool]:
    """The first call: the explanations and the summary, as strict JSON, with
    no tool — the model does not search in a call like this one anyway."""
    started = time.monotonic()
    try:
        async with vision._API_SLOTS:
            response = await asyncio.wait_for(
                vision._client.aio.models.generate_content(
                    model=settings.EXPLAIN_MODEL,
                    contents=[EXPLAIN_PROMPT, text],
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
        retryable = vision._should_retry(exc) and not isinstance(exc, TimeoutError)
        return None, _stats("explain", None, started, exc), retryable
    return response, _stats("explain", response, started), False


async def _search(item: dict) -> tuple[list[Source], list[CallStats]]:
    """One explanation searched for: the sources its call returned, and every
    call it took.

    At a low thinking level the model sometimes answers without running a
    search at all, and the explanation is then dropped for having no source —
    three of six in record 47, none at the model's own default in any call
    measured. So a search that answered and found nothing is made once more
    at the default. The cheap call is the usual one; the dear one only where
    the cheap one did not look. A call that failed is not asked again: a
    timeout would only double the wait, and an error is not a search the
    model chose to skip.
    """
    sources, stats = await _search_once(item, settings.SOURCE_THINKING_LEVEL)
    if sources or not stats.success or settings.SOURCE_THINKING_LEVEL == "unset":
        return sources, [stats]
    again, second = await _search_once(item, "unset")
    return again, [stats, second]


async def _search_once(item: dict, thinking: str) -> tuple[list[Source], CallStats]:
    started = time.monotonic()
    try:
        async with vision._API_SLOTS:
            response = await asyncio.wait_for(
                vision._client.aio.models.generate_content(
                    model=settings.EXPLAIN_MODEL,
                    contents=[f"{SOURCE_PROMPT}\n{item['title']}: {item['text']}"],
                    config=types.GenerateContentConfig(
                        temperature=1.0,
                        max_output_tokens=vision.MAX_OUTPUT_TOKENS,
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        thinking_config=vision.thinking_config(thinking),
                        automatic_function_calling=vision.NO_AFC,
                    ),
                ),
                timeout=_SOURCE_TIMEOUT_S,
            )
    except Exception as exc:
        return [], _stats("source", None, started, exc)
    return _sources(response), _stats("source", response, started)


async def explain(markdown: str) -> Explaining:
    """Explain a trusted record and sum it up. Never touches the database."""
    if not settings.EXPLAIN_ENABLED:
        return Explaining()

    # The record as the reader will see it numbered, so "(3)" in an answer
    # is the "(3)" on the page.
    text = pdf.numbered_for_reading(markdown)
    all_stats: list[CallStats] = []
    response = None
    for attempt in range(_ATTEMPTS):
        response, stats, retryable = await _write(text)
        all_stats.append(stats)  # rule 4: a call that failed was still a call
        if response is not None:
            break
        last = attempt == _ATTEMPTS - 1
        logger.warning(
            "explain attempt %d/%d failed, %s: %s",
            attempt + 1,
            _ATTEMPTS,
            "retrying" if retryable and not last else "no retry",
            stats.error,
        )
        if last or not retryable:
            break
        await asyncio.sleep(_RETRY_PAUSE_S)

    if response is None:
        return Explaining(refused="call failed", stats=all_stats)

    answer = vision._response_text(response)
    parsed = parse(answer)
    if parsed is None:
        logger.warning("explain: the answer did not parse as the JSON asked for")
        return Explaining(refused="unparseable", stats=all_stats)

    items, summary = parsed
    items = items[:_MAX_EXPLANATIONS]
    # Before the searches, so a dropped explanation costs none.
    fair = [item for item in items if not judges_the_record(item["title"], item["text"])]
    judged = len(items) - len(fair)
    items = fair
    searched = await asyncio.gather(*(_search(item) for item in items))
    explanations: list[Explanation] = []
    unsourced = 0
    for item, (sources, stats) in zip(items, searched):
        all_stats.extend(stats)
        if not sources:
            unsourced += 1
            continue
        explanations.append(
            Explanation(item["anchor"], item["title"], item["text"], sources)
        )

    summary_refused = False
    carried = set(_NUMBER_RE.findall(markdown))
    if summary is not None:
        stated = set(_NUMBER_RE.findall(summary))
        if not stated <= carried:
            summary_refused = True
            summary = None

    elements: list[Element] = []
    elements_dropped = 0
    for box in elements_of(answer)[:_MAX_ELEMENTS]:
        refused = _element_refused(box, carried)
        if refused:
            elements_dropped += 1
            logger.info("explain: a teacher's %s dropped, %s", box["kind"], refused)
            continue
        elements.append(Element(**box))

    logger.info(
        "explain: %d explanations kept, %d without a source dropped, "
        "%d judging the record dropped, %d teacher's boxes kept, %d dropped, "
        "summary %s, model %s",
        len(explanations),
        unsourced,
        judged,
        len(elements),
        elements_dropped,
        "refused" if summary_refused else ("kept" if summary else "absent"),
        settings.EXPLAIN_MODEL,
    )
    return Explaining(
        explanations=explanations,
        summary=summary,
        unsourced=unsourced,
        judged=judged,
        summary_refused=summary_refused,
        elements=elements,
        elements_dropped=elements_dropped,
        stats=all_stats,
    )
