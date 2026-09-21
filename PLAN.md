# PLAN.md

Work plan for Claude Code. Lives in the repo root next to `CLAUDE.md`.

**How to work with this file:**

1. The user names a task number. You do **only that one**.
2. Before writing code, describe the plan of changes and wait for confirmation.
3. Once done, check `[x]` in the list below and update the "State" section
   strictly following the template.
4. Don't do anything from the following tasks, even if it "would only take
   two minutes."
5. Don't add abstractions, caching, queues, or retries where they aren't
   explicitly written down.
6. Found a contradiction or an ambiguity in this file — **ask**, don't
   decide on your own.
7. A disputed question about types, boundaries, and field semantics —
   check the "Contracts" section at the end of the file first.

---

## Progress

- [x] 1. Skeleton and deployment
- [x] 2. Users and events
- [x] 3. Receiving a photo
- [x] 4. Frame check
- [x] 5. Recognition
- [x] 6. Three runs and comparison
- [x] 7. Calculation check
- [x] 8. Saving and limits
- [x] 9. Word documents and albums
- [x] 10. Reliability

**Week 2 — getting the corpus back out:**

- [x] 11. Reading the corpus
- [x] 12. Search
- [x] 13. Correcting records
- [x] 14. Statistics

**Fixes and export, from real use:**

- [x] 15. An album arrives as one record
- [x] 16. Numeric divergences without the noise
- [ ] 17. The record as a PDF

## State

Update strictly following this template, adding or removing nothing:

```
Done: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
Current task: none
Next task: 17
Blockers: none
```

---

## Target structure

```
app/
  __init__.py
  main.py
  bot/
    __init__.py
    handlers.py
    texts.py
    middlewares.py
    albums.py
    corpus.py
  services/
    __init__.py
    vision.py
    images.py
    limits.py
    photoguard.py      # ready-made, don't change
    consensus.py       # ready-made, don't change
    mathcheck.py       # ready-made, don't change
  db/
    __init__.py
    models.py
    session.py
    migrations/
  core/
    __init__.py
    config.py
    events.py
tests/
  __init__.py
CLAUDE.md
PLAN.md
prompts-v3.md
requirements.txt
requirements-dev.txt
Procfile
.env.example
```

**All paths are written from the repo root.** `app` is a package. Imports
are absolute and always prefixed with `app.`: `from app.core.config import
settings`. No relative imports.

`app/bot/albums.py` is created in task 9, it doesn't exist before that.

### Ready-made modules

`photoguard.py`, `consensus.py`, `mathcheck.py` are already written and
covered by tests. **Don't rewrite, "improve," or extend them.** Only import
and call. Found a bug in them — report it, don't fix it.

```python
# photoguard
check_photo_bytes(data: bytes) -> PhotoVerdict
#   PhotoVerdict: .ok, .reason, .line_height_px, .sharpness,
#                 .paper_fraction, .contrast

# consensus
compare(runs: list[str]) -> ConsensusReport       # .divergences, .agreement
compare_text(runs: list[str]) -> TextConsensus    # .similarity
pick_representative(runs: list[str]) -> int       # index of the best run

# mathcheck
check(markdown: str) -> Report                    # .ok, .issues, .render()
#   Issue: .kind, .severity, .message, .detail, .suggestion
```

In all three, `runs` is a list of `markdown` strings, not objects.
The `Divergence` structure is in the "Contracts" section.

---

## Environment variables

```
BOT_TOKEN=                       required
DATABASE_URL=                    required
GEMINI_API_KEY=                  required
WEBHOOK_URL=                     required
WEBHOOK_SECRET=                  required
AI_ENABLED=true
DAILY_PAGES_PER_USER=30
DAILY_COST_LIMIT_USD=5
VISION_RUNS=3
VISION_MODEL=gemini-3.5-flash-lite
MIN_MARKDOWN_LEN=40
MAX_ALBUM_PAGES=10
LOG_LEVEL=INFO
```

Five required variables: missing any of them and the app **crashes at
startup**, not on the first request.

`WEBHOOK_URL` — **the service's base address without a path**, e.g.
`https://konspekt-bot.up.railway.app`. The app builds the path itself:
`{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}`. Don't put a path in the variable.

`VISION_RUNS` below 2 is forbidden: there would be nothing to compare
against. Validate it in `Settings` and crash at startup.

**All daily boundaries are UTC.** Both the reset of `pages_used_today` and
the `ai_calls` selection for today.

## Dependencies

`requirements.txt` — production:

```
fastapi
uvicorn[standard]
aiogram>=3.30
sqlalchemy[asyncio]>=2.0
asyncpg
alembic
pydantic-settings
google-genai
httpx
pillow
numpy
python-docx
```

`requirements-dev.txt` — local only:

```
-r requirements.txt
pytest
pytest-asyncio
```

Importing the Gemini client: `from google import genai`.
Don't add anything beyond these lists without an explicit request.

---

## Transaction model

**Read before task 2.** Exactly three rules here, and they explain why
the project has two different sessions.

**1. The main session comes from the middleware, one per update.** The
middleware opens it, puts it in `data["session"]`, commits after the
handler, and rolls back on an exception. Everything lives in it: `notes`,
`users`, `events`.

**2. `events` are transactional and are lost on rollback.** This is
accepted deliberately: an event describes something that, in the end,
didn't happen, and there's no point keeping it. `session.begin_nested()`
inside `log_event` is **not** there to survive a rollback — it's there for
a different reason: if the event's INSERT fails, without a SAVEPOINT it
would poison the whole transaction, and the "swallowed" error would bring
down the very next request.

**3. `ai_calls` are written in a SEPARATE session and committed
immediately.** Money was spent regardless of how the processing ended.
The spend row must survive a rollback of the main transaction, otherwise
the daily cap would be understated and the circuit breaker would stop
working.

⚠️ `session.begin_nested()` **does not give you this.** A SAVEPOINT lives
inside the outer transaction and disappears with it on rollback. The only
approach that works is a session of its own with its own commit:

```python
async def log_ai_calls(user_id: int, stats: list[CallStats]) -> None:
    """Writes ai_calls in its own session and commits immediately.
    Doesn't take a session: spend rows must not depend
    on the fate of the main transaction."""
    async with async_session_maker() as own:
        async with own.begin():
            own.add_all([...])
```

Consequence: the database may end up with `ai_calls` rows that have no
matching `Note`. That's **correct** — the money was spent.

**`ai_calls` without a `Note` is the expected outcome, not an incident.**
That's what any processing looks like where Gemini was called but no
record was created: `rejected`, `NO_TEXT_FOUND`, `transcribe_consensus`
returned `None`, a skipped album page, an unhandled error after the model
call. Don't try to "fix" such rows and don't create compensating records
for them — financial accounting is kept independent of record accounting.

**Exception for `note_failed`.** The global error handler runs while the
main transaction is already rolling back. The `note_failed` event is
written **in a separate session**, the same way as `ai_calls`. Every other
event is written in the main one.

---

## Final processing order for a photo

**The canonical sequence for a single photo.** If a "before or after"
question comes up while working on a task, the answer is here.

```
 1. take message.photo[-1]
 2. download into memory
 3. compress (images.compress)
 0. media_group_id set?                              ← into the buffer, exit (task 9)
 4. check limits (limits.check_limits, pages=1)       ← rejection: exit
 5. check the frame (photoguard.check_photo_bytes)    ← rejection: exit
 6. reply with texts.PROCESSING
 7. three recognition runs (vision.transcribe_consensus)
 8. record spend (vision.log_ai_calls)                ← always, own session
 9. result is None                                    ← texts.ERROR_GENERIC, exit
10. verdict == "rejected"                              ← texts.REJECTED_QUALITY, exit
11. markdown shorter than MIN_MARKDOWN_LEN             ← texts.NO_TEXT_FOUND, exit
12. check calculations (mathcheck.check)
13. save the Note
14. debit the quota (limits.consume, pages=1)
15. log the note_processed event
16. reply to the user
```

Step 0 keeps the label "0" even though it runs after step 3, not before
step 1: `PageInput` needs `bytes_before`/`bytes_after`/`width`/`height`,
which only exist once steps 1–3 have run, so the album check can't
physically precede them. The label stays "0" purely so every other
cross-reference in this document (steps 4, 5, 9, 10, 11, the "order steps
appear in code" table, the docx skip list) doesn't have to be
renumbered.

**Any exit at steps 4, 5, 9, 10, 11 means the same thing:** no record is
created, no quota is debited, `note_processed` is not written,
`note_failed` **is not written either** (these are normal rejections, not
failures), the user gets exactly one message with the reason.

**Step 8 always runs** once step 7 has been reached.

**Step 15 goes strictly between `consume` and the reply to the user.** The
event means "processing finished successfully end to end," so it can't be
written before the record and the quota have been saved.

What's sent at step 16:

1. `title` and `markdown` — the main body of the record
2. if `verdict == "needs_review"` — `texts.NEEDS_REVIEW`
3. if `mathcheck` found anything — `report.render()`
4. if `numeric_divergences` is non-empty — `texts.DIVERGENCES_HEADER`
   and the list of discrepancies, one per line
5. if `uncertain` is non-empty — `texts.UNCERTAIN_HEADER` and the list of
   uncertain spots, one per line: `"{text}" — {why}`

Items 2–5 go in **one separate message** after the main text.

### When saving appears

Steps 13–15 are implemented **in task 8** (the `note_processed` event gets
its full contract in task 10). Before task 8, in tasks 5–7, the result is
only sent to the user: the `notes` table doesn't exist yet. Don't create a
`Note` before task 8. The phrase "mark the record" in tasks 6 and 7 means
"set the `verdict` variable and show it to the user."

### Why this order

**Limits before the frame check:** with `AI_ENABLED=false` or an exhausted
cap, there's no point asking the user to retake the photo.

**`PROCESSING` after the frame check:** before it, processing takes a
fraction of a second, and an instant rejection after "processing..." would
look silly.

**Spend as a separate step in a separate session:** see "Transaction
model."

**The quota is debited after a successful save.**

### Order in which the steps appear in code

| Step | Appears in task | Where it's inserted |
|---|---|---|
| 1–3 | 3 | from scratch |
| 5 | 4 | after step 3 |
| 6 | 3 temporarily, moves in task 4 | after step 5 |
| 7, 8, 9, 11 | 5 (one run), rewritten in 6 | after step 6 |
| 10 | 6 | between steps 9 and 11 |
| 12 | 7 | after step 11 |
| 4 | 8 | **before** step 5 from task 4 |
| 13–15 | 8 | after step 12 |
| 0 | 9 | after step 3, before step 4 |

Tasks 8 and 9 insert their steps ahead of others'. This is the only
allowed edit to someone else's step: **you may change the call order,
never the logic inside.**

---

## All user-facing texts

Live in `app/bot/texts.py`, in Russian.

| Constant | When it's sent |
|---|---|
| `START` | the `/start` command |
| `PROCESSING` | step 6: frame accepted, recognition starting |
| `NO_TEXT_FOUND` | markdown shorter than `MIN_MARKDOWN_LEN` |
| `REJECTED_QUALITY` | `verdict == "rejected"`; for an album — if no page passed |
| `NEEDS_REVIEW` | `verdict == "needs_review"` |
| `DIVERGENCES_HEADER` | header for the list of numeric discrepancies |
| `UNCERTAIN_HEADER` | header for the list of uncertain spots |
| `LIMIT_PAGES` | daily page limit exhausted |
| `LIMIT_COST` | daily cost cap exceeded |
| `AI_DISABLED` | `AI_ENABLED=false` on an AI-dependent path |
| `DOCX_ONLY` | the document isn't `.docx` |
| `FILE_TOO_BIG` | file bigger than 5 MB |
| `TOO_MANY_PAGES` | album has more than `MAX_ALBUM_PAGES` pages |
| `PAGE_SKIPPED` | an album page was skipped, template with number and reason |
| `ERROR_GENERIC` | unhandled error, and also when `transcribe_consensus` returns `None` |

**The one exception:** `PhotoVerdict.reason` from `photoguard` is sent to
the user as is.

No user-facing strings outside `texts.py` — including list headers and
separators.

---

# Task 1. Skeleton and deployment

## Create

**`app/core/config.py`** — `Settings(BaseSettings)` with all the
variables. A module-level `settings` instance. Validation for
`VISION_RUNS >= 2`. The pricing constant:

```python
PRICE_PER_MTOK = {"gemini-3.5-flash-lite": (0.30, 2.50)}  # (input, output), USD
```

Model missing from the dict → cost is `None`, not a `KeyError`.

⚠️ **`DATABASE_URL` normalization.** Railway's Postgres addon hands out a
string like `postgresql://…`, but SQLAlchemy with asyncpg needs
`postgresql+asyncpg://…`. Without this fix the app crashes at startup with
`InvalidRequestError`, and the same thing happens in `alembic upgrade head`
during deployment.

In `Settings` — a validator that swaps the scheme:

```python
@field_validator("DATABASE_URL")
@classmethod
def _asyncpg_scheme(cls, v: str) -> str:
    if v.startswith("postgres://"):
        v = v.replace("postgres://", "postgresql://", 1)
    if v.startswith("postgresql://"):
        v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
    return v
```

Don't touch the variable in Railway itself: it's set there automatically by
the addon and can be refreshed if the database is recreated. Fix the
scheme only in code.

**`app/db/session.py`** — the async engine, `async_session_maker`, and
the `get_session()` dependency for FastAPI routes. aiogram handlers get
their session a different way, see task 2. The first consumer of
`get_session()` appears in task 10 (`/health`) — that's fine, don't invent
another use for it now.

`async_session_maker` is also used directly elsewhere, for the separate
sessions described in "Transaction model." Export it from the module.

Alembic's `env.py` takes the connection string **from `settings`**, not
from `alembic.ini`: otherwise the scheme normalization wouldn't apply and
migrations would fail on deploy. The migrations directory itself is
`app/db/migrations/`, as in "Target structure"; `script_location` in
`alembic.ini` points there.

**The engine is created with `pool_pre_ping=True` and `pool_recycle=1800`.**
This isn't a retry or fault tolerance — it's a required setting for a
managed Postgres instance: the provider closes idle connections, and by
its nature the bot sits idle for hours between photos. Without
`pool_pre_ping`, the very first request after a pause would fail on a dead
pooled connection — and it would look like a random database error.

**`app/db/models.py`** — the declarative base and two models:

```python
class User(Base):
    __tablename__ = "users"
    id: int                     # PK
    tg_id: int                  # BIGINT, unique, not null, index
    username: str | None
    first_name: str | None
    created_at: datetime        # server_default=now()
    pages_used_today: int       # not null, default 0
    quota_reset_at: date | None # the (UTC) day the counter was computed for

class Event(Base):
    __tablename__ = "events"
    id: int                     # PK
    user_id: int | None         # FK users.id, index
    type: str                   # not null, index
    payload: dict               # JSONB, not null, default {}
    created_at: datetime        # server_default=now(), index
```

**`app/bot/texts.py`** — only `START` for now.

**`app/bot/handlers.py`** — the aiogram router, `/start` replies with
`texts.START`.

**`app/main.py`** — the FastAPI application:

- `Bot` and `Dispatcher` are created **once, at module level**, not
  inside a request handler
- lifecycle managed via FastAPI's `lifespan`, not the deprecated
  `@app.on_event`
- on startup: `set_webhook` to `{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}`
  with `secret_token=WEBHOOK_SECRET`. **A `set_webhook` failure crashes
  the app**, not just a log warning: a bot without a webhook is useless
- `POST /webhook/{secret}` — checks the `secret` from the path against
  `settings.WEBHOOK_SECRET` and the `X-Telegram-Bot-Api-Secret-Token`
  header; either mismatch → 403. The double check is deliberate, don't
  simplify it
- `GET /health` → `{"status": "ok"}`
- on shutdown: `bot.session.close()`

**Alembic** — on the async engine, migration `001_users_events`.

**`Procfile`**:

```
web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**The Python version is pinned explicitly.** Without this, Railway would
use its own default version, and the code might not build on the same
version it was checked against locally. File `.python-version` at the
root:

```
3.12
```

**`.env.example`** — all the variables from the list above, required ones
with an empty value, the rest with defaults. Don't commit the real `.env`
to the repo: add it to `.gitignore` along with `__pycache__/`, `*.pyc`,
and `.venv/`.

## Acceptance criterion

`/start` to the live bot → the reply comes back **from the version
deployed on Railway**. Not from local, not via polling.
`GET /health` on the public URL returns 200.

## Don't do

No photo processing at all. No model calls. No business logic.

## Notes

- aiogram 3.x: `Dispatcher.feed_update(bot, update)` for the webhook.
- Update processing happens **inside the webhook request**, the 200
  response goes out after it finishes. A deliberate choice, see "Known
  risks." Don't switch it to background tasks on your own initiative.

---

# Task 2. Users and events

Read the "Transaction model" section before starting.

## Create

**`app/core/events.py`**:

```python
async def log_event(
    session: AsyncSession,
    user_id: int | None,
    event_type: str,
    payload: dict | None = None,
) -> None:
    """Write an event to the MAIN session. Transactional:
    lost if the update rolls back, and that's fine.

    Never raises.
    The insert runs inside session.begin_nested() — the SAVEPOINT
    isn't there to survive a rollback, it's there so that a failed
    INSERT doesn't poison the whole transaction and a "swallowed"
    error doesn't bring down the next request.

    The parameter is named event_type, not type: no need to shadow
    the builtin name. The database column stays named type."""

async def log_event_standalone(
    user_id: int | None,
    event_type: str,
    payload: dict | None = None,
) -> None:
    """Same thing, but in its own session with an immediate commit.
    Only for cases where the main transaction is already rolling
    back — i.e. note_failed from the global error handler (task 10).
    Don't use it anywhere else."""
```

**`app/bot/middlewares.py`** — an aiogram middleware, on every update:
- opens a session, puts it in `data["session"]`
- finds or creates the user by `tg_id`, puts it in `data["user"]`
- on creation, logs a `user_registered` event
- commits after the handler, rolls back on an exception

FastAPI's `get_session()` dependency doesn't work in aiogram handlers —
these are different mechanisms.

**`handlers.py`** — `/start` gets `session` and `user` already provided
as arguments.

## Acceptance criterion

After `/start`, there's one row in `users` and one `user_registered` row
in `events`. A second `/start` doesn't create a duplicate or log another
event.

## Don't do

Don't build an analytics system. Don't use `log_event_standalone` anywhere
except task 10.

---

# Task 3. Receiving a photo

## Create

**`app/services/images.py`**:

```python
def compress(image_bytes: bytes, max_side: int = 1500, quality: int = 85) -> bytes:
    """Resize by the long side and re-encode as JPEG.
    Honors EXIF orientation (ImageOps.exif_transpose).
    Don't upscale an image smaller than max_side."""
```

**Parameters `max_side=1500` and `quality=85` must not change.**
`photoguard`'s thresholds are calibrated against an image produced by
exactly this compression: `line_height_px` and `sharpness` depend directly
on the resolution.

**`handlers.py`** — the `F.photo` handler, steps 1–3:

1. `message.photo[-1]` — the largest version. Smaller ones are Telegram's
   thumbnails.
2. Download into memory via `bot.download`, never write to disk.
3. Compress.
4. Reply with `texts.PROCESSING` (temporary: moves in task 4).
5. Log a `note_captured` event with the payload per the contract (see
   "Contracts").

**Never save the original, neither to disk nor to the database.**

## Acceptance criterion

Photo sent to the bot → a reply comes back. `note_captured` shows the
compression, usually 5–15x.

## Don't do

Don't call the model. Don't save a record. Don't think about
`media_group_id` yet — albums are task 9.

---

# Task 4. Frame check

## Do

Drop the ready-made `photoguard.py` into `app/services/`. Don't change it.

Step 5 of the canonical order, **before any call to the model**:

```python
photo_verdict = check_photo_bytes(compressed)
await log_event(session, user.id,
    "photo_accepted" if photo_verdict.ok else "photo_rejected",
    {
        "reason": photo_verdict.reason,
        "line_height_px": photo_verdict.line_height_px,
        "sharpness": photo_verdict.sharpness,
        "paper_fraction": photo_verdict.paper_fraction,
        "contrast": photo_verdict.contrast,
    })
if not photo_verdict.ok:
    await message.answer(photo_verdict.reason)
    return
```

The variable is named `photo_verdict`, not `verdict`: starting in task 6,
the same handler gets a `verdict` variable — the string
`clean | needs_review | rejected`. Two different things with the same name
would sooner or later get mixed up.

`texts.PROCESSING` is sent **after** this block.

Metrics are logged **for every** photo, including accepted ones: this is
data for future threshold calibration.

## Acceptance criterion

A photo taken from far away or in the dark → rejected with a human-
readable message, no call to Gemini shows up in the logs.

## Don't do

Don't tune the thresholds. The values in the module are a working
hypothesis.

---

# Task 5. Recognition

## Create

**`app/services/vision.py`**. Data types:

```python
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
```

The semantics of `success`, `latency_ms`, and `cost_usd` are in the
"Contracts" section. Read it before implementing.

Functions:

```python
async def transcribe(
    image_bytes: bytes,
) -> tuple[Transcription | None, list[CallStats]]:
    """A single Gemini call. Never touches the database.
    Returns the parsed result and stats for each attempt:
    in this task there's always exactly one attempt, it becomes
    up to three in task 10.
    The first element is None on: a network error, invalid JSON,
    a schema mismatch. The stats list is always non-empty."""

async def log_ai_calls(user_id: int, stats: list[CallStats]) -> None:
    """Writes rows to ai_calls in ITS OWN session, with an immediate
    commit. Doesn't take a session — see "Transaction model."
    One row per attempt, successful or not."""
```

**Why neither `transcribe` nor `transcribe_consensus` takes a session.**
In task 6 the runs go through `asyncio.gather`, and in task 9 album pages
go through `gather` too. A single `AsyncSession` can't handle concurrent
use — SQLAlchemy would raise `IllegalStateChangeError`. So **anything
that calls the model never touches the database**, and returns its stats
upward instead.

### Calling Gemini

To avoid guessing:

```python
client = genai.Client(api_key=settings.GEMINI_API_KEY)

response = await client.aio.models.generate_content(
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
```

- the image always comes out of `compress`, so it's always `image/jpeg`
- `response_mime_type="application/json"` strips the ```json wrapper, but
  `parse_response` still has to survive it showing up anyway
- **don't lower `temperature`.** The three runs in task 6 only work
  because of the variance between samples. At temperature 0 the runs
  would come out identical, agreement would always be 100%, and the
  safeguard against hallucinations would stop working
- don't set a schema via `response_schema`: parsing and validation are
  done by our own code, which has to survive garbage regardless
- the timeout is set from the outside, via `asyncio.wait_for` — task 10

Create the client **once, at module level**, not on every call.

The prompt is the `TRANSCRIBE_PROMPT` constant, the text from
`prompts-v3.md` **verbatim**. **Don't lengthen it**: every extra rule
degrades the main task, this has been established experimentally.

### Parsing the response

A pure function with no I/O:

```python
def parse_response(raw: str) -> Transcription | None:
    """Never raises — returns None."""
```

The full table of types and fallback values is in the "Contracts"
section.

### Accounting for spend

Model `AiCall`, migration `002_ai_calls`:

```python
class AiCall(Base):
    __tablename__ = "ai_calls"
    id: int
    user_id: int | None         # FK, index
    kind: str                   # "transcribe"
    model: str
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None
    latency_ms: int
    success: bool               # not null
    error: str | None
    created_at: datetime        # server_default=now(), index
```

Cost is computed from `settings.PRICE_PER_MTOK`, tokens come from
`usage_metadata`; if they're missing — `None`, don't make numbers up.

### Wiring it into the handler

```
6.  send texts.PROCESSING
7.  result, stats = await transcribe(compressed)
8.  await log_ai_calls(user.id, stats)               # always
9.  result is None                          -> texts.ERROR_GENERIC, exit
11. markdown shorter than MIN_MARKDOWN_LEN  -> texts.NO_TEXT_FOUND, exit
    otherwise send title and markdown
```

Step 10 (the verdict) doesn't exist yet in this task, it appears in
task 6.

A message longer than 4000 characters gets cut at paragraph boundaries —
Telegram's limit is 4096.

## Acceptance criterion

Photo of a lecture note → structured text in the reply.
Photo without text → `texts.NO_TEXT_FOUND`, not a traceback.
A two-page note arrives in full, not truncated.
Exactly one row in `ai_calls` per photo.

## Tests required

`tests/test_parse_response.py` — one test per row of the parsing table
from "Contracts," plus:
- valid JSON
- JSON wrapped in ```json … ```
- invalid JSON
- empty string
- an extra `confidence` field → parsing still succeeds

Every case → `None` or a correct object. Never an exception.

## Don't do

Only one call, no retries — those are task 10.
No multiple runs — that's task 6.
Only `ai_calls` and `events` are written to the database.
Don't style the output: no markup, no buttons, no emoji.

---

# Task 6. Three runs and comparison

## Do

Drop the ready-made `consensus.py` into `app/services/`. Don't change it.

```python
@dataclass                          # not frozen: task 7 mutates verdict
class TranscriptionResult:
    best: Transcription
    text_agreement: float          # 0..1
    numeric_divergences: list      # ConsensusReport.divergences
    verdict: str                   # "clean" | "needs_review" | "rejected"

async def transcribe_consensus(
    image_bytes: bytes,
) -> tuple[TranscriptionResult | None, list[CallStats]]:
    """settings.VISION_RUNS parallel calls to transcribe()
    via asyncio.gather(..., return_exceptions=True).

    Never touches the database — collects every run's stats into
    one flat list and returns it as the second element. The handler
    is the one that logs it.

    Failed runs are discarded.
    Fewer than two successful ones -> first element None, but the
    stats list is still returned non-empty."""
```

How to compute it, verbatim:

```python
markdowns = [t.markdown for t in ok_runs]
text_agreement = consensus.compare_text(markdowns).similarity
numeric_divergences = consensus.compare(markdowns).divergences
best = ok_runs[consensus.pick_representative(markdowns)]
```

Verdict boundaries, non-overlapping:

| `text_agreement` | verdict | What to do |
|---|---|---|
| `>= 0.90` | `clean` | accept, show numeric discrepancies |
| `>= 0.70` and `< 0.90` | `needs_review` | accept, flag the whole record |
| `< 0.70` | `rejected` | don't save, `texts.REJECTED_QUALITY` |

**Never splice pieces from different runs together.** You'd end up with
text that no single model output produced, and the calculation check on
it would lose all meaning.

Numeric discrepancies are shown for any verdict except `rejected` — this
is the main payoff of the three runs. In task 8 they go into the
`Note.numeric_divergences` column.

### What changes in the handler

The `transcribe` call is replaced with `transcribe_consensus`. The
`log_ai_calls` call **stays in the handler**, its stats list is just
longer now. A second `log_ai_calls` call doesn't appear anywhere.

```
7.  result, stats = await transcribe_consensus(compressed)
8.  await log_ai_calls(user.id, stats)               # always
9.  result is None                          -> texts.ERROR_GENERIC, exit
10. result.verdict == "rejected"            -> texts.REJECTED_QUALITY, exit
11. markdown shorter than MIN_MARKDOWN_LEN  -> texts.NO_TEXT_FOUND, exit
```

The length check moves to `result.best.markdown` and happens **after**
the verdict, not before.

`verdict` at this stage is a plain variable. Only `ai_calls` and `events`
are written to the database.

## Acceptance criterion

A sharp photo of a single page → `text_agreement` above 0.9.
A notebook spread shot from far away → `rejected`, no record saved.
Exactly `VISION_RUNS` rows in `ai_calls` per photo.

⚠️ The last point holds **only up to task 10**. Once retries are added,
the number of rows equals the actual number of Gemini calls and can be
higher.

## Don't do

Don't add a verification model call that "finds discrepancies."
Established experimentally: it invents discrepancies that don't exist and
misses the real ones.

Don't do a targeted re-ask on found discrepancies — that's second week.

Don't move `log_ai_calls` inside `transcribe_consensus`.

Don't lower `temperature` for "stability" — that would break the entire
point of the three runs.

---

# Task 7. Calculation check

## Do

Drop the ready-made `mathcheck.py` into `app/services/`. Don't change it.

Step 12 — only if the verdict isn't `rejected` and the text isn't shorter
than `MIN_MARKDOWN_LEN`:

```python
report = mathcheck.check(result.best.markdown)
has_critical = any(i.severity == "critical" for i in report.issues)
if has_critical and result.verdict == "clean":
    result.verdict = "needs_review"
```

**Only `severity == "critical"` downgrades the verdict.** Not
`report.ok`: it can be `False` on warnings too, and forcing the user to
recheck the whole record over a warning would be overkill. The rest of
the issues are shown, but they don't change the status.

`clean` can become `needs_review`. There's no way back.

**After this task, `result.verdict` is considered the pipeline's final
verdict.** It's what goes into `Note.status` and into the
`note_processed` event.

Show what was found via `report.render()`. Nothing is written to the
database yet: `report.issues` is held in a variable until task 8.

Event `math_issues_found`: the count and the list of `kind` values.

## Acceptance criterion

A page with Planck's constant as `6.67·10⁻³⁴` → the bot reports the
constant was recorded incorrectly (the reference value is `6.626·10⁻³⁴`)
and suggests checking it.

## Don't do

Don't ask the model to check arithmetic.

---

# Task 8. Saving and limits

## Create

Migration `003_notes`:

```python
class Note(Base):
    __tablename__ = "notes"
    id: int
    user_id: int                # FK, index
    title: str                  # not null
    subject: str | None
    markdown: str                # TEXT
    source_type: str            # "photo" | "docx"
    page_count: int             # not null, default 1
    status: str                  # "ready" | "needs_review"
    uncertain: list             # JSONB, not null, default []
    issues: list                 # JSONB, not null, default []
    numeric_divergences: list    # JSONB, not null, default []
    unreadable_count: int        # not null, default 0
    text_agreement: float | None
    photo_sharpness: float | None
    photo_line_height: float | None
    photo_paper_fraction: float | None
    photo_contrast: float | None
    created_at: datetime         # server_default=now(), index
```

`page_count` = **the number of pages that actually made it into the
record**, not the number sent. For a single photo it's always 1.

**Serialization is required.** `Uncertain` and `Issue` are dataclasses,
JSONB won't accept them as is. Use `[asdict(x) for x in ...]`. The
structure of a `numeric_divergences` element is in "Contracts."

Where the values come from for a single photo:

| Column | Source |
|---|---|
| `title`, `subject`, `markdown` | `result.best` |
| `uncertain`, `unreadable_count` | `result.best` |
| `text_agreement`, `numeric_divergences` | `result` |
| `issues` | `report.issues` from task 7 |
| `photo_*` | `photo_verdict` from task 4 |
| `source_type` | `"photo"` |
| `page_count` | `1` |

Verdict-to-status mapping:

| verdict | Note.status |
|---|---|
| `clean` | `ready` |
| `needs_review` | `needs_review` |
| `rejected` | no record is created at all |

After saving and `consume` — the `note_processed` event (step 15). The
full event contract is in task 10 and in "Contracts"; for now, log it
with whichever fields already exist.

**`app/services/limits.py`**:

```python
async def check_limits(
    session: AsyncSession, user: User, pages: int
) -> str | None:
    """Return the rejection text from texts.py if not allowed, else None.
    Check order:
      1. settings.AI_ENABLED is off               -> texts.AI_DISABLED
      2. sum of cost_usd in ai_calls for today
         >= DAILY_COST_LIMIT_USD                    -> texts.LIMIT_COST
      3. user.pages_used_today + pages
         > DAILY_PAGES_PER_USER                     -> texts.LIMIT_PAGES

    Before the third check: if user.quota_reset_at is empty OR is
    earlier than today's (UTC) date, reset pages_used_today to zero
    and set quota_reset_at to today. An empty quota_reset_at is every
    new user, and comparing None to a date would raise TypeError.

    ai_calls rows with cost_usd = None don't count toward the sum."""

async def consume(session: AsyncSession, user: User, pages: int) -> None:
    """Increment pages_used_today. Called ONLY after the record has
    been saved successfully — step 14."""
```

**`DAILY_COST_LIMIT_USD` is a soft limit.** It's only checked before
processing starts, no budget is reserved for the current operation. So
the cap can be exceeded by the cost of one album. This is accepted
deliberately: reservation would require two-phase accounting, which
doesn't pay off for a single user.

`check_limits` is step 4, **before** the frame check and before any call
to the model. Insert it ahead of the block from task 4.

`limits.py` imports `from app.bot import texts` and returns a ready-made
string. No import cycle results. Don't invent error codes or a mapping
table.

Days are UTC everywhere.

## Acceptance criterion

The 31st page in a day → `texts.LIMIT_PAGES`.
`AI_ENABLED=false` → `texts.AI_DISABLED`, zero API calls.
A frame rejected on quality doesn't consume quota.
A brand-new user's first-ever photo (`quota_reset_at is None`) processes
without an error.

## Tests required

`tests/test_limits.py`: under the limit, exactly at the limit, over the
limit, `quota_reset_at is None`, reset on the next day, `AI_ENABLED`
disabled, cost cap exceeded, `ai_calls` with `cost_usd=None` in the
selection.

## Don't do

Limits are the same for everyone, no per-user configuration and no
pricing tiers. No `/limits` or `/stats` commands — look at the database
directly. Don't build a background job to reset the counter: it resets
lazily. Don't introduce row locking on the user — see "Known risks."

---

# Task 9. Word documents and albums

## Do

### `.docx` documents

`F.document` handler:

- extension isn't `.docx` → `texts.DOCX_ONLY`
- size over 5 MB → `texts.FILE_TOO_BIG`
- extract text via `python-docx`
- **never call the model.** In a `.docx` the text is already machine
  text: there's nothing to recognize, structure already exists. Word
  headings → markdown headings, paragraphs → paragraphs. This is pure
  code
- **`check_limits` is not called, `consume` is not called.** No money is
  spent, the model isn't invoked; with `AI_ENABLED=false` a Word doc is
  processed as normal
- `source_type = "docx"`, `page_count = 1`, `status = "ready"`,
  `text_agreement = None`, `numeric_divergences = []`, `issues = []`,
  `uncertain = []`, `unreadable_count = 0`, `photo_*` = `None`
- steps 0, 4–10, 12, and 14 are skipped (14 is `consume`: docx never
  touches the page quota, matching "`consume` is not called" above)
- step 11 still applies: an empty document → `texts.NO_TEXT_FOUND`, no
  record is created
- events `note_captured` and `note_processed` — per the `docx` contract
  (see "Contracts")

### Albums

Telegram sends an album as separate messages sharing a `media_group_id`.

**Branching right at the start of the `F.photo` handler** — step 0,
right after compression and **before** the limit check:

```python
if message.media_group_id:
    albums.add_page(message.media_group_id, PageInput(
        data=compressed,
        message_id=message.message_id,
        chat_id=message.chat.id,
        media_group_id=message.media_group_id,
        bytes_before=len(original),
        bytes_after=len(compressed),
        width=w, height=h,
    ))
    return          # steps 4-16 for the individual page do NOT run
```

The single-photo pipeline never applies to album pages, not in any part.
Compression metrics go into the buffer right away: this update's session
is about to close, and `note_captured` for the pages is logged later,
when the batch is assembled.

**`app/bot/albums.py`** — the buffer and the assembly logic:

- an in-process dict: `media_group_id -> list[PageInput]`
- wait 1.0 second after the last message in the group

⚠️ **A single owner for the batch.** Several handlers can finish waiting
for silence at the same time. After waiting, the handler **atomically
pulls the group out of the buffer** — `pop`. Only the one whose `pop`
returned a non-empty list continues processing; the others exit silently,
without replying to the user.

Without this, a single batch gets processed twice: duplicate Gemini
calls, two records, double quota debit. Don't add Redis, a queue, or any
external storage for this — `dict.pop` in a single-process app is atomic
and sufficient.

**Page order.** Before processing, the batch is sorted by `message_id`
ascending. The `page` sequence number is assigned **after sorting**,
starting at 1. This number is used everywhere: in `PAGE_SKIPPED`, in
`note_captured`, in the `page` field of `numeric_divergences`,
`uncertain`, and `issues`, and when concatenating markdown. The order
updates arrive in doesn't determine the numbering.

**Order of checks for a batch — exactly this:**

```
1. len(pages) > MAX_ALBUM_PAGES   -> texts.TOO_MANY_PAGES, exit
2. check_limits(pages=len(pages)) -> rejection: exit
3. one note_captured per page
4. reply with texts.PROCESSING (once, before gather)
5. gather over the pages
6. log_ai_calls once, on the combined stats
7. assemble the record, save, consume, note_processed
```

Size is checked **before** limits: it's a shape-of-request check, not a
spend check. An 11-page album gets `TOO_MANY_PAGES` even with the quota
exhausted.

**Page processing:**

- in parallel via `asyncio.gather(..., return_exceptions=True)`
- for each: `check_photo_bytes`, then `transcribe_consensus`
- ⚠️ **`log_ai_calls` is called once, after `gather`**, on the combined
  stats of all pages. Not inside per-page processing

**A single semantics for a page rejection.** A page is skipped if any of
the following happens:

| Reason | What goes in `PAGE_SKIPPED` |
|---|---|
| the frame failed `photoguard` | `photo_verdict.reason` |
| `transcribe_consensus` returned `None` | "couldn't recognize" |
| `verdict == "rejected"` | "recognition runs diverged" |
| markdown shorter than `MIN_MARKDOWN_LEN` | "no text found" |
| timeout, exception, any other error | "processing error" |

**One page's failure doesn't cancel the rest.** That's exactly why
`gather` is called with `return_exceptions=True`: an exception turns into
a `PAGE_SKIPPED`, and the batch keeps going. If instead the overall album
timeout fires and the remaining pages' results can't be retrieved,
`log_ai_calls` gets whatever stats were collected up to the cancellation.

A skipped page: doesn't count toward `page_count`, doesn't count toward
the aggregates, doesn't consume quota, doesn't cancel the `Note` because
of it, `note_failed` is not written. The reply includes `texts.PAGE_SKIPPED`
with the page number and the reason.

If **not a single** page passes → `texts.REJECTED_QUALITY`, no record is
created, no quota is debited.

**Record fields for an album** — computed only from successfully
processed pages:

- `text_agreement` = the minimum over the processed pages. If only one
  was processed — its own value, unadjusted
- every `photo_*` = the minimum over the processed pages
- `status` = `needs_review` if at least one processed page gave
  `needs_review`; otherwise `ready`. Skipped pages don't participate in
  this
- `uncertain`, `issues`, `numeric_divergences` — concatenated, each
  element gets a `page` field added
- `unreadable_count` = the sum over the processed pages
- `markdown` — concatenated via `\n\n---\n\n`, in `page` order
- `page_count` = the number of successfully processed pages
- `consume(pages=page_count)` — for pages actually processed, not sent

**Concurrency cap.** In `vision.py`, a module-level
`asyncio.Semaphore(10)`, wrapped around every Gemini call. Without it, an
album fires 30 simultaneous requests (with task 10's retries — up to 90),
Gemini responds with 429s, and retries multiply them further. Three lines
of code, not a queue; don't add anything beyond the semaphore.

## Acceptance criterion

Three photos sent as one album → one record made of three pages, not
three records. The user gets one `PROCESSING`, not three.
An album where the second page is blurry → a record made of two pages,
the reply says page 2 was skipped, quota debited for 2.
An 11-page album with the quota exhausted → `TOO_MANY_PAGES`, not
`LIMIT_PAGES`.
`.docx` is saved without a single model call, even with `AI_ENABLED=false`.

## Don't do

No other formats: no PDF, no `.doc`, no `.txt`, no photos sent as a
document. All of those get a polite rejection.
Don't extract images or tables from `.docx`: text and headings only.
Don't move the album buffer to Redis and don't make it survive a restart.

---

# Task 10. Reliability

## Do

**Retries** inside `transcribe()`: up to three attempts, pauses of 1 and
2 seconds between them (three attempts — two pauses).

**The loop stops as soon as the first attempt succeeds.** The remaining
ones don't run.

Error classification — complete, so nothing is guessed:

| Retry | Don't retry |
|---|---|
| `asyncio.wait_for` timeout | 400, 401, 403, 404 |
| connection dropped, reset, DNS failure | any parsing or schema error |
| 408, 429 | empty model response |
| any 5xx | |
| SDK error with no HTTP code | |

Rule for an unknown error: **if it's unclear whether it's transport-level
or logical — don't retry.** An extra call costs money, an extra rejection
costs one tap of a "try again" button.

⚠️ Retries multiply with the runs: 3 runs × 3 attempts = up to 9 calls per
page. So:
- retries happen only inside `transcribe()`, **not** around
  `transcribe_consensus()`
- every attempt is returned in the `CallStats` list and makes it to
  `log_ai_calls`
- the semaphore from task 9 is shared across every attempt of every run

**Timeouts:**

| What | How long | Why that much |
|---|---|---|
| one model call | 30 s | typical response ~6 s |
| `transcribe_consensus` | 120 s | 3 attempts × 30 s + 1 and 2 s pauses = 93 s, plus margin |
| a whole album | 300 s | covers the worst case across 10 pages |

The consensus timeout must be greater than the worst case of a single run
with retries, otherwise it would cut processing short before the retries
themselves finish.

The album timeout must cover the worst-case page schedule under
`Semaphore(10)`: for 10 pages at 3 runs each, that's three waves of up to
93 seconds each, i.e. up to 279 seconds. **300 seconds is a normative
value, not an approximation**, and it must not be lowered.

**aiogram's global error handler**: any unhandled exception → the user
gets `texts.ERROR_GENERIC`, details go to the log with a traceback. **Not
a single traceback reaches the user.**

The `note_failed` event is written **via `log_event_standalone`**: the
main transaction is already rolling back at this point, and a regular
`log_event` would disappear along with it.

**Events** `note_processed` and `note_failed` — per the contract (see
"Contracts").

**`GET /health`** gets an added database connectivity check: return 503
when the DB is unreachable.

## Acceptance criterion

Swap `GEMINI_API_KEY` for an invalid one → the bot apologizes with a clear
message, doesn't go silent, doesn't crash. The logs show the real cause.
Rows appear in `ai_calls` even for a completely failed processing run.
A `note_failed` event exists in the database after an unhandled
exception.

## Don't do

Don't wire up Sentry or external monitoring: Railway's logs are enough.
Don't build a circuit breaker, don't add exponential jitter — three
attempts with fixed pauses cover everything that happens with a single
user.
Don't rewrite previous tasks' code in the name of reliability.

---

# Task 11. Reading the corpus

## Create

`app/bot/corpus.py` with its own `Router`: every command that reads or
changes an existing record lives there. `handlers.py` keeps capture — photo,
document, `/start`, the catch-all — and is not touched.

**Router order in `main.py` is load-bearing.** `handlers.router` ends with a
filterless catch-all that matches every message, so a router included after
it never receives anything:

```python
dp.include_router(corpus.router)    # commands first
dp.include_router(handlers.router)  # capture, and the catch-all last
```

## Do

`/notes` — the last 10 records of **this user**, newest first:

```
#42 · 14.09 · Производная сложной функции · матан · 3 с.
#41 · 13.09 · Интегрирование по частям · матан · 1 с. · нужна проверка
```

`id`, `created_at` as `DD.MM`, `title`, `subject` (omitted when `None`),
`page_count`, and the words `нужна проверка` when `status == "needs_review"`.

An empty corpus gets `texts.CORPUS_EMPTY`, not an empty list. `/notes 2`
shows the next ten; a page past the end says so rather than replying with
nothing.

`/note 42` — the whole record: title, then markdown through the existing
`_split_message`, then the record's flags (`needs_review`, `issues`,
`numeric_divergences`, `uncertain`) rendered by the same `texts` helpers the
capture path already uses. Reuse that rendering, don't write a second one.

**Every query filters by `user_id`.** One user today is not a reason to write
a query that returns someone else's record tomorrow. A foreign or missing id
is answered with `texts.NOTE_NOT_FOUND` — identical answers, because there is
nothing to gain from revealing that a record exists.

Events: `corpus_listed` with `page` and `shown`; `note_opened` with `note_id`.

## Acceptance criterion

Three photos sent, `/notes` lists three records, and `/note <id>` of the
middle one returns the text the bot replied with when it was created.

## Don't do

No inline buttons, no pagination state, no editing — that is task 13.

---

# Task 12. Search

## Do

`/search производная` — over `title` and `markdown` of this user's records.

PostgreSQL full text with the `russian` configuration, computed in the query,
with no stored column and no index:

```python
vector = func.to_tsvector("russian", Note.title + " " + Note.markdown)
condition = vector.op("@@")(func.plainto_tsquery("russian", query))
```

**Why not `ILIKE`.** Russian morphology. `ILIKE '%производная%'` does not
match «производной», and a search that misses the declined form of the word
you just typed is not a search. `to_tsvector` stems both sides.

**Why no index.** A GIN index needs a generated column and a migration, and a
sequential scan over one student's corpus is instant. Add the index when the
corpus makes it necessary, not in advance.

Results render exactly as `/notes` renders them, capped at 10, ordered by
`ts_rank` descending. Nothing found → `texts.SEARCH_EMPTY` naming the query.
`/search` with no argument → `texts.SEARCH_USAGE`.

Event `corpus_searched`: `query`, `found`. The query text is stored: with one
user there is no privacy cost, and what you search for is the most direct
signal of what the corpus is actually for.

## Acceptance criterion

A record containing «производной сложной функции» is found by
`/search производная`.

## Tests required

That declension case, against a real PostgreSQL. SQLite has no `to_tsvector`,
so the test is skipped without `TEST_DATABASE_URL`, the same way
`test_spend_survives_main_rollback` is.

## Don't do

No ranking tuning, no `ts_headline` snippets, no searching inside `uncertain`
or `issues`, no stored tsvector column.

---

# Task 13. Correcting records

## Do

Two operations — the ones that repair real damage to the corpus.

`/retitle 42 Производная сложной функции` replaces `title`. Titles are
derived automatically and are often wrong, and a wrong title makes a record
unfindable by eye. Capped at 60 characters, as everywhere else.

`/delete 42` deletes the record. A page shot badly enough to produce a
plausible retelling is worse than no record at all, and the corpus is the
product: taking garbage out of it has to be possible.

Deletion is immediate, with no confirmation. A confirmation step needs either
inline buttons or a second command, and for one user re-photographing a page
costs less than that machinery.

Both reply with the record's title, so it is visible what was affected. Both
filter by `user_id`. A missing or foreign id → `texts.NOTE_NOT_FOUND`.

Events: `note_retitled` with `note_id`; `note_deleted` with `note_id`,
`title`, `page_count`. The row itself is gone afterwards, so anything worth
keeping about it has to live in the event.

## Acceptance criterion

`/retitle` changes what `/notes` shows. `/delete` removes the record from
`/notes` and from `/search`, and `note_deleted` remains in `events`.

## Don't do

Don't edit `markdown`. Don't add FSM or any conversation state. Don't
soft-delete — no `deleted_at` column, no filtering of dead rows in every
query from now until forever. The row goes.

---

# Task 14. Statistics

## Do

`/stats` — what the corpus has come to:

```
12 записей, 27 страниц
Первая — 18 августа, последняя — сегодня
Подряд: 4 дня
```

Over this user's `notes`: row count, `SUM(page_count)`, `MIN(created_at)`,
`MAX(created_at)`. The streak counts consecutive UTC days back from today —
or from yesterday when nothing has arrived yet today. A counter that read
zero every morning until you posted would be noise rather than a signal, so
the streak breaks only once a whole day passes with nothing.

Empty corpus → `texts.STATS_EMPTY`. Event `stats_viewed`, no payload.

## Why this belongs in the week

The stage question is whether the author uses this daily, and the stated core
value is the accumulated corpus. Both are invisible while the only way to see
the pile is to query the database by hand. `/stats` makes accumulation
visible, and visible accumulation is what is supposed to make leaving costly.

## Acceptance criterion

Records on three consecutive days give a streak of 3; skipping yesterday
gives 1.

## Don't do

No charts, no per-subject breakdown, no cost or token figures — `ai_calls` is
for psql, not for a user-facing screen.

---

# Definition of week-2-ready

- [ ] `/notes` lists the corpus, newest first, with paging
- [ ] `/note <id>` returns a record in full, flags included
- [ ] `/search` finds a record by a declined form of the word
- [ ] Every corpus query filters by `user_id`
- [ ] A foreign id is indistinguishable from a missing one
- [ ] `/retitle` and `/delete` change what `/notes` shows
- [ ] `note_deleted` outlives the record it describes
- [ ] `/stats` counts records, pages and the streak
- [ ] Commands answer on an empty corpus without an error

---

# Contracts

Everything that would otherwise have to be guessed lives here. **For any
dispute about types, boundaries, and semantics — the answer is here.**

## `CallStats.success`

`success = True` **only if the attempt produced a usable
`Transcription`**: the API responded, the JSON parsed, the schema
matched.

| Situation | `success` | `cost_usd` | Retry |
|---|---|---|---|
| API 200, parsing succeeded | `True` | filled in | no, the loop ends |
| API 200, invalid JSON | `False` | **filled in** | no |
| API 200, schema didn't match | `False` | **filled in** | no |
| API 429 / 5xx / timeout | `False` | `None` | yes |
| API 400 / 401 / 403 | `False` | `None` | no |

Key point: **cost is always recorded when the model responded** — the
tokens were burned regardless of whether we understood the response.

One attempt = one network call to Gemini plus all the parsing that
follows it.

## `latency_ms`

Measured with **a single monotonic timer** (`time.monotonic()`) over the
relevant interval. **Don't sum `CallStats.latency_ms` values:** under
parallel execution the sum isn't the real elapsed time.

| Where | Interval |
|---|---|
| `CallStats` | one attempt: from the start of the network call to the end of parsing its response |
| `note_processed`, photo | step 7 → end of step 15 |
| `note_processed`, album | start of `gather` → end of save and `consume` |
| `note_processed`, `.docx` | text extraction |

## `cost_usd`

- only values other than `None` are summed
- if **all** the terms are `None` — the result is `None`, not zero
- if at least one is known — the result equals the sum of the known ones
- for `.docx` — always `None`, there were no calls
- for an album — the sum over every actual call, including retries and
  failed runs

## `numeric_divergences`

`ConsensusReport.divergences` — a list of `Divergence` objects:

```python
position: int                # sequential index of the numeric position
variants: dict[str, int]     # value -> how many runs produced it
context: str                 # the source text of the number
```

`asdict` is what goes into JSONB. For an album, each element also gets a
`page: int` — the page's sequence number after sorting, starting at 1.

## Empty markdown

The length check is done **after `.strip()`**:

```python
len(markdown.strip()) < settings.MIN_MARKDOWN_LEN
```

A string made only of whitespace and newlines counts as empty. The same
rule applies to a single photo, album pages, and `.docx`.

## `parse_response`: field types

A wrong type doesn't fail the parse — a fallback value is used instead.

| Field | Expected | Wrong type or missing |
|---|---|---|
| `markdown` | non-empty string | → **`None` for the whole record** |
| `title` | string | first 60 characters of the first non-empty line of `markdown`; if that's empty too — `"Untitled"` |
| `subject` | string | `None` |
| `margin_notes` | list of strings | `[]`; non-string elements are dropped |
| `numeric_tokens` | list of strings | `[]`; non-string elements are dropped |
| `unreadable_count` | integer | `0`; a numeric string is coerced, otherwise `0` |
| `uncertain` | list of objects | `[]` |
| `uncertain[].text` | string | **the element is dropped** |
| `uncertain[].where` | string | `""` |
| `uncertain[].why` | string | `""` |
| `uncertain[].alternatives` | list of strings | `[]` |

`uncertain`'s element has exactly one required key — `text`. An element
without it is dropped silently, the whole response isn't discarded.

Extra fields are ignored. Prompt v3 returns `confidence` — deliberately
unused: the model's self-assessment turned out to be a useless signal.

## `PageInput`

Album buffer fields: `data`, `message_id`, `chat_id`, `media_group_id`,
`bytes_before`, `bytes_after`, `width`, `height`.

`media_group_id` is stored on every page and used when building
`note_captured`. It's the same across every page of one batch.

## Event `note_captured`

| Source | payload |
|---|---|
| photo | `bytes_before`, `bytes_after`, `width`, `height`, `source_type: "photo"` |
| album page | same, plus `page`, `media_group_id`; logged when the batch is assembled, not on receipt |
| `.docx` | `bytes_before`, `source_type: "docx"` |

For `.docx` there are no `bytes_after`, `width`, or `height` fields,
because the document doesn't go through image compression. Don't
fabricate values for them.

## Event `note_processed`

Written **once, after steps 13 and 14 succeed** — i.e. after the `Note`
is saved and `consume` succeeds, but **before** the final reply is sent
to the user. The event means processing of the record finished
completely.

It's transactional: committed together with the `Note` and the quota
change, in the main session. On any normal rejection (steps 4, 5, 9, 10,
11) it isn't written.

| Field | photo | album | `.docx` |
|---|---|---|---|
| `verdict` | final, after task 7 | see below | `"clean"` |
| `latency_ms` | steps 7→15 | `gather`→save | text extraction |
| `cost_usd` | sum of attempts | sum over every page | `None` |
| `page_count` | `1` | processed pages | `1` |
| `source_type` | `"photo"` | `"photo"` | `"docx"` |
| `pages_skipped` | — | number skipped | — |

**`verdict` for an album** is computed only from successfully processed
pages: if at least one gives `needs_review`, the result is
`needs_review`; otherwise `clean`. Pages skipped due to `photoguard`,
`transcribe_consensus == None`, `rejected`, short markdown, or a
processing error don't participate in this.

## Event `note_failed`

Written **only on an unhandled exception**, from the global handler, via
`log_event_standalone`.

Normal rejections — a limit, `AI_DISABLED`, a bad frame, `rejected`,
`NO_TEXT_FOUND`, an album page skip — **are not `note_failed`**. They're
already reflected in their own events and in the reply to the user.

payload: `{"reason": <exception type>, "where": <handler name>}`.

## Testing boundaries

Required: the tests from tasks 5 and 8, plus exactly three integration
tests for the mechanisms where a bug costs real money:

1. **Retry.** `429`, then success → two `CallStats` elements and two rows
   in `ai_calls`.
2. **Batch ownership.** Two concurrent handlers with the same
   `media_group_id` process it exactly once.
3. **Independence of spend.** Rolling back the main transaction doesn't
   remove already-committed `ai_calls`.

Nothing else: not on consensus, not on album assembly, not on the
middleware, not on the webhook. A deliberate scope limit for the first
week.

---

# Known risks

Found, discussed, left as is. **Don't fix on your own initiative** — if
one of these actually bites, it becomes its own task.

**Processing happens inside the webhook request.** `POST /webhook`
replies to Telegram with 200 only after `feed_update` finishes, and that
can take up to 120 seconds for a photo and up to 300 for an album.
Telegram considers an update undelivered after roughly a minute and
resends it — which produces a second round of processing for the same
photo: extra Gemini calls and a second quota debit. The tell: two
identical `notes` rows a minute apart and doubled `ai_calls`. Fixed by
deduplicating on `update_id` or by replying 200 before processing — a
separate task, at the user's discretion.

⚠️ **This risk is amplified for albums.** The atomic `pop` protects
against two handlers within a single delivery, but redelivered pages
arrive as new messages and will assemble into a new batch under the same
`media_group_id` — one the first handler already took. An album that
takes 300 seconds is guaranteed to be resent by Telegram. Same tell:
duplicated records and spend. Accepted deliberately for the first week.

**A race between checking and debiting the quota.** `check_limits` reads
`pages_used_today`, `consume` increments it, and there are seconds of
model work in between. Two parallel processing runs for the same user
could both pass the check and both debit the quota. Row locking isn't
introduced deliberately: for a single user, the cost of the bug is one
extra page counted.

**The cost limit is soft.** `DAILY_COST_LIMIT_USD` is only checked before
processing starts, no budget is reserved. The cap can be exceeded by the
cost of one album — at current prices, that's cents.

**The album buffer lives in the process's memory.** Railway restarts the
container — an unfinished batch is silently lost. Redis doesn't pay off
for a single user.

---

# Definition of week-ready

- [ ] `/start` replies from the deployed version
- [ ] Photo → structured text
- [ ] A bad frame is rejected before the model is called
- [ ] Three runs are compared, numeric discrepancies are shown
- [ ] Calculation errors are found and shown
- [ ] Limits work; `AI_ENABLED=false` blocks AI-dependent paths,
      `.docx` keeps working without Gemini
- [ ] An album produces one record and one `PROCESSING`
- [ ] Exactly one handler owns an assembled batch
- [ ] The album timeout is 300 seconds
- [ ] `ai_calls` survive a rollback of the main transaction
- [ ] `note_processed` is written only after `Note` and `consume`
- [ ] Not a single traceback reaches the user
- [ ] Events are logged from day one
- [ ] Frame metrics are saved for calibration

---

# Backlog. Don't implement or suggest

- A Mini App or any interface other than the bot
- Flashcards, spaced repetition
- A targeted re-ask to the model about found discrepancies
- Video, lecture transcription
- Payments, subscriptions
- Export to any format
- Styling and design of responses
- Caching, queues, workers, Redis
- Deduplication on `update_id`
- Row locking, two-phase spend accounting
- Docker, CI
- End-to-end tests of the photo and document handlers — the unit
  suite was extended by decision, these were left out on purpose
  (see `CLAUDE.md` → Tests)
