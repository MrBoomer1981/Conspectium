# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Project context. Read at the start of every session.
**Update this file with every architectural decision.**

---

## What this is

A Telegram bot for students. The user photographs a lecture note and gets
back a structured record, which accumulates in their personal corpus.
Later, the records are turned into spaced-repetition flashcards.

**The core value is the accumulated corpus, not the flashcards.** Flashcards
give a reason to keep feeding in notes regularly; the corpus gives a reason
not to leave. When choosing between "improve the flashcards" and "improve
work with the corpus," choose the corpus.

**Stage:** first week, one user — the author. The goal is to check whether
the author will actually use this daily. Not launch, not growth, not
revenue, not scale.

---

## Stack

- Python 3.12
- FastAPI — bot webhook and the future home of the Mini App API, single process
- aiogram 3.x — bot, webhook only, no polling
- SQLAlchemy 2.x (async) + Alembic + PostgreSQL (Railway addon)
- Google Gemini 2.5 Flash Lite — recognition
- Pillow + numpy — image processing
- Railway — hosting

Don't add dependencies without an explicit need. Don't introduce Redis,
queues, workers, Docker, or CI — there's a single user.

---

## Development commands

Install (locally, for running tests):

    pip install -r requirements-dev.txt

`app.core.config.settings` is built from the environment at import time, so
anything importing `app.*` needs the five required variables. Copy
`.env.example` to `.env` and fill them in before running `alembic` or
`uvicorn`, or they crash with a validation error before ever reaching the
database. `pytest` is the exception: `tests/conftest.py` fills the same
variables with placeholders, so the suite collects without an `.env`.

Run tests:

    pytest

Run a single test:

    pytest tests/test_parse_response.py::test_name

`asyncio_mode = "auto"` in `pyproject.toml`: async tests and fixtures need no
`@pytest.mark.asyncio`. Tests that need a database use SQLite through
`aiosqlite`; nothing in the suite makes a network or Gemini call.

Create a new migration:

    alembic revision -m "description"

Revision ids are hand-written, not the generated hash — `001_users_events`,
`002_ai_calls`, `003_notes`. Continue the numbering.

Apply migrations:

    alembic upgrade head

Run locally (needs a process with a public URL for the webhook, e.g. ngrok):

    uvicorn app.main:app --reload

Production (Railway, see `Procfile`):

    alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT

No linter is configured yet — don't add one without an explicit request.

---

## Inviolable rules

1. **The LLM is called only from the server.** The key never reaches the
   client. Also: the Gemini API isn't reachable directly from Russia, so
   calls go out from Railway.

2. **Compress the image before sending it to the model.** Long side capped
   at 1500 px, JPEG quality 85. A full-size phone photo costs several times
   more with no gain in accuracy.

3. **Never store the original photos.** Only the recognized text.

4. **Every model call is written to `ai_calls`** — model, tokens, cost,
   latency, success, error. No exceptions.

5. **Every significant action is written to `events`.** Retention can't be
   computed after the fact.

6. **Limits are checked before the model call, not after.**

7. **Never trust JSON from the model.** Always validate the schema, always
   handle garbage input. The parsing function never raises — it returns
   `None`.

---

## Established experimentally

These conclusions come from real runs. Don't revisit them without new
data — each one stands on a reproduced failure.

**A short prompt beats a long one.** A 1500-word version of the prompt
fixed one thing and broke three that the 250-word version read correctly.
Every extra rule steals attention from the main task.
**Don't lengthen `TRANSCRIBE_PROMPT`.**

**A verification model call doesn't work.** The request "compare the
transcription with the photo and find discrepancies" invented a
discrepancy that didn't exist, duplicated it three times, and found none
of the real ones. **Don't add a verification pass with the model.**

**Agreement between independent runs works.** Three runs of the same short
prompt, results compared by code. Where they agree, trust it; where they
diverge, flag it. This is the only uncertainty signal that has turned out
to be reliable.

**The model's self-assessment is useless.** The `confidence` field gave
0.95 on a page with three errors. That's why it's not in the schema.
`unreadable_count: 0` is likewise not a sign of quality.

**Arithmetic is checked by code, not by the model.** The model makes
calculation errors and silently "fixes" things that don't add up.
`mathcheck` found an error in a constant and a diverging chain that the
model missed across four runs.

**The model attributes its own errors to the author.** Having misread a
semicolon as a letter, it wrote in `uncertain`: "possibly a typo by the
author." The prompt now explicitly forbids this kind of interpretation.

**A bad shot is more dangerous than difficult text.** On a spread
photographed from a distance, the model recognized the topic from the
heading and produced a coherent textbook-style retelling with
`unreadable_count: 0`. No after-the-fact check catches this. That's why
`photoguard` is called **before** the model and must never be bypassed.

---

## Sessions and transactions

The full reasoning and a worked example are in `PLAN.md` → "Transaction
model". The essentials, because this shapes every handler:

1. **One session per update, opened by the middleware.** It lives in
   `data["session"]`, commits after the handler, and rolls back on any
   exception. `notes`, `users`, and `events` all go through it.

   One deliberate exception: a **new** user is committed by the middleware
   *before* the handler runs. `log_ai_calls` opens its own session
   mid-handler and inserts `ai_calls.user_id`; without that early commit the
   other session can't see the row yet and the foreign key fails. Someone who
   wrote to the bot is registered regardless of how their first update ends.

2. **`events` are transactional and disappear on rollback — deliberately.**
   An event describes something that, in the end, didn't happen. `log_event`
   wraps its insert in a SAVEPOINT (`begin_nested`) not to survive a
   rollback but so that a failed insert can't poison the surrounding
   transaction and bring down the next request.

3. **`ai_calls` are written in their own session and committed
   immediately.** Money was spent regardless of how processing ended, so the
   spend row must outlive a rollback of the main transaction — otherwise the
   daily cap is understated and the circuit breaker stops working.
   `log_ai_calls` takes no session; it opens its own. Consequence:
   `ai_calls` rows with no matching `Note` are a normal outcome, not a bug
   to fix.

4. **`note_failed` is the only event written standalone**
   (`log_event_standalone`), because the global error handler runs while the
   main transaction is already rolling back. Every other event uses
   `log_event`.

5. **Anything that calls the model never touches the database.** The three
   runs and the pages of an album run in parallel, and a single
   `AsyncSession` cannot be used concurrently. Model-calling functions
   return their stats upward; the handler performs the writes.

---

## The pipeline

The canonical step order for a photo is in `PLAN.md` → "Final processing
order for a photo". Every "does this come before or after that?" question is
answered there, not here. Three things that order implies and that are easy
to get wrong:

**`verdict` and `status` are different vocabularies.** `verdict` belongs to
the pipeline and is `clean | needs_review | rejected`; `Note.status` is
stored and is only `ready | needs_review`. A `rejected` verdict exits at
step 10 and never reaches the database. A critical `mathcheck` issue
downgrades `clean` → `needs_review`, one way only — a warning is shown but
leaves the verdict alone.

**An album is owned by exactly one update.** Telegram delivers an album as
separate messages sharing a `media_group_id`, each its own webhook update
with its own session. `albums.collect()` waits for the group to go quiet and
hands the whole batch to a single caller; every other caller gets `None` and
**must return without replying**. Reply there and the album gets processed
once per page.

**`.docx` bypasses the model entirely.** No limits are checked and no quota
is spent, so a Word file is still processed with `AI_ENABLED=false` — it is
already machine text. Only the empty-text gate (step 11) still applies.

---

## Concurrency ceilings

These constants are derived from each other across three files. Changing one
on its own breaks the arithmetic:

| Constant | Where | Why that value |
|---|---|---|
| `_API_SLOTS` | `services/vision.py` | `Semaphore(10)` — Gemini answers a bigger burst with 429s |
| `_CALL_TIMEOUT_S` | `services/vision.py` | 30 s for one call; a typical response is ~6 s |
| `_CONSENSUS_TIMEOUT_S` | `services/vision.py` | 120 s > one run's worst case with retries (3 × 30 + 1 + 2 = 93 s) |
| `_ALBUM_TIMEOUT_S` | `bot/albums.py` | 300 s = three waves of 93 s under `Semaphore(10)`. Normative — don't lower it |
| `max_overflow` | `db/session.py` | 15 — `MAX_ALBUM_PAGES` updates each hold a session open through the debounce |

Both ceilings use `asyncio.wait`, never `wait_for`, and cancel the
stragglers in a `finally`. Cancelling the group as a whole would discard the
`CallStats` of runs that already returned — and those calls were billed.
An orphaned run also keeps making paid calls with the result thrown away.

---

## Ready-made modules

`app/services/` contains three modules written and tested in advance:

| Module | What it provides |
|---|---|
| `photoguard.py` | `check_photo_bytes(data) -> PhotoVerdict` |
| `consensus.py` | `compare`, `compare_text`, `pick_representative` |
| `mathcheck.py` | `check(markdown) -> Report` |

**Don't rewrite or "improve" them.** Only import and call. Found a bug in
one — report it, don't fix it silently.

---

## Structure

All ten `PLAN.md` tasks are done — everything below is on disk.

```
app/
  main.py             FastAPI, webhook, /health
  bot/
    handlers.py       aiogram handlers
    texts.py          all user-facing messages
    middlewares.py    DB session and user injected into handlers
    albums.py         album buffer and assembly
  services/
    vision.py         Gemini: prompt, response parsing, three runs
    images.py         compression
    limits.py         spend limits
    docx.py           .docx -> markdown, no model call
    photoguard.py     ready-made
    consensus.py      ready-made
    mathcheck.py      ready-made
  db/
    models.py
    session.py
    migrations/
  core/
    config.py         settings from the environment
    events.py         event logging (log_event + log_event_standalone)
tests/
CLAUDE.md
PLAN.md
prompts-v3.md        TRANSCRIBE_PROMPT, read from disk at import
```

`prompts-v3.md` holds the recognition prompt as plain text. `vision.py`
doesn't copy it — it reads the file from the repo root at **import time**.
So the file has to ship with the deploy or the process dies at startup, and
editing it changes the prompt without touching any Python.

---

## Environment variables

```
BOT_TOKEN                required
DATABASE_URL             required
GEMINI_API_KEY           required
WEBHOOK_URL              required
WEBHOOK_SECRET           required
AI_ENABLED=true          kill switch for all model calls
DAILY_PAGES_PER_USER=30
DAILY_COST_LIMIT_USD=5
VISION_RUNS=3
VISION_MODEL=gemini-2.5-flash-lite
MIN_MARKDOWN_LEN=40
MAX_ALBUM_PAGES=10
LOG_LEVEL=INFO
```

A missing required variable must crash the app at startup, not on the
first request.

`VISION_MODEL` is coupled to `PRICE_PER_MTOK` in `core/config.py`: a model
absent from that table yields `cost_usd = NULL`, and `NULL` rows are skipped
by the `SUM` behind `DAILY_COST_LIMIT_USD`. Switching models without adding
the price silently disables the cost circuit breaker.

---

## Tests

Required only for these places, everything else has no tests yet:

1. Parsing the model's response, including garbage, the ```json wrapper,
   missing fields, and wrong types — `test_parse_response.py`
2. Spend limit checks — `test_limits.py`
3. Reliability: retryable vs. final Gemini failures, exactly one owner per
   album batch, spend surviving a rollback of the main transaction —
   `test_reliability.py`
4. FSRS schedule calculation (third week, not started yet)

---

## How to work in this project

- **Describe the plan of changes first, wait for confirmation, then write
  code.** No size threshold — a one-line, single-point change still gets
  its plan stated and confirmed before any edit. "It's just one line" is
  not a reason to skip straight to code.
- One task from `PLAN.md` — one session — one commit.
- Nothing beyond the current task. Got an idea — put it in the `PLAN.md`
  backlog.
- Write code that can be explained out loud. A non-obvious decision gets
  a comment about **why**, not what.
- Russian in user-facing messages, English in code and logs.
- All user-facing strings live in `bot/texts.py`, not in the handlers.
- Don't create abstractions for the future. Duplication now is cheaper
  than premature architecture.
- Not a single traceback reaches the user. Any unhandled error →
  a clear message to the user, details to the log.

---

## What NOT to do at this stage

Everything below is deliberately postponed. Don't suggest or implement:

- A Mini App or any interface other than the bot
- Flashcards and spaced repetition (third week)
- Search across the corpus and editing records (second week)
- Video and lecture transcription
- Payments, subscriptions, pricing tiers
- Custom registration and passwords — identity already comes from Telegram
- An admin panel
- Export to Anki or any other format
- A language trainer, text rewriting, or any second feature
- Visual design and styling of bot responses
- Social features, sharing, friends
- Caching, queues, microservices, Docker, CI
