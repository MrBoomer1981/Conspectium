"""Stage three: hard places explained, and the record summed up.

The group's reader was not at the lecture, and the record is exactly what the
author wrote — steps skipped, notation never introduced, the lecturer's
context left unsaid. This stage adds what a classmate who was there would
add. Everything it writes is the bot's own and is printed as the bot's, in a
box of its own tone: adding is not forbidden, adding unmarked is.

It runs over the text the runs agreed on and the composer marked up, and like
the composer it never sees the photograph — the worst failure this project
has reproduced needs an image to invent from. What it may add is held by two
guards, both in code:

- An explanation carries the sources Google Search gave for it, attributed
  from the answer's own grounding metadata rather than from anything the
  model wrote about its sources. One with no source behind it is not printed
  — the reader cannot check a claim, so the page has to say where it is from.
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
import re
import time
from dataclasses import dataclass, field

from google.genai import types

from app.core.config import GROUNDING_USD_PER_CALL, settings
from app.services import pdf, vision
from app.services.vision import CallStats

logger = logging.getLogger(__name__)

EXPLAIN_PROMPT = vision.load_prompt(settings.EXPLAIN_PROMPT_FILE)
EXPLAIN_PROMPT_WORDS = len(EXPLAIN_PROMPT.split())

# The prompt asks for one or two a section and eight at most; this is where
# "at most" is kept.
_MAX_EXPLANATIONS = 8
# Three links under an explanation say where it is from; more is a list.
_MAX_SOURCES = 3
# A grounding segment shorter than this matches too much to attribute by.
_MIN_SEGMENT_CHARS = 12
# The composer's retry policy, for the composer's reasons: a call over the
# whole record, where a timeout means it was working and a second wait buys
# the same answer.
_ATTEMPTS = 2
_RETRY_PAUSE_S = 2

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")
_PLAIN_RE = re.compile(r"[\s\\$\"'«»{}]+")


@dataclass
class Source:
    title: str
    uri: str


@dataclass
class Explanation:
    anchor: str
    title: str
    text: str
    sources: list[Source] = field(default_factory=list)


@dataclass
class Explaining:
    """What the caller stores, whether or not the stage ran."""

    explanations: list[Explanation] = field(default_factory=list)
    summary: str | None = None
    # Why nothing, or less than asked, came back: None when the stage ran
    # and its answer was read.
    refused: str | None = None
    # Explanations written with no source behind them, and so not printed.
    unsourced: int = 0
    # A summary thrown away for stating a number the record does not carry.
    summary_refused: bool = False
    stats: list[CallStats] = field(default_factory=list)


def parse(text: str) -> tuple[list[dict], str | None] | None:
    """The answer's explanations and summary, or None when it is not the JSON
    asked for. Never raises — rule 7, the same as recognition's answers.

    The answer comes without response_mime_type, which cannot be combined with
    the search tool, so a fence or a sentence round the JSON is tolerated and
    the outermost braces are what is read.
    """
    stripped = _FENCE_RE.sub("", text.strip())
    start, end = stripped.find("{"), stripped.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(stripped[start : end + 1])
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
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


def _plain(text: str) -> str:
    """Text reduced to what survives JSON escaping and LaTeX's backslashes, so
    a grounding segment of the raw answer can be found in a parsed field."""
    return _PLAIN_RE.sub("", text).lower()


def _grounding(response: object) -> tuple[list[Source], list[tuple[str, list[int]]]]:
    """The sources the search returned, and which stretch of the answer each
    one supports. Empty when the call was not grounded. Never raises."""
    try:
        meta = response.candidates[0].grounding_metadata
    except Exception:
        return [], []
    if meta is None:
        return [], []
    sources: list[Source] = []
    for chunk in getattr(meta, "grounding_chunks", None) or []:
        web = getattr(chunk, "web", None)
        uri = getattr(web, "uri", None) if web else None
        title = (getattr(web, "title", None) or getattr(web, "domain", None) or "") if web else ""
        sources.append(Source(title=title or (uri or ""), uri=uri or ""))
    supports: list[tuple[str, list[int]]] = []
    for support in getattr(meta, "grounding_supports", None) or []:
        segment = getattr(support, "segment", None)
        text = getattr(segment, "text", None) if segment else None
        indices = list(getattr(support, "grounding_chunk_indices", None) or [])
        if text and indices:
            supports.append((text, indices))
    return sources, supports


def _attribute(
    item: dict, sources: list[Source], supports: list[tuple[str, list[int]]]
) -> list[Source]:
    """The sources behind one explanation: those of every grounding support
    whose segment of the answer lies inside this explanation's text."""
    body = _plain(item["text"])
    found: list[Source] = []
    for segment, indices in supports:
        plain = _plain(segment)
        if len(plain) < _MIN_SEGMENT_CHARS or plain not in body:
            continue
        for index in indices:
            if 0 <= index < len(sources) and sources[index].uri:
                source = sources[index]
                if all(source.uri != kept.uri for kept in found):
                    found.append(source)
    return found[:_MAX_SOURCES]


def _grounded(response: object) -> bool:
    try:
        meta = response.candidates[0].grounding_metadata
    except Exception:
        return False
    return bool(meta and (getattr(meta, "web_search_queries", None) or getattr(meta, "grounding_chunks", None)))


async def _one_call(text: str) -> tuple[object | None, CallStats, bool]:
    """One call, and whether the failure that ended it is worth another."""
    started = time.monotonic()
    model = settings.EXPLAIN_MODEL
    try:
        async with vision._API_SLOTS:
            response = await asyncio.wait_for(
                vision._client.aio.models.generate_content(
                    model=model,
                    contents=[EXPLAIN_PROMPT, text],
                    config=types.GenerateContentConfig(
                        temperature=1.0,
                        max_output_tokens=vision.MAX_OUTPUT_TOKENS,
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                ),
                timeout=settings.EXPLAIN_CALL_TIMEOUT_S,
            )
    except Exception as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        retryable = vision._should_retry(exc) and not isinstance(exc, TimeoutError)
        return None, CallStats(
            kind="explain",
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
    cost = vision._cost_usd(model, tokens_in, tokens_out, tokens_thought)
    # The search is billed per grounded call on top of the tokens, and the
    # daily cap has to see it.
    if cost is not None and _grounded(response):
        cost += GROUNDING_USD_PER_CALL
    answered = bool(vision._response_text(response).strip())
    return response, CallStats(
        kind="explain",
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tokens_thought=tokens_thought,
        cost_usd=cost,
        latency_ms=int((time.monotonic() - started) * 1000),
        success=answered,
        error=None if answered else "empty model response",
    ), False


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
        response, stats, retryable = await _one_call(text)
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

    parsed = parse(vision._response_text(response))
    if parsed is None:
        logger.warning("explain: the answer did not parse as the JSON asked for")
        return Explaining(refused="unparseable", stats=all_stats)

    items, summary = parsed
    sources, supports = _grounding(response)
    explanations: list[Explanation] = []
    unsourced = 0
    for item in items[:_MAX_EXPLANATIONS]:
        backed = _attribute(item, sources, supports)
        if not backed:
            unsourced += 1
            continue
        explanations.append(Explanation(item["anchor"], item["title"], item["text"], backed))

    summary_refused = False
    if summary is not None:
        stated = set(_NUMBER_RE.findall(summary))
        carried = set(_NUMBER_RE.findall(markdown))
        if not stated <= carried:
            summary_refused = True
            summary = None

    logger.info(
        "explain: %d explanations kept, %d without a source dropped, "
        "summary %s, %d sources, model %s",
        len(explanations),
        unsourced,
        "refused" if summary_refused else ("kept" if summary else "absent"),
        len(sources),
        settings.EXPLAIN_MODEL,
    )
    return Explaining(
        explanations=explanations,
        summary=summary,
        unsourced=unsourced,
        summary_refused=summary_refused,
        stats=all_stats,
    )
