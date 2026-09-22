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

This is a product meant for **many users**. It runs for one today, and the
stage governs what gets built, but "there is only one user" is never a reason
a design is correct — when a shortcut only breaks under concurrency, say so
and record it under "Scale debt" rather than calling it done.

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

Don't add dependencies without an explicit need. Redis, queues, workers,
Docker and CI stay out for now — not because the product is single-user, but
because the second user hasn't arrived. See "Scale debt" for what that
postpones and what it costs.

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

2. **Compress the image before sending it to the model.** `IMAGE_MAX_SIDE`
   and `IMAGE_QUALITY`, 1500 px and 85. A full-size phone photo costs several
   times more with no gain in accuracy — which, like the prompt ceiling, is
   evidence about a retired model. The numbers are settings now so that
   claim can be measured against the same album instead of argued about; the
   defaults do not drift.

3. **Never store the original photos.** Only the recognized text.

4. **Every model call is written to `ai_calls`** — model, tokens, cost,
   latency, success, error. No exceptions.

5. **Every significant action is written to `events`.** Retention can't be
   computed after the fact.

6. **Limits are checked before the model call, not after.**

7. **Never trust JSON from the model.** Always validate the schema, always
   handle garbage input. The parsing function never raises — it returns
   `None`. When it does, the `ai_calls` row names the response's own
   `finish_reason`: `MAX_TOKENS` means we truncated the answer at
   `max_output_tokens` and the JSON ends mid-string, `STOP` means the model
   finished and simply did not return JSON, `SAFETY` means it refused. Three
   different problems that used to arrive as one sentence.

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
**Don't lengthen `TRANSCRIBE_PROMPT`.** That is a budget, not a wall: 250
words is the length that was proven to work, and `prompts-v3.md` is at
**245**. Count the words after every edit.

**That ceiling did not hold, and it was measured, not argued.** The finding
is evidence about `gemini-2.5-flash-lite`; this runs on
`gemini-3.5-flash-lite`, the case where a fresh reproduction outranks the
note. `prompts-v4.md` went against the same four-page album at 310 words:

| | v3, 242 words | v4, 310 words |
|---|---|---|
| lowest `text_agreement` | 0.783 | **0.828** |
| median | 0.862 | **0.907** |
| pages needing review | 3 of 4 | **2 of 4** |

Every order statistic improved — the distribution moved, not one lucky page.
Rule 8 was the one to watch: joining lines that continue a sentence is the
only rule that touches the text rather than its markup, and a model that
joins tends to tidy while it joins. `text_agreement` measures exactly that,
and it went up.

Read it for what it is. One album, four pages, and Gemini was returning 503s
through the second run. It does not establish a new ceiling — it removes the
old one as a reason not to try. `prompts-v4.md` is at 321 words now; measure
again before going much past it, and count with `PROMPT_WORDS` from the
startup log, because `wc -w` reads three words more than `str.split`.

**Read the mean, not the minimum.** v4 was run twice on the same album. The
mean agreement came back 0.902 and 0.903; the lowest page moved 0.828 → 0.807
and the median 0.907 → 0.9125. So the per-page minimum wobbles by about 0.02
between two runs of the *same* prompt, while the mean reproduces to a
thousandth. The v3 → v4 shift was 0.854 → 0.902 of the mean — five times the
spread the instrument shows at rest. Compare means; the minimum is the noisy
one and the first table above led with it.

**`prompts-v5.md` asks the question the length test did not.** Of v4's 321
words, some 86 are about how the page should look: headings, bold terms,
display formulas, sub-headings on definitions, lists only where lists are,
lines joined into paragraphs. The total length turned out survivable; whether
those particular rules cost reading accuracy was never measured. v5 is v3 with
every one of them removed — 235 words, shorter than v3 — keeping rule 6,
because a graph as an edge list is extraction, not presentation, and it is
what feeds `graphcheck`.

A record made with v5 will look flat: no headings, no bold, nothing set on its
own line. That is the point, not a defect. It measures reading alone, and
formatting would belong to a second pass over the trusted text.

**A verification model call doesn't work.** The request "compare the
transcription with the photo and find discrepancies" invented a
discrepancy that didn't exist, duplicated it three times, and found none
of the real ones. **Don't add a verification pass with the model.**

**Agreement between independent runs works.** Three runs of the same short
prompt, results compared by code. Where they agree, trust it; where they
diverge, flag it. This is the only uncertainty signal that has turned out
to be reliable.

**There are two agreement numbers now, and they answer different questions.**
`text_agreement` compares the markdown, so it moves when a prompt changes how
a page is *laid out* rather than how it was *read* — that is the confound that
made the v5 measurement unreadable, and it would make a two-stage run
incomparable with a one-stage one. `vision.numeric_agreement` compares the
runs' `numeric_tokens` sequences instead. A number has no layout.

Read it across the arms of one experiment, never against a threshold: a page
of matrices is hundreds of numbers drawn from a handful of digits, a
repetitive sequence has many equally good alignments, and the absolute value
runs low on exactly the pages the measure was made for. `difflib`'s autojunk
heuristic is off for the same reason — left on, it calls the common digits
noise and reports four changes in four hundred as total disagreement.

**The model's self-assessment is useless.** The `confidence` field gave
0.95 on a page with three errors. That's why it's not in the schema.
`unreadable_count: 0` is likewise not a sign of quality.

**`uncertain` is a complaint, not an ambiguity.** The prompt asks for places
where a symbol "действительно читается двояко". One album came back with seven
entries and not one named a second reading: "слово обрезано краем страницы",
"написано на полях", "частично смазано" — the state of the paper, and in one
case a word that had been read in full. `vision.meaningful_uncertain` enforces
the prompt's own test in code, because stating it in the prompt did not work:
an entry that cannot name an alternative is not an ambiguity, and one whose
text already carries `[неразборчиво]` is a mark that stands in the record
itself, in place.

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

   **Each row names its own model.** `CallStats` carries `kind` and `model`,
   and `log_ai_calls` writes what the stats say rather than reading
   `settings.VISION_MODEL`. A second stage on another model would otherwise
   be recorded and priced as the first one, and rule 4 would stop holding
   with nothing failing to show it.

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
step 10 and never reaches the database.

Two findings downgrade `clean` → `needs_review`, both one way only. A critical
`mathcheck` issue does it in the handlers — a warning is shown but leaves the
verdict alone. A surviving **numeric divergence** does it in
`transcribe_consensus`, where the divergences are computed and filtered, so
the rule lives in one place rather than in both capture paths.

The second one exists because `text_agreement` cannot see what it is for. Two
runs reading a matrix cell as 6 and as 8 differ by one character, which barely
moves the agreement, so the page comes back `clean` with the disagreement
sitting in it — that happened twice in one evening's logs. And of everything a
record carries, a number is what a reader can least check afterwards: a
sentence that makes no sense gets caught on re-reading, a wrong digit looks
exactly as authoritative as a right one. What makes it safe to act on is
`vision.meaningful_divergences`: before that filter a single page of notes
produced eight divergences of which one was genuine, and every record would
have worn the flag.

**The webhook answers before it works.** Telegram delivers the updates of one
chat **strictly in sequence** — it does not send the next until the current
request ends; updates from different chats are already concurrent. Processing
a photo takes about nine seconds, so handling an update inside the request
stops that chat from sending anything else, and an album can never assemble:
its later pages do not exist for us yet. `telegram_webhook` schedules the work
and returns immediately. **Never `await` the processing of an update inside
the endpoint.**

**An album is owned by exactly one update.** Telegram delivers an album as
separate messages sharing a `media_group_id`, each its own webhook update
with its own session. `albums.collect()` waits for the group to go quiet and
hands the whole batch to a single caller; every other caller gets `None` and
**must return without replying**. Reply there and the album gets processed
once per page.

Telegram never says how many items a media group holds, so "the album has
ended" can only ever be a guess at silence. **Register a page with
`albums.announce` the moment its update arrives, before downloading it**, and
call `add_page` with the bytes afterwards. The debounce times the
announcements, which Telegram delivers milliseconds apart; a batch closes only
once it has also downloaded every page it was told about.

Announcing after the download instead times our own network speed, and no
value of `_QUIET_SECONDS` survives that — the first page to finish fetching
claims the batch while the rest are still in flight, and each of them then
opens a record of its own. That failure happened twice on the deployed bot: a
four-page album came back as four records, each with its own reply, its own
PDF and its own three paid recognition runs.

**Router order in `main.py` is load-bearing.** `handlers.router` ends with a
filterless catch-all that matches every message, so any router included after
it receives nothing. `corpus.router` is included **first**, capture second.
Adding a third router means deciding where it goes relative to that catch-all.

**A saved record goes out as a PDF.** Recognised notes are dense with LaTeX,
and `$\sum_{i=1}^{p} \rho(v_i) = 2q$` reads as noise until it is drawn, so all
three capture paths finish by calling `corpus.send_record`. Rendering is
CPU-bound and runs in a thread; if it fails for any reason the record is sent
as plain text instead. A record is never lost over its presentation.

**mathtext is not LaTeX.** matplotlib rejects `\limits`, `\nolimits`,
`\displaystyle`, `\mbox` and every matrix environment outright, and a formula
it rejects is printed as its own source. That is not hypothetical:
`\sum\limits_{i=1}^p` went out on a deployed record as raw backslashes while
the same sum written `\sum_{i=1}^p` drew perfectly two pages later.
`pdf.for_mathtext` drops the commands that either do nothing to the layout or
have a synonym mathtext knows. It cannot rescue `\begin{pmatrix}` — a matrix
has to arrive as a markdown table to be drawn at all.

The expensive half of that is `pdf._SYNONYMS`. LaTeX spells nine common things
two ways and mathtext knows only one of each; the model writes the other. `\le`
and `\ge` cost a whole record — every inequality on a page about nested
intervals went out as raw source while the formulas around them drew. The same
boundary applies as to `\limits`, for the same reason: `\le` opens `\leq`,
`\left` and `\leftarrow`, so a command ends where its letters end.

**A drawing comes back as data, not a sentence about itself.** Rule 6 of
`prompts-v3.md` asks for a graph as `[граф: 1-2, 2->3, 3-3]` and for a matrix
or table as an ordinary markdown table; `pdf.blocks()` turns both into
pictures, and `[схема: ...]` still carries everything that is neither. The two
sides are one contract in two files: change the syntax on either and the
record still renders, it just prints the spec where the drawing should be.

Asking for the structure of a drawing asks the model to **interpret**, which
is what it is worst at — and a wrong edge looks exactly as authoritative as a
right one. Rule 6 forbids adding edges it cannot see, and `parse_graph`
refuses anything that doesn't read as vertices, but nothing yet compares the
three runs against each other the way numbers are compared. Recorded under
`PLAN.md` → Known risks.

**A generic flag gives way to a specific one.** "Прогоны распознавания
местами разошлись" above a list of exactly what diverged repeats that list's
own heading. Both `corpus._flags` and `corpus._callouts` add it only when
nothing more exact is there to say; the subtitle of the document carries
"нужна проверка" either way.

**A record is all its pages or none of them.** A page that could not be read
used to be named in the reply and left out, and the record went into the
corpus regardless — reading as a whole one, with nothing in it to say which
page is missing. An album with any skipped page now saves nothing, writes
`album_incomplete`, and names the pages to photograph again. The pages that
*were* recognised are still charged against the daily quota: the model calls
behind them were made and billed, and that rule did not change.

**A callout says what we already know, never what the model thinks.** The
tinted boxes at the top of a record — needs review, arithmetic that doesn't
add up, numbers the runs read differently, spots read two ways — are built by
`corpus._callouts` out of the `Note`'s own columns, through the same three
readers `_flags` uses for the message, so the document and the chat cannot
come to disagree. `pdf.py` receives a list of `Callout` and knows nothing
about where a record came from.

What that forecloses is worth naming, because it will be asked for. A box
headed "what this topic is about" or "the main points", written by the model
from the photograph, is the exact shape of the failure recorded above under a
bad shot: fluent, confident, and indistinguishable from the real thing. If
that text is ever wanted, it belongs in a second call over the **transcription
already trusted**, in a column of its own, marked as machine-written on the
page — never in the call that reads the photo.

**Reading and composing are two jobs with opposite requirements, and they are
two calls.** Sort the failures recorded above into the ones where the model
*misread* something and the ones where it *interpreted*: a semicolon read as a
letter and a digit in a hand-drawn matrix are perception; the fluent retelling
of a distant photograph, "possibly a typo by the author", the silently fixed
arithmetic, the invented discrepancy, `confidence: 0.95`, and `uncertain` as a
complaint about the paper are all the interpretive faculty leaking into the
literal job. Six of eight. We fought that with words in the prompt — "не
пересказывай", "не дополняй", "не исправляй" — and every such word also steals
attention from the reading.

So `compose.py` is a second call over the text the runs already agreed on, and
it **never receives the photograph**. That is the point, not an implementation
detail: the worst failure this project has reproduced needs an image to invent
from, and there is none. The stage's own job — heading levels, bold terms, a
formula on its own line, a run of lines into a list — is transformation, which
is what a model is good at.

What makes it safe to ship is that its output is checked against its input **by
code**. CLAUDE.md records that a verification model call does not work, and
that finding stands: *that* call compared text against a photograph, which is
perception again, and it invented a discrepancy. These guards compare text
against text. The multiset of numbers must be identical, list markers stripped
first because rule 8 lets the composer renumber a list; the count of
`[неразборчиво]` must be identical; the document must not come back materially
shorter. Any of those, and the record is the one stage one produced. Off,
refused, or failed, the worst case of the stage is the pipeline without it.

Word drift is **measured and not refused on**, deliberately. Rule 6 of
`prompts-compose-v1.md` asks for `### Определение` over a definition, so the
stage is *required* to write a word the page does not carry; a word guard would
refuse the prompt's own instruction. The count goes into the log and the
`note_processed` payload so the size of that liberty can be seen before anyone
decides what to do about it.

This is the same second call the paragraph above anticipated, spent on markup
rather than on commentary. **Commentary is still not built.** A box explaining
the mathematics would also belong here rather than in the reading call, and it
would still have to be marked as machine-written on the page.

**The matrix is checked against the graph, by code.** The uncertainty a
record carries is not spread evenly: of six numeric divergences in one album,
five sat on the single page with two hand-drawn matrices, and every one of
them was a single digit. Whether a cell is 0 or 1 is not a matter of opinion
and not something a lookup can settle — the edges of the graph beside it
decide. `graphcheck.check` computes the adjacency from the edge list and
compares, and checks an incidence matrix the only way its unknown column
order allows: every column holds the two ends of one edge, every row sum is a
degree.

It returns `mathcheck.Issue`, so the findings ride the record's existing
`issues` column, callout and critical → needs_review downgrade rather than
opening a second channel for the same kind of finding. It parses with
`pdf.blocks` and `pdf.parse_graph` — the same two functions the drawing goes
through — so the check and the picture see one structure by construction.

The half that matters more is when it stays quiet. A cycle has as many edges
as vertices, and then a square table reads as either matrix with equal force;
nothing on the page settles it, so nothing is said. Same for labels that
don't match the vertices, and for a bare matrix of *named* vertices, where
the row order cannot be known. A confident wrong "does not agree with the
graph" costs more than a check that said nothing.

**A remark sits beside the line it explains.** `uncertain` — what was read,
on which page, and why it was ambiguous — used to be a list at the top of the
document. That said what was doubtful without saying where, and by the time a
reader reached the text they had forgotten it. `corpus._remarks` turns each
entry into a `pdf.Remark` anchored on the text that was read, and `render`
sets it under whichever block contains that text; one that anchors nowhere
goes to the end rather than nowhere.

The reference document the author works from does the same and goes further:
every addition of its own sits in a marked box, and a box about a reading
says what the manuscript actually had — *"в рукописи матрица плохо читается
…, поэтому она восстановлена по рисунку графа"*. That is the standard.
**Adding is not forbidden; adding unmarked is.** The `uncertain` remarks are
the first half of it, built from data already collected. The second half —
commentary on the mathematics — is not built, and when it is, it comes from a
separate call over the trusted transcription.

**`.docx` bypasses the model entirely.** No limits are checked and no quota
is spent, so a Word file is still processed with `AI_ENABLED=false` — it is
already machine text. Only the empty-text gate (step 11) still applies.

---

## Concurrency ceilings

**One of these is a setting; two are computed from it.** That arithmetic used
to live in comments across two files, where raising one number on its own left
the other two quietly cutting the work short:

| Constant | Where | Value |
|---|---|---|
| `API_SLOTS` | `services/vision.py` | `10` — Gemini answers a bigger burst with 429s. The semaphore is built from it and `albums.py` counts waves with it |
| `VISION_CALL_TIMEOUT_S` | environment | **The only one anybody sets.** 30 s, the range is 5–180 |
| `RUN_WORST_CASE_S` | `services/vision.py` | `(pauses + 1) × call + sum(pauses)` — every attempt timing out. 93 s at the default |
| `_CONSENSUS_TIMEOUT_S` | `services/vision.py` | `RUN_WORST_CASE_S × TIMEOUT_MARGIN` — 120 s at the default |
| `_ALBUM_TIMEOUT_S` | `bot/albums.py` | `waves × RUN_WORST_CASE_S × TIMEOUT_MARGIN`, waves = ⌈`MAX_ALBUM_PAGES` × `VISION_RUNS` ÷ `API_SLOTS`⌉ — 362 s at the default. Normative: raising it is allowed, lowering it is not |
| `_QUIET_SECONDS` | `bot/albums.py` | 3 s of silence **since the last `announce`** closes an album, provided every announced page has downloaded |
| `_COLLECT_MAX_S` | `bot/albums.py` | 60 s from the first page, so a stream that never goes quiet can't hold a session for ever |
| `max_overflow` | `db/session.py` | 15 — `MAX_ALBUM_PAGES` updates each hold a session through the debounce, and the one that wins the batch holds its own for the whole album |

`TIMEOUT_MARGIN = 1.3` is the ratio the hand-written 120 s held to 93 s, so the
defaults land back on the numbers they replaced — `_ALBUM_TIMEOUT_S` is the one
that moves, 300 → 362, in the direction the rule permits. The startup log
prints all three: two are computed now, and the only way to know what a deploy
is running on is for it to say so.

Raising `VISION_CALL_TIMEOUT_S` is what a slower or thinking model needs, and
the cost is not linear — at 90 s the album ceiling becomes 1064 s. That is a
ceiling, not an expectation; it fires only when calls hang. What it really buys
is exposure, because an album is processed in a background task that any deploy
cancels.

Both ceilings use `asyncio.wait`, never `wait_for`, and cancel the
stragglers in a `finally`. Cancelling the group as a whole would discard the
`CallStats` of runs that already returned — and those calls were billed.
An orphaned run also keeps making paid calls with the result thrown away.

---

## Scale debt

The product targets many users; these shortcuts are deliberate, and each one
breaks at a knowable point. Don't treat any of them as settled design, and
don't add the machinery before the point arrives either — record what you find
here instead.

| Shortcut | Breaks at | What happens |
|---|---|---|
| The album buffer is five module-level dicts in `bot/albums.py` | **a second replica** | pages of one album land in different processes and become separate records |
| An update is processed in a background task | **any deploy** | in-flight updates are cancelled; paid Gemini calls are wasted |
| No deduplication on `update_id` | **a delivery timeout** | Telegram retries, producing a duplicate record and a second set of paid calls |
| `DAILY_COST_LIMIT_USD` is global, not per user | **two users** | one person can exhaust the day's budget for everyone |
| `limits.consume` takes no row lock | **concurrent uploads by one user** | the page quota undercounts |
| DB pool is 5 + 15 | **~20 updates in flight** | connection checkout starts timing out |
| `_API_SLOTS` is a per-process `Semaphore(10)` | **tens of active chats** | the queue to Gemini grows into timeouts |
| Photos are held whole in memory | **many parallel downloads** | container memory |

**One replica is a requirement, not a default.** The album buffer lives in the
process. Scaling the Railway service horizontally will silently split albums
again — the failure looks exactly like the bug that took three attempts to
find. Fix the first row before adding a replica.

The natural next step for that first row is Postgres as the buffer — a
`note_pages` table keyed by `media_group_id`, assembled by `message_id` — not
Redis. The data is already in Postgres, and a debounce would then only decide
*when to send the PDF*, never whether a page survives.

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

That rule has exactly one exception, made deliberately and after the failure
was reproduced three times with byte-identical numbers. `photoguard` refused a
good page — sharpness nineteen times its threshold, the page filling 97% of
the frame — because `_line_height` returns `0.0` when it cannot build a line
profile at all, and `0.0` was read as a measurement of a very small line. A
page written *large* has few lines, so it is nearer that cliff than a page
written small: the check was inverted exactly where it mattered. Since a
record is all its pages or none, one such page cost a whole album, every time.

What changed is one rule and nothing else: `UNMEASURED_LINE_HEIGHT` names the
sentinel, and the criterion is skipped when the height was not measured. The
other three checks still decide, and they are what stood between us and the
retelling of a page photographed from across the room. **The measurement
itself is still wrong** — see PLAN.md → Known risks — and fixing it needs real
pages to calibrate against, not reasoning.

One is known and worked around rather than fixed. `consensus.extract_numbers`
treats every numeric literal on the page as a value to compare, list markers
and subscripts included, so `compare()` reports a divergence wherever the runs
happen to align differently. On a real page of lecture notes that produced
eight reported divergences of which one was genuine. The filter lives in
`vision.meaningful_divergences`, which keeps a position only when at least two
runs read it as *different numbers* — a number against a gap is an alignment
artefact, not a misreading. Two rules were added after a second album: a
position where no reading has a majority **and** a gap is among the variants
is dropped, because the runs there produced different counts of numbers rather
than different readings of one; and an identical line is printed once, since
two cells of a matrix read "6 against 2" are indistinguishable in a message
that never carries the position.

**A second one is reported and not worked around: `photoguard._line_height`
reads a large hand as small text.** It estimates the line pitch as the height
of the paper region divided by the number of lines it detects, and if it
detects fewer than three it returns **0.0** — below any threshold, printing
"Текст мелкий — снимите одну страницу крупным планом". The larger the
handwriting, the fewer lines a page carries, so a large hand sits *closer* to
that cliff than a small one and the message it produces is exactly backwards.
Reproduced on the deployed bot: a close-up of a page written large, refused as
small text, and — since a record is all its pages or none — the whole
three-page album lost with it.

Not fixed here, because these modules are only imported and called. What was
built instead is the evidence: `albums.process_page` keeps all four frame
metrics on every skip, logs a refusal against its thresholds, and the
`album_incomplete` event carries the numbers per page. Before that the album
was the one path where a page could be turned away leaving nothing but a
Russian sentence to argue with, while a single photo wrote all four to
`photo_rejected`.

The same function has a second edge worth knowing: `_paper_box` thresholds at
`0.82 x percentile99`, so a bright highlight raises the percentile, the mask
shrinks to the glare, `paper_fraction` collapses into "подойдите ближе", and
every metric after it is measured on the glare instead of the page. And all
four thresholds are applied to the **compressed** image, so `IMAGE_MAX_SIDE`
silently recalibrates them.

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
    compose.py        stage two: the trusted transcription, formatted
    docx.py           .docx -> markdown, no model call
    pdf.py            a record as a PDF: formulas, graphs, tables, remarks
    photoguard.py     ready-made
    consensus.py      ready-made
    mathcheck.py      ready-made
    graphcheck.py     a matrix against the graph drawn beside it
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
prompts-v4.md        the longer variant under test, behind PROMPT_FILE
prompts-v5.md        extraction only — no rule about how a page should look
prompts-compose-v1.md  stage two: markup over text already trusted
```

The prompt files hold the recognition prompt as plain text. `vision.py`
doesn't copy one — it reads `PROMPT_FILE` from the repo root at **import
time**. So the file has to ship with the deploy or the process dies at
startup, and editing it changes the prompt without touching any Python.

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
VISION_CALL_TIMEOUT_S=30
VISION_MEDIA_RESOLUTION=unset
VISION_THINKING_LEVEL=unset
COMPOSE_ENABLED=false
COMPOSE_MODEL=gemini-3.5-flash-lite
COMPOSE_PROMPT_FILE=prompts-compose-v1.md
PROMPT_FILE=prompts-v3.md
IMAGE_MAX_SIDE=1500
IMAGE_QUALITY=85
ALLOW_UNPRICED_MODEL=false
MIN_MARKDOWN_LEN=40
MAX_ALBUM_PAGES=10
LOG_LEVEL=INFO
```

A missing required variable must crash the app at startup, not on the
first request.

`VISION_MODEL` is coupled to `PRICE_PER_MTOK` in `core/config.py`: a model
absent from that table yields `cost_usd = NULL`, `NULL` rows are skipped by
the `SUM` behind `DAILY_COST_LIMIT_USD`, and the cost breaker stops working
with nothing visible to show for it. A validator refuses to start on an
unpriced model, so changing `VISION_MODEL` normally means adding its cost per
million tokens in the same commit. The price is one line; a cap that quietly
is not a cap is not a thing to discover from a bill.

`ALLOW_UNPRICED_MODEL=true` runs one anyway. Trying a model before its price
is published is a real thing to want, and the refusal exists to make the state
chosen rather than stumbled into — the deploy log then carries a warning on
every start. What still guards the spend in that state is
`DAILY_PAGES_PER_USER` alone, so raising both at once leaves nothing.

`COMPOSE_ENABLED` turns stage two on. Off by default, and `COMPOSE_MODEL` is
priced by the same validator as `VISION_MODEL` — half the spend going out
unpriced breaks the daily cap exactly as quietly as all of it.

`VISION_MEDIA_RESOLUTION` and `VISION_THINKING_LEVEL` are the two knobs on
*how* the model is asked, as opposed to what it is asked. Both default to
`unset`, which means the field is not sent at all — Gemini's own default, and
bit-for-bit what the call did before they existed. Neither has ever been
measured, which is the point: every quality finding in this file was made on
a call that sent three fields and nothing else.

Media resolution is the direct lever on reading a photograph, and it is
checkable from our own data: raising it raises the input tokens per image, and
`ai_calls.tokens_in` is written on every call. An unknown value is refused at
startup rather than ignored, because a knob that silently does nothing is how
an experiment comes to compare a setting against itself.

What is deliberately *not* a setting is `seed`, and `temperature` stays at
1.0. Three runs made identical would send `text_agreement` up without touching
accuracy — the instrument inverted rather than merely broken, the same shape
of mistake as letting the model search the internet while it reads.

`VISION_CALL_TIMEOUT_S` is how long one model call may take, and it is the
only timeout that is a variable — see "Concurrency ceilings" for the two that
are computed from it. It exists because 30 s was tuned against a model that
answered in about six seconds, and a slower one turns every call into a
timeout: three attempts wasted per run, and pages of an album silently
dropped. The log of that failure carried nothing but empty error messages,
because `str(TimeoutError())` is `""`.

`PROMPT_FILE` names the prompt `vision.py` loads at import. It exists so a
variant can be tried on the deployed bot and rolled back by changing one
variable, and it is the only honest way to compare two prompts: the startup
log says which file and how many words, so a record can be attributed to the
prompt that produced it. A name that isn't in the repo kills the process at
startup, deliberately.

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
| `test_config.py` | the `DATABASE_URL` scheme rewrite, `VISION_RUNS >= 2`, and that `PROMPT_FILE` really selects the prompt — proved in a subprocess, because reloading `vision` rebinds its dataclasses under the rest of the suite |
| `test_handlers.py` | `_split_message`, the catch-all reply |
| `test_middleware.py` | session per update, rollback, the early commit of a new user |
| `test_graphcheck.py` | the matrix against the graph: what it must catch, and — the longer half — every shape it must stay quiet about |
| `test_corpus.py` | listing, opening, correcting, statistics, the flags rebuilt from JSONB as text, as callouts and as anchored remarks — and that no query reaches another user's records |
| `test_wiring.py` | router order in `main.py`, and that every command the bot answers has a menu description |
| `test_webhook.py` | that the endpoint answers before processing, and still checks the secret |
| `test_photoguard.py` | the one rule in photoguard this project has edited: a line height that could not be measured is not a small one |
| `test_compose.py` | stage two: that it is off by default, that the photo never reaches it, and every guard that makes it refuse itself |
| `test_pdf.py` | how a page is parsed into blocks, escaping, the LaTeX mathtext refuses, graphs read back from `[граф: ...]`, heading levels, callouts, and that nothing unreadable ever sinks the document |

`tests/conftest.py` does two things without which nothing imports: it fills
the five required environment variables with placeholders, and it teaches the
SQLite compiler to render `JSONB` as `JSON`. The second is a test-side
adapter for the sqlite dialect only — `app/db/models.py` stays PostgreSQL.

Deliberately **not** covered: `consensus` and `mathcheck`, which arrived with
their own tests — and `photoguard` except for the one rule this project
changed, and the photo and document pipelines end
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
