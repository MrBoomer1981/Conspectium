# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Project context. Read at the start of every session.
**Update this file with every architectural decision.**

It holds the rules and each one's reason in a sentence. The failure or the
measurement a rule was bought with — the date, the album, the numbers — is in
`FINDINGS.md`, and a `→ "…"` after a rule names the section there. New
evidence goes there; the rule it produces goes here.

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
owned by the chat rather than by a person) — under way since task 39 put the
bot in the chat. The question the whole thing exists
to answer is whether a group uses this weekly. Not launch, not growth, not
revenue, not scale.

---

## Stack

- Python 3.12
- FastAPI — bot webhook and the future home of the Mini App API, single process
- aiogram 3.x — bot, webhook only, no polling
- SQLAlchemy 2.x (async) + Alembic + PostgreSQL (Railway addon)
- Google Gemini — recognition, and composition when it is on. The version is a
  setting, not a fact about the stack: it has changed twice, and the startup
  log names what a deploy reads with
- Pillow + numpy — image processing
- reportlab + matplotlib — a record as a PDF, formulas drawn by mathtext
- Railway — hosting

Don't add dependencies without an explicit need. Redis, queues, workers,
Docker and CI stay out — not because the product is single-user, but because
the second user hasn't arrived. "Scale debt" says what that postpones.

---

## Development commands

    pip install -r requirements-dev.txt
    pytest                                           # the whole suite, offline
    pytest tests/test_parse_response.py::test_name   # one test
    pytest -k parse_response                         # by name, across files
    alembic revision -m "description"                # then hand-write the id, below
    alembic upgrade head
    uvicorn app.main:app --reload                    # needs a public URL for the webhook, e.g. ngrok

Production runs the `Procfile`: `alembic upgrade head && uvicorn app.main:app
--host 0.0.0.0 --port $PORT`.

`app.core.config.settings` is built from the environment at import time, so
anything importing `app.*` needs the five required variables: copy
`.env.example` to `.env` before running `alembic` or `uvicorn`, or they crash
with a validation error before reaching the database. `pytest` is the
exception — `tests/conftest.py` fills the same variables with placeholders.

`asyncio_mode = "auto"` in `pyproject.toml`: async tests and fixtures need no
`@pytest.mark.asyncio`. One test needs a real PostgreSQL and is skipped
without it (see "Tests"):

    TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db pytest

`.python-version` pins 3.12, which is what Railway runs. If pyenv doesn't have
it, the suite also runs on 3.11 in a virtualenv built with an explicit
interpreter path, bypassing the shim — nothing under `tests/` needs 3.12:

    ~/.pyenv/versions/3.11.9/bin/python -m venv .venv
    .venv/bin/pip install -r requirements-dev.txt
    .venv/bin/pytest

Revision ids are hand-written, not the generated hash — `001_users_events`
through `011_groups`, which is the current head. The next one is
`012_`.

No linter is configured — don't add one without an explicit request.

---

## Inviolable rules

1. **The LLM is called only from the server.** The key never reaches the
   client, and the Gemini API isn't reachable directly from Russia, so calls
   go out from Railway.

2. **Compress the image before sending it to the model.** `IMAGE_MAX_SIDE`
   and `IMAGE_QUALITY`, 1500 px and 85. That a full-size photo costs several
   times more for no gain in accuracy is evidence about a retired model; the
   numbers are settings so the claim can be measured on the same album rather
   than argued, and the defaults do not drift.

3. **Never store the original photos.** Only the recognized text.

4. **Every model call is written to `ai_calls`** — model, tokens, cost,
   latency, success, error. No exceptions, a failed attempt included.

5. **Every significant action is written to `events`.** Retention can't be
   computed after the fact.

6. **Limits are checked before the model call, not after.**

7. **Never trust JSON from the model.** Validate the schema, handle garbage;
   the parsing function never raises, it returns `None`. The `ai_calls` row
   then names the response's own `finish_reason` — `MAX_TOKENS`: our
   `max_output_tokens` cut the JSON mid-string; `STOP`: the model finished and
   returned no JSON; `SAFETY`: it refused — and the **shape** of what came
   back: `not json`, or the answer's top-level keys. A LaTeX command the
   model wrote with one backslash is repaired before recognition's answer is
   parsed (`vision._JSON_BACKSLASH_RE`): `\pmod` failed the whole answer and
   `\frac` read as a form feed. Keys only; the values are
   a student's lecture page and do not belong in a log. **The call is made
   again** unless the finish reason says a second one is pointless: `SAFETY`
   repeats, and `MAX_TOKENS` walks into the same ceiling.
   → "Unparseable answers"

---

## Established experimentally

Each of these stands on a reproduced failure or a measurement; don't revisit
one without new data. The failures were established on
`gemini-2.5-flash-lite`, which Google closed to new accounts in September
2026, and recognition has changed model twice since — the startup log names
what a deploy reads with, `PLAN.md` → "What production says" what production
ran on the day it was read. If recognition starts behaving differently (the
prompt length trade-off, the value of three runs, the uselessness of
self-assessment), suspect the model first: a fresh reproduction outranks the
note. `PLAN.md` → "Where the quality work stands" is how to run the next arm.

### What the measurements settled

- **A prompt's length is a budget, not a wall.** The 250-word ceiling was
  real on the old model and did not hold on the new one: v4 at 321 words beat
  v3 at 242 on every order statistic. Measure before going much past it, and
  count with `PROMPT_WORDS` from the startup log — `wc -w` reads three words
  more than `str.split`. → "The prompt's length"
- **Compare means, and know the noise floor before believing an arm.** Two
  runs of one configuration move the mean of `numeric_agreement` by about
  **0.03** and of `text_agreement` by about **0.005**. An arm that moves the
  numeric mean by less than 0.03 on one album has said nothing, and the
  noisier number is the one arms are compared on. → "The three arms"
- **`media_resolution` is not a lever on this model at this image size.**
  `high` left `tokens_in` exactly where `unset` put it. Don't carry it in an
  arm: a setting proven inert makes the arm compare a setting against itself.
  → "The three arms"
- **The two-stage architecture works; it waited on a model, not a prompt.**
  On `gemini-3.5-flash-lite` the composer returned its input; on
  `gemini-3.8-flash`, same prompt and album, it produces the markup one stage
  does. It is the expensive call in the system — one composition costs about
  six recognition calls — and it **over-structures**, splitting a sentence
  into a heading. → "The composer"
- **v5 against v4 is open, not settled.** Every v5 album so far scored above
  every v4 album on mean `numeric_agreement`, by three times the noise — on
  four observations against two. A reason to run two more v4 albums, not a
  reason to believe v5 reads better. → "What the arms left open"

### The failures that govern the pipeline

**A verification model call doesn't work.** Asked to compare the
transcription with the photo and find discrepancies, the model invented one
that didn't exist, duplicated it three times, and found none of the real
ones. **Don't add a verification pass with the model.**

**Agreement between independent runs works.** Three runs of the same short
prompt, results compared by code: where they agree, trust it; where they
diverge, flag it. It is the only uncertainty signal that has proved reliable.

**There are two agreement numbers, and they answer different questions.**
`text_agreement` compares the markdown, so it moves when a prompt changes how
a page is *laid out* rather than how it was *read*; it cannot be compared
across prompts that change the page's shape, nor between a one-stage and a
two-stage run. `vision.numeric_agreement` compares the runs' `numeric_tokens`
instead — a number has no layout. Both are columns on `notes`, each the
album's *worst* page; `.docx` records keep `NULL` in both. Read them across
the arms of one experiment, never against a threshold: a page of matrices is
hundreds of numbers from a handful of digits, a repetitive sequence has many
equally good alignments, and the value runs low on exactly the pages the
measure was made for. `difflib`'s autojunk stays off for the same reason.
→ "The two agreement numbers"

**The model's self-assessment is useless.** `confidence` gave 0.95 on a page
with three errors, which is why it's not in the schema. `unreadable_count: 0`
is not a sign of quality either.

**`uncertain` is a complaint, not an ambiguity.** Asked for symbols that read
two ways, the model lists the state of the paper. `vision.meaningful_uncertain`
enforces the prompt's own test in code: an entry that names no alternative is
not an ambiguity, and one whose text already carries `[неразборчиво]` is a
mark that stands in the record itself. → "What `uncertain` came back with"

**Arithmetic is checked by code, not by the model.** The model makes
calculation errors and silently "fixes" what doesn't add up; `mathcheck`
found an error in a constant and a diverging chain it missed across four runs.

**The model attributes its own errors to the author.** Having misread a
semicolon as a letter, it wrote "possibly a typo by the author". The prompt
explicitly forbids that kind of interpretation.

**A bad shot is more dangerous than difficult text.** On a spread
photographed from a distance the model recognised the topic from the heading
and produced a coherent textbook retelling with `unreadable_count: 0`. No
after-the-fact check catches this, which is why `photoguard` runs **before**
the model and must never be bypassed.

---

## Sessions and transactions

The full reasoning and a worked example are in `PLAN.md` → "Transaction
model". The essentials, because they shape every handler:

1. **One session per update, opened by the middleware.** It lives in
   `data["session"]`, commits after the handler and rolls back on any
   exception; `notes`, `users` and `events` go through it. One deliberate
   exception: a **new** user is committed *before* the handler runs, because
   `log_ai_calls` inserts `ai_calls.user_id` from a session of its own and
   would otherwise fail the foreign key. Someone who wrote to the bot is
   registered however their first update ends. The middleware serves messages
   and the bot's own membership updates alike, and puts the group chat, if
   any, in `data["group"]`. A user or group row that two updates insert at
   once — the pages of an album from someone the bot has never seen — is
   fetched by the loser rather than failing on the unique index
   (`middlewares._insert_or_fetch`): a lost race used to be a lost page.

2. **`events` are transactional and disappear on rollback — deliberately.**
   An event describes something that, in the end, didn't happen. `log_event`
   wraps its insert in a SAVEPOINT (`begin_nested`) not to survive a rollback
   but so that a failed insert can't poison the transaction and bring down the
   next request.

3. **`ai_calls` are written in their own session and committed at once.**
   Money was spent however processing ended, and a spend row lost to a
   rollback understates the daily cap and disarms the breaker. `log_ai_calls`
   takes no session. `ai_calls` rows with no matching `Note` are a normal
   outcome, not a bug to fix.

   **Each row names its own model:** `CallStats` carries `kind` and `model`,
   and `log_ai_calls` writes those rather than `settings.VISION_MODEL`, or a
   second stage would be recorded and priced as the first. **And each row
   carries two output counts:** `tokens_out` is `candidates_token_count`, the
   visible answer; `tokens_thought` is `thoughts_token_count`, drawn from the
   same `max_output_tokens` and billed at the same rate. Both are in
   `_cost_usd`. `MAX_OUTPUT_TOKENS` — **32768**, in `services/vision.py`,
   imported by `compose` — is one constant for both calls: a cap is billed
   only when reached, and two drifting apart costs a run.
   → "Unparseable answers"

4. **`note_failed` is the only event written standalone**
   (`log_event_standalone`), because the global error handler runs while the
   main transaction is already rolling back.

5. **Anything that calls the model never touches the database.** The runs and
   the pages of an album run in parallel, and one `AsyncSession` cannot be
   used concurrently. Model-calling functions return their stats upward; the
   handler performs the writes.

---

## The pipeline

The canonical step order for a photo is `PLAN.md` → "Final processing order
for a photo"; every "does this come before or after that?" question is
answered there. There are three **capture paths** — a photo, an album, a
`.docx` — and two of them, the **photo paths** (`handlers.handle_photo` and
`albums.process_page`), read photographs.

**`.docx` bypasses the model entirely.** No limits are checked and no quota
is spent, so a Word file is processed even with `AI_ENABLED=false` — it is
already machine text. Only the empty-text gate (`MIN_MARKDOWN_LEN`, step 10)
applies.

### Verdicts

**`verdict` and `status` are different vocabularies.** `verdict` belongs to
the pipeline and is `clean | needs_review | rejected`; `Note.status` is stored
and is only `ready | needs_review`.

**A page is dropped for three reasons and no others:** the **frame** was
refused, **not one run** parsed, or there is **no text** on it — the cases
where asking for the photograph again is the only useful answer. Everything
else is kept and, where needed, marked:

- **`rejected` removes nothing.** The band is `text_agreement`, which
  measures layout, and `prompts-v5.md` leaves layout free. The page is kept as
  `needs_review`, and `notes.unverified_pages` names it as read without a
  second opinion. The same for a page only one run came back for:
  `transcribe_consensus` returns that single reading with both agreements
  `None`, because one reading is not nothing. → "Pages refused for their
  layout"
- **The numbers can vouch for a `rejected` page.** `vision.numbers_vouch`: no
  reported divergence at all, on the unfiltered list, and at least
  `_VOUCH_MIN_NUMBERS` = 5 numbers in every run, counted from the markdown
  rather than from the model's own `numeric_tokens`. A vouched page is an
  ordinary `needs_review` page rather than one listed in `unverified_pages`
  with a box of its own — **never** lifted to `clean`, because the runs did
  disagree about something. Invention does not produce the same five numbers
  in the same order three times.
- **Two findings downgrade `clean` → `needs_review`, one way only.** A
  critical `mathcheck` issue, in both photo paths — a warning is shown but
  leaves the verdict alone. And a surviving **numeric divergence**, in
  `transcribe_consensus` where the divergences are computed and filtered, so
  the rule lives in one place: a misread digit barely moves
  `text_agreement`, and a wrong digit is what a reader can least check
  afterwards. → "Numbers the agreement could not see"

What keeping every legible page trades away: the band was the second line of
defence against a page photographed from across the room coming back as a
fluent retelling. The first line is `photoguard`, and it was strengthened in
answer (task 35); a retelling that gets past it reaches the corpus wearing
"прочитано без сверки" rather than being refused.

**A page the frame check refuses stops its album before anything is read.**
`albums.refused_frames` checks every frame first, and if one fails the album is
not read with a hole in it: the reply names the page and the reason and asks
for the album again, whole (`album_retake_requested`), with nothing spent and
nothing charged. A refused frame is the one loss only the photographer can
fix — the author's decision, 2026-09-25, after record 45 came back without its
first page and "пришлите их отдельно". The other two reasons a page is lost,
not one run parsed and no text on it, are no fault of the photograph, and
still leave a hole. → "Record 45, a lecture on remainders"

**A record names the pages it is missing; it is thrown away only when there
are none left.** `albums._assemble` puts a marker where each unread page
stood, `notes.missing_pages` holds their numbers, and the document opens with
a box naming them. A record with a hole is always `needs_review`. Only when
**not one page** was read is there nothing to deliver — `record is None` is
exactly that case — and the album writes `album_incomplete`, the reply naming
the pages and their reasons. Recognised pages are charged against the daily
quota, skipped ones are not, and the four frame metrics of every skipped page
ride the `note_processed` or `album_incomplete` payload: the calibration data
for the frame check. → "Albums lost over one page"

### Updates and albums

**The webhook answers before it works.** Telegram delivers the updates of one
chat strictly in sequence, so an update handled inside the request stops that
chat for the ~9 s a photo takes, and an album can never assemble — its later
pages do not exist for us yet. `telegram_webhook` schedules the work and
returns. **Never `await` the processing of an update inside the endpoint.**

**An album is owned by exactly one update.** Each page is its own webhook
update with its own session. `albums.collect()` waits for the group to go
quiet and hands the whole batch to one caller; every other caller gets `None`
and **must return without replying**, or the album is processed once per page.

**Register a page with `albums.announce` the moment its update arrives,
before downloading it**, and call `add_page` with the bytes afterwards.
Telegram never says how many items a media group holds, so the end of an
album is a guess at silence: the debounce times the announcements, which
arrive milliseconds apart, and a batch closes only once every announced page
has also downloaded. Timed from the downloads, it measures our own network
and splits the album. → "The album that came back as four records"

**Router order in `main.py` is load-bearing.** `handlers.router` ends with a
filterless catch-all, so any router included after it receives nothing.
`corpus.router` goes **first**, capture second; a third router has to be
placed relative to that catch-all. `on_tag` matches on the message text
rather than a `Command`, so that ordering is the only thing between a "#word"
and "пришли фотографию страницы".

### The corpus

**A "#word" is the one way in and the one way back.** After a record is
delivered the bot asks which subject it belongs to and shows the topics it
read off the record's headings; the answer is stored on `Note.tag`. A later
"#word" searches subjects and topics at once, and a single match comes back
as the document itself rather than a line about it.

Which of the two a message means is decided by the corpus, not by a state
machine: **if the newest record has no subject, the question is still open;
if it has one, nothing was asked.** It is stateless, so it survives a restart
and a second replica. And it is about the *newest* record only, so a search
typed today never files last week's untagged record under a subject nobody
chose. It is a private chat's rule: a group never asks — "A group chat",
below. A photo sent with "#word" in its caption is filed at once in a private
chat too, and the question gives way to where it was filed.

**Topics are the main five,** read by `tags.topics_of` from headings the
pipeline already produced — no model call. The title, then the headings
ranked by *level* rather than position: ranked by position, the slots on a
subsection-heavy page go to `### Определение` and its kind, words every record
carries, which match everything and so find nothing. Topics are exactly as
good as the headings, so an invented section is an invented topic — acceptable
only because the user sees the topics in the reply straight away. They are
stored when the record is made, not when it is tagged, so an untagged record
is still findable. `note_topics` is a table, not JSONB on `Note`: "which
records carry this topic" is a join on an indexed column that reads the same
on PostgreSQL and on the suite's SQLite.

### A group chat

**A record made in a group belongs to the chat** (`notes.group_id`); its
`user_id` only says who photographed it. Every corpus query goes through
`corpus._owned`: in a group, the group's records, which any member reaches;
in a private chat, the user's own records that belong to no group. So the
photographer finds a group's record in the group like everyone else, and a
private record never surfaces in a group. `groups` is keyed by our own id,
because Telegram's changes when a group becomes a supergroup: the middleware
moves the row on either half of the migration notice, and every record moves
with it.

**The bot takes a page in a group only when it comes with its subject** — a
"#word" anywhere in the caption of a photo, an album or a `.docx`
(`tags.from_caption`; an album's caption rides on one page, `albums.tag_of`
finds it). The author's decision, 2026-09-25: a course chat is mostly memes,
screenshots and talk, and a record costs about $0.38. The word is the
record's subject from birth, so **a group is never asked** which subject a
record belongs to, and a "#word" there only searches. That removes the
failure the stateless question could not survive in a chat, where the newest
record is everyone's and the next "#word" anyone's.

**What is not addressed to the bot never reaches it.** `middlewares.heard`
runs before a session is opened. In a group it lets through a command, a
message that is one "#word" and nothing else (`tags.is_bare` — "#дз на
завтра" is for the classmates), a photo or a file with a tagged caption,
every page of an album (judged whole in `_process_album`), and the migration
notice. Everything else is dropped with no session, no user row and no event:
a classmate who only ever said hello is not a user. What gets through and is
still not the bot's — an untagged album, a search that finds nothing, an
unreadable tag, a file that is not `.docx`, a notice — gets no answer in a
group; the missed search is still logged.

**Whether the bot sees a group's photos is decided in BotFather, not here.**
With privacy mode on — as it was on 2026-09-25 — a bot sees only commands and
replies to itself, unless it is an admin of the chat. The startup log says
which (`Groups:`); the welcome posted when the bot is added
(`handlers.on_joined`) names the fix, making it an admin with no rights, and
`on_promoted` says when that worked. Joining, promotion and removal arrive as
`my_chat_member` updates: the webhook subscribes to what is handled
(`dp.resolve_used_update_types()`), they get a session like messages do, and
a join is registered before a promotion, because being added straight in as
an admin is both and only the first match runs.

**Events name the group they happened in** (`events.group_id`) — whether a
group uses the bot week after week is the question the project exists to
answer. `group_joined` carries whether the bot can see the photos;
`group_promoted` and `group_left` carry nothing else. Limits are still the
photographer's page quota and the global cost cap; per group is task 41.

**Before adding an interface to the corpus, check `events` for whether the
last one was used.** `/notes`, `/note`, `/search`, `/retitle`, `/delete` and
`/pdf` were built, tested and deployed, never used once, and deleted.
`/stats`, touched once, stays on the menu beside `/start` and `/help`.

### The document

**A saved record goes out as a PDF.** Recognised notes are dense with LaTeX,
and `$\sum_{i=1}^{p} \rho(v_i) = 2q$` reads as noise until it is drawn, so all
three capture paths finish with `corpus.send_record`. Rendering is CPU-bound
and runs in a thread; if it fails for any reason the record is sent as plain
text. A record is never lost over its presentation.

**The document's look is one system, decided in `pdf.py` (task 36), and it is
copied from one file: the author's `матан 24.09.2026.pdf`.** Its values were
read out of that PDF — sizes, greys, rules, the column — not chosen by eye;
a change to the look is a change measured against it. It is what the group
receives, so none of it is left to reportlab's defaults:

- **Lato for the text, Computer Modern for the formulas**, as the reference's
  Lato and KaTeX. Lato 2 is bundled in `app/assets/fonts/` under its OFL
  licence: the Lato Google serves has no Cyrillic. Lato lacks some symbols —
  `∀ ∈ ⇒ ► ℝ` — and reportlab has no fallback of its own, so `pdf._text`
  sets every run of them in DejaVu; without it they print as empty boxes.
  Computer Modern has no Cyrillic either, and mathtext sets a `\text{кольца}`
  in a serif of its own, which is what the reference does too.
- **One scale and one rhythm.** Body 12 pt at a leading of 1.6, title 24,
  sections 18 and 14, formulas ×1.06. Heading levels are counted from the top
  one the record uses, so "##" sections look like "#" ones. The space between
  two blocks comes from `_space_before`, which knows what both of them are:
  lines of one paragraph sit at the leading alone, a blank line opens a
  paragraph, a display formula, a table or a drawing is set apart, and a run
  of display formulas is one close block.
- **The column is the reference's: 66 pt either side, 463 pt of text.**
  reportlab's frame pads its content by 6 pt inside the margins, and the
  margins allow for it; left out, every box as wide as the column ran 12 pt
  past its right edge.
- **A formula is a picture, and is made to sit like text.** It is lowered by
  its measured depth so its baseline is the line's, shrunk to the column when
  wider, and drawn with a quarter-point stroke — Computer Modern's hairlines,
  smoothed as pixels, came out a pale grey beside Lato. A zero-width space
  after an inline formula, where the page had a space, is the only place
  reportlab will break a line after an image.
- **A heading is held back and set in one group with what it heads**, a
  remark with its line, a table whole. The groups are built by hand and flat:
  reportlab's own `keepWithNext` nests one `KeepTogether` in another, the inner
  one reports an effectively infinite height, and the heading stays behind.
- **Every box beside the text has one anatomy**, the reference's
  "ЗАМЕЧАНИЕ": a 3 pt bar down the left, a label in spaced capitals (drawn by
  `pdf._Label` — a paragraph cannot space letters), the lines at the size of
  the text. A remark is grey throughout; a callout about the record carries
  its accent in the bar and the label. The explanation of task 38 is the same
  box in a tone of its own.
- **A graph is cut to what is drawn**, at one scale for every graph. A graph
  or a matrix name ("A =") followed directly by a table is set beside it — a
  blank line may stand between them, a line of text may not. A table is ruled
  under its header, and after its first column when that column names the
  rows; never caged in a grid. A table the composing stage used for layout —
  lines stacked with `<br>` in a cell, cells as long as sentences — is set as
  columns of text with no rules at all, and a header with nothing in it is
  not a header.
- **Lists hang**, bullets and the author's own "1)" and "2." alike.
- **A main formula is framed, larger (×1.2) and numbered "(1)", "(2)"** at
  the column's edge, through the whole record. When every formula stood at
  one size the one a section leads to was lost among the steps to it. Two
  sources mark one, and they are kept apart on purpose: what the author
  framed on the page is perception, and recognition writes it as `\boxed{…}`
  (framed words as `[рамка: …]`); which formula is a section's result is
  interpretation, and the composing stage marks it the same way, at most two
  a section — `compose._cap_marks` takes the frame off the rest and never off
  a frame the source already had. Older records' frames — `[в рамке: …]`, a
  bracket closed lines later, an array ruled with `\hline` — are read as
  frames too.
- **From page two the record's title stands over the text, and a record of
  more than one page is numbered "2 / 5"** — not "с. 2", which inside a
  record means a photographed page. The title draws its formulas; the
  running head, the file's own title and its name, and a chat listing get
  them as characters (`pdf.plain`: "2¹⁰⁰¹", never "$2^{1001}$" or "21001").
- **Markup never prints as its source.** `$$` on lines of their own is a
  display formula, `$$…$$` inside a line is a formula, emphasis pairs across
  a formula, and `~~…~~` is drawn struck through, the way the author crossed
  it out. A remark's quoted LaTeX goes through `pdf.as_formula`; its anchor
  stays raw, because it has to be found in the record as it stands.

→ "The document as the group got it"

**mathtext is not LaTeX, and a formula it refuses prints as its own source.**
`pdf.for_mathtext` rewrites what the model writes into what mathtext draws. It
drops the commands that do nothing to the layout (`\limits`, `\nolimits`,
`\displaystyle`), and `pdf._SYNONYMS` maps what LaTeX spells two ways to the
spelling mathtext knows (`\le` → `\leq`, `\mbox` → `\text`, …). A command ends
where its letters end — `(?![A-Za-z])`, because `\le` opens `\leq`, `\left`
and `\leftarrow` — which is also why the drop list needs no longest-first
sort. A sweep of about 120 constructs found the rest, and `test_pdf.py`
proves each one both rewrites *and* draws:

| Written by the model | Rewritten to |
|---|---|
| `\textrm{...}` | `\text{...}` — the same swap `\mbox` gets |
| `\tfrac{a}{b}` | `\frac{a}{b}`; a size variant with no meaning here, like `\displaystyle` |
| `\stackrel{a}{b}` | `\overset{a}{b}` |
| `\big(` `\Big(` `\bigg(` `\Bigg(` | the modifier dropped, the delimiter renders |
| `\xrightarrow{t}` | `\overset{t}{\to}` — a braced argument, one level of nesting (`\xrightarrow{\text{фермент}}`); deeper goes out as source |
| `\overbrace` / `\underbrace` | `\overline` / `\underline`; the grouping survives, the brace does not |
| `\begin{cases}`, `pmatrix`, `bmatrix`, `vmatrix`, `array`, `aligned`, … | `\left<delimiter>\substack{row \\ row}\right<delimiter>` |
| `\pmod{n}`, `\pmod 13` | `\quad(\mathrm{mod}\ n)` — a run of digits is one modulus, "(mod 13)" and never LaTeX's "(mod 1)3" |
| `\bmod`, `\mod` | `\ \mathrm{mod}\ `, `\quad\mathrm{mod}\ ` |
| `\textbf{…}`, `\textit{…}`, `\emph{…}` | `\mathbf{…}`, `\mathit{…}` with spaces kept as `\ `, lifted out of a `\text{…}` round them — inside `\text` mathtext reads no command and printed "¤extbf" |
| `"` | `\text{"}`, outside a `\text` |
| `\cline{a-b}` | dropped, argument and all, where the array is not drawn as a table |

So `\begin{cases} A \\ B \end{cases}` becomes `\left\{\substack{A \\ B}\right.`
and draws as a proper piecewise brace; `pmatrix` keeps its parentheses,
`vmatrix` its bars, and `array` loses only its column spec.

The environments lose two things. Column **alignment**: `\substack` centres
each row, so a wide matrix comes out ragged but readable — which is why a
matrix is still asked for as a markdown table, which keeps its columns. And
`&` means two things, so it is translated twice: a column separator becomes
`\quad`, while in the aligned family it marks where two lines line up and is
removed. **What is left is `\ce{...}`** — mhchem is a language, not a
command, and needs a rule in the prompt forbidding it or the drawing
contract.

**An array ruled inside is drawn as a table, not as a formula.** A display
formula that is nothing but arrays with a `|` in the column spec or a
`\cline`/`\hline` in the body — a polynomial divided "уголком" — goes through
`pdf.ruled_arrays` and is set as tables side by side: every cell a formula in
its column's alignment, so `\phantom` still lines the steps up; a line under
the cells a rule names; and the bar only along the rows with something on its
far side, which in a long division is the corner itself. An array barred at
both ends, `{|l|}` with `\hline`, is still the author's frame. → "Record 45,
a lecture on remainders"

**A formula mathtext refuses is a warning in the log**, carrying mathtext's
own diagnosis (`Unknown symbol: \xrightarrow` names the command) — the *last*
line of its message, which opens with a blank line and a caret — printed once
per distinct formula per document, because a macro the model cannot spell is
usually on every page of the record.
→ "mathtext, one record at a time"

**A drawing comes back as data, not a sentence about itself.** Rule 6 of the
recognition prompt asks for a graph as `[граф: 1-2, 2->3, 3-3]` and for a
matrix or table as a markdown table; `pdf.blocks()` draws both, and
`[схема: ...]` carries everything else. The two sides are one contract in two
files: change the syntax on either and the record prints the spec where the
drawing should be. Reading a drawing's structure is interpretation, and
nothing yet compares the runs' edge lists — `PLAN.md` → Known risks.

**A callout says what we already know, never what the model thinks.** The
boxes at the top of a record are built by `corpus._callouts` from the
`Note`'s own columns, so the document and the chat cannot disagree; `pdf.py`
receives a list of `Callout` and knows nothing about where a record came
from. A generic flag gives way to a specific one: the capture handlers and
`corpus._callouts` add "Прогоны распознавания местами разошлись" only when
nothing more exact is there to say, and the subtitle carries "нужна проверка"
either way.

**A remark sits beside the line it explains.** `corpus._remarks` turns each
`uncertain` entry into a `pdf.Remark` anchored on the text that was read, and
`render` sets it under the block that contains that text; one that anchors
nowhere goes to the end rather than nowhere.

**Adding is not forbidden; adding unmarked is.** The reference document puts
every addition in a marked box that says what the manuscript actually had —
*"в рукописи матрица плохо читается …, поэтому она восстановлена по рисунку
графа"*. The remarks are the first half of that standard; the second is stage
three, below — a separate call over the **trusted transcription**, in columns
of their own, printed as the bot's. Never from the call that reads the photo:
a box of "the main points" written from a photograph is exactly the fluent
retelling of a bad shot.

**A sentence that ran over a page edge is put back together, by code.**
`albums._continues` joins it only when both sides are ordinary prose — not a
table row, a list item, a heading, a display formula, a drawing or a
missing-page marker — the first half does not end like a finished sentence,
and the second begins in lower case; the page rule goes with the seam. Narrow
on purpose: joining two things that were not one sentence is worse than the
seam. → "The sentence cut by a page edge"

### Stage two: composing

**Reading and composing are two jobs with opposite requirements, and two
calls.** Most of the failures above are the interpretive faculty leaking into
the literal job, so `compose.py` is a second call over the text the runs
already agreed on, and it **never receives the photograph** — the worst
failure this project has reproduced needs an image to invent from. Its own
job — heading levels, bold terms, a formula on its own line, lines into a
list — is transformation. → "Why reading and composing are two calls"

**Its output is checked against its input by code.** This is not the
verification pass forbidden above: that compared text with a photograph,
which is perception again; these compare text with text. The multiset of
numbers must be identical (list markers stripped first, since rule 8 lets the
composer renumber a list), the count of `[неразборчиво]` must be identical,
and the document must not come back materially shorter. Any of those, and the
record is the one stage one produced: off, refused or failed, the worst case
of the stage is the pipeline without it.

**One thing is repaired rather than refused: a heading that is not one.**
`_demote_invented_headings` takes the marker off three shapes and leaves every
word where it was — a heading with no letters (`## 4.`), one that does not
start with a word or a number (a formula line promoted), and one whose next
line of prose begins in lower case (the first half of a sentence). What it
removes is markup the stage itself added, so the numbers, marks and length
the guards compare cannot move; it runs **before** `_refusal` so that what was
checked is what is stored. The count goes to the log and to `note_processed`
as `compose_demoted`. → "Headings the composer invented"

**Main-formula marks are capped, like headings are repaired.** Rule 9 of
`prompts-compose-v3.md` asks the stage to frame a section's main formula —
a reading of the page, and emphasis on everything is emphasis on nothing — so
`_cap_marks` keeps two of the stage's own frames a section and unwraps the
rest, leaving the formula where it was. A frame already in the source came
from recognition, which is to say from the author's pen, and is never touched
or counted. The count goes to `note_processed` as `compose_unmarked`.

**Word drift is measured, not refused on.** Rule 6 of the composing prompt
asks for `### Определение` over a definition, so a word guard would refuse the
prompt's own instruction. The count goes to the log and to `note_processed`
until someone decides what a large one means.

The stage's own ceiling and retry policy are in "Concurrency ceilings".

### Stage three: what the bot adds

**`explain.py` explains the hard places and sums the record up — and prints
it as the bot's.** The reader was not at the lecture: a step skipped, a
symbol never introduced, the lecturer's context left unsaid. The stage adds
what a classmate who was there would add, in the flow of the material, and a
short summary at the end — the author's decision, 2026-09-24. Like the
composer, it never sees the photograph.

**Two steps, because one did not work on the live model.** Asked to explain
and search in one call, `gemini-3.8-flash` searched for nothing — asked for a
quote from a found source, it wrote plausible textbook quotes from memory
with no search behind them. A short request of its own, "find a source for
this", it does search. So one call writes the explanations and the summary
as strict JSON, over the composed text numbered by `pdf.numbered_for_reading`
the way the page will be numbered ("(3)" in an answer is "(3)" on the page),
and each explanation then gets a call of its own with Google Search on
(`prompts-explain-source-v2.md`), in parallel. → "What the model did with a
search tool"

**Two guards, both in code, hold what it may add.**

- An explanation is printed only with the sources its own search call
  returned, read from that call's grounding metadata — never from anything
  the model writes about its sources, which is how the quotes from memory
  above would have got onto the page. One whose search found nothing is
  dropped and counted (`explain_unsourced`). The reader cannot check a claim,
  so the page has to say where it is from.
- The summary restates the record and may not state a number the record does
  not carry; one that does is dropped (`summary_refused`). A new number in the
  one box that claims to say what the lecture said is the model inventing.

**Sources are ranked, never filtered.** A search returns what it returns — a
university's course beside a shop's page — and an explanation shows three.
`explain._TIERS` decides which three and in what order: scientific sites
(universities, academies, scientific publishers, arXiv) first, then
encyclopedias, then study sites, then everything else; within a tier the
search's own order stands. Nothing is dropped for being everyday — the
author's decision, 2026-09-25, after the first live run printed a shop's page
as an explanation's source and put `nsc.ru` behind `codechick.io`. The site
is read from the grounding chunk — `web.domain`, else `web.title`, which on
the Gemini API *is* the registered domain, `wolfram.com` and never
`mathworld.wolfram.com` — and never from the link, which is Google's
redirect. **One link a site:** a second page of one prints under the same
name and reads as a duplicate, so the next site takes its place. The lists
are kept by hand, in registered domains, and kept short: a site nobody listed
is "everything else", so a missing name costs a place and never a source.
`prompts-explain-source-v2.md` asks the search the same way round, so that
there is more to rank; v1 is what the records before that date were sourced
with.

**Stored apart, printed as the bot's.** `notes.explanations` (JSONB, with the
sources) and `notes.summary` (text), never mixed into `markdown`. The PDF sets
each explanation under the line it quotes or the formula it numbers — after
the remarks of that line — and the summary last, after a section rule, both
in a green no other box has, labelled "Пояснение бота" and "Итог · составлен
ботом по тексту записи". At most eight explanations; an anchor found nowhere
puts its box at the end, like a remark's. Rule 6 holds for the third call as
for the second: limits before it, `pages=0`. A Gemini 3 model's
Google search is billed per query it runs, on top of the tokens —
`GROUNDING_USD_PER_QUERY`, times the queries the call's grounding metadata
lists — so the daily cap sees it. → "What a record costs" Off, refused or failed, the record goes out as it would have without the
stage. `.docx` does not go through it: that path bypasses the model entirely.

### The matrix against the graph

**`graphcheck.check` checks a matrix against the graph drawn beside it.**
Whether a cell is 0 or 1 is decided by the edges, not by a vote: the
adjacency is computed from the edge list and compared, and an incidence
matrix is checked the only way its unknown column order allows — every column
holds the two ends of one edge, every row sum is a degree. It returns
`mathcheck.Issue`, so findings ride the existing `issues` column, callout and
critical downgrade, and it parses with `pdf.blocks` and `pdf.parse_graph`, so
the check and the picture see one structure.

**It stays quiet when the page does not settle it** — a cycle, where as many
edges as vertices make a square table read as either matrix; labels that don't
match the vertices; a bare matrix of *named* vertices, whose row order cannot
be known. A confident wrong "does not agree with the graph" costs more than
silence. → "Numbers the agreement could not see"

---

## Concurrency ceilings

Two of these are settings and three are computed from one of them, so raising
one number never leaves another quietly cutting the work short:

| Constant | Where | Value |
|---|---|---|
| `API_SLOTS` | `services/vision.py` | `10` — Gemini answers a bigger burst with 429s. The semaphore is built from it and `albums.py` counts waves with it |
| `VISION_CALL_TIMEOUT_S` | environment | 30 s, the range is 5–180. One call over **one page**; the three ceilings below are computed from it |
| `COMPOSE_CALL_TIMEOUT_S` | environment | 240 s, the range is 30–600. One call over **the whole record**, so nothing derives from it and it derives from nothing |
| `EXPLAIN_CALL_TIMEOUT_S` | environment | 240 s, the range is 30–600. The writing call over **the whole record**, sized like the composing stage's and for the same reasons; it takes an `API_SLOTS` slot the same way and also runs after `process_batch` |
| `_SOURCE_TIMEOUT_S` | `services/explain.py` | 90 s — one search over one short claim. Up to eight of them run at once, each on an `API_SLOTS` slot |
| compose's slot | `services/compose.py` | one of the `API_SLOTS`, taken from the same semaphore and held for the whole call — about 40 s measured, up to `COMPOSE_CALL_TIMEOUT_S` per attempt, where a page holds one for seconds. It runs after `process_batch`, so `_ALBUM_TIMEOUT_S` does not cover it |
| `RUN_WORST_CASE_S` | `services/vision.py` | `(pauses + 1) × call + sum(pauses)` — every attempt timing out. 93 s at the default |
| `_CONSENSUS_TIMEOUT_S` | `services/vision.py` | `RUN_WORST_CASE_S × TIMEOUT_MARGIN` — 120 s at the default |
| `_ALBUM_TIMEOUT_S` | `bot/albums.py` | `waves × RUN_WORST_CASE_S × TIMEOUT_MARGIN`, waves = ⌈`MAX_ALBUM_PAGES` × `VISION_RUNS` ÷ `API_SLOTS`⌉ — 362 s at the default. Normative: raising it is allowed, lowering it is not |
| `_QUIET_SECONDS` | `bot/albums.py` | 3 s of silence **since the last `announce`** closes an album, provided every announced page has downloaded |
| `_COLLECT_MAX_S` | `bot/albums.py` | 60 s from the first page, so a stream that never goes quiet can't hold a session for ever |
| `max_overflow` | `db/session.py` | 15 — `MAX_ALBUM_PAGES` updates each hold a session through the debounce, and the one that wins the batch holds its own for the whole album |

`TIMEOUT_MARGIN = 1.3` is the ratio the old hand-written 120 s held to 93 s.
The startup log prints all four timeouts: three are computed, and the only way
to know what a deploy runs on is for it to say so.

**The two timeout settings are not interchangeable.** Recognition is one call
per page, and every album ceiling derives from it; composition is one call
over the whole record, so its wait grows with the album. Composition waiting
on the page ceiling cost a record its markup — `PLAN.md` → "Fixed since: the
ceiling the composer waited on". Three pages compose in about 43 s on
`gemini-3.8-flash`, hence 240 s.

**Composition does not retry a timeout.** It makes at most two calls, the
second for a 429, a 503 or a dropped connection. `vision._should_retry` says
a timeout is worth another call, which is right for a page, where a hung
connection is the usual cause; at a ceiling of minutes a call that reached it
was working, and waiting again doubles the window in which a deploy cancels
the background task. Every attempt is written to `ai_calls`.

Raising `VISION_CALL_TIMEOUT_S` is what a slower or thinking model needs, and
the cost is not linear — at 90 s the album ceiling becomes 1064 s. That fires
only when calls hang; what it really buys is exposure, because any deploy
cancels the background task an album runs in.

The two group ceilings, `_CONSENSUS_TIMEOUT_S` and `_ALBUM_TIMEOUT_S`, use
`asyncio.wait`, never `wait_for`, and cancel the stragglers in a `finally`;
`wait_for` is only for a single call. Cancelling the group would discard the
`CallStats` of runs that already returned — and those calls were billed. An
orphaned run also keeps making paid calls with the result thrown away.

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
| `DAILY_COST_LIMIT_USD` is global, not per user | **two users** — reached with the group | one person, or one group, can exhaust the day's budget for everyone; task 41 |
| In a group every album page is downloaded before the album's tag is known | **a chat that shares many photo albums** | bandwidth and memory spent on albums the bot then drops unread |
| `limits.consume` takes no row lock | **concurrent uploads by one user** | the page quota undercounts |
| DB pool is 5 + 15 | **~20 updates in flight** | connection checkout starts timing out |
| `_API_SLOTS` is a per-process `Semaphore(10)` | **tens of active chats** | the queue to Gemini grows into timeouts |
| Stage three searches up to eight explanations at once | **two records finishing together** | the searches hold most of the ten slots for ~20 s, and another chat's pages queue behind them |
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

**That rule has three exceptions, each made after the failure was
reproduced — two in `photoguard._line_height` and one in the threshold it is
compared with.** First the sentinel: `UNMEASURED_LINE_HEIGHT`
names it, and the line-height criterion is skipped when the height was not
measured, instead of `0.0` being read as a very small line. Then the
measurement itself (task 35): the ink threshold is **Otsu** rather than a
rank, so it finds the valley between paper and ink wherever they sit; the
pitch is the **median distance between bands of ink**, so a drawing or an
empty margin no longer stretches it; and there is **no three-line minimum** —
a single band answers with its own height, a lower bound on a pitch and so
the right kind of answer for a threshold that looks for one.
→ "The line height photoguard could not measure". Then the threshold (task
43): `MIN_LINE_HEIGHT_PX` went from 20 to 16. Telegram sends a photo at 1280 px,
and record 45's notebook, written densely, measured 22.75 px on four pages
that read well and 19.75 px on the fifth, which 20 cut off — retaken from the
same distance it would have measured the same. → "Record 45, a lecture on
remainders"

What those exceptions left alone, and is still open:

- **`MIN_LINE_HEIGHT_PX` is calibrated from above only.** It is still the
  pitch in pixels of the compressed frame. Record 45 showed 20 cutting off a
  legible page; nothing yet shows where below 16 a page stops being legible —
  a single photo refused at 15.0 px is the only frame measured there, and
  whether it could have been read is unknown. The module's own CLI over a
  folder of real pages would settle it. The evidence path for that stands:
  `albums.process_page` keeps all four frame metrics on every skip and logs a
  refusal against its thresholds, and the events carry them per page.
- **`_paper_box` still has its edge.** It thresholds at `0.82 x percentile99`,
  so a bright highlight raises the percentile, the mask shrinks to the glare,
  `paper_fraction` collapses into "подойдите ближе", and every metric after it
  is measured on the glare instead of the page.
- **All four thresholds apply to the compressed image**, so `IMAGE_MAX_SIDE`
  silently recalibrates them.

**`mathcheck.check_chains` is worked around, not fixed.** It reads any line
with two "=" as one chain of equalities, and a line of modular arithmetic set
1001 against 32 across a "⇒" and a "≡" — a critical finding and a
`needs_review` on record 45. `vision.arithmetic_issues` is what both photo
paths call: the constants check sees the page as it is, the chain check sees
it with every line holding a relation other than "=" blanked, so the lines it
does report keep the numbers mathcheck gave them.
→ "Record 45, a lecture on remainders"

**`consensus.extract_numbers` is worked around, not fixed.** It treats every
numeric literal as a value to compare — list markers and subscripts included —
so `compare()` reports a divergence wherever the runs align differently.
`vision.meaningful_divergences` keeps a position only when at least two runs
read it as *different numbers*, since a number against a gap is an alignment
artefact; drops a position where no reading has a majority **and** a gap is
among the variants, since the runs there produced different counts of numbers
rather than different readings of one; and prints an identical line once,
since the message never carries the position.
→ "Numbers the agreement could not see"

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
    middlewares.py    DB session, user and group injected; group chatter dropped
    albums.py         album buffer and assembly
    corpus.py         tags, search by tag, and a record as a file, scoped to its chat
    tags.py           what a #tag is, and where a record's topics come from
  services/
    vision.py         Gemini: prompt, response parsing, three runs
    images.py         compression
    limits.py         spend limits
    compose.py        stage two: the trusted transcription, formatted
    explain.py        stage three: hard places explained with sources, a summary
    docx.py           .docx -> markdown, no model call
    pdf.py            a record as a PDF: formulas, graphs, tables, remarks
    photoguard.py     ready-made
    consensus.py      ready-made
    mathcheck.py      ready-made
    graphcheck.py     a matrix against the graph drawn beside it
  assets/
    fonts/            Lato 2 and its OFL licence — the document's text face
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
FINDINGS.md          the evidence behind the rules in this file
prompts-v3.md        TRANSCRIBE_PROMPT, read from disk at import
prompts-v4.md        the longer variant under test, behind PROMPT_FILE
prompts-v5.md        extraction only — no rule about how a page should look
prompts-compose-v1.md  stage two: markup over text already trusted
prompts-compose-v2.md  the same job, said as instructions rather than bans
prompts-compose-v3.md  v2, and the main formula of a section framed
prompts-explain-v1.md  stage three: explanations and a summary, as JSON
prompts-explain-source-v1.md  stage three: the search for one explanation's source
prompts-explain-source-v2.md  the same search, asked for science first
prompts-v6.md        v5, and the author's frames written as \boxed{...}
```

The prompt files hold the prompts as plain text. `vision.py` doesn't copy
one — it reads `PROMPT_FILE` from the repo root at **import time**, so the
file has to ship with the deploy or the process dies at startup, and editing
it changes the prompt without touching any Python.

The `.pdf` records and Railway log dumps in the repository root are **not**
tracked — `.gitignore` covers `*.pdf` and `*.log`. They are the evidence
behind `FINDINGS.md`, the albums the arms were measured on and the logs a
number was read out of; nothing reads them at runtime or in the suite. A
record is a user's page of notes, and the corpus lives in the database, not
in git.

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
COMPOSE_THINKING_LEVEL=low
EXPLAIN_ENABLED=false
EXPLAIN_MODEL=gemini-3.5-flash-lite
EXPLAIN_PROMPT_FILE=prompts-explain-v1.md
EXPLAIN_CALL_TIMEOUT_S=240
SOURCE_THINKING_LEVEL=low
PROMPT_FILE=prompts-v3.md
IMAGE_MAX_SIDE=1500
IMAGE_QUALITY=85
ALLOW_UNPRICED_MODEL=false
MIN_MARKDOWN_LEN=40
MAX_ALBUM_PAGES=10
LOG_LEVEL=INFO
```

A missing required variable must crash the app at startup, not on the first
request.

**A model setting is coupled to its price.** A model absent from
`PRICE_PER_MTOK` in `core/config.py` writes `cost_usd = NULL`, the `SUM`
behind `DAILY_COST_LIMIT_USD` skips `NULL`, and the cost breaker stops working
with nothing visible to show for it. So a validator refuses to start on an
unpriced `VISION_MODEL` or `COMPOSE_MODEL`, and changing either means adding
its price in the same commit. `PRICED_MODEL_SETTINGS` and
`Settings.unpriced_models()` are one list, read by both the refusal and the
warning below, and a test asserts the two cover the same settings: any future
setting that names a model goes in that tuple and nowhere else.

**A price is the Standard tier's, and an announced change is written down
with its day.** A plain call is billed at the Standard tier; the Batch and
Flex rows of the price page are half of it, and one of them stood in
`PRICE_PER_MTOK` for three days, so the cap let through twice its figure.
`PRICE_CHANGES` holds a change the page has already announced — Gemini 3.8
Flash doubles on 2027-01-01 — and `config.price_per_mtok` reads it by the day
of the call, because a price change left to memory is the same silent
halving of the cap. → "What a record costs"

**`ALLOW_UNPRICED_MODEL=true` runs one anyway**, with a warning in the deploy
log on every start. Trying a model before its price is published is a real
thing to want; the refusal exists so the state is chosen rather than stumbled
into. In that state `DAILY_PAGES_PER_USER` alone guards the spend, so raising
both at once leaves nothing. Turn it back off once the model is priced: left
on, it disarms the next swap silently, and the rows written meanwhile can
never be priced. → "What a model change broke"

`COMPOSE_ENABLED` turns stage two on and `EXPLAIN_ENABLED` stage three; both
are off by default, and `EXPLAIN_MODEL` is priced by the same validator as the
other two — it is in `PRICED_MODEL_SETTINGS`. `EXPLAIN_CALL_TIMEOUT_S` has the
composing stage's range, for its reasons.
`COMPOSE_CALL_TIMEOUT_S` ranges 30–600: under 30 s the stage refuses itself
by construction — the shortest composition ever measured on a model strong
enough to compose took 41 s — and over 600 s the wait outlives the background
task it runs in, which a deploy cancels, so the record goes out unformatted
anyway.

**`VISION_MEDIA_RESOLUTION` and `VISION_THINKING_LEVEL` are knobs on *how*
the model is asked.** `unset` means the field is not sent at all — Gemini's
own default, and bit-for-bit the call every quality finding was made on. An
unknown value is refused at startup, because a knob that silently does nothing
is how an experiment comes to compare a setting against itself. Media
resolution was measured and does nothing here: leave it `unset`. Thinking
level is still untouched and is now visible in `ai_calls.tokens_thought`;
leave it `unset` until that column has a few albums in it, because turning it
down changes how the model reads, and it would be done for a budget reason.
It does not reach `compose`, which builds its own config.

**The composing call and the source searches think `low`, and recognition at
the model's default.** `COMPOSE_THINKING_LEVEL` and `SOURCE_THINKING_LEVEL`
take the same values and are refused at startup the same way. Both were
measured on record 45 before being set: the composition came back with the
same headings and frames at half the price, the searches grounded every
explanation with fewer queries at under half the price, and both in a third of
the time. Recognition is the one left at the default, because turning it down
changes how a page is read, and that is an arm to run on one album, not a
setting to try — and the one arm run so far (record 47 against 46) wrote
formula environments bare across lines, which printed as source. A search at
`low` that answered without running a search is made once more at the
model's default (`explain._search`): three of six did so on record 47, and
their explanations would have been dropped for having no source. "minimal" is
a level the SDK knows and `gemini-3.8-flash` refuses with a 400. → "What a
record costs"

**`seed` is deliberately not a setting, and `temperature` stays at 1.0.**
Three runs made identical would send `text_agreement` up without touching
accuracy — the instrument inverted rather than merely broken.

`VISION_CALL_TIMEOUT_S` is the timeout the album ceilings are computed from
(see "Concurrency ceilings"); a slower model needs it raised. A bare
`TimeoutError` has an empty message, so `vision._short_error` writes the
exception's type into `ai_calls.error` instead. → "What a model change broke"

`PROMPT_FILE` names the prompt `vision.py` loads at import, so a variant can
be tried on the deployed bot and rolled back by changing one variable. A name
that isn't in the repo kills the process at startup, deliberately.

**The startup log is the instrument's label, and what it leaves out is
unmeasurable.** Its first line is `Recognition: <model>, N runs` — the run
count because a page scored on two runs agrees more easily than one scored on
three — then the prompt file and its word count, image compression, the
compose stage, the two call knobs and the four timeouts. What is still
missing is the other direction: a **record** does not say which prompt made
it, so pooling albums across days rests on remembering — `PLAN.md` → "Where
the quality work stands", gap 3.

---

## Tests

The suite is offline: no network, no Gemini, no Postgres. Everything that
needs a database runs on in-memory SQLite through `aiosqlite`.

| File | Covers |
|---|---|
| `test_parse_response.py` | the model's reply: garbage, the ```json fence, missing fields, wrong types, and LaTeX written with one backslash |
| `test_limits.py` | `check_limits` / `consume` — the money-critical path |
| `test_reliability.py` | retry classification, one owner per album batch, spend surviving a rollback |
| `test_vision_pure.py` | `_should_retry`, `_cost_usd`, `total_cost`, `_verdict` and the numbers that vouch for a page, `_short_error`, what an unparseable answer says and earns, and the chains mathcheck is not shown |
| `test_albums.py` | `_assemble` aggregates and the marker it leaves where a page could not be read, the three reasons a page is dropped and the two that only mark it, `process_batch` survivor logic, an album's tag from whichever page carries it, the frames an album is refused for before it is read |
| `test_docx.py` | heading styles to markdown, title derivation |
| `test_images.py` | the 1500 px cap, EXIF orientation, JPEG output |
| `test_config.py` | the `DATABASE_URL` scheme rewrite, `VISION_RUNS >= 2`, stage three off by default with its model priced and its timeout bounded, and that `PROMPT_FILE` really selects the prompt — proved in a subprocess, because reloading `vision` rebinds its dataclasses under the rest of the suite |
| `test_handlers.py` | `_split_message`, the catch-all reply, and in a group: an untagged album left alone, a tagged record owned by the chat and filed at once, a file that is not `.docx` unanswered, the welcome and the admin hint, and the three membership events; an album with a refused frame asked for again unread |
| `test_middleware.py` | session per update, rollback, the early commit of a new user, what a group chat lets through before a session is opened, a group registered once and moved to a supergroup's new id, and a row two album pages race to insert |
| `test_graphcheck.py` | the matrix against the graph: what it must catch, and — the longer half — every shape it must stay quiet about |
| `test_corpus.py` | filing a record under a subject, finding it by a topic, statistics, the flags rebuilt from JSONB as callouts and as anchored remarks, the LaTeX a remark quotes marked to be drawn while its anchor stays raw — and that no query reaches another owner's records: a group reaches its own, a private chat the user's own, neither the other's, and a "#word" in a group never files |
| `test_tags.py` | what a #tag normalizes to, what counts as one, which topics a record yields, the tag in a caption, and what counts as a search in a group |
| `test_wiring.py` | router order in `main.py`, that every command the bot answers has a menu description, and that membership updates are subscribed to, given a session, and matched join before promotion |
| `test_webhook.py` | that the endpoint answers before processing, and still checks the secret |
| `test_photoguard.py` | the rules in photoguard this project has edited: a line height that could not be measured is not a small one, what the measurement answers on pages whose pitch is known by construction, and a densely written page read rather than refused |
| `test_explain.py` | stage three: off by default, only text ever sent, a writing call in strict JSON with no search and a search call per explanation, the record sent numbered, sources read from each search's grounding and an explanation whose search found nothing dropped, the sources ranked science first with an everyday one kept behind them, the summary's numbers guard, never more than eight, LaTeX with single backslashes surviving the JSON, the grounding fee in the bill, and a failed search costing only its own explanation |
| `test_compose.py` | stage two: that it is off by default, that the photo never reaches it, every guard that makes it refuse itself, the ceiling it waits on, which failures earn a second call, which headings are taken back, and the two main-formula marks a section it may keep while the author's frames are never touched |
| `test_pdf.py` | how a page is parsed into blocks, `$$` on lines of their own, escaping and emphasis across a formula, the LaTeX mathtext refuses and the environments it now draws through `\substack`, graphs read back from `[граф: ...]` and cut to size, a graph beside its matrix, the author's frames in every notation and main formulas framed and numbered, congruences, bold words in a formula, a long division drawn as a ruled table, a title's formula drawn and turned into characters where it cannot be, heading levels, the rhythm, groups that are never nested, one anatomy for every box, the formula's serif, baseline and width, the page furniture, that nothing unreadable ever sinks the document — and that no file under `app/` carries an invalid escape sequence |

`tests/conftest.py` does two things without which nothing imports: it fills
the five required environment variables with placeholders, and it teaches the
SQLite compiler to render `JSONB` as `JSON` — a test-side adapter for the
sqlite dialect only; `app/db/models.py` stays PostgreSQL.

Deliberately **not** covered: `consensus` and `mathcheck`, which arrived with
their own tests; `photoguard` beyond the two rules this project changed; and
the photo and document pipelines end to end — those break on every
reordering of a handler, and the pipeline is not settled yet.

One test is skipped unless `TEST_DATABASE_URL` points at a real Postgres:
`test_spend_survives_main_rollback`, which needs two genuinely separate
transactions.

---

## How to work in this project

- **Write the plan of changes first, then the code.** No size threshold — a
  one-line, single-point change still gets its plan stated before any edit.
  "It's just one line" is not a reason to skip straight to code. If the plan
  is satisfactory and leaves no open question, carry it out straight away;
  stop and ask only when it holds a decision that is the user's to make — a
  trade-off with no clear default, a change of scope, a conflict with
  `PLAN.md` or this file — and give a recommendation with the question.
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
  and readability are the product itself — see "The document"
- Social features, sharing, friends
- Caching, queues, microservices, Docker, CI
