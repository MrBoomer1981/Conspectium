"""Gemini recognition: prompt, one model call, response parsing, spend logging.

Task 5 wires in exactly one call per photo. Retries (task 10) and three parallel
runs (task 6) come later. Nothing here touches the database except log_ai_calls,
which uses its own session on purpose — see CLAUDE.md -> Sessions and transactions.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import types

from app.core.config import PRICE_PER_MTOK, settings
from app.db.models import AiCall
from app.db.session import async_session_maker

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


def _short_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:500]


async def transcribe(
    image_bytes: bytes,
) -> tuple[Transcription | None, list[CallStats]]:
    """One Gemini call. Never touches the database. Returns the parsed result
    (None on a network error, invalid JSON, or a schema mismatch) and a
    one-element stats list, always non-empty. Retries are task 10; the
    external timeout is task 10 too."""
    started = time.monotonic()
    try:
        response = await _client.aio.models.generate_content(
            model=settings.VISION_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                TRANSCRIBE_PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=1.0,
                max_output_tokens=8192,
            ),
        )
    except Exception as exc:
        # No response → no tokens billed → no cost to record.
        latency_ms = int((time.monotonic() - started) * 1000)
        logger.warning("Gemini call failed: %s", exc)
        return None, [CallStats(None, None, None, latency_ms, False, _short_error(exc))]

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
    return result, [stats]


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
