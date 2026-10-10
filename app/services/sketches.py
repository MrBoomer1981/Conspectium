"""Where each drawing of a page is, and what its labels say, read by the
model so a sketch can be drawn again from the page (task 101).

Recognition writes a sketch as "[схема: …]" — words, since a set or a ball
is no data (charts.py). This call is given the page and those lines and
asked two things the model reads well: each drawing's frame, and each
label written on it with its box. Never the drawing's lines: asked for
them, the model drew circles of the wrong size and a grid the author never
drew, and each run its own (`docs/FINDINGS.md` → "Sketches drawn from the
page"). The lines are the photograph's (strokes.py).

Three runs, compared as recognition's are: a frame counts where two runs
frame the drawing alike, a label where two read it alike at one place —
invention does not write the same label in the same place twice. A run
that frames a different number of drawings than the lines it was given is
no pairing and counts for nothing. Nothing here touches the database; every
call's stats are returned for the caller to write (rule 4), and nothing
raises — a page whose drawings cannot be read keeps their words.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time

from google.genai import types

from app.core.config import settings
from app.services import strokes, vision
from app.services.vision import CallStats

logger = logging.getLogger(__name__)

SKETCH_PROMPT_FILE = "prompts-sketch-v1.md"
SKETCH_PROMPT = vision.load_prompt(SKETCH_PROMPT_FILE)
SKETCH_PROMPT_WORDS = len(SKETCH_PROMPT.split())

# Three runs, as recognition reads a page: two that agree outvote one that
# does not, and a third gives the majority when two disagree.
RUNS = 3
# A call that failed for a 429, a 503 or a dropped connection is asked once
# more; recognition's pauses, not its ceiling — this answer is short.
_ATTEMPTS = 2
_RETRY_PAUSE_S = 1.0

# "[схема: …]": recognition's line for a drawing that is not data, as
# figures.py reads it.
_SCHEME_RE = re.compile(r"\[\s*схема\s*:\s*([^\[\]]*?)\s*\]", re.IGNORECASE)

# Two frames are one drawing's when they overlap this much of their union.
_SAME_FRAME = 0.5
# Two labels are one when they read the same and their centres stand within
# this many thousandths of the photograph — about two letters.
_SAME_PLACE = 15
# A label is a letter, a number or a short sign, not a sentence.
_MAX_LABEL_CHARS = 40
_MAX_LABELS = 30


def lines(markdown: str) -> list[str]:
    """The words of each "[схема: …]" line, in order."""
    return [" ".join(words.split()) for words in _SCHEME_RE.findall(markdown)]


def _box(value: object) -> tuple[int, int, int, int] | None:
    """A box as the prompt asks for it — [top, left, bottom, right] in
    thousandths, inside the photograph and not empty — or None."""
    if not isinstance(value, list) or len(value) != 4:
        return None
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
        return None
    top, left, bottom, right = (int(round(v)) for v in value)
    top, left = max(0, top), max(0, left)
    bottom, right = min(1000, bottom), min(1000, right)
    if bottom <= top or right <= left:
        return None
    return top, left, bottom, right


def parse(raw: str) -> list[dict] | None:
    """One run's answer: each drawing's frame and labels, in order; None
    for an answer that is no list of drawings. Never raises (rule 7): a
    label that is not one is left out, a drawing with no frame stays in
    its place as None, so the pairing with the lines is not shifted."""
    try:
        data = json.loads(vision._repair_backslashes(raw))
    except Exception:
        return None
    if isinstance(data, dict):
        data = data.get("drawings")
    if not isinstance(data, list):
        return None
    out: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            out.append({"frame": None, "labels": []})
            continue
        labels = []
        found = item.get("labels")
        for label in found[:_MAX_LABELS] if isinstance(found, list) else []:
            if not isinstance(label, dict):
                continue
            text, box = label.get("text"), _box(label.get("box"))
            if isinstance(text, str) and text.strip() and len(text) <= _MAX_LABEL_CHARS and box:
                labels.append(strokes.Label(text.strip(), box))
        out.append({"frame": _box(item.get("frame")), "labels": labels})
    return out


def _overlap(a, b) -> float:
    top, left = max(a[0], b[0]), max(a[1], b[1])
    bottom, right = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, bottom - top) * max(0, right - left)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _same_text(text: str) -> str:
    """A label as compared: no dollars, no spaces, \\text{…} its words,
    a lone letter's braces gone — «x_{1}» is «x_1»."""
    text = text.replace("$", "")
    text = re.sub(r"\\(?:text|mathrm|textit|mbox)\s*\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\{(\w)\}", r"\1", text)
    return re.sub(r"\s+", "", text)


def _centre(box) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def agreed(runs: list[list[dict] | None], count: int) -> list[strokes.Sketch | None]:
    """Each drawing as the runs agree on it, or None: the largest set of
    runs whose frames overlap pairwise by half, two at least; the frame
    every one of them reaches and the one they all hold; and the labels
    of the first of them that another reads the same at the same place."""
    usable = [run for run in runs if run is not None and len(run) == count]
    out: list[strokes.Sketch | None] = []
    for i in range(count):
        frames = [run[i]["frame"] for run in usable]
        best: list[int] = []
        for a, frame in enumerate(frames):
            if frame is None:
                continue
            group = [
                b for b, other in enumerate(frames)
                if other is not None and _overlap(frame, other) >= _SAME_FRAME
            ]
            if len(group) > len(best):
                best = group
        if len(best) < 2:
            out.append(None)
            continue
        held = [frames[g] for g in best]
        frame = (min(f[0] for f in held), min(f[1] for f in held), max(f[2] for f in held), max(f[3] for f in held))
        inner = (max(f[0] for f in held), max(f[1] for f in held), min(f[2] for f in held), min(f[3] for f in held))
        if inner[2] <= inner[0] or inner[3] <= inner[1]:
            out.append(None)
            continue
        labels = []
        for label in usable[best[0]][i]["labels"]:
            text, (cy, cx) = _same_text(label.text), _centre(label.box)
            if not text:
                continue
            for g in best[1:]:
                if any(
                    _same_text(other.text) == text
                    and abs(_centre(other.box)[0] - cy) <= _SAME_PLACE
                    and abs(_centre(other.box)[1] - cx) <= _SAME_PLACE
                    for other in usable[g][i]["labels"]
                ):
                    labels.append(label)
                    break
        out.append(strokes.Sketch(frame, inner, labels))
    return out


async def _one_call(image_bytes: bytes, prompt: str) -> tuple[str | None, CallStats, bool]:
    started = time.monotonic()
    model = settings.VISION_MODEL
    try:
        async with vision._API_SLOTS:
            response = await asyncio.wait_for(
                vision._client.aio.models.generate_content(
                    model=model,
                    contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt],
                    # recognition's: the same model reading the same page,
                    # thinking at its default, at temperature 1 so the runs
                    # are independent
                    config=vision._generation_config(),
                ),
                timeout=settings.VISION_CALL_TIMEOUT_S,
            )
    except Exception as exc:
        return None, CallStats(
            kind="sketch", model=model, tokens_in=None, tokens_out=None, tokens_thought=None,
            cost_usd=None, latency_ms=int((time.monotonic() - started) * 1000),
            success=False, error=vision._short_error(exc),
            # a timeout is not asked again: three runs were asked, and the
            # page's record waits on the slowest
        ), vision._should_retry(exc) and not isinstance(exc, TimeoutError)
    tokens_in, tokens_out, tokens_thought = vision._usage(response)
    text = vision._response_text(response)
    return text, CallStats(
        kind="sketch", model=model, tokens_in=tokens_in, tokens_out=tokens_out,
        tokens_thought=tokens_thought,
        cost_usd=vision._cost_usd(model, tokens_in, tokens_out, tokens_thought),
        latency_ms=int((time.monotonic() - started) * 1000),
        success=bool(text), error=None if text else "empty model response",
    ), False


async def _run(image_bytes: bytes, prompt: str, stats: list[CallStats]) -> list[dict] | None:
    for attempt in range(_ATTEMPTS):
        raw, call, retryable = await _one_call(image_bytes, prompt)
        stats.append(call)
        if raw is not None:
            found = parse(raw)
            if found is None:
                call.success = False
                call.error = vision._answer_shape(raw)
            return found
        if not retryable or attempt == _ATTEMPTS - 1:
            return None
        await asyncio.sleep(_RETRY_PAUSE_S)
    return None


async def read(image_bytes: bytes, markdown: str) -> tuple[list[strokes.Sketch | None], list[CallStats]]:
    """The page's drawings — one entry a "[схема: …]" line of `markdown`, in
    order, None where the runs did not agree — and every call made. A page
    with no such line costs nothing."""
    described = lines(markdown)
    if not described:
        return [], []
    prompt = SKETCH_PROMPT.replace(
        "{drawings}", "\n".join(f"{n}. [схема: {words}]" for n, words in enumerate(described, 1))
    )
    stats: list[CallStats] = []
    # A run that failed in a way nobody foresaw is a run with no answer; the
    # page's text never waits on its drawings.
    answers = await asyncio.gather(
        *(_run(image_bytes, prompt, stats) for _ in range(RUNS)), return_exceptions=True
    )
    runs = []
    for answer in answers:
        if isinstance(answer, BaseException):
            logger.warning("sketches: a run failed", exc_info=answer)
            runs.append(None)
        else:
            runs.append(answer)
    try:
        sketches = agreed(runs, len(described))
    except Exception:
        logger.warning("sketches: the runs could not be compared", exc_info=True)
        sketches = [None] * len(described)
    logger.info(
        "sketches: %d drawings described, %d framed alike by two runs, runs answering %s, labels %s",
        len(described),
        sum(s is not None for s in sketches),
        [len(run) if run is not None else None for run in runs],
        [len(s.labels) if s is not None else None for s in sketches],
    )
    return sketches, stats
