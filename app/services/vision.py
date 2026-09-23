"""Gemini recognition: prompt, model call, response parsing, spend logging.

`_one_attempt` is a single call; `transcribe` retries it up to three times on a
transient failure; `transcribe_consensus` runs VISION_RUNS of those in parallel
and compares them. Nothing here touches the database except log_ai_calls, which
uses its own session on purpose — see CLAUDE.md -> Sessions and transactions.
"""

from __future__ import annotations

import asyncio
import difflib
import itertools
import json
import logging
import re
import time
from dataclasses import dataclass, replace
from pathlib import Path

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.core.config import PRICE_PER_MTOK, settings
from app.db.models import AiCall
from app.db.session import async_session_maker
from app.services import consensus

logger = logging.getLogger(__name__)

def load_prompt(name: str) -> str:
    """One prompt file from the repo root, verbatim. A bare file name, not a
    path: the file ships with the deploy. A missing one raises here, at import,
    so the process dies on the deploy rather than on somebody's first photo."""
    return (
        (Path(__file__).resolve().parents[2] / name).read_text(encoding="utf-8").strip()
    )


# Which file is PROMPT_FILE, so a variant can be tried on the deployed bot and
# rolled back by changing one variable. A short prompt beats a long one — see
# CLAUDE.md before making one longer, and measure what it costs.
TRANSCRIBE_PROMPT = load_prompt(settings.PROMPT_FILE)
PROMPT_WORDS = len(TRANSCRIBE_PROMPT.split())

# One client per process, not one per call.
_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# An album fans VISION_RUNS calls out per page — 30 at once for ten pages, up
# to 90 with retries. Gemini answers a burst that size with 429s. One
# process-wide semaphore around the API call, not a queue. The count is a
# module constant because albums.py derives its own ceiling from it.
API_SLOTS = 10
_API_SLOTS = asyncio.Semaphore(API_SLOTS)

# One model call. 30 s fits a model that answers in ~6 s; a thinking or
# otherwise slower one needs more, and it is the only one of the three
# timeouts that is a setting — raising it alone would leave the two ceilings
# below cutting the retries short, so they are computed from it.
_CALL_TIMEOUT_S = settings.VISION_CALL_TIMEOUT_S
# transcribe(): three attempts, so two pauses; the loop stops at the first
# success or the first non-retryable failure.
_RETRY_PAUSES_S = (1, 2)
# One run's worst case: every attempt timing out, plus the pauses between them.
RUN_WORST_CASE_S = (
    (len(_RETRY_PAUSES_S) + 1) * _CALL_TIMEOUT_S + sum(_RETRY_PAUSES_S)
)
# Enough over that worst case to absorb scheduling and the wait for a
# semaphore slot. 1.3 is the ratio the hand-written 120 s held to 93 s, so the
# default reproduces the old number exactly; albums.py applies the same margin.
TIMEOUT_MARGIN = 1.3
# transcribe_consensus(): guards a run that hangs past its own retries.
_CONSENSUS_TIMEOUT_S = int(RUN_WORST_CASE_S * TIMEOUT_MARGIN)


@dataclass
class Uncertain:
    text: str
    where: str
    why: str
    alternatives: list[str]


@dataclass
class Transcription:
    title: str
    subject: str | None
    markdown: str
    margin_notes: list[str]
    uncertain: list[Uncertain]
    numeric_tokens: list[str]
    unreadable_count: int


@dataclass
class CallStats:
    """One model call, in the shape of the row it becomes.

    kind and model are carried rather than read from settings at write time:
    a second stage calling a different model would otherwise be billed and
    recorded as the first one, and rule 4 would break without anything
    failing."""

    kind: str
    model: str
    tokens_in: int | None
    tokens_out: int | None
    # The answer and the thinking are two numbers because they were one for a
    # week and the one hid a truncation. Both come out of max_output_tokens
    # and both are billed at the output rate.
    tokens_thought: int | None
    cost_usd: float | None
    latency_ms: int
    success: bool
    error: str | None


@dataclass
class TranscriptionResult:
    """Outcome of settings.VISION_RUNS runs compared against each other.
    Not frozen: task 7 may downgrade `verdict` after the arithmetic check."""

    best: Transcription
    text_agreement: float  # 0..1
    # The two agreements answer different questions and neither stands in for
    # the other: text_agreement compares the markdown, so it moves when a
    # prompt changes how a page is laid out; this one compares the numbers,
    # and a number has no layout. Stored rather than logged only, because
    # comparing two prompts should be a query and Railway's logs roll off.
    numeric_agreement: float  # 0..1
    numeric_divergences: list  # consensus.Divergence objects
    verdict: str  # "clean" | "needs_review" | "rejected"


# ── Parsing ──────────────────────────────────────────────────────────────────
# parse_response never raises. A wrong type on any field falls back to a
# default; only a missing or non-string `markdown` discards the whole record.
# The full table is in PLAN.md -> Contracts.

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)


def _load_json(raw: str) -> object | None:
    """json.loads, tolerating a ```json ... ``` fence even though
    response_mime_type=application/json should already have stripped it."""
    text = raw.strip()
    fenced = _FENCE_RE.match(text)
    if fenced:
        text = fenced.group(1)
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def _first_nonempty_line(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _title(value: object, markdown: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()[:60]
    fallback = _first_nonempty_line(markdown)
    return fallback[:60] if fallback else "Untitled"


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _int_or_zero(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0


def _uncertain_list(value: object) -> list[Uncertain]:
    if not isinstance(value, list):
        return []
    out: list[Uncertain] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue  # `text` is the only required key; without it, drop the entry
        out.append(
            Uncertain(
                text=text,
                where=item["where"] if isinstance(item.get("where"), str) else "",
                why=item["why"] if isinstance(item.get("why"), str) else "",
                alternatives=_str_list(item.get("alternatives")),
            )
        )
    return out


def parse_response(raw: str) -> Transcription | None:
    """Turn the model's reply into a Transcription, or None if it can't be
    trusted (not JSON, not an object, or no usable `markdown`). Never raises."""
    data = _load_json(raw)
    if not isinstance(data, dict):
        return None
    markdown = data.get("markdown")
    if not isinstance(markdown, str):
        return None
    subject = data.get("subject")
    return Transcription(
        title=_title(data.get("title"), markdown),
        subject=subject if isinstance(subject, str) else None,
        markdown=markdown,
        margin_notes=_str_list(data.get("margin_notes")),
        uncertain=_uncertain_list(data.get("uncertain")),
        numeric_tokens=_str_list(data.get("numeric_tokens")),
        unreadable_count=_int_or_zero(data.get("unreadable_count")),
    )


# ── Model call ───────────────────────────────────────────────────────────────


def _usage(response: object) -> tuple[int | None, int | None, int | None]:
    """Prompt, answer, thinking — three numbers, because the second one alone
    hid a truncation for a week. `candidates_token_count` is the visible
    answer; a thinking model spends `thoughts_token_count` out of the same
    `max_output_tokens`, so a call can stop at the ceiling while the column we
    stored said 498. Both halves are recorded now."""
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return None, None, None
    return (
        getattr(meta, "prompt_token_count", None),
        getattr(meta, "candidates_token_count", None),
        getattr(meta, "thoughts_token_count", None),
    )


def _cost_usd(
    model: str,
    tokens_in: int | None,
    tokens_out: int | None,
    tokens_thought: int | None = None,
) -> float | None:
    """None unless the model is priced and both token counts are known — we
    don't invent numbers.

    Thinking is billed at the output rate, so it belongs in the sum. Left out,
    a call that thinks fifteen times as long as it speaks is recorded at a
    fifteenth of its price, and `DAILY_COST_LIMIT_USD` stops being a limit
    without anything failing. A missing count is read as zero rather than as
    unknown: it is absent exactly when the model did not think.
    """
    price = PRICE_PER_MTOK.get(model)
    if price is None or tokens_in is None or tokens_out is None:
        return None
    price_in, price_out = price
    billed_out = tokens_out + (tokens_thought or 0)
    return (tokens_in * price_in + billed_out * price_out) / 1_000_000


def _response_text(response: object) -> str:
    try:
        return response.text or ""
    except Exception:  # a blocked or part-less response raises on .text
        return ""


def _finish_reason(response: object) -> str | None:
    """Why the model stopped, straight from the response.

    MAX_TOKENS is the one that matters: it means the answer was cut off at our
    own max_output_tokens, so the JSON ends mid-string and cannot parse. That
    is a fact the response carries — not something to infer from a token count
    sitting near the ceiling. Defensive like _usage: a response with no
    candidates must not turn a parse failure into a crash.
    """
    try:
        reason = response.candidates[0].finish_reason
    except Exception:
        return None
    if not reason:
        return None
    # .name because it is an enum, and str() on one prints
    # "FinishReason.MAX_TOKENS" into a column that is read by eye.
    return getattr(reason, "name", None) or str(reason)


# How many keys of the answer are named. Enough to tell an envelope from a
# stranger; not a dump of the object.
_SHAPE_KEYS = 8
# A parse failure earns another draw, with two exceptions. SAFETY is a refusal
# and repeats. MAX_TOKENS is our own ceiling: the second call hits the same
# wall, having spent the same tokens walking into it.
_FINISH_NOT_WORTH_REPEATING = frozenset({"SAFETY", "MAX_TOKENS", "RECITATION"})


def _answer_shape(raw: str) -> str:
    """What came back, said without saying what was on the page.

    "Not JSON at all" and "JSON without a markdown field" are two different
    failures with two different fixes, and the error column said the same
    sentence for both. Keys are structure and diagnose it; the values are a
    student's lecture notes and have no business in a log.
    """
    if not raw.strip():
        return "empty answer"
    data = _load_json(raw)
    if data is None:
        return "not json"
    if not isinstance(data, dict):
        return f"json {type(data).__name__}"
    if not data:
        return "json object with no keys"
    return "json keys: " + ",".join(sorted(str(k) for k in data)[:_SHAPE_KEYS])


def _worth_asking_again(response: object) -> bool:
    """Is a 200 that would not parse worth one more call?

    It used to never be, and that was reasoned from a cost this pipeline no
    longer has: "an extra call costs money, an extra rejection costs one tap of
    try again". Since "a record is all its pages or none", a lost run costs a
    page and a lost page costs the album. On 2026-09-23 one album spent four of
    its fifteen runs on unparseable answers, one page lost all three, and the
    five-page record was never made — while eleven calls in the same minute
    parsed fine. At temperature 1.0 the next call is an independent draw.
    """
    return _finish_reason(response) not in _FINISH_NOT_WORTH_REPEATING


def _unparseable(response: object) -> str:
    """The error for a 200 whose body would not parse.

    Naming why the model stopped is the whole difference between "it came back
    wrong" and an answer: MAX_TOKENS is our ceiling, STOP is the model
    returning something that is not JSON, SAFETY is a refusal. The shape says
    what arrived instead of the record.
    """
    reason = _finish_reason(response)
    said = ([f"finish_reason={reason}"] if reason else []) + [
        _answer_shape(_response_text(response))
    ]
    return f"unparseable model response ({', '.join(said)})"[:500]


def _short_error(exc: BaseException) -> str:
    text = str(exc)
    # A bare TimeoutError() from wait_for stringifies to "", which would leave
    # a trailing ": " in the ai_calls.error column.
    return (f"{type(exc).__name__}: {text}" if text else type(exc).__name__)[:500]


def _should_retry(exc: BaseException) -> bool:
    """The full classification from PLAN.md task 10. When it is unclear whether
    a failure is transport-level or logical, do not retry — an extra call costs
    money, an extra rejection costs one tap of "try again"."""
    if isinstance(exc, TimeoutError):  # asyncio.TimeoutError is this since 3.11
        return True
    if isinstance(exc, httpx.TransportError):  # dropped, reset, DNS, read/write
        return True
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            return code in (408, 429) or code >= 500  # 4xx (400/401/403/404): no
        return True  # an SDK error with no usable HTTP code is transport-ish
    return False


_MEDIA_RESOLUTION = {
    "low": types.MediaResolution.MEDIA_RESOLUTION_LOW,
    "medium": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
    "high": types.MediaResolution.MEDIA_RESOLUTION_HIGH,
}
_THINKING_LEVEL = {
    "minimal": types.ThinkingLevel.MINIMAL,
    "low": types.ThinkingLevel.LOW,
    "medium": types.ThinkingLevel.MEDIUM,
    "high": types.ThinkingLevel.HIGH,
}

# A cap, not a reservation: tokens are billed as produced, so a ceiling nobody
# reaches costs nothing. A ceiling that is reached still costs a whole run: a
# 200 whose JSON stopped mid-string is the one parse failure not worth asking
# again, because the second call walks into the same wall.
#
# 8192 was reached. `finish_reason=MAX_TOKENS` arrived on a call whose visible
# answer was 498 tokens and whose latency was 37 s: the budget went on
# *thinking*, which draws on the same allowance and is counted apart from the
# answer. Visible answers here run 289-1457 tokens, so what this number really
# sizes is how long the model may think.
MAX_OUTPUT_TOKENS = 32768


def _generation_config() -> types.GenerateContentConfig:
    """How the model is asked, as opposed to what it is asked.

    Both new fields default to absent, which is Gemini's own default and
    bit-for-bit what this call did before the settings existed. Neither has
    been measured; they are here so that they can be, one at a time, against
    the same album.

    temperature stays at 1.0 and no seed is sent, deliberately. Three runs
    that agree because they were made identical would drive text_agreement up
    without touching accuracy, and agreement between independent runs is the
    only uncertainty signal that has ever worked here.
    """
    thinking = _THINKING_LEVEL.get(settings.VISION_THINKING_LEVEL)
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=1.0,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        media_resolution=_MEDIA_RESOLUTION.get(settings.VISION_MEDIA_RESOLUTION),
        thinking_config=(
            types.ThinkingConfig(thinking_level=thinking) if thinking else None
        ),
    )


async def _one_attempt(
    image_bytes: bytes,
    model: str,
) -> tuple[Transcription | None, CallStats, bool]:
    """A single Gemini call plus the parsing that follows it. The third element
    says whether a retry is worth it: a transient exception, or a 200 whose
    body would not parse and whose finish reason leaves room for a different
    answer — see _worth_asking_again for why that stopped being "never".

    The model is a parameter, not a read of settings: the row this produces
    has to name the model that was actually called."""
    started = time.monotonic()
    try:
        async with _API_SLOTS:
            response = await asyncio.wait_for(
                _client.aio.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes, mime_type="image/jpeg"
                        ),
                        TRANSCRIBE_PROMPT,
                    ],
                    config=_generation_config(),
                ),
                timeout=_CALL_TIMEOUT_S,
            )
    except Exception as exc:
        # No response → no tokens billed → no cost to record. The failure is
        # logged by transcribe(), the only caller that knows whether a
        # retryable one is actually going to be retried.
        latency_ms = int((time.monotonic() - started) * 1000)
        stats = CallStats(
            kind="transcribe",
            model=model,
            tokens_in=None,
            tokens_out=None,
            tokens_thought=None,
            cost_usd=None,
            latency_ms=latency_ms,
            success=False,
            error=_short_error(exc),
        )
        return None, stats, _should_retry(exc)

    tokens_in, tokens_out, tokens_thought = _usage(response)
    result = parse_response(_response_text(response))
    latency_ms = int((time.monotonic() - started) * 1000)

    # The model answered, so the tokens were spent whether or not we could read
    # the answer — cost is recorded either way (PLAN.md -> Contracts).
    stats = CallStats(
        kind="transcribe",
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tokens_thought=tokens_thought,
        cost_usd=_cost_usd(model, tokens_in, tokens_out, tokens_thought),
        latency_ms=latency_ms,
        success=result is not None,
        error=None if result is not None else _unparseable(response),
    )
    return result, stats, result is None and _worth_asking_again(response)


async def transcribe(
    image_bytes: bytes,
    model: str,
) -> tuple[Transcription | None, list[CallStats]]:
    """Up to three attempts with 1 s then 2 s pauses, stopping at the first
    success or the first non-retryable failure. Never touches the database.
    Every attempt is recorded in the returned list, which is always non-empty."""
    all_stats: list[CallStats] = []
    last = len(_RETRY_PAUSES_S)
    for attempt in range(last + 1):
        result, stats, retryable = await _one_attempt(image_bytes, model)
        all_stats.append(stats)
        if result is not None:
            return result, all_stats
        # stats.error, not the exception: str(TimeoutError()) is "", and a
        # timeout used to reach the log as a line ending in a bare colon. The
        # column had it right; the log had fallen behind.
        logger.warning(
            "Gemini attempt %d/%d failed, %s: %s",
            attempt + 1,
            last + 1,
            "retrying" if retryable and attempt < last else "no retry left",
            stats.error,
        )
        if not retryable or attempt == last:
            return None, all_stats
        await asyncio.sleep(_RETRY_PAUSES_S[attempt])
    return None, all_stats  # unreachable; keeps the type checker happy


def total_cost(stats: list[CallStats]) -> float | None:
    """Sum of the known cost_usd values, or None when every one is unknown —
    for the note_processed event (PLAN.md -> Contracts -> cost_usd)."""
    known = [s.cost_usd for s in stats if s.cost_usd is not None]
    return sum(known) if known else None


def _is_value(variant: str) -> bool:
    """True for a variant that is an actual number. consensus renders values
    with `%.10g`, so the only non-numeric key a Divergence can carry is its
    "missing" bucket — matching on the number, not on that Russian string,
    keeps this independent of the ready-made module's wording."""
    try:
        float(variant)
    except ValueError:
        return False
    return True


def meaningful_divergences(divergences: list) -> list:
    """Keep only the positions where runs read genuinely different numbers.

    `consensus.extract_numbers` collects every numeric literal on the page,
    list markers and subscripts included, and aligns the runs by position. Most
    of what comes back is therefore an alignment artefact: one run emitted a
    number where another emitted nothing, which says nothing about how the page
    was read. Reported upstream as a defect in the ready-made module; filtered
    here because that module is not ours to change.

    A position earns a line in the reply only when at least two runs put
    *different values* on it, one of those readings is what most runs saw, and
    the same line has not already been printed.

    The majority rule is the second half of the same argument. Where no value
    has more runs behind it than the gap does — "6 (1 of 3) or 2 (1 of 3) or
    missing (1 of 3)" — the three runs did not disagree about a number, they
    produced different counts of numbers, and the position they were aligned
    on is not the same position. There is nothing to report and nothing to
    check.
    """
    kept: list = []
    seen: set[tuple[str, tuple[tuple[str, int], ...]]] = set()
    for divergence in divergences:
        values = {k for k in divergence.variants if _is_value(k)}
        if len(values) < 2:
            continue
        has_gap = len(values) < len(divergence.variants)
        if has_gap and max(divergence.variants.values()) < 2:
            continue
        # Two cells of a matrix read "6 against 2" produce two identical lines.
        # The position is in the data but never in the message, so the second
        # line says nothing the first did not.
        key = (divergence.context, tuple(sorted(divergence.variants.items())))
        if key in seen:
            continue
        seen.add(key)
        kept.append(divergence)
    return kept


def meaningful_uncertain(uncertain: list[Uncertain]) -> list[Uncertain]:
    """Keep only the spots that are actually ambiguous.

    The prompt asks for places where a symbol "действительно читается двояко",
    and the model answers with the state of the paper instead: a word cropped
    by the edge, a smudge, an abbreviation, something written in the margin.
    Seven such entries came back on one album and not one of them named a
    second reading.

    `alternatives` is the test, and it is the prompt's own: an entry that
    cannot say what else the symbol might be is not an ambiguity. An entry
    whose text already carries `[неразборчиво]` is not one either — that mark
    stands in the record itself, in place, and a list repeating it adds a line
    without adding a fact.
    """
    return [
        u
        for u in uncertain
        if any(a.strip() for a in u.alternatives) and "[неразборчиво]" not in u.text
    ]


def numeric_agreement(runs: list[list[str]]) -> float:
    """Mean pairwise similarity of the runs' numeric_tokens sequences.

    text_agreement compares the markdown, so it moves when a prompt changes
    how the page is laid out rather than how it was read — the confound that
    made the v5 measurement unreadable, and the one that would make a
    two-stage run incomparable with a one-stage one. A number has no layout.

    autojunk off, and it is not a detail: past 200 elements difflib treats
    anything common as noise, and a page of matrices is four hundred numbers
    drawn from a handful of digits. On such a page four changes out of four
    hundred read as 0.04 with the heuristic on and 0.59 with it off.

    That 0.59 is worth knowing about too. A repetitive sequence has many
    equally good alignments, so the absolute value runs low on exactly the
    pages this was meant for. Compare it across arms of one experiment, never
    against a threshold.
    """
    pairs = list(itertools.combinations(runs, 2))
    if not pairs:
        return 1.0  # one run agrees with itself; the caller guarantees two
    ratios = (
        difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
        for a, b in pairs
    )
    return sum(ratios) / len(pairs)


# How many numbers a page must carry before their agreement counts as
# evidence. Measured over the corpus on 2026-09-23: the median page carries
# 7.5 and the thinnest albums about 5.7, so five keeps an ordinary page
# eligible. Below that the agreement is cheap — two runs that both write
# "1905" have said little — and above it, three independent runs producing the
# same numbers in the same order is not something invention does.
_VOUCH_MIN_NUMBERS = 5


def numbers_vouch(markdowns: list[str], reported: list) -> bool:
    """Did the runs read the same page, whatever they did with its layout?

    `reported` is `consensus.compare`'s unfiltered list, so an empty one means
    the numeric sequences of every run aligned with no difference at all — not
    even a number against a gap. The count is taken from the markdown rather
    than from the model's own `numeric_tokens`, for the reason this project
    distrusts every self-report: one is computed from the text that will be
    stored, the other is a field the model fills in about itself.
    """
    if reported:
        return False
    return min(len(consensus.extract_numbers(m)) for m in markdowns) >= (
        _VOUCH_MIN_NUMBERS
    )


def _verdict(text_agreement: float, numbers_vouched: bool) -> str:
    """Non-overlapping bands from PLAN.md task 6, with one way out of the
    bottom one.

    The bands are `text_agreement`, which compares the markdown and therefore
    measures how a page was laid out rather than how it was read. That was
    sound while the prompt prescribed the layout; `prompts-v5.md` deliberately
    gives layout away to the composing stage, and the bands stayed where they
    were. On 2026-09-23 a five-page album lost two pages — and with them, under
    "all its pages or none", the other three — at `text_agreement` 0.428 and
    0.419 while their numbers agreed exactly and the frames were nineteen times
    over the sharpness threshold.

    So a page whose numbers vouch for it is never *rejected*: it is saved and
    flagged. It is not lifted to clean either, because the runs did disagree
    about something, and a reader should hear about it.
    """
    if text_agreement >= 0.90:
        return "clean"
    if text_agreement >= 0.70:
        return "needs_review"
    return "needs_review" if numbers_vouched else "rejected"


async def transcribe_consensus(
    image_bytes: bytes,
) -> tuple[TranscriptionResult | None, list[CallStats]]:
    """settings.VISION_RUNS independent transcribe() calls in parallel, then
    compared by code. Never touches the database: the returned list carries the
    stats of every run that finished. Fewer than two successful runs → first
    element None (the list is then empty only if the 120 s ceiling fired before
    any run returned).

    _CONSENSUS_TIMEOUT_S guards a run that hangs past its own retries. It is
    asyncio.wait, not wait_for: cancelling the whole gather would throw away the
    CallStats of runs that already finished, and those calls were still billed."""
    tasks = [
        asyncio.create_task(transcribe(image_bytes, settings.VISION_MODEL))
        for _ in range(settings.VISION_RUNS)
    ]
    try:
        done, pending = await asyncio.wait(tasks, timeout=_CONSENSUS_TIMEOUT_S)
        if pending:
            logger.warning(
                "consensus: %d/%d runs unfinished in %ds",
                len(pending),
                settings.VISION_RUNS,
                _CONSENSUS_TIMEOUT_S,
            )
    finally:
        # asyncio.wait leaves its tasks running. Cancel whatever is still going
        # — on the ceiling above, or when this coroutine is itself cancelled
        # (an album page dropped by process_batch). An orphaned run keeps
        # making paid calls with the result thrown away.
        leftover = [task for task in tasks if not task.done()]
        for task in leftover:
            task.cancel()
        if leftover:
            await asyncio.gather(*leftover, return_exceptions=True)

    all_stats: list[CallStats] = []
    ok_runs: list[Transcription] = []
    for task in done:
        try:
            transcription, stats = task.result()
        except Exception as exc:
            logger.warning("transcribe run crashed: %s", exc)
            all_stats.append(
                CallStats(
                    kind="transcribe",
                    model=settings.VISION_MODEL,
                    tokens_in=None,
                    tokens_out=None,
                    tokens_thought=None,
                    cost_usd=None,
                    latency_ms=0,
                    success=False,
                    error=_short_error(exc),
                )
            )
            continue
        all_stats.extend(stats)
        if transcription is not None:
            ok_runs.append(transcription)

    if len(ok_runs) < 2:
        return None, all_stats

    markdowns = [t.markdown for t in ok_runs]
    text_agreement = consensus.compare_text(markdowns).similarity
    # Filtered once, here, so the handler, the album assembly and the stored
    # record all see the same signal and none of them stores the noise.
    reported = consensus.compare(markdowns).divergences
    numeric_divergences = meaningful_divergences(reported)
    chosen = ok_runs[consensus.pick_representative(markdowns)]
    # Filtered in the same place and for the same reason as the divergences,
    # so the reply, the document and the stored record all see one signal.
    # A copy rather than an assignment: the runs belong to the comparison that
    # produced them, and nothing here needs to be the one place that edits one.
    best = replace(chosen, uncertain=meaningful_uncertain(chosen.uncertain))

    vouched = numbers_vouch(markdowns, reported)
    verdict = _verdict(text_agreement, vouched)
    if verdict == "clean" and numeric_divergences:
        # A kept divergence means at least two runs read one position as
        # different *numbers* — meaningful_divergences has already dropped the
        # alignment artefacts, which is what makes this safe to act on.
        #
        # It is worth a flag in a way that prose is not. A reader re-reading
        # the record will catch a sentence that makes no sense; a 6 that
        # should be an 8 in a matrix looks exactly as authoritative as the
        # right digit and stays in the corpus for ever. text_agreement cannot
        # see it either — a one-character difference barely moves it, so the
        # page comes back clean with the disagreement sitting in it.
        #
        # One way only, exactly like a critical mathcheck finding: this can
        # lower a clean verdict and can never lift a rejected one.
        verdict = "needs_review"
    # Built before the log line rather than after it, so the number printed and
    # the number stored are one value. Computed twice they could drift apart,
    # and the log is what anyone would check the column against.
    result = TranscriptionResult(
        best=best,
        text_agreement=text_agreement,
        numeric_agreement=numeric_agreement([t.numeric_tokens for t in ok_runs]),
        numeric_divergences=numeric_divergences,
        verdict=verdict,
    )
    logger.info(
        "consensus: %d/%d runs ok, text_agreement=%.3f, "
        "numeric_agreement=%.3f, verdict=%s%s, "
        "divergences %d of %d kept, uncertain %d of %d kept",
        len(ok_runs),
        settings.VISION_RUNS,
        result.text_agreement,
        result.numeric_agreement,
        result.verdict,
        # Only when it changed the outcome, so the line does not carry a word
        # about a rule that did not fire.
        " (numbers vouched)" if vouched and text_agreement < 0.70 else "",
        len(numeric_divergences),
        len(reported),
        len(best.uncertain),
        len(chosen.uncertain),
    )
    return result, all_stats


# ── Spend logging ────────────────────────────────────────────────────────────


async def log_ai_calls(user_id: int, stats: list[CallStats]) -> None:
    """Write one ai_calls row per attempt in a dedicated session, committed
    immediately. Takes no session on purpose: spend must survive a rollback of
    the main transaction (CLAUDE.md -> Sessions and transactions). Never raises."""
    try:
        async with async_session_maker() as session, session.begin():
            session.add_all(
                [
                    AiCall(
                        user_id=user_id,
                        # Both from the stats, not from settings: a second
                        # stage on another model has to be billed as itself.
                        kind=s.kind,
                        model=s.model,
                        tokens_in=s.tokens_in,
                        tokens_out=s.tokens_out,
                        tokens_thought=s.tokens_thought,
                        cost_usd=s.cost_usd,
                        latency_ms=s.latency_ms,
                        success=s.success,
                        error=s.error,
                    )
                    for s in stats
                ]
            )
    except Exception:
        logger.exception("log_ai_calls failed")
