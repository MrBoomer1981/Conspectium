# CLAUDE.md

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

Run tests:

    pytest

Create a new migration:

    alembic revision -m "description"

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

```
app/
  main.py             FastAPI, webhook, /health
  bot/
    handlers.py       aiogram handlers
    texts.py          all user-facing messages
    middlewares.py    DB session and user injected into handlers
  services/
    vision.py         Gemini: prompt, response parsing, three runs
    images.py         compression
    limits.py         spend limits
    photoguard.py     ready-made
    consensus.py      ready-made
    mathcheck.py      ready-made
  db/
    models.py
    session.py
    migrations/
  core/
    config.py         settings from the environment
    events.py         event logging
tests/
CLAUDE.md
PLAN.md
```

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

---

## Tests

Required only for three places, everything else has no tests yet:

1. Parsing the model's response, including garbage, the ```json wrapper,
   missing fields, and wrong types
2. Spend limit checks
3. FSRS schedule calculation (third week, not started yet)

---

## How to work in this project

- **Describe the plan of changes first, wait for confirmation, then write
  code.**
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
