"""Gemini recognition: prompt, model call, response parsing, spend logging.

`_one_attempt` is a single call; `transcribe` retries it up to three times on a
transient failure; `transcribe_consensus` runs VISION_RUNS of those in parallel
and compares them. Nothing here touches the database except log_ai_calls, which
uses its own session on purpose — see CLAUDE.md -> Sessions and transactions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
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

# The prompt is maintained in prompts-v3.md at the repo root and loaded verbatim.
# A short prompt beats a long one — see CLAUDE.md; do not lengthen it.
TRANSCRIBE_PROMPT = (
    (Path(__file__).resolve().parents[2] / "prompts-v3.md")
    .read_text(encoding="utf-8")
    .strip()
)

# One client per process, not one per call.
_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# An album fans VISION_RUNS calls out per page — 30 at once for ten pages, up
# to 90 with retries. Gemini answers a burst that size with 429s. One
# process-wide semaphore around the API call, not a queue.
_API_SLOTS = asyncio.Semaphore(10)

# One model call: typical response is ~6 s.
_CALL_TIMEOUT_S = 30
# transcribe(): three attempts, so two pauses; the loop stops at the first
# success or the first non-retryable failure.
_RETRY_PAUSES_S = (1, 2)
# transcribe_consensus(): must exceed one run's worst case with retries —
# 3 * 30 s + 1 s + 2 s = 93 s — so a timeout never cuts the retries short.
_CONSENSUS_TIMEOUT_S = 120


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
    tokens_in: int | None
    tokens_out: int | None
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


def _usage(response: object) -> tuple[int | None, int | None]:
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return None, None
    return (
        getattr(meta, "prompt_token_count", None),
        getattr(meta, "candidates_token_count", None),
    )


def _cost_usd(model: str, tokens_in: int | None, tokens_out: int | None) -> float | None:
    """None unless the model is priced and both token counts are known — we
    don't invent numbers."""
    price = PRICE_PER_MTOK.get(model)
    if price is None or tokens_in is None or tokens_out is None:
        return None
    price_in, price_out = price
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


def _response_text(response: object) -> str:
    try:
        return response.text or ""
    except Exception:  # a blocked or part-less response raises on .text
        return ""


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


async def _one_attempt(
    image_bytes: bytes,
) -> tuple[Transcription | None, CallStats, bool]:
    """A single Gemini call plus the parsing that follows it. The third element
    says whether a retry is worth it: True only for a transient exception. A
    200 that parsed badly is never retried (PLAN.md -> Contracts)."""
    started = time.monotonic()
    try:
        async with _API_SLOTS:
            response = await asyncio.wait_for(
                _client.aio.models.generate_content(
                    model=settings.VISION_MODEL,
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes, mime_type="image/jpeg"
                        ),
                        TRANSCRIBE_PROMPT,
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=1.0,
                        max_output_tokens=8192,
                    ),
                ),
                timeout=_CALL_TIMEOUT_S,
            )
    except Exception as exc:
        # No response → no tokens billed → no cost to record.
        latency_ms = int((time.monotonic() - started) * 1000)
        retryable = _should_retry(exc)
        logger.warning(
            "Gemini attempt failed (%s): %s",
            "retryable" if retryable else "final",
            exc,
        )
        stats = CallStats(None, None, None, latency_ms, False, _short_error(exc))
        return None, stats, retryable

    tokens_in, tokens_out = _usage(response)
    result = parse_response(_response_text(response))
    latency_ms = int((time.monotonic() - started) * 1000)

    # The model answered, so the tokens were spent whether or not we could read
    # the answer — cost is recorded either way (PLAN.md -> Contracts).
    stats = CallStats(
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_cost_usd(settings.VISION_MODEL, tokens_in, tokens_out),
        latency_ms=latency_ms,
        success=result is not None,
        error=None if result is not None else "unparseable model response",
    )
    return result, stats, False


async def transcribe(
    image_bytes: bytes,
) -> tuple[Transcription | None, list[CallStats]]:
    """Up to three attempts with 1 s then 2 s pauses, stopping at the first
    success or the first non-retryable failure. Never touches the database.
    Every attempt is recorded in the returned list, which is always non-empty."""
    all_stats: list[CallStats] = []
    last = len(_RETRY_PAUSES_S)
    for attempt in range(last + 1):
        result, stats, retryable = await _one_attempt(image_bytes)
        all_stats.append(stats)
        if result is not None:
            return result, all_stats
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
    *different values* on it.
    """
    return [
        d for d in divergences if len({k for k in d.variants if _is_value(k)}) >= 2
    ]


def _verdict(text_agreement: float) -> str:
    """Non-overlapping bands from PLAN.md task 6."""
    if text_agreement >= 0.90:
        return "clean"
    if text_agreement >= 0.70:
        return "needs_review"
    return "rejected"


async def transcribe_consensus(
    image_bytes: bytes,
) -> tuple[TranscriptionResult | None, list[CallStats]]:
    """settings.VISION_RUNS independent transcribe() calls in parallel, then
    compared by code. Never touches the database: the returned list carries the
    stats of every run that finished. Fewer than two successful runs → first
    element None (the list is then empty only if the 120 s ceiling fired before
    any run returned).

    A 120 s ceiling guards against a run that hangs past its own retries. It is
    asyncio.wait, not wait_for: cancelling the whole gather would throw away the
    CallStats of runs that already finished, and those calls were still billed."""
    tasks = [
        asyncio.create_task(transcribe(image_bytes))
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
                CallStats(None, None, None, 0, False, _short_error(exc))
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
    best = ok_runs[consensus.pick_representative(markdowns)]

    verdict = _verdict(text_agreement)
    logger.info(
        "consensus: %d/%d runs ok, text_agreement=%.3f, verdict=%s, "
        "divergences %d of %d kept",
        len(ok_runs),
        settings.VISION_RUNS,
        text_agreement,
        verdict,
        len(numeric_divergences),
        len(reported),
    )
    return (
        TranscriptionResult(best, text_agreement, numeric_divergences, verdict),
        all_stats,
    )


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
                        kind="transcribe",
                        model=settings.VISION_MODEL,
                        tokens_in=s.tokens_in,
                        tokens_out=s.tokens_out,
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
