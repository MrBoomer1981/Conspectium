# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Project context. Read at the start of every session.
**Update this file with every architectural decision.**

---

## What this is

A Telegram bot for a **university group**. One person photographs a
handwritten page of a lecture; everyone in the group gets back a PDF they can
study from without having been there. The record is not merely transcribed:
hard passages are explained, context the page only implied is restored, and
**everything the bot added stands in a marked box with its sources** — never
woven into the author's own text. The records accumulate into the group's
corpus, and a "#word" finds one again by its subject or by a topic read off
its own headings.

**The core value is the document the group gets.** The corpus is what those
documents accumulate into, and it grows more valuable with every lecture — but
it is a consequence, not the goal. When choosing between "make the document
better" and "build another way into the corpus", choose the document. Four
days of production said this plainly: 133 pages went in and exactly one search
came back out, by the author, minutes after the search shipped.

**Marked is the whole licence to add.** The reference document the author works
from puts every addition of its own in a box that says what the manuscript
actually had. Adding is not forbidden; adding unmarked is. In a group this
stops being a matter of taste: the reader who most needs the explanation is the
one who was not at the lecture and therefore cannot tell an invented sentence
from a remembered one.

This is a product meant for **many users** — now literally, since a group is
several of them around one chat. "There is only one user" is never a reason a
design is correct: when a shortcut only breaks under concurrency, say so and
record it under "Scale debt" rather than calling it done.

**Stage:** the pipeline runs in production for one chat — the author's. Capture
works (133 pages over four days, 37 records), and it still loses about one
album in five. The three phases in `PLAN.md` are, in order: **reliability** (a
record has to exist), **the ideal record** (the explaining stage and a PDF that
never prints raw LaTeX), and **the group** (the bot in a course chat, a record
owned by the chat rather than by a person). The question the whole thing exists
to answer is whether a group uses this weekly. Not launch, not growth, not
revenue, not scale.

---

## Stack

- Python 3.12
- FastAPI — bot webhook and the future home of the Mini App API, single process
- aiogram 3.x — bot, webhook only, no polling
- SQLAlchemy 2.x (async) + Alembic + PostgreSQL (Railway addon)
- Google Gemini — recognition, and composition when it is on. Which version
  is a setting rather than a fact about the stack: it has changed twice, the
  startup log names what a deploy reads with, and `PLAN.md` → "What production
  says" names what production ran on the day it was read
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

Run everything whose name matches, across files:

    pytest -k parse_response

One test is skipped without a real PostgreSQL (see "Tests"); to run it:

    TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db pytest

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

Revision ids are hand-written, not the generated hash — `001_users_events`
through `009_unverified_pages`, which is the current head. Continue the
numbering: the next one is `010_`.

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

   The row also names the **shape** of what came back — `not json`, or the
   answer's own top-level keys — because "not JSON at all" and "JSON without a
   `markdown` field" have different fixes and read identically otherwise. Keys
   only: the values are a student's lecture page and do not belong in a log.

   **And the call is made again**, unless the finish reason says a second one
   is pointless: `SAFETY` is a refusal that repeats, `MAX_TOKENS` is our own
   ceiling and the next call walks into the same wall. This used to be "never
   retried", reasoned from a cost the pipeline no longer has — a lost run cost
   a tap of "try again" then, and costs the album now. One album on 2026-09-23
   spent four of its fifteen runs on unparseable answers, one page lost all
   three, and nothing was saved; eleven calls in the same minute parsed fine.

---

## Established experimentally

These conclusions come from real runs. Don't revisit them without new
data — each one stands on a reproduced failure.

**The chronicle is in `FINDINGS.md`; what a change to the code has to obey is
here.** Prompt lengths v3/v4/v5, the three arms, the noise floor of both
agreement numbers, and the composer's two prompts and its model swap are each a
dated measurement with a table of its own, and reading the whole journal is not
what an edit to the pipeline needs. `FINDINGS.md` keeps them in the order they
were made; `PLAN.md` → "Where the quality work stands" is how to run the next
arm. Below: first what those measurements settled, then the failures that
govern the pipeline.

The failures were established on `gemini-2.5-flash-lite`, which Google closed
to new accounts in September 2026. Recognition has changed model twice since —
the startup log names what a given deploy reads with, and `PLAN.md` → "What
production says" names what production ran on the day it was read. The findings
are kept because each cost a real failure to discover, but they are evidence
about the model of their day. If recognition starts behaving differently — the
prompt length trade-off, the value of three runs, the uselessness of
self-assessment — the model change is the first thing to suspect, and a fresh
reproduction outranks the note.

### What the measurements settled

Each line is a conclusion; the entry named after it is the run it came from.

- **A prompt's length is a budget, not a wall.** The 250-word ceiling was real
  on the old model and did not hold on the new one: v4 at 321 words beat v3 at
  242 on every order statistic. Measure before going much past it, and count
  with `PROMPT_WORDS` from the startup log — `wc -w` reads three words more
  than `str.split`. → "The prompt's length"

- **Compare means, and know the noise floor before believing an arm.** Two runs
  of one configuration move the mean of `numeric_agreement` by about **0.03**
  and the mean of `text_agreement` by about **0.005**. An arm that moves the
  numeric mean by less than 0.03 on one album has said nothing, and the noisier
  of the two numbers is the one the arms are compared on. → "Arm B"

- **`media_resolution` is not a lever on this model at this image size.**
  `high` left `tokens_in` at exactly the value `unset` produced — 1809, min
  equal to max, in both arms — so nothing about the tiling changed. Don't carry
  it in an arm; a setting proven inert makes that arm compare a setting against
  itself. → "Arm B"

- **The two-stage architecture works, and what it waited on was a model, not a
  prompt.** On `gemini-3.5-flash-lite` the composer returned its input; on
  `gemini-3.8-flash`, same prompt and same album, it produces the markup one
  stage does. It is the expensive call in the system — 15079 thinking tokens
  for 593 of output, 41 s, $0.0298, two thirds of what all nine recognition
  calls of that album cost together — and it **over-structures**, splitting a sentence into a
  heading, which is interpretation and is checkable by eye only. → "The
  composer"

- **v5 against v4 is open, not settled.** Every v5 album so far scored above
  every v4 album on the mean of `numeric_agreement`, by three times the
  instrument's noise — on four observations against two, one subject, one
  album each. A reason to run two more v4 albums, not a reason to believe v5
  reads better. → "What the arms left open"

- **`text_agreement` cannot be compared across prompts that change the page's
  shape.** That is the confound that made the first v5 measurement unreadable,
  and it is why `numeric_agreement` exists. Both are described below.

### The failures that govern the pipeline

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

**Both are columns on `notes`.** The second one was in the log alone, which
made comparing two prompts a grep through Railway's logs — and those roll
off, so an arm measured last week stops being checkable. Each takes the
album's *worst* page, and that is rarely the same page twice: on the album of
2026-09-22 the text minimum came from page 2 and the numeric minimum from
page 3, which is the whole argument for keeping both. `.docx` records have no
runs to compare and keep `NULL` in both.

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

   **And each row carries two output counts, not one.** `tokens_out` is
   `candidates_token_count`, the visible answer; `tokens_thought` is
   `thoughts_token_count`, which comes out of the same `max_output_tokens` and
   is billed at the same output rate. One column made a truncation invisible
   for a week — a call stopping at the ceiling with 498 visible tokens looks
   exactly like a short answer — and it understated the price of that call
   fifteenfold, which is the cap's problem rather than the log's. Both are in
   `_cost_usd` now. `MAX_OUTPUT_TOKENS` — **32768**, in `services/vision.py`,
   imported from there by `compose` — is one constant for both calls: a cap
   is billed only when reached, so the two sites sharing it costs nothing and
   the two drifting apart costs a run.

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
stored and is only `ready | needs_review`.

**A `rejected` verdict no longer removes anything.** It used to exit the
pipeline and never reach the database, and that rule was checked against the
photographs it was refusing: the text on them is perfectly legible. What
`text_agreement` measures is the shape the runs gave the page, and
`prompts-v5.md` deliberately leaves that shape free — so the band was reading
layout and calling it illegibility, at the price of the page and, until the
rule above changed, the album with it. The page is kept, its verdict becomes
`needs_review`, and `notes.unverified_pages` names it as read without a
second opinion. The same for a page only one run came back for:
`transcribe_consensus` returns that single reading with both agreements
`None` instead of returning nothing, because a comparison needs two of
something and one reading is not nothing.

A page is now dropped for three reasons and no others: the **frame** was
refused, **not one run** parsed, or there is **no text** on it. Those are the
cases where asking for the photograph again is the only useful answer.

What this trades away should be said plainly, because it was bought with a
reproduced failure: the band was the second line of defence against a page
photographed from across the room coming back as a fluent retelling. The first
line is `photoguard`, which runs before the model and must never be bypassed,
and it is the one that was strengthened in answer: `photoguard._line_height`
measures a line now instead of answering "could not measure" to every ordinary
page (task 35). A retelling still reaches the corpus wearing "прочитано без
сверки" rather than being refused — what changed is that the frame check in
front of it works.

Two findings downgrade `clean` → `needs_review`, both one way only. A critical
`mathcheck` issue does it in both photo paths, `handlers.handle_photo` and
`albums.process_page` — a warning is shown but leaves the verdict alone. A
surviving **numeric divergence** does it in `transcribe_consensus`, where the
divergences are computed and filtered, so the rule lives in one place rather
than in both photo paths.

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

**And one finding lifts `rejected` → `needs_review`: the numbers vouching for
the page.** The bands are `text_agreement`, which compares markdown and
therefore measures how a page was laid out rather than how it was read. That
was sound while the prompt prescribed the layout. `prompts-v5.md` deliberately
hands layout to the composing stage, and the bands stayed where task 6 put
them — so on 2026-09-23 a five-page album lost two pages at `text_agreement`
0.428 and 0.419, and under "a record is all its pages or none" the other three
went with them. $0.085 of paid calls, five photographed pages, nothing saved.
The frames were fine: sharpness 4033 and 3257 against a threshold of 90, the
page filling 96% of the frame. The numbers those runs extracted were
**identical** — `consensus.compare` reported not one divergence, not even a
number against a gap.

`vision.numbers_vouch` is that test in code: no reported divergence at all, on
the unfiltered list, and at least `_VOUCH_MIN_NUMBERS` = 5 numbers in every
run. Five because the corpus's median page carries 7.5 and its thinnest albums
5.7, while agreement on one or two numbers is cheap. The count comes from the
markdown rather than from the model's own `numeric_tokens`, for the reason
this file distrusts every self-report. A vouched page is **saved and flagged**,
never lifted to `clean`: the runs did disagree about something, and the reader
should hear about it.

Since a `rejected` band stopped dropping pages, this decides something
narrower and still worth having: whether the page is *flagged* as unread-by-a
-second-opinion. Numbers that vouch make it an ordinary `needs_review` page;
numbers that do not put it in `unverified_pages` and in a box of its own.

What this does *not* weaken is the failure the band exists for. A page
photographed from across the room comes back as three different retellings,
and invention does not produce the same five numbers in the same order three
times.

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
It guards more than the commands now: `on_tag` matches on the text of the
message rather than on a `Command`, so the only thing between a "#word" and
"пришли фотографию страницы" is that ordering.

**The corpus has one way in and one way back, and a "#word" is both.** After a
record is delivered the bot asks which subject it belongs to and shows the
topics it read off the record's own headings; the user's answer is stored on
`Note.tag`. A later "#word" searches, over the subject and the topics at once,
and a single match comes back as the document itself rather than as a line
about it.

Which of the two a message means is decided by the corpus, not by a state
machine: **if the newest record has no subject the question is still open, and
if it has one nothing was asked.** That is deliberate twice over. It is
stateless, so it survives a restart and a second replica — the album buffer is
the standing reminder of what remembering-in-the-process costs. And it is
about the *newest* record only: an untagged record from last week is a
question the user walked away from, and a search typed today must not quietly
file it under a subject nobody chose.

Topics come from the headings the pipeline has already produced —
`tags.topics_of` reads them, no second model call, and nothing here interprets
anything. **Five of them, and they are the main five**: the title, then the
headings ordered by *level* rather than by position on the page. That ordering
is the whole of the word "main", and it earns its place — rule 6 of the
composing prompt asks for `### Определение` over a definition, so nearly every
record carries one. Ranked by position, the five slots on a subsection-heavy
page go to words every record has, which match everything and therefore find
nothing. The consequence is that topics are exactly as good as the headings:
a composing stage that splits a sentence into a section invents a topic with
it. That failure is visible in the reply the user gets straight away, which is
the only reason it is acceptable. They are stored where the record is made
rather than where it is tagged, so a record nobody ever tagged is still
findable by what it is about.

`note_topics` is a table and not a JSONB column on `Note`. The question asked
of it is "which records carry this topic", which is a join on an indexed
column and reads the same on PostgreSQL and on the SQLite the suite runs
against; containment would be neither. That is also what finally made the
search testable offline — the four full-text tests that needed a real
PostgreSQL went out with `/search`.

**Six commands were deleted, and the reason is worth keeping.** `/notes`,
`/note`, `/search`, `/retitle`, `/delete` and `/pdf` were built, tested and
deployed, and `events` recorded that not one of them had ever been used.
`/stats` is the seventh of that week's commands and the only one anybody
touched — once — which is why it is still on the menu beside `/start` and
`/help`. Before adding an interface to the corpus, look at
whether the last one was touched — this project can build a week of them
without noticing that nobody wanted any.

**A saved record goes out as a PDF.** Recognised notes are dense with LaTeX,
and `$\sum_{i=1}^{p} \rho(v_i) = 2q$` reads as noise until it is drawn, so all
three capture paths — a photo, an album and a `.docx` — finish by calling
`corpus.send_record`. Rendering is
CPU-bound and runs in a thread; if it fails for any reason the record is sent
as plain text instead. A record is never lost over its presentation.

**mathtext is not LaTeX.** matplotlib rejects `\limits`, `\nolimits`,
`\displaystyle`, `\mbox` and every matrix environment outright, and a formula
it rejects is printed as its own source. That is not hypothetical:
`\sum\limits_{i=1}^p` went out on a deployed record as raw backslashes while
the same sum written `\sum_{i=1}^p` drew perfectly two pages later.
`pdf.for_mathtext` drops the commands that either do nothing to the layout or
have a synonym mathtext knows. A matrix is still asked for as a markdown
table, which keeps its columns; one that arrives as an environment is drawn
through `\substack` (below) and loses its alignment.

The expensive half of that is `pdf._SYNONYMS`. LaTeX spells nine common things
two ways and mathtext knows only one of each; the model writes the other. `\le`
and `\ge` cost a whole record — every inequality on a page about nested
intervals went out as raw source while the formulas around them drew. The same
boundary applies as to `\limits`, for the same reason: `\le` opens `\leq`,
`\left` and `\leftarrow`, so a command ends where its letters end.

**The full list, swept rather than discovered one report at a time.** Three
separate rounds of this cost three records before anybody thought to ask
mathtext the whole question at once. About 120 constructs were put through
`pdf.for_mathtext` and then through the parser; these are what still come back
refused. The six below are built; `pdf.for_mathtext` does them and
`test_pdf.py` proves each one both rewrites *and* draws.

| Written by the model | Now rewritten to |
|---|---|
| `\textrm{...}` | `\text{...}` — the same swap `\mbox` already gets |
| `\tfrac{a}{b}` | `\frac{a}{b}`; a size variant with no meaning here, like `\displaystyle` |
| `\stackrel{a}{b}` | `\overset{a}{b}` |
| `\big(` `\Big(` `\bigg(` `\Bigg(` | drop the modifier, the delimiter renders |
| `\xrightarrow{t}` | `\overset{t}{\to}` — needs a braced argument, not a word swap |
| `\overbrace` / `\underbrace` | `\overline` / `\underline`; the grouping survives, the brace does not |
| `\begin{cases}`, `pmatrix`, `bmatrix`, `vmatrix`, `array`, `aligned`, … | `\left<delimiter>\substack{row \\ row}\right<delimiter>` — see below |

`\xrightarrow` is the one that mattered most for these notes: an arrow with
its condition written above is most of the reactions on a page of biology. It
needs a braced argument rather than a word swap, and the pattern allows one
level of nesting so `\xrightarrow{\text{фермент}}` works; deeper than that it
does not match and the formula goes out as its own source, which is what
happened before.

**The environments were on the list of things nothing could rescue, and they
are off it.** mathtext has no `\begin` at all, so `\begin{cases}`,
`\begin{aligned}`, `\begin{array}` and every matrix environment printed as
their own source — and `cases` is ordinary mathematics, so it went out on a
real record on 2026-09-23 as a line of backslashes. What was missed is that
mathtext *does* have `\substack`, which stacks rows **at full size**, and
`\left...\right`, which puts a delimiter around them. Between the two,
`\begin{cases} A \\ B \end{cases}` becomes `\left\{\substack{A \\ B}\right.`
and draws as a proper piecewise brace; `pmatrix` keeps its parentheses,
`vmatrix` its bars, and `array` loses only its column spec.

Two things are lost and both are worth stating. Column **alignment** goes:
`\substack` centres each row, so a wide matrix comes out ragged — readable,
which a page of backslashes is not. And `&` means two different things, so it
is translated twice: a column separator becomes `\quad`, while in the aligned
family it marks where two lines line up inside one expression and is simply
removed, because a `\quad` there opens a gap the page does not have.

**What is left of that set is `\ce{...}`** — mhchem is a language of its own
rather than a command, and there are still only two paths for it: a rule in
the prompt that forbids it, or the drawing contract.

**A formula mathtext refuses now says so in the log.** All three rounds went
the other way: the author noticed a broken page, and only then did anyone
look. The line existed the whole time at `logger.debug`, and `LOG_LEVEL` is
`INFO` — produced and thrown away. It is a warning now, it carries mathtext's
own diagnosis (`Unknown symbol: \xrightarrow` names the command), and it is
printed once per distinct formula per document, because a macro the model
cannot spell is usually on every page of the record.

Two traps in that one line, both already paid for elsewhere. mathtext's
message opens with a blank line and a caret under the source, so the *last*
line is the diagnosis — the same shape as `str(TimeoutError())` being `""`.
And the drop list needs no longest-first sort: `(?![A-Za-z])` makes a short
match fail where a letter follows, so `\bigl` backtracks out of `big` on its
own. A sort there survived every mutation, which is what dead sophistication
looks like.

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
own heading. The capture handlers and `corpus._callouts` add it only when
nothing more exact is there to say; the subtitle of the document carries
"нужна проверка" either way.

**A record names the pages it is missing; it is thrown away only when there
are none left.** The rule used to be all its pages or none, and the reason was
sound: a page that was silently left out made the record read as a whole one,
with nothing in it to say what was gone. The cost turned out to be worse than
the disease — on 2026-09-23 two five-page albums were lost in one evening over
a single page each, and in a group chat a lost album is a course without its
lecture.

So the reason is kept and the remedy is not. `albums._assemble` puts a marker
at the position of every page that could not be read, `notes.missing_pages`
holds their numbers, and the document opens with a box naming them — the
`corpus._callouts` rule again, where the chat and the document are built from
one column and cannot come to disagree. A record with a hole is always
`needs_review`, whatever the pages that were read scored.

Only when **not one page** was read is there nothing to deliver: then the
album writes `album_incomplete` and the reply names the pages with their
reasons. `record is None` is exactly that case, by construction. The pages
that *were* recognised are still charged against the daily quota, skipped ones
are not, and the four frame metrics of every skipped page ride the
`note_processed` payload — that is now the only place they are kept, and they
are the calibration data for the frame check.

**A sentence that ran over the edge of a page is put back together, by code.**
Pages are read one at a time and joined by a rule, so a sentence the author
carried onto the next sheet came out as two halves with a horizontal line
between them — "Если граф ориентирован, то ребро" / `---` / "учитывается один
раз". Nothing downstream repairs that: the composing stage sees the rule as
the hard boundary it is, and by then it is right to.

`albums._continues` decides it deterministically and narrowly, because joining
two things that were not one sentence is worse than the seam: both sides must
be ordinary prose — not a table row, a list item, a heading, a display
formula, a drawing or a missing-page marker — the first half must not end like
a finished sentence, and the second must begin in lower case. When it fires,
the page rule goes with the seam, because a horizontal line inside a sentence
is exactly what made the record read as broken. Checked against the record
that prompted it: the rule fires on that one seam and stays quiet on the other
three of the same album.

**A callout says what we already know, never what the model thinks.** The
tinted boxes at the top of a record — needs review, arithmetic that doesn't
add up, numbers the runs read differently, spots read two ways — are built by
`corpus._callouts` out of the `Note`'s own columns, so the document and the
chat cannot come to disagree. `pdf.py` receives a list of `Callout` and knows
nothing about where a record came from.

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

How long that call may take, and the one case where a second one is not made,
are in "Concurrency ceilings" — the stage has its own ceiling because it is one
call over the whole record rather than one call over a page.

**One thing the stage produces is repaired rather than refused: a heading that
is not one.** Rule 1 asks for a section heading and the model decides what a
section is — interpretation, on a page it cannot see — and since topics are
read off headings, an invented section becomes a word the corpus is searched
by. `_demote_invented_headings` takes the marker off three shapes and leaves
every word where it was: a heading with no letters in it (`## 4.`, which
normalises to the topic "4"), one that does not start with a word or a number
(a formula line promoted), and one whose next line of prose begins in lower
case, which makes the heading the first half of a sentence. Measured against
the whole corpus the day it was written, it takes **11 headings of 111**, and
each one is a case this file or `PLAN.md` had already named by hand.

A repair and not a guard, deliberately, and it is the one place the stage's
output is edited rather than accepted or rejected. A refusal costs the whole
composition — note 36 had two invented headings among nine good ones — and
what the repair removes is markup this stage itself added, never a word, so
the numbers, the marks and the length the guards compare cannot move. It runs
**before** `_refusal` so that what was checked is what is stored. The count
goes to the log and into `note_processed` as `compose_demoted`, beside the
word drift, because nobody has yet decided what a large number there means.

The split it catches is not a judgement call: the composer writes the same
content correctly elsewhere in the same corpus — `**Принцип неопред.
Гейзинга**: если мы знаем…` as a bold term and a colon in one record, and as
a heading with the sentence running on below it in another. The page did not
change; the markup did.

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
already machine text. Only the empty-text gate (`MIN_MARKDOWN_LEN`, step 10)
still applies.

---

## Concurrency ceilings

**Two of these are settings; three are computed from one of them.** That
arithmetic used to live in comments across two files, where raising one number
on its own left the other two quietly cutting the work short:

| Constant | Where | Value |
|---|---|---|
| `API_SLOTS` | `services/vision.py` | `10` — Gemini answers a bigger burst with 429s. The semaphore is built from it and `albums.py` counts waves with it |
| `VISION_CALL_TIMEOUT_S` | environment | 30 s, the range is 5–180. One call over **one page**; the three ceilings below are computed from it |
| `COMPOSE_CALL_TIMEOUT_S` | environment | 240 s, the range is 30–600. One call over **the whole record**, so nothing derives from it and it derives from nothing |
| compose's slot | `services/compose.py` | one of the `API_SLOTS`, taken from the same semaphore and held for the whole call — about 40 s measured, up to `COMPOSE_CALL_TIMEOUT_S` per attempt, where a page holds one for seconds. It runs after `process_batch`, so `_ALBUM_TIMEOUT_S` does not cover it |
| `RUN_WORST_CASE_S` | `services/vision.py` | `(pauses + 1) × call + sum(pauses)` — every attempt timing out. 93 s at the default |
| `_CONSENSUS_TIMEOUT_S` | `services/vision.py` | `RUN_WORST_CASE_S × TIMEOUT_MARGIN` — 120 s at the default |
| `_ALBUM_TIMEOUT_S` | `bot/albums.py` | `waves × RUN_WORST_CASE_S × TIMEOUT_MARGIN`, waves = ⌈`MAX_ALBUM_PAGES` × `VISION_RUNS` ÷ `API_SLOTS`⌉ — 362 s at the default. Normative: raising it is allowed, lowering it is not |
| `_QUIET_SECONDS` | `bot/albums.py` | 3 s of silence **since the last `announce`** closes an album, provided every announced page has downloaded |
| `_COLLECT_MAX_S` | `bot/albums.py` | 60 s from the first page, so a stream that never goes quiet can't hold a session for ever |
| `max_overflow` | `db/session.py` | 15 — `MAX_ALBUM_PAGES` updates each hold a session through the debounce, and the one that wins the batch holds its own for the whole album |

`TIMEOUT_MARGIN = 1.3` is the ratio the hand-written 120 s held to 93 s, so the
defaults land back on the numbers they replaced — `_ALBUM_TIMEOUT_S` is the one
that moves, 300 → 362, in the direction the rule permits. The startup log
prints all four: three are computed now, and the only way to know what a deploy
is running on is for it to say so.

**The two settings are not interchangeable, and treating them as one cost a
record.** Recognition is one call per page, so its ceiling is about a page and
every album ceiling is derived from it. Composition is one call over the whole
assembled record, so its wait grows with the album while the page ceiling does
not. `compose` waited on `VISION_CALL_TIMEOUT_S` until a four-page album hit
exactly 90 s (`ai_calls` id 361, 2026-09-23) and the record went into the
corpus with the flat text `prompts-v5.md` produces — three headings over 2866
characters, where the composed record of the previous album had nine over
1603. Topics are read off headings, so the record came out both flatter and
harder to find. Measured on `gemini-3.8-flash`: three pages compose in about
43 s, which is where the 240 s default comes from.

**And the second attempt is not the same policy as recognition's.** `compose`
makes at most two calls and **does not retry a timeout** — `vision._should_retry`
says it should, which is right for a page, where the ceiling is tens of seconds
and a hung connection is the usual cause. At a ceiling of minutes, sized for
the whole record, a call that reached it was working rather than hanging:
waiting those minutes again buys the same answer and doubles the window in
which a deploy cancels the background task. The retry is there for a 429, a
503 or a dropped connection, which is what the second attempt can actually
fix. Every attempt is written to `ai_calls` — rule 4 has no exception for the
one that failed.

Raising `VISION_CALL_TIMEOUT_S` is what a slower or thinking model needs, and
the cost is not linear — at 90 s the album ceiling becomes 1064 s. That is a
ceiling, not an expectation; it fires only when calls hang. What it really buys
is exposure, because an album is processed in a background task that any deploy
cancels.

The two group ceilings, `_CONSENSUS_TIMEOUT_S` and `_ALBUM_TIMEOUT_S`, use
`asyncio.wait`, never `wait_for`, and cancel the stragglers in a `finally`;
`wait_for` is only for a single call. Cancelling the group as a whole would discard the
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

That rule has two exceptions, both in `photoguard._line_height`. The first was
made deliberately and after the failure was reproduced three times with
byte-identical numbers. `photoguard` refused a good page — sharpness nineteen
times its threshold, the page filling 97% of the frame — because
`_line_height` returned `0.0` when it could not build a line profile at all,
and `0.0` was read as a measurement of a very small line. A page written
*large* has few lines, so it is nearer that cliff than a page written small:
the check was inverted exactly where it mattered. At the time a record was all
its pages or none, so one such page cost a whole album, every time.

What changed is one rule and nothing else: `UNMEASURED_LINE_HEIGHT` names the
sentinel, and the criterion is skipped when the height was not measured. The
other three checks still decide, and they are what stood between us and the
retelling of a page photographed from across the room. The measurement itself
was replaced afterwards — that is the second exception, below.

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

**The second exception is the same function, measured rather than argued.**
`photoguard._line_height` estimated the pitch as the height of the paper region
divided by the number of lines it detected, and returned **0.0** below three
lines — so a large hand, which carries few lines, sat nearer that cliff than a
small one and was refused as "Текст мелкий". The sentinel half was fixed
first; the measurement itself is what this second edit replaces, and the
replacement was chosen against pages whose pitch is known by construction
rather than against anybody's impression of a photograph.

What the bench showed first is that the old estimator could not measure an
ordinary page **at all**: it thresholded ink at the 35th percentile of
brightness, and a real page is about 5% ink, so the threshold landed on the
paper, the mask covered the whole sheet, the profile came out flat and the
answer was the sentinel. Every synthetic page — 28 px pitch to 260 — came back
0.0.

Three changes, and each one is a line of the recorded design: the ink
threshold is **Otsu** rather than a rank, so it finds the valley between paper
and ink wherever those two sit on the scale; the pitch is the **median
distance between bands of ink**, so a drawing or an empty margin no longer
stretches it — that was the 2.5-to-16-fold spread between mean and median on a
page with a drawing; and the **three-line minimum is gone**, with a single band
answering with its own height, which is a lower bound on a pitch and therefore
the right kind of answer for a threshold that looks for one. Measured against
known pitches the estimator now lands within 5% from 28 px to 220 px, on pale
ink, on a dark photograph and with a drawing on the page.

`MIN_LINE_HEIGHT_PX` did not move and its unit did not change: it is still the
pitch in pixels of the compressed frame. It is also still uncalibrated against
real photographs — 20 px on a 1500 px page means seventy lines to a sheet,
which is defensible and is not evidence. The module's own CLI over a folder of
real pages is what would settle it.

The evidence path built for this stands and is what a future calibration reads:
`albums.process_page` keeps all four frame metrics on every skip, logs a
refusal against its thresholds, and the `album_incomplete` event carries the
numbers per page.

**`_paper_box` is untouched and still has its edge**, which is the boundary of
this exception: `_paper_box` thresholds at
`0.82 x percentile99`, so a bright highlight raises the percentile, the mask
shrinks to the glare, `paper_fraction` collapses into "подойдите ближе", and
every metric after it is measured on the glare instead of the page. And all
four thresholds are applied to the **compressed** image, so `IMAGE_MAX_SIDE`
silently recalibrates them.

---

## Structure

Everything below is on disk; what is done and what comes next is `PLAN.md` →
Progress.

```
app/
  main.py             FastAPI, webhook, /health
  bot/
    handlers.py       aiogram handlers
    texts.py          all user-facing messages, and the command list
    middlewares.py    DB session and user injected into handlers
    albums.py         album buffer and assembly
    corpus.py         tags, search by tag, and a record as a file
    tags.py           what a #tag is, and where a record's topics come from
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
FINDINGS.md          the run-by-run record behind "Established experimentally"
prompts-v3.md        TRANSCRIBE_PROMPT, read from disk at import
prompts-v4.md        the longer variant under test, behind PROMPT_FILE
prompts-v5.md        extraction only — no rule about how a page should look
prompts-compose-v1.md  stage two: markup over text already trusted
prompts-compose-v2.md  the same job, said as instructions rather than bans
```

The prompt files hold the recognition prompt as plain text. `vision.py`
doesn't copy one — it reads `PROMPT_FILE` from the repo root at **import
time**. So the file has to ship with the deploy or the process dies at
startup, and editing it changes the prompt without touching any Python.

The repository root also carries a handful of `.pdf` records and Railway log
dumps that are **not** tracked. They are the evidence behind the findings — the
albums the arms were measured on, the logs a number was read out of — kept
where they were downloaded to. Nothing reads them at runtime, and nothing in
the suite needs them, so `.gitignore` covers `*.pdf` and `*.log`: a record is a
user's page of notes, and the corpus lives in the database, not in git.

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
COMPOSE_CALL_TIMEOUT_S=240
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

**That state was held for days and it is what the escape hatch costs.**
`gemini-3.8-flash` ran unpriced from the model change until 2026-09-23, so
every `ai_calls` row it wrote carries `cost_usd = NULL`, and no recomputation
will recover them — the tokens are there, the price of the day is not. It is
priced now at 0.375 in / 1.875 out per Mtok, which puts a three-page album at
about **4.2 cents**: 14481 tokens in, 19807 out, and **two thirds of the bill
is thinking**. At `DAILY_COST_LIMIT_USD=5` that is roughly 117 albums a day,
so the cap is not binding at this volume — but it is a cap again, and the
warning in the deploy log is gone. Turn `ALLOW_UNPRICED_MODEL` back off once
a model is priced; left on, it is the one setting that disarms the next one
silently.

`COMPOSE_ENABLED` turns stage two on. Off by default, and `COMPOSE_MODEL` is
priced by the same validator as `VISION_MODEL` — half the spend going out
unpriced breaks the daily cap exactly as quietly as all of it.

`COMPOSE_CALL_TIMEOUT_S` is the second timeout that is a setting, and the
reason it is not `VISION_CALL_TIMEOUT_S` is in "Concurrency ceilings": one
call over a page against one call over a record. The range is 30–600. Under
30 s the stage refuses itself by construction — the shortest composition ever
measured on a model strong enough to compose took 41 s — and over 600 s the
wait outlives the background task it runs in, where a deploy cancels it and
the record goes out unformatted anyway, which is the outcome the wait was
meant to prevent.

**The refusal and the warning read one list, and that is load-bearing.** They
did not: the validator checked both models from the day `compose` shipped,
while the warning that stands in for it under `ALLOW_UNPRICED_MODEL` named
`VISION_MODEL` alone, so swapping `COMPOSE_MODEL` for an unpriced one started
in silence with half the day's spend writing `NULL`. `PRICED_MODEL_SETTINGS`
and `Settings.unpriced_models()` are one list read twice, and a test asserts
the two paths cover the same settings. Any future setting that names a model
goes in that tuple and nowhere else.

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

**It was measured and it does nothing.** `high` left `tokens_in` at exactly the
value `unset` produced — see `FINDINGS.md` → "Arm B". Leave it `unset`; it is
not a lever on this model at this image size, and carrying it in an arm makes
that arm compare a setting against itself, which is the failure this paragraph
was written to prevent.

`VISION_THINKING_LEVEL` is the one still untouched, and it is now *visible*
rather than merely settable: `ai_calls.tokens_thought` says how much thinking
every call actually does. Leave it `unset` until that column has a few albums
in it. Turning it down is a change to how the model reads, and it would be
made to solve a budget problem — the wrong reason, and every quality finding
in this file was made with the field absent.

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

**The startup log is the instrument's label, and what it leaves out is
unmeasurable.** It named the prompt, the compose model, both call knobs and all
four timeouts — and not `VISION_MODEL`, the attribute every finding in this
file carries and the one that has already changed twice here, retiring a page
of them. `Recognition: <model>, N runs` is the first line now, the run count on
it because a page scored on two runs agrees more easily than one scored on
three. What is still missing is the other direction: a **record** does not say
which prompt made it, so pooling albums across days rests on remembering. See
`PLAN.md` → "Where the quality work stands" → gap 3.

---

## Tests

The suite is offline: no network, no Gemini, no Postgres. Everything that
needs a database runs on in-memory SQLite.

| File | Covers |
|---|---|
| `test_parse_response.py` | the model's reply: garbage, the ```json fence, missing fields, wrong types |
| `test_limits.py` | `check_limits` / `consume` — the money-critical path |
| `test_reliability.py` | retry classification, one owner per album batch, spend surviving a rollback |
| `test_vision_pure.py` | `_should_retry`, `_cost_usd`, `total_cost`, `_verdict` and the numbers that vouch for a page, `_short_error`, and what an unparseable answer says and earns |
| `test_albums.py` | `_assemble` aggregates and the marker it leaves where a page could not be read, the three reasons a page is dropped and the two that only mark it, `process_batch` survivor logic |
| `test_docx.py` | heading styles to markdown, title derivation |
| `test_images.py` | the 1500 px cap, EXIF orientation, JPEG output |
| `test_config.py` | the `DATABASE_URL` scheme rewrite, `VISION_RUNS >= 2`, and that `PROMPT_FILE` really selects the prompt — proved in a subprocess, because reloading `vision` rebinds its dataclasses under the rest of the suite |
| `test_handlers.py` | `_split_message`, the catch-all reply |
| `test_middleware.py` | session per update, rollback, the early commit of a new user |
| `test_graphcheck.py` | the matrix against the graph: what it must catch, and — the longer half — every shape it must stay quiet about |
| `test_corpus.py` | filing a record under a subject, finding it by a topic, statistics, the flags rebuilt from JSONB as callouts and as anchored remarks — and that no query reaches another user's records |
| `test_tags.py` | what a #tag normalizes to, what counts as one, and which topics a record yields |
| `test_wiring.py` | router order in `main.py`, and that every command the bot answers has a menu description |
| `test_webhook.py` | that the endpoint answers before processing, and still checks the secret |
| `test_photoguard.py` | the two rules in photoguard this project has edited: a line height that could not be measured is not a small one, and what the measurement answers on pages whose pitch is known by construction |
| `test_compose.py` | stage two: that it is off by default, that the photo never reaches it, every guard that makes it refuse itself, the ceiling it waits on, which failures earn a second call, and which headings are taken back |
| `test_pdf.py` | how a page is parsed into blocks, escaping, the LaTeX mathtext refuses and the environments it now draws through `\substack`, graphs read back from `[граф: ...]`, heading levels, callouts, that nothing unreadable ever sinks the document — and that no file under `app/` carries an invalid escape sequence |

`tests/conftest.py` does two things without which nothing imports: it fills
the five required environment variables with placeholders, and it teaches the
SQLite compiler to render `JSONB` as `JSON`. The second is a test-side
adapter for the sqlite dialect only — `app/db/models.py` stays PostgreSQL.

Deliberately **not** covered: `consensus` and `mathcheck`, which arrived with
their own tests — and `photoguard` except for the two rules this project
changed, and the photo and document pipelines end
to end — those break on every reordering of a handler, and the pipeline is
not settled yet.

One test is skipped unless `TEST_DATABASE_URL` points at a real Postgres:
`test_spend_survives_main_rollback`, which needs two genuinely separate
transactions. It used to be five — the other four were the behavioural search
tests, and they went out with `/search`; the tag search that replaced it joins
an indexed column and reads the same on SQLite, which is half the reason
`note_topics` is a table.

Still to write: nothing is scheduled. The FSRS schedule calculation used to
stand here; flashcards are dropped for a long time and the tests go with them.

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
- Flashcards and spaced repetition. Dropped for a long time, not scheduled:
  they were the reason to come back daily in a product whose corpus was the
  goal, and the goal is the document now. Nothing in the schema forbids them
  later; nothing plans for them either
- Video and lecture transcription
- Payments, subscriptions, pricing tiers
- Custom registration and passwords — identity already comes from Telegram
- An admin panel
- Export to Anki, and any bulk export of the corpus. A record comes back as
  one PDF when a tag matches it — that is presentation, not an exit door, and
  it is not licence to add "download everything"
- A language trainer, text rewriting, or any second feature
- Visual design and styling of **bot responses** — the chat stays plain text.
  This is not the document: the PDF is what the group receives, so its design
  and readability are the product itself and are task 36 in `PLAN.md`
- Social features, sharing, friends
- Caching, queues, microservices, Docker, CI
