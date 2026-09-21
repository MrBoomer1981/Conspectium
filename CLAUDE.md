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

**Stage:** second week, one user — the author. Week 1 (capture: photo to
structured record) is built and unit-tested, but has never been confirmed
end to end on the deployed bot — the "Definition of week-ready" checklist in
`PLAN.md` is still open. Week 2 gives the corpus a way out: reading, search,
correction, statistics. The question the whole thing exists to answer is
still whether the author uses this daily. Not launch, not growth, not
revenue, not scale.

---

## Stack

- Python 3.12
- FastAPI — bot webhook and the future home of the Mini App API, single process
- aiogram 3.x — bot, webhook only, no polling
- SQLAlchemy 2.x (async) + Alembic + PostgreSQL (Railway addon)
- Google Gemini 3.5 Flash Lite — recognition
- Pillow + numpy — image processing
- reportlab + matplotlib — a record as a PDF, formulas drawn by mathtext
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

`.python-version` pins 3.12, which is what Railway runs. If pyenv doesn't
have it, the suite also runs on 3.11 in a virtualenv built with an explicit
interpreter path, bypassing the shim — nothing under `tests/` needs 3.12:

    ~/.pyenv/versions/3.11.9/bin/python -m venv .venv
    .venv/bin/pip install -r requirements-dev.txt
    .venv/bin/pytest

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

All of them were established on `gemini-2.5-flash-lite`, which Google closed
to new accounts in September 2026; recognition now runs on
`gemini-3.5-flash-lite`. The findings are kept because each cost a real
failure to discover, but they are evidence about the old model. If
recognition starts behaving differently — the prompt length trade-off, the
value of three runs, the uselessness of self-assessment — the model change is
the first thing to suspect, and a fresh reproduction outranks the note.

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

Telegram never says how many items a media group holds, so "the album has
ended" can only ever be a guess at silence. A page reaches the buffer only
after `handle_photo` has downloaded and compressed it, so the gap between
arrivals is one photo's worth of work — seconds, not milliseconds. Too short
a window and one album becomes several one-page records, each with its own
reply and its own paid recognition. That is a real failure, not a
hypothetical: at 1 s a four-page album arrived as four records.

**Router order in `main.py` is load-bearing.** `handlers.router` ends with a
filterless catch-all that matches every message, so any router included after
it receives nothing. `corpus.router` is included **first**, capture second.
Adding a third router means deciding where it goes relative to that catch-all.

**A saved record goes out as a PDF.** Recognised notes are dense with LaTeX,
and `$\sum_{i=1}^{p} \rho(v_i) = 2q$` reads as noise until it is drawn, so all
three capture paths finish by calling `corpus.send_record`. Rendering is
CPU-bound and runs in a thread; if it fails for any reason the record is sent
as plain text instead. A record is never lost over its presentation.

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
| `_QUIET_SECONDS` | `bot/albums.py` | 3 s of silence closes an album. Must exceed the gap between pages *landing in the buffer* — that gap is one photo's download and compression, not Telegram's delivery |
| `_COLLECT_MAX_S` | `bot/albums.py` | 60 s from the first page, so a stream that never goes quiet can't hold a session for ever |
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

One is known and worked around rather than fixed. `consensus.extract_numbers`
treats every numeric literal on the page as a value to compare, list markers
and subscripts included, so `compare()` reports a divergence wherever the runs
happen to align differently. On a real page of lecture notes that produced
eight reported divergences of which one was genuine. The filter lives in
`vision.meaningful_divergences`, which keeps a position only when at least two
runs read it as *different numbers* — a number against a gap is an alignment
artefact, not a misreading.

---

## Structure

All ten `PLAN.md` tasks are done — everything below is on disk.

```
app/
  main.py             FastAPI, webhook, /health
  bot/
    handlers.py       aiogram handlers
    texts.py          all user-facing messages, and the command list
    middlewares.py    DB session and user injected into handlers
    albums.py         album buffer and assembly
    corpus.py         reading, search and correction commands
  services/
    vision.py         Gemini: prompt, response parsing, three runs
    images.py         compression
    limits.py         spend limits
    docx.py           .docx -> markdown, no model call
    pdf.py            a record as a PDF, formulas drawn
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
VISION_MODEL=gemini-3.5-flash-lite
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

The suite is offline: no network, no Gemini, no Postgres. Everything that
needs a database runs on in-memory SQLite.

| File | Covers |
|---|---|
| `test_parse_response.py` | the model's reply: garbage, the ```json fence, missing fields, wrong types |
| `test_limits.py` | `check_limits` / `consume` — the money-critical path |
| `test_reliability.py` | retry classification, one owner per album batch, spend surviving a rollback |
| `test_vision_pure.py` | `_should_retry`, `_cost_usd`, `total_cost`, `_verdict`, `_short_error` |
| `test_albums.py` | `_assemble` aggregates, `process_batch` survivor logic |
| `test_docx.py` | heading styles to markdown, title derivation |
| `test_images.py` | the 1500 px cap, EXIF orientation, JPEG output |
| `test_config.py` | the `DATABASE_URL` scheme rewrite, `VISION_RUNS >= 2` |
| `test_handlers.py` | `_split_message`, the catch-all reply |
| `test_middleware.py` | session per update, rollback, the early commit of a new user |
| `test_corpus.py` | listing, opening, correcting, statistics — and that no query reaches another user's records |
| `test_wiring.py` | router order in `main.py`, and that every command the bot answers has a menu description |
| `test_pdf.py` | how a page is parsed into blocks, escaping, and that an unreadable formula never sinks the document |

`tests/conftest.py` does two things without which nothing imports: it fills
the five required environment variables with placeholders, and it teaches the
SQLite compiler to render `JSONB` as `JSON`. The second is a test-side
adapter for the sqlite dialect only — `app/db/models.py` stays PostgreSQL.

Deliberately **not** covered: `photoguard`, `consensus` and `mathcheck`,
which arrived with their own tests, and the photo and document pipelines end
to end — those break on every reordering of a handler, and the pipeline is
not settled yet.

Five tests are skipped unless `TEST_DATABASE_URL` points at a real Postgres:
`test_spend_survives_main_rollback`, which needs two genuinely separate
transactions, and the four behavioural search tests, because SQLite has no
`to_tsvector`. The shape of the search statement is checked without a server
by compiling it against the PostgreSQL dialect — that is what catches an
un-inlined regconfig — but the matching itself is unproven until a Postgres
is available.

Still to write: the FSRS schedule calculation (third week, not started).

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
- Video and lecture transcription
- Payments, subscriptions, pricing tiers
- Custom registration and passwords — identity already comes from Telegram
- An admin panel
- Export to Anki, and any bulk export of the corpus. `/pdf` renders **one
  record** so it can be read — that is presentation, not an exit door, and
  it is not licence to add "download everything"
- A language trainer, text rewriting, or any second feature
- Visual design and styling of bot responses
- Social features, sharing, friends
- Caching, queues, microservices, Docker, CI
