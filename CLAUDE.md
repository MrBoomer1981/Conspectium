# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read at the start of every session. **Update it with every architectural
decision**, in the commit that makes it.

It holds the rules, each with its reason in a sentence, and how the system is
built. What a rule was bought with — the failure, the album, the numbers — is
in `docs/FINDINGS.md`, and a `→ "…"` after a rule names the section there.
The work and its order are in `docs/PLAN.md`, the document's look in
`docs/BRAND.md`, and the details of a mechanism in its module's docstrings.

---

## What this is

**SUM** — the Telegram bot `@sum_konspictiumbot` — for a **university group**.
One person photographs a handwritten page of a lecture, and everyone in the
group gets back a PDF they can study from without having been there: the
lecture set out by topic, its formulas drawn, its hard places explained,
questions to check oneself at the end — the study version, built from the
record the bot reads and keeps (2026-10-08). **Everything the
bot adds stands in a marked box with its sources**, never woven into the
author's text. The records accumulate into the group's corpus, and a "#word"
finds one again by its subject or by a topic read off its headings.

Four decisions the rest follows:

- **The document is the product.** The corpus is what documents accumulate
  into — a consequence, not the goal. Given "make the document better" or
  "build another way into the corpus", choose the document. The app of
  phase F (2026-10-02) is where a group studies from its documents, built
  after them and out of what they hold. → "Moved from CLAUDE.md, 2026-10-01"
- **Its quality is not traded for its price** (2026-09-29). A saving leaves
  the document as it is — a model that reads as well for less, a call paid for
  and thrown away. A candidate that might touch the reading is measured on an
  album already read, and the check against the photographs decides, not the
  price. → "What a record costs"
- **Marked is the whole licence to add, and the document never talks about
  how it was read** (2026-09-25). The reader who most needs an explanation was
  not at the lecture and cannot tell an invented sentence from a remembered
  one. No reading that could have been another, no "в рукописи", no page read
  without a second opinion: a remark is an error the code found in the work,
  at its place. → "Remarks about the reading"
- **Many users.** A group is several people around one chat, and "there is
  only one user" never makes a design correct. A shortcut that breaks only
  under concurrency is recorded under "Scale debt", not called done.

The question the project exists to answer is whether a group uses this
weekly — not launch, growth, revenue or scale.

---

## Who decides

Two owners, by area, since 2026-09-30; `README.md` maps every area to its
code.

- **The CEO** — the interface and the product for students: what the bot
  says and does in a chat, the document the group gets, how a "#word" finds
  things, and the app (2026-10-02).
- **The CPO** — the database and the model: schema, migrations and queries;
  recognition, prompts, the model stages and their measurements; cost and
  limits; the infrastructure.
- **Both** — the order of work in `docs/PLAN.md`; three sections of this
  file, "Inviolable rules", "Established experimentally" and "What NOT to
  do"; and the contract between the prompts and `pdf.py` — the syntax of a
  graph, a table, a frame, a drawing, a definition's heading — which one side
  writes and the other draws. Where they disagree, what is stays as it is.

**Since 2026-10-01 the CEO's word is enough in every area** — the CPO's and
what is shared included — agreed with the CPO beforehand. The CEO changes a
prompt, a model setting, the schema or a rule here without waiting, and the
change is still logged for the CPO to read. It is one way: the CPO's change
in the CEO's area, or in what is shared, waits for the CEO.

"The author" here and in the plan is the owner of the area a decision falls
in, and both for what is shared. A decision dated before 2026-09-30 was made
when the CEO was the only author, and stands until the owner of its area
revises it.

In a session:

- **Whose session it is**, `git config user.name` says: `Sokrat` is the CEO,
  any other author the CPO.
- **Start with what the other pushed**: `git fetch`, then
  `git log --format='%h %an %as %s' HEAD..origin/main` and the lines of
  `docs/PLAN.md` → "Plan changes" waiting for this person's word. Say what
  changed, in whose area, and anything that breaks a rule here.
- **In the CPO's sessions, the CEO's area needs the CEO's word.** Before
  changing a text students read, a command, the document's look, or what is
  shared, ask whether it is agreed, and say so in the commit. In the CEO's
  sessions every area is open. A migration is named to the other before it
  is pushed, whoever writes it: two written at once give Alembic two heads,
  and the deploy stops.
- **Every change to `docs/PLAN.md` beyond a task's checkbox and its owner's
  line in "State", and every change to a rule here, is a line in "Plan
  changes"**, in the commit of the work it belongs to. One the CPO makes in
  the CEO's area, or in what is shared, waits there for the CEO's word; the
  CEO's are accepted as written.
- **One piece of work, one commit** (the CEO, 2026-10-10: «всегда отправляем
  меньшим кол-вом коммитов»): its code, its lines in `docs/PLAN.md`, the
  documents and `README.md` go in together. A push carries as few commits
  as the work it ships.
- **Pull before pushing, and never force-push `main`**: both push to it,
  GitHub's free plan cannot protect a private repository's branch, and every
  push deploys.
- **Every push carries `README.md` up to date** (the CEO, 2026-10-07): its
  plan of development first — the phases, what is done, what is under way
  and whose, what comes next — read off `docs/PLAN.md` → "Progress" and
  "State". In the commit of the work, never a push of its own: every push
  deploys, and a deploy cancels what is being processed.

---

## Where it stands

- **Production** is one Railway service with PostgreSQL, serving the CEO's
  private chat and one course chat. Task 63's parts — the repeats, the move
  into a group, the whole notebook, the semester — are on branch `task-63`,
  off production until the CEO debugs them (2026-10-13): what this file says
  of them is the branch's. Railway deploys `main` on every push; the
  `Procfile` runs `alembic upgrade head`, then uvicorn. A deploy cancels
  whatever is being processed at that moment.
- **Phases** A — reliability, a record has to exist; B — the ideal record,
  the explaining stage and a PDF that never prints raw LaTeX; C — the group, a
  record owned by the chat — are done. **D, the subject**, set on 2026-09-30:
  a group adds the bot by itself, spend is counted per group, a subject's
  records come back as one document on command, the document has a look of
  its own, materials uploaded under a subject are found by "#word" —
  `docs/PLAN.md` → "Where this is going, decided 2026-09-30". **E, any
  material**, set on 2026-10-02: a record from a board, a recording or a
  film as from a notebook, and the subject whole with its earlier lectures;
  **F, the app**: a Telegram Mini App where a group studies from its
  records. Both after 56 and 47, the records' quality first — "Where this
  is going, decided 2026-10-02". What is under way is "State" there.
- **What production runs**, as last read off the startup log, 2026-10-08 —
  the log is the authority, and `docs/PLAN.md` → "What production says" the
  record of the first readings: recognition on `gemini-3.8-flash`, three
  runs, `prompts-v11.md` since 2026-10-10 — v6 with a drawing that is data
  written as data, the CEO's switch — thinking at the model's default; composition on,
  `gemini-3.8-flash`, `prompts-compose-v4.md` since 2026-10-06, thinking
  `low`; the explaining stage on,
  `gemini-3.8-flash`, its searches at `low`, `prompts-explain-v3.md` since
  2026-10-08, the teacher's boxes since 2026-10-03; sketches drawn again from
  the page the night of 2026-10-11 and archived the next morning with task
  54's cut-outs, the CEO's word (task 101); a call's ceiling 90 s. **The
  code's defaults are not these** — `gemini-3.5-flash-lite`, `prompts-v3.md`,
  both stages and the sketches off, 30 s — so a deploy that lost its
  variables reads worse, and its startup log says so.

---

## Stack

- Python 3.12
- FastAPI — the bot's webhook, one process
- aiogram 3.x — webhook only, no polling
- SQLAlchemy 2.x (async), Alembic, PostgreSQL (a Railway addon)
- Google Gemini — recognition, composition, and the explanations, sourced
  through its Google Search tool. The model is a setting, not a fact about the
  stack: it has changed twice, and the startup log names it
- Pillow and numpy — images; pypdfium2 — a PDF's pages drawn as pictures
  (task 100), PDFium under its Apache and BSD licences, where PyMuPDF's is
  the AGPL
- reportlab and matplotlib — a record as a PDF; formulas drawn by MathJax 4
  in V8 (mini-racer), rasterised by resvg-py, with mathtext behind it (task 99)
- Railway — hosting

No dependency without an explicit need. Redis, queues, workers, Docker and CI
stay out — not because the product is single-user, but because the second
user hasn't arrived; "Scale debt" says what that postpones.

---

## Development commands

    pip install -r requirements-dev.txt
    pytest                                           # the whole suite, offline
    pytest tests/test_parse_response.py::test_name   # one test
    pytest -k parse_response                         # by name, across files
    alembic revision -m "description"                # then hand-write the id
    alembic upgrade head
    uvicorn app.main:app --reload                    # the webhook needs a public URL, e.g. ngrok

- `app.core.config.settings` is built from the environment at import, so
  anything importing `app.*` needs the five required variables: copy
  `.env.example` to `.env` first, or `alembic` and `uvicorn` die with a
  validation error. `pytest` is the exception — `tests/conftest.py` fills the
  five with placeholders — but `settings` still reads `.env` for everything
  else, and a `.env` set the way production runs fails the tests in
  `test_config`, `test_compose` and `test_explain` that pin the defaults.
  Move it aside before blaming the change.
- `asyncio_mode = "auto"`: async tests need no marker. One test needs a real
  PostgreSQL and is skipped without it:
  `TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db pytest`.
- `.python-version` pins 3.12, which Railway runs. The suite also runs on
  3.11, in a virtualenv built from an explicit interpreter, bypassing the pyenv
  shim: `~/.pyenv/versions/3.11.9/bin/python -m venv .venv`, then
  `.venv/bin/python -m pip install -r requirements-dev.txt` and
  `.venv/bin/python -m pytest` — `python -m`, because a venv's scripts carry
  the path it was built at and fail with "bad interpreter" once the
  repository moves.
- Revision ids are hand-written: `001_users_events` through
  `023_notebook`, the head. The next is `024_`.
- No linter is configured; don't add one without an explicit request.

---

## Inviolable rules

Shared by both owners.

1. **The LLM is called only from the server.** The key never reaches a
   client, and the Gemini API is not reachable from Russia, so calls go out
   from Railway.
2. **The image is compressed before it is sent to the model** —
   `IMAGE_MAX_SIDE` and `IMAGE_QUALITY`, 1500 px and 85. That a full-size
   photo costs several times more for no gain is evidence about a retired
   model; the numbers are settings so the claim can be measured on one album
   rather than argued, and the defaults do not drift.
3. **The original photos are never stored**, only the recognised text — and
   the drawings taken from them (`note_figures`): since 2026-10-11 a sketch
   drawn again from its page, the pen's lines traced off the photograph and
   its labels set in type (task 101), before it the frame of one drawing
   reduced to the darkness of its ink (task 54) — kept as darkness because
   the document is drawn again every time a "#word" brings the record back. What
   `group_pages` keeps for seven days is Telegram's reference to a group
   album's page (`file_id`), which the bot fetches the photo by while Telegram
   keeps it — not the photo. It lets a reply call the bot on an album somebody
   else sent (2026-09-29). Nor is a PDF stored (task 100): its pages, drawn
   as pictures, exist while they are read.
4. **Every model call is written to `ai_calls`** — model, tokens, cost,
   latency, success, error. No exceptions, a failed attempt included.
5. **Every significant action is written to `events`.** Retention cannot be
   computed after the fact.
6. **Limits are checked before the model call, not after.**
7. **JSON from the model is never trusted.** The schema is validated and
   garbage handled; a parser never raises, it returns `None`. The `ai_calls`
   row then names the response's own `finish_reason` — `MAX_TOKENS`: our
   `max_output_tokens` cut the JSON; `STOP`: the model finished with no JSON;
   `SAFETY`: it refused — and the shape of what came back: `not json`, or its
   top-level keys. Keys only: the values are a student's page and do not
   belong in a log. A LaTeX command written with one backslash is repaired
   before recognition's answer is parsed (`vision._JSON_BACKSLASH_RE`):
   `\pmod` failed the whole answer, `\frac` read as a form feed. The call is
   made again unless its finish reason says a second is pointless — `SAFETY`
   repeats, `MAX_TOKENS` walks into the same ceiling, and `RECITATION` is left
   alone with them (`vision._FINISH_NOT_WORTH_REPEATING`). → "Unparseable
   answers"

---

## Established experimentally

Shared by both owners. Each stands on a reproduced failure or a measurement;
don't revisit one without new data. The failures were found on
`gemini-2.5-flash-lite`, closed to new accounts in September 2026, and
recognition has changed model twice since. If it starts behaving differently
— the prompt-length trade-off, the value of three runs, the uselessness of
self-assessment — suspect the model first: a fresh reproduction outranks the
note. `docs/PLAN.md` → "Where the quality work stands" is how to run the next
arm.

### What the model is not trusted with

- **A verification call doesn't work.** Asked to compare the transcription
  with the photo and list the discrepancies, the model invented one, repeated
  it three times, and found none of the real ones. **Don't add a verification
  pass with the model.** → "Moved from CLAUDE.md, 2026-10-01"
- **Its self-assessment is useless.** `confidence` gave 0.95 on a page with
  three errors, which is why it is not in the schema; `unreadable_count: 0` is
  no sign of quality either.
- **`uncertain` is a complaint, not an ambiguity.** Asked for the symbols
  that read two ways, the model lists the state of the paper.
  `vision.meaningful_uncertain` holds the prompt's own test in code: an entry
  that names no alternative is no ambiguity, and one whose text already
  carries `[неразборчиво]` is a mark the record itself carries. → "What
  `uncertain` came back with"
- **Its geometry of a sketch is not drawn** (task 101, 2026-10-11). Asked
  for a sketch's lines with coordinates, three runs drew circles of the
  wrong size where the author drew four balls and a full grid where he drew
  three lines, each its own. Its frames and its reading of the labels hold
  across runs; the lines are traced off the photograph. → "Sketches drawn
  from the page"
- **Arithmetic is checked by code, not by the model.** The model makes
  calculation errors and silently "fixes" what does not add up; `mathcheck`
  found a wrong constant and a diverging chain it missed across four runs.
- **It blames the author for its own misreadings** — a semicolon read as a
  letter became "possibly a typo by the author". The prompt forbids that kind
  of interpretation.
- **A bad shot is more dangerous than difficult text.** A spread
  photographed from a distance came back as a coherent textbook retelling of
  its heading's topic, with `unreadable_count: 0`. Nothing after the fact
  catches it, which is why `photoguard` runs **before** the model and is never
  bypassed.

### What works, and what the measurements settled

- **Agreement between independent runs.** Three runs of one short prompt,
  compared by code: trust where they agree, flag where they diverge. It is the
  only uncertainty signal that has proved reliable.
- **Two runs that stopped short do not outvote one that read the page whole**
  (task 65, 2026-10-04): a page kept the half two runs read and lost the
  proof the third had read. When a run read a block of a dozen words or
  more that the chosen run did not, where the chosen has nothing in its stead
  (`merge.lacking`), two more runs are asked for (`vision.MORE_RUNS`), and a
  block two runs read is on the page: the comparison is then of the runs that
  carry it (`vision._read_whole`). A block one run alone read stays out —
  invention does not write the same block twice. The more runs are part of
  the page's reading, like a retry: limits were checked before the page, and
  every call is in `ai_calls`. `note_processed` counts `runs_added` and
  `read_further`, and the consensus log line the words each run read. →
  "Record 67, half a page"
- **Two agreement numbers answer two questions.** `text_agreement` compares
  the markdown, so it moves when a prompt changes how a page is *laid out*
  rather than how it was *read*; it cannot be compared across prompts that
  change the layout, nor between one stage and two. `numeric_agreement`
  compares numbers, which have no layout — the runs' `numeric_tokens`, or,
  under a prompt that does not ask for that list (v7), the numbers of each
  run's markdown (`vision.run_numbers`): a different instrument, never set
  against the other. Both are columns on `notes`, each the album's *worst*
  page, `NULL` for `.docx`. Read them across the arms of one experiment, never
  against a threshold: a page of matrices or a repetitive sequence runs low
  on exactly the pages the measure was made for; `difflib`'s autojunk stays
  off for the same reason. → "The two agreement numbers"
- **Compare means, and know the noise floor.** Two runs of one configuration
  move the mean `numeric_agreement` by about 0.03 and `text_agreement` by
  about 0.005; an arm that moves the numeric mean by less on one album has
  said nothing. → "The three arms"
- **A prompt's length is a budget, not a wall**: v4 at 321 words beat v3 at
  242 on the new model. Measure before going much past it, counting with
  `PROMPT_WORDS` from the startup log — `wc -w` reads three words more than
  `str.split`. → "The prompt's length"
- **`media_resolution` is not a lever** on this model at this image size:
  `high` left `tokens_in` where `unset` put it. Don't carry it in an arm. →
  "The three arms"
- **Two stages work; they waited on a model, not a prompt.** On
  `gemini-3.5-flash-lite` the composer returned its input; on
  `gemini-3.8-flash`, same prompt and album, it composes. It is the dearest
  call — about six recognition calls — and it over-structures. → "The
  composer"
- **The list of numbers is not free to drop.** Asked for none (v7), the
  model checked them in its thinking instead: the answer 44% shorter, the
  thinking 69% longer, recognition 14% dearer, read as well. → "What a record
  costs"
- **`gemini-3.5-flash-lite` reads worse than `gemini-3.8-flash`** — `Z/Im Z`
  for `ℤ/mℤ`, a step of a proof dropped — so recognition stays on 3.8-flash.
  → "What a record costs"
- **v5 against v4 is open.** Every v5 album scored above every v4 album by
  three times the noise, on four observations against two: a reason to run
  two more v4 albums, not to believe v5 reads better. → "What the arms left
  open"

---

## Sessions and transactions

The reasoning and a worked example: `docs/PLAN.md` → "Transaction model".

1. **One session per update, opened by the middleware.** It lives in
   `data["session"]`, commits after the handler and rolls back on any
   exception; `notes`, `users` and `events` go through it. It serves messages,
   the bot's own membership updates and the presses of its buttons, and puts
   the group chat, if any, in `data["group"]` — for a press, the chat of the
   message the button is on. Eight deliberate exceptions:
   - a **new** user is committed *before* the handler: `log_ai_calls` inserts
     `ai_calls.user_id` from a session of its own and would fail the foreign
     key;
   - a user or group row two updates insert at once is fetched by the loser
     rather than failing on the unique index (`middlewares._insert_or_fetch`):
     a lost race was a lost page;
   - a group album page's reference is committed as soon as it is written
     (`handlers._remember_page`): the update that claims the batch holds its
     session through the album, and its rollback would lose the page for
     every later call on it;
   - every album page's update commits before it waits for its album
     (`handlers.handle_photo`, task 81): nothing of its own is left to
     write, and an album of ten waits a minute for the rest of its send —
     a send of thirty pages is thirty updates waiting at once, and the pool
     is twenty;
   - a group's record is committed before the pages it was read from are
     free for another reading (`corpus.reading`, task 41): a second call on
     them finds the reading or the record, never neither;
   - every record is committed before it is delivered (`handlers._saved`,
     task 104): a document Telegram refused, or a message after it, rolled
     the update back with the record in it — its reading paid for, nothing
     kept, the reader told to send the photo again;
   - a lecture moved into a group is committed before the group is told
     (`to_group.on_move`, task 63): a line that could not be sent leaves
     it moved, and a move that could not be kept tells nobody anything;
   - a whole notebook's update commits before its pages are read, and
     again after each of its lectures is sent (`handlers._read_notebook`,
     task 63): a hundred pages take twenty minutes to read, and a lecture
     that fails rolls back only itself.
2. **`events` are transactional and vanish on rollback — deliberately**: an
   event describes something that in the end happened. `log_event` wraps its
   insert in a SAVEPOINT (`begin_nested`) so a failed insert cannot poison the
   transaction.
3. **`ai_calls` are written in their own session and committed at once.**
   Money was spent however processing ended, and a row lost to a rollback
   understates the daily cap. `log_ai_calls` takes no session; a row with no
   `Note` is normal. Each row names its own `kind` and `model` from
   `CallStats`, never `settings.VISION_MODEL`, or a second stage would be
   priced as the first, and the group chat it was made for (`group_id`,
   task 41): what a group costs. It carries two output counts — `tokens_out`
   (`candidates_token_count`, the answer) and `tokens_thought`
   (`thoughts_token_count`), drawn from the same `max_output_tokens`, billed
   at the same rate, both in `_cost_usd`. `MAX_OUTPUT_TOKENS` (32768,
   `vision.py`, imported by `compose`) is one constant for every call: a cap
   is billed only when reached, and two drifting apart cost a run. →
   "Unparseable answers"
4. **`note_failed` is the only event written standalone**
   (`log_event_standalone`): the global error handler runs while the main
   transaction is rolling back.
5. **Anything that calls the model never touches the database.** Runs and
   pages run in parallel, and one `AsyncSession` cannot be used concurrently;
   model-calling functions return their stats, and the handler writes.
6. **A person's day is counted by the database** (task 76): `check_limits`
   reads it and writes nothing, and `consume` adds the record's pages in one
   UPDATE, a day that is over starting again from them. Written at the
   check, the rollover locked the person's row for the record's minutes: their
   second album waited for the first, then zeroed its pages. A refreshed name
   or title still locks it, rarely: "Scale debt". → "What the bot spends its
   time and memory on"

---

## The pipeline

Four **capture paths** — a photo, an album, a PDF, a `.docx` — two of them
**photo paths** (`handlers.handle_photo`, `albums.process_page`). An image
sent as a file (JPEG, PNG, WebP — `middlewares.page_file`) is a photo to
both; in a group, a reply can call the bot on pages somebody else sent
(`handlers.handle_summon`), into the same two paths. **A PDF is an album of
its pages** (`handlers._read_pdf`, task 100): every page drawn as a picture
(`images.pdf_pages`) and read as an album's page, whatever the PDF holds —
its text layer is no way in, since a typed PDF's formulas come out of it
flattened and a scanner lays a junk reading of its own over handwriting. A
blank page is left out without a word, the others keeping their number in
the PDF (`PageInput.number`); more pages than an album may hold refuse the
PDF before a page is read. **A whole notebook** (task 63,
`handlers._read_notebook`): in a private chat, a send or a PDF of more
pages than an album may hold, or one whose caption says «тетрадь», up to
`NOTEBOOK_MAX_PAGES` — read a few pages at a time with a prompt of its own
and cut into its lectures, each made as an album's record is ("The
corpus"). **`.docx` is never read by a model**: no page
limit, no quota, neither stage, and it works with `AI_ENABLED=false`; only
`MIN_MARKDOWN_LEN` applies. Its delivery is the one call it can make — the
study version, as on every path, inside the day's cost cap (`pages=0`); off
or refused, the record's own document.

A photo's way, in the order the code takes it — `handlers._read_photo`
numbers its steps, and `docs/PLAN.md` → "Final processing order for a
photo" gives every exit and why each step stands where it does:

```
main.telegram_webhook        answers at once; the update runs in a task
middlewares                  heard or dropped; a session, the user, the group
handlers.handle_photo        an album's page: albums.announce, add_page,
                             collect — one update owns the batch
corpus.reading               a group's pages claimed against a second call
images.compress              in a worker thread (images.in_worker)
 4   limits.check_limits     the kill switch, the cost cap, the group's day,
                             the person's
 5   photoguard              the frame, before any model call
 6   waiting.shown           one line changed in place every 8 s until the
                             end, then deleted (task 105)
 7   vision.transcribe_consensus   three runs compared, two more where one
                             read further; a chart drawn only when two read
                             it alike (charts.agreed)
 8   vision.log_ai_calls     always, in a session of its own
 9, 10                       nothing parsed, or too little text: the page is
                             dropped
     sketches.read           where each sketch is, what its labels say:
                             three calls a page that describes one
     figures.redraw          its lines traced off the photo, while the
                             image is here (v8: figures.cut) — both off,
                             archived on 2026-10-11
12   vision.findings         mathcheck and graphcheck, each with its text
12a  compose.compose         behind check_limits(pages=0)
     figures.place           the drawings back, after composing
     subjects.repeated       the subject's album before's last page,
                             photographed again, cut off the head
     subjects.joining        the lecture this notebook joins, if any
12b  explain.explain         its captions beside it, and the study version for
                             a record that joins no lecture (task 104), behind
                             check_limits(pages=0)
13   Note, subjects.file
14   limits.consume
15   note_processed
17   corpus.tag_line         the subject asked, or where it was filed; then
                             the record committed (handlers._saved)
16   corpus.deliver          the study version, built at 12b, kept or built
                             now (study.build), else the record's own
                             document, step 17's words in its caption;
                             pdf.render in a thread
```

An album checks its limits before its pages are fetched
(`handlers._fetch_pages`) and every frame before any page is read
(`albums.refused_frames`); `albums.process_batch` reads every page at once —
the frame, the runs, the drawings, the checks — and assembles one record
(`albums._assemble`, `_one_lecture`), which `handlers._process_album` takes
from 12a, once.

### Verdicts

- **`verdict` and `status` are different vocabularies**: `verdict` is the
  pipeline's, `clean | needs_review | rejected`; `Note.status` is stored and
  only `ready | needs_review`.
- **A page is dropped for three reasons and no others**: the frame was
  refused, not one run parsed, or there is no text on it — where asking for the
  photograph again is the only useful answer. Everything else is kept and
  marked:
  - **`rejected` removes nothing.** Its band is `text_agreement`, which
    measures layout, and from `prompts-v5.md` on the prompt leaves layout
    free. The page stays as `needs_review` and is named in
    `notes.unverified_pages` — for the measurements; the document does not
    print it. A page only one run came back for is one reading, both
    agreements `None`. → "Pages refused for their layout"
  - **The numbers can vouch for a `rejected` page** (`vision.numbers_vouch`):
    no reported divergence on the unfiltered list, and at least
    `_VOUCH_MIN_NUMBERS` = 5 numbers in every run, counted from the markdown —
    invention does not produce the same five numbers three times. It becomes
    an ordinary `needs_review` page, **never** `clean`.
  - **Two findings downgrade `clean` to `needs_review`, one way only**: a
    critical `mathcheck` issue, in both photo paths (a warning only shows),
    and a surviving numeric divergence, decided in `transcribe_consensus`
    where divergences are computed — a wrong digit barely moves
    `text_agreement` and is what a reader can least check. → "Numbers the
    agreement could not see"
  - The price of keeping every legible page: the band was the second defence
    against a page shot from across the room coming back as a fluent
    retelling. The first is `photoguard`, strengthened in answer (task 35).
- **A page the frame check refuses stops its album before anything is read**
  (`albums.refused_frames`): the reply names the page and asks for the album
  again, whole (`album_retake_requested`), with nothing spent — the one loss
  only the photographer can fix (2026-09-25). A PDF's page stops its PDF the
  same way, the CEO's choice of 2026-10-10 (`texts.pdf_retake`). → "Record
  45, a lecture on remainders"
- **A record names the pages it is missing**: `albums._assemble` leaves a
  marker where an unread page stood, `notes.missing_pages` holds their
  numbers, the document opens with a box naming them, and such a record is
  always `needs_review`. Only with not one page read (`record is None`) is
  nothing delivered — `album_incomplete`, the reply naming pages and reasons.
  Read pages are charged, skipped ones not, and every skipped page's four frame
  metrics ride `note_processed` or `album_incomplete`: the frame check's
  calibration data. → "Albums lost over one page"

### Updates and albums

- **The webhook answers before it works.** Telegram delivers one chat's
  updates strictly in sequence, so an update handled inside the request stops
  that chat for the ~9 s a photo takes, and an album never assembles.
  `telegram_webhook` schedules the work and returns — **never `await` the
  processing inside the endpoint.**
- **An album is owned by exactly one update.** `albums.collect()` waits for
  the group to go quiet and hands the batch to one caller; every other caller
  gets `None` and **must return without replying**, or the album is processed
  once per page.
- **A page is registered with `albums.announce` the moment its update
  arrives**, and handed to `add_page` as Telegram's reference, not downloaded:
  Telegram never says how many items a media group holds, so the debounce
  times the announcements, milliseconds apart, and a batch closes only once
  every announced page is in. **The update that claims the batch downloads the
  pages** (`handlers._fetch_pages`), after the album's tag, size and limits —
  so an untagged album in a group is never fetched. → "The album that came
  back as four records"
- **A send of more than ten pages is one album** (task 81, 2026-10-08):
  Telegram puts at most ten photographs in an album and sends the rest as
  the next, and a page left over after the tens can come as a photo of its
  own. The albums one person sends into one chat are one batch while every
  one before the last holds ten (`albums._send_of`) — up to
  `MAX_ALBUM_PAGES`, past which an album begins a send of its own, and
  never across two "#words". An album of exactly ten waits `_CONTINUE_S`,
  a minute, for the rest: a phone sends each album once its photographs are
  uploaded (task 85). A photo its sender sends meanwhile joins as an album
  of one page, heard in a group without its "#word" (`albums.collecting`).
  Decided when the batch closes, over every album of theirs still waiting —
  never when a page arrives, since pages register in the order their updates
  finish their database work. The record's pages are in message order
  across the albums, its subject whichever album carries one, its source
  key in a group the first album's; `note_processed` counts `album_parts`.
  → "A lecture sent at once", "Records 90, 91 and 92"
- **Router order in `main.py` is load-bearing.** `handlers.router` ends with a
  filterless catch-all, so `corpus.router` goes before it, capture after, and
  a third router is placed relative to that catch-all. `on_tag` matches text,
  not a `Command`. A "#word" in reply to a page in a group is refused there
  (`middlewares.is_summon`) and reaches `handlers.handle_summon`, before the
  catch-all. `feedback.router` goes first of all: a reply to the bot's
  question under a press — «что не так», «что понравилось» — is feedback
  whatever it says, a "#word" included.

### Stage two: composing

- **Reading and composing are two jobs with opposite requirements, and two
  calls.** Most failures are the interpretive faculty leaking into the literal
  job, so `compose.py` is a second call over the text the runs agreed on, and
  it **never receives the photograph** — the worst failure reproduced here
  needs an image to invent from. → "Why reading and composing are two calls"
- **Its output is checked against its input by code** — text against text,
  not the forbidden verification against a photograph: the multiset of
  numbers identical, the count of `[неразборчиво]` identical, the document
  not materially shorter. Otherwise the record is the one stage one produced:
  off, refused or failed, the worst case of the stage is the pipeline without
  it — and a refusal costs the record its headings, which is why the guard
  counts values, never what only counts items: "1)", "1))", "2." or a bare
  number before a capitalised word opening a line, a heading, a bold label
  or a bulleted item; "1)" after a colon or a semicolon inside a line; a run
  of numbers in order, 1, 2, 3, each opening a line, however the composer
  sets the item (`compose._items`, task 88) — and never a number that closes
  a bracket, «(0; 1)», «[1; 2)». Alone before a lower-case word a number is
  a value: «2 мн-ва» written «два множества» is refused. What the author
  struck out, a `~~…~~` of the source over up to three lines, leaves the
  numbers, the count of `[неразборчиво]` and the length alike, and what
  `\phantom{…}` only measures is no value. Each pattern in `compose.py` says
  which record showed it. The log line says how many numbers went and came,
  never which. → "The composition record 59 lost", "Record 86, √2", "Records
  88 and 89", "Records 90, 91 and 92"
- **A refused composition is asked for once more** (`compose_retried`,
  2026-10-03): the composer is sampled, and a refusal is one sample's — one
  call more on about one record in thirty, and the guards judge the second
  as they judged the first. → "Record 66's composition"
- **A heading that is not one is repaired, not refused**
  (`_demote_invented_headings`, before `_refusal`, counted as
  `compose_demoted`): the marker comes off, every word stays. → "Headings the
  composer invented"
- **A formula the composer changed is put back, not refused**
  (`_restore_formulas`, task 82, before `_refusal`, counted as
  `compose_restored`): where the numbers differ, a formula of the
  composition the source does not carry is matched against the source's
  formulas and against runs of them one after another — a working's lines,
  which the composer makes one formula — and the closest, four-fifths alike,
  is put back as read where that brings the numbers closer: the bot does not
  correct the author, and a record should not lose every heading for one
  exponent. → "Records 88 and 89"
- **A chart's data never reaches the composer** (`charts.held`, task 94):
  it stands in the text as `[схема: рисунок данными N]`, which the composer
  keeps as it keeps every `[схема: …]`, and goes back after. A formula in a
  chart is the drawing's, which rule 4 would set apart as the lecture's;
  a composition that loses one is refused, as one that loses a number is.
- **Main-formula marks are capped**: rule 9 of `prompts-compose-v3.md` frames a
  section's main formula, and `_cap_marks` keeps two of the stage's own frames
  a section (`compose_unmarked`). A frame from recognition is the author's pen
  and is never touched.
- **Word drift is measured, not refused on**: rule 6 asks for
  `### Определение` over a definition.
- **The author's shorthand is spelled out** (rule 10 of
  `prompts-compose-v4.md`, the CEO's decision of 2026-10-06): an ordinary
  word written short is written whole, in the form its phrase needs — «мн-ом»
  is «множеством» — «]» is «Пусть», and a ∀ or ∃ standing for a word in a
  sentence is the word. The abbreviations a lecture introduces itself (ОД,
  БД), «т.е.» and «т.к.», formulas and numbers stay as written, and so does
  whatever the composer is not sure of. A student who missed the lecture
  should not have to decode the notebook. The only rewording the stage is
  allowed, measured as drift like the rest. Production composes with v4
  since 2026-10-06, the CEO's switch, unmeasured. → "Record 74, a lecture on
  trees"
- Its ceiling and retries are in "Concurrency ceilings".

### Stage three: what the bot adds

- **`explain.py` explains the hard places and sums the record up, as the
  bot's** (2026-09-24) — what a classmate who was there would add. It never
  sees the photograph.
- **Two steps, because one did not work on the live model**: asked to explain
  and search in one call, `gemini-3.8-flash` searched for nothing and quoted
  from memory. One call writes the explanations and the summary as strict
  JSON over the record numbered by `pdf.numbered_for_reading` — "(3)" in an
  answer is "(3)" on the page — and each explanation then gets a search call
  of its own (`prompts-explain-source-v2.md`), in parallel. → "What the model
  did with a search tool"
- **Three guards, all in code**: an explanation is printed only with the
  sources its own search returned, read from the grounding metadata, never
  from what the model writes — one with none is dropped
  (`explain_unsourced`); the summary may not state a number the record does
  not carry (`summary_refused`); and an explanation that judges the record —
  «опечатка», «описка», the author's mistake — is dropped before it is
  searched for (`explain_judged`), in a stored record too: the prompt's «Не
  исправляй автора» did not hold, and the bot cannot tell what the author
  wrote from what was read, and neither can the reader. → "Record 62, record
  59's album read again"
- **Sources are ranked, and a forum is none** (`explain._TIERS`): science
  first, then encyclopedias, study sites, the rest; three a box, one link a
  site; the site read from the grounding chunk's `web.domain` or `web.title`,
  never from the link, which is Google's redirect (2026-09-25). A forum, a
  social network or a video is dropped (`explain.not_a_source`, 2026-10-01),
  and an explanation left with no source goes with it, as
  `explain_unsourced` — in a stored record too, when its document is drawn
  (`corpus._explanations`). → "What the model did with a search tool",
  "Moved from CLAUDE.md, 2026-10-10"
- **Stored apart, printed as the bot's**: `notes.explanations` (with the
  sources) and `notes.summary`, never mixed into `markdown`. An explanation
  stands under the sentence it quotes or the formula it numbers, after that
  sentence's findings (task 83, "The document"); the summary opens the
  document as "Суть". At most eight; an anchor found nowhere puts its box at
  the end. Limits come before the call
  (`pages=0`); each search is billed per query (`GROUNDING_USD_PER_QUERY`),
  inside the cap. Off, refused or failed, the record goes out as without it;
  `.docx` skips it.
- **What a teacher adds, besides** (task 56, 2026-10-03, `prompts-explain-v2.md`):
  «Идея» before every proof — its plan; «Зачем условие» at every definition
  and theorem with a condition — what it is for and what breaks without it,
  where no explanation stands already; «Пример» at every new notion — one
  unlike the lecture's own, and never the lecture's working with another
  number (`prompts-explain-v3.md`, task 78), which a reader takes for the
  lecture misread. Written by the same first call, in `elements` of its
  JSON, so they cost no call of their own. They are reasoning about the
  lecture rather than facts from books, so no search can source them: each is
  printed without a source, under a label that says whose it is
  (`texts.ELEMENT_LABELS`), and checked by code wherever there is something to
  check. An idea or a condition may state no number the record does not
  carry; an example's working is checked equality by equality, with
  `mathcheck`'s reading of a number and its tolerance (`explain._working_fails`
  — mathcheck itself compares chains of two "=" only); one that judges the
  record goes, as an explanation would. Dropped ones are counted
  (`elements_dropped`). Stored in `notes.explanations` beside the explanations,
  each naming its `kind`; an idea is set before the sentence it is anchored
  in, the others after it. At most twelve. → "The teacher's boxes"
- **A formula or a drawing the record says not a word about gets a
  caption** (task 95, the CEO's, 2026-10-09): what it is, in two to five
  words, and one sentence on what it states or shows — a formula with not a
  word about it tells a reader who was not there nothing. **A call of its
  own**, `prompts-explain-captions-v1.md` at thinking `low`, made beside the
  first call, at the same time, over the same numbered record: asked in the
  first call (`prompts-explain-v4.md`), the model wrote the captions right
  and fewer teacher's boxes, the ideas of proofs most. About $0.003 and a
  few seconds a record, its row `kind="caption"`; failed, it costs the
  captions alone.
  Checked as an idea is, and kept only where its anchor stands at a
  formula set apart or a drawing, as the document finds it
  (`pdf.on_formula_or_drawing`) — a drawing quoted with its brackets and a
  column of formulas quoted whole: at a line of words it would be an
  explanation printed without a source. At most six, counted `captions`
  and `captions_dropped`. Printed under «Что это · от бота» over what it
  names and the formulas right above it in one column, never over the
  words before them (`pdf._headed_line`): the sentence code reads may begin
  with another definition. Never at the end of the text; stored as `kind:
  "caption"`.
  The stage runs once, when a record is made: a record made before keeps
  its boxes. → "Captions"

### Drawings taken from the page

- **Archived on 2026-10-11, the CEO's word** after record 107: «давай пока
  оставим работу с рисунками. оставь только самые простые». The document
  draws what code draws from data — a graph, a function, a number line, a
  mapping (task 94, "The document") — and a sketch is its words,
  `[схема: …]`. Every way of drawing a sketch from its photograph read worse
  than its words: its ink cut out with the grid left faint (task 54), the
  model's geometry, the pen's lines traced (task 101, production for one
  night), and its ink again with the grid taken off line by line, which was
  task 54's way once more. Their code stays, off — `SKETCHES_ENABLED`,
  `prompts-v8.md` — and what follows is how it is built, for whoever takes
  it up; taking it up is the CEO's. → `docs/PLAN.md` → Backlog, "Sketches
  drawn from the page"
- **A sketch is drawn again from its page, by its own lines** (task 101,
  the CEO's, 2026-10-11): a set, a ball, a neighbourhood, a graph with no
  formula — no data (task 94) — and a proof carried in them printed as
  sentences about them. Never from the model's words or its geometry —
  the model's picture of the topic, the place it invents. `sketches.read`
  asks the model, three runs a page that describes one, only where each
  drawing is and what its labels say (`prompts-sketch-v1.md`): a frame
  counts where two runs frame it alike, a label where two read it alike at
  one place, or one does and the drawing's own words name it. `strokes.py` traces the lines off the photograph: the paper's
  light divided out, the notebook's grid found off the spectrum and taken
  off line by line, the strokes by an oriented filter, joined, kept once,
  straight where drawn straight; the labels set in type where the
  handwriting stood, never where nothing is written; a point a dot. Every
  line drawn is one the pen left. → "Sketches drawn from the page"
- **What reads worse than its words stays its words**: a gate in code
  refuses a drawing in pieces — more than 0.45 of its length in open
  strokes shorter than a letter, more than 0.2 in short straight pieces
  along the page's axes, half along the grid. A plane drawn along the
  grid's own lines is refused: the author's lines and the notebook's are
  one there. Set on six drawings of one hand, and watched.
- **A switch, `SKETCHES_ENABLED`**, off in production since the morning
  of 2026-10-11, the CEO's word after record 107: its five sketches drawn
  came out broken, with strokes the author never drew — the grid's stubs, a
  hatch made a tangle — and the gate passed them all. On, both photo paths, the
  calls in `ai_calls` as `kind="sketch"`, part of reading the page as task
  65's further runs are, `note_processed` counting `sketched`. Kept in
  `note_figures` like a cut-out, its resolution in the PNG so the document
  sets it at its size (`pdf._picture`).
- **A drawing cut out of the page** (task 54, 2026-10-01) is the asleep
  way: from `prompts-v8.md` on, recognition gives each `[схема: …]` its
  frame on the photo in `drawings`, outside `markdown`, so neither agreement
  moves. A graph is still data and still drawn from its edges.
- **Taken while the image is here, placed after composing** (`figures.py`):
  both photo paths draw the sketches again, or cut the best run's frames out
  of the compressed image, right after recognition, pairing them with the
  `[схема: …]` lines in order and taking none when the counts differ. Composition never sees a drawing;
  afterwards `figures.place` turns the `[схема: …]` that carries a cut-out's
  words into `[рисунок N: …]`, N through the record, and a line the composer
  reworded keeps none — a drawing can go missing, never land at the wrong
  line. `note_processed` counts both, `drawings` and `figures`.
- **What is kept is ink, not a photograph**: the paper's light, a shadow
  across it included, divided out; ink kept whole, dashes and hatching too;
  a notebook's grid left faint, since on squared paper in a hand's shadow it
  could be told from the ink neither by colour nor by width; the other side
  of the sheet gone; the edges faded. A greyscale PNG, the colour the
  document's. → "Drawings cut out of the page"

### One lecture, one record

- **An album rarely begins and ends where its lecture does** (task 64,
  2026-10-03): a notebook runs on, and a record opens on the end of the
  lecture before or closes on the next one begun. Nothing in the
  text says where a lecture begins; the page does — a date, «Лекция N», the
  author's line. From `prompts-v9.md` on, recognition names the first line of
  every lecture that begins on a page in `lecture_starts`, outside
  `markdown`, so neither agreement moves.
- **A start counts only when every run read names it** (`lectures.agreed`,
  in `transcribe_consensus`, where the runs are compared); a page one run
  came back for is never cut. A line of the lecture lost is worse than a
  line of another kept.
- **Cut at the album's edges only** (`albums._one_lecture`): above the first
  start on its first page, the lecture before; from the last start on its
  last page, the lecture after, with the line the author drew before it.
  Only with two pages read or more, on the album's own first and last page;
  never a single page — a photograph, or the one page an album kept — which
  says nothing of which lecture is meant, never the middle of an album,
  never a whole page. What is cut is not kept;
  a cut page's findings are found again on what stays, and the record's
  title is taken from what stays when the first page lost its head.
  `note_processed` counts the lines, `lecture_head_cut` and
  `lecture_tail_cut`.
- **Asleep since its measurement** (2026-10-03): under v9 the model named no
  start on two pages where the CEO knew one lecture ended — nothing on them
  told a lecture from a section. The way left is the page photographed
  twice, which task 63 takes up. → "One lecture, one record"
- **Woken for a whole notebook** (task 63, 2026-10-13): its pages are read
  with `prompts-v12.md`, v11 with v9's rule, and the notebook is cut at
  every start all runs named (`lectures.cut`) — the CEO's notebooks open a
  lecture with its date and a heading. An album keeps v11 and is not cut.
  → "A whole notebook's prompt"

### The matrix against the graph

`graphcheck.check` decides a cell by the edges, not by a vote: the adjacency is
computed from the edge list and compared; an incidence matrix is checked the
only way its unknown column order allows — every column the two ends of one
edge, every row sum a degree. Findings are `mathcheck.Issue`s, riding the
`issues` column and the critical downgrade; `graphcheck.located` names the
graph each goes under, parsed by `pdf.parse_graph` like the picture. **It
stays quiet when the page does not settle it** — a cycle, labels that don't
match, a bare matrix of named vertices: a confident wrong finding costs more
than silence. → "Numbers the agreement could not see"

### An equality that does not hold

`algebracheck.failures` (task 84, the CEO's of 2026-10-08) counts the two
sides of every «=» that carries letters at three points picked at random —
an identity holds at each — and a finding under the sentence says where they
differ, at small numbers the reader can count: «Равенство (−x)(−x) = x не
выполняется. При x = 2 левая часть равна 4, правая — 2». Found when the
document is drawn (`corpus._remarks`), never stored, so a record made before
it has it too; no model, no library. It is the one class of the lecture's
errors code can prove. **It stays quiet when the page does not settle it**:
only sides with the same letters, after what the lecture defined («положим
h = b/3c») is put in; never what the author struck out, a capital letter, i
or j, a formula with \lim, \to or \infty, an «=» that holds as the letters
grow in a lecture on limits, a line that solves, supposes or argues the
contrary, a lecture on logic, or what it does not read — f(x), arg z, a set,
an absolute value. The module's docstring gives each case with the record
that taught it: an equality reported that holds tells the reader the
lecture is wrong where it is not. Nor does it read a formula of more than
1000 tokens, four times the longest of 102 records, and brackets nested past
Python's recursion keep it quiet (task 104): it runs in every delivery of
its record, and what it raised sank them all. → "An equality that does not
hold", "Record 97"

---

## The corpus

- **A "#word" is the one way in and the one way back.** Under a record's
  document in a private chat — in its caption, one message (task 105) — the
  bot asks its subject and shows the topics read off its headings; the
  answer is stored on `Note.tag`. A later "#word"
  searches subjects and topics at once, and a single match comes back as the
  document itself — its study version, since 2026-10-08.
- **Which of the two a "#word" means is decided by the corpus, not a state
  machine**: the newest record without a subject means the question is open;
  with one, the word searches. Stateless — it survives a restart and a second
  replica — and about the newest record only. A photo sent with "#word" in its
  caption is filed at once.
- **Topics are the main five** (`tags.topics_of`), read from headings the
  pipeline already made, no model call: the title, then headings ranked by
  *level*, since by position the slots went to `### Определение`, which
  matches everything. Stored when the record is made; `note_topics` is a
  table, an indexed join on PostgreSQL and the suite's SQLite alike.
- **A "#word" is one Telegram highlights whole** (task 106, the CEO's): a
  topic or a subject keeps letters, decimal digits and underscores, every
  other character a gap and gaps one underscore (`tags.normalize`) —
  Telegram ends a hashtag at anything else, and «#ε-окрестность» was
  highlighted as «#ε». A topic with no letter is none (`tags.highlighted`):
  Telegram makes no hashtag of «#1». What was stored before was written
  the same way (`020_hashtags`), so either spelling typed finds the same
  records.
- **Before adding an interface to the corpus, check `events` for whether the
  last one was used.** `/notes`, `/note`, `/search`, `/retitle`, `/delete` and
  `/pdf` were built, tested, deployed, never used once, and deleted. `/stats`
  stays beside `/start` and `/help`.

### A subject, its lectures, and one lecture from several notebooks

- **A subject is a row, and so is a lecture** (task 63, 2026-10-04):
  `subjects` — a chat's "#word", owned as a record is — and `lectures` — one
  class of it on the day it was given. Every material of the class points at
  its lecture; a board, a recording or the teacher's files will as they come.
  `subjects.file` files a record — `Note.tag`, `subject_id`, `lecture_id`
  together, and nothing else writes them; the search still reads the tag.
  A word new to a chat that two albums bring at once makes one subject: the
  loser fetches the winner's row, as for a user.
- **A lecture's day is the day it was given** (`subjects.day_of`): the
  caption's ("#матан 12.09"), else the margin's when it names one day and only
  one — a page ending one lecture and beginning the next names two — else the
  day the pages came; a later notebook that knows it better moves it. The head
  of the document carries it, and a "#word" lists lectures in its order. A
  margin's day after the day the pages came — a day's grace for the timezone
  — dates nothing (task 71): a lecture cannot have been given after its
  notebook was photographed, and taken for last year's it heads the
  document a year back. Last year's notebook is dated by its caption, which
  keeps its year. → "Record 79, dated a year back"
- **Two notebooks of one lecture are one lecture, decided by code**
  (`merge.same_lecture`): the same subject, a day within a week — never two
  different days both written down — and half of one text found in the
  other. One album read again agreed at 0.70–1.00, different lectures of a
  course at 0.40 at most. Unsure, a lecture of its own: two documents are
  better than one mixed. → "One lecture from several notebooks"
- **The base is the fullest notebook** (`subjects.base_of`), and what another
  adds goes in **only where the base has nothing in its stead**
  (`merge.merged`): aligned word by word — never by paragraph, which two
  readings break differently — a line the base read its own way is a variant,
  judged by the line, and the base stays: the bot never chooses between two
  readings and says nothing about them. Nor goes in what the base already has
  elsewhere, a drawing's description, a heading alone, or what the other
  notebook carries past a line across the page at its edge — the next lecture
  begun as often as this one's last page. A model never merges notebooks: the
  text of a lecture is what its authors wrote.
- **The group gets the lecture's document** — the base with every passage
  set in under «Из другого конспекта» — and a line saying the lecture was
  there (`texts.lecture_added`, `lecture_led`), the CEO's decisions of
  2026-10-04. A notebook that joins a lecture whose base is fuller is not
  explained (`subjects.joining`, before stage three): the document carries
  the base's explanations. `note_processed` and `note_tagged` say where a
  record went (`lecture_id`, `lecture_joined`, `explain_skipped`).
- **The page photographed twice is cut as a record is filed**
  (`subjects.repeated`, the CEO's «удаление повторов» of 2026-10-12): a
  record whose first page is its subject's album before's last page, read
  again, loses that head before it is matched to a lecture, explained or
  studied — the lecture before's end, which its own record has. Found by
  its words in order (`merge.repeated_head`): the whole of that page at the
  record's very first words, never a part of it, which is what a recap
  is. Cut only where sure: the album before sent on a day before this
  lecture's, and either this lecture's day written down or the page
  written on past the repeat. A page photographed after the next lecture
  began carries its first lines, and a line of the lecture before kept is
  better than a line of this one lost. A record tagged after it was made
  is trimmed when it is tagged (`subjects.trim`) — its title, findings,
  boxes and topics with it. → "The page photographed twice"
- **A search answers once a lecture** (`corpus._one_per_lecture`): a
  lecture's notebooks are one answer, and so are the records of no subject
  that read as one text — an album sent again before any of it was filed;
  the fullest stands for them. Fifty records are read for the ten answers
  a list shows. `021_one_lecture` joined the lectures that
  `014_subjects_lectures` had made twice.
- **A private lecture is moved into a group by a button** (`to_group.py`,
  the CEO's of 2026-10-12): under every document of a private record with
  its subject, and under the line that files one, «В группу «…»» for each
  group the bot is in that Telegram says the person is a member of. A
  press moves the lecture's notebooks, claimed by one conditional update
  so a double tap moves them once, into the group's subject of their word
  and the group's lecture they are notebooks of (`subjects.refile`), the
  private lecture's day kept; the group is shown one line, its verb in the
  present, which names nobody a man or a woman. A lecture moved is the
  group's, found there and no longer in the private chat, and counts in no
  day's pages (`notes.moved_at`): it was read and paid for where it was
  made.
- **A whole notebook is cut into its lectures** (`notebook.py`, the CEO's
  of 2026-10-12): from every start all runs named to the next, across
  pages, the author's line before a start dropped; a stretch of more than
  an album's pages with no start kept in near equal parts of an album's,
  and the person told. Each lecture is dated by the margin of the page it
  begins on — the page's days in order are its lectures' in order when it
  names as many as begin there — keeps only its own day in its margin
  notes (`subjects.margin_for`), and is made, kept and sent as an album's
  record is, two at a time and in order; its record carries the notebook
  (`notes.notebook`). A last message sums the notebook up with «Все в
  группу «…»», or asks its subject once, the answer filing every lecture of
  it (`corpus._file_notebook`). A page the frame check refuses does not
  stop it: the last message names it, and the page sent again in reply goes
  where its marker stands (`handlers._notebook_page`). A line says how far
  it is (`waiting.progress`). One a person a day, beyond their pages:
  counted once a notebook has come out whole (`notebook_read`), so one a
  deploy cut short is sent again; its pages are never in the person's
  day. A caption's day is the notebook's, never a lecture's; two albums
  whose captions name different days are two sends.
- **Not yet built**, in the CEO's order of 2026-10-12 (`docs/PLAN.md` →
  task 63): the semester as one document by its topics, task 52's new
  form.

### A group chat

- **A record made in a group belongs to the chat** (`notes.group_id`); its
  `user_id` only says who brought the pages. Every query goes through
  `corpus._owned`: in a group the group's records, in a private chat the
  user's own that belong to no group. `groups` is keyed by our own id: when a
  group becomes a supergroup, the middleware moves the row on either half of
  the migration notice, records and all.
- **The bot takes a page in a group only with its subject** — a "#word"
  anywhere in the caption of a photo, an album, a PDF or a `.docx`
  (`tags.from_caption`, `albums.tag_of`) — so a group is never asked, and a
  "#word" there only searches. A course chat is mostly memes, and a record
  costs money (2026-09-25).
- **Pages sent without their subject can be called on by a reply that is one
  "#word"** (task 40, 2026-09-29; `tags.from_reply` — the bot's @name may
  stand beside it). Whoever replied is `user_id` and is charged. An album is
  found whole from `group_pages`, where every album page in a group is written
  down on arrival and kept seven days; one the bot never saw whole is asked
  for again. A record remembers its source (`notes.source_key`, built by
  `corpus.source_key`), so a second call on the same pages sends that record
  instead of paying again; while they are being read — by their own tagged
  album or an earlier call — a second call is told so and starts nothing
  (`corpus.reading`, task 41). A bare mention earns one line of hint; every
  call writes `note_summoned`.
- **What is not addressed to the bot never reaches it.** `middlewares.heard`
  runs before a session, and in a group lets through a command, a message
  that is one "#word" and nothing else (`tags.is_bare` — "#дз на завтра" is
  for the classmates), a photo or a file with a tagged caption, a reply
  that calls or names the bot, a reply to the bot's own message
  (`middlewares.replies_to_bot` — how its question under a press is
  answered), every album page (judged whole in `_process_album`), and the
  migration notice. The rest is dropped with no session, no user row, no
  event. What gets through and is not the bot's gets no answer in a group —
  an untagged photo replying to the bot is still refused by `handle_photo` —
  and a missed search is still logged.
- **Whether the bot sees a group's photos is decided in BotFather**: with
  privacy mode on it sees only commands and replies to itself unless it is an
  admin. Privacy mode is off since 2026-10-03 (task 47, the CEO), so the bot
  sees a chat as an ordinary member and the welcome asks for nothing;
  `middlewares.heard` still drops what is not addressed to it. The startup
  log says which (`Groups:`), the welcome (`handlers.on_joined`) names the
  fix should privacy mode come back, `on_promoted` says when it worked.
- **A group adds the bot in one tap** (task 47): `/start` and `/help` in a
  private chat carry one button, «Добавить в чат группы», opening
  `t.me/<bot>?startgroup=add` — Telegram's own chat picker, the username from
  `bot.me()`. Never `&admin=…`, which would list only the chats where the
  person can appoint admins. The `/start@<bot> add` the person's client then
  sends into the chat is not answered — the welcome has been said — and is
  counted as `group_invited`.
  Membership arrives as `my_chat_member` updates, subscribed to through
  `dp.resolve_used_update_types()` and given a session; a join is registered
  before a promotion.
- **Events name their group** (`events.group_id`): weekly use by a group is the
  question. `group_joined` carries whether the bot sees the photos,
  `group_invited` the button's payload; `group_promoted` and `group_left`
  nothing else.
- **A group has a day of its own, in pages** (task 41, the CEO's,
  2026-10-07): `DAILY_PAGES_PER_GROUP`, counted from the group's records
  made since 00:00 UTC — 03:00 in Moscow, which is what the group is told —
  a `.docx` not counted, nothing stored for it. Checked after the global
  cost cap, the breaker over every chat, and before the quota of whoever
  brought the pages (`limits.check_limits`); asked when pages come and never
  for a record's later stages, so a record let in is composed and explained
  whatever the count says by then. Pages rather than dollars, so `/stats`
  says exactly what is left and the count does not halve when the prices
  do; what a group costs is read off `ai_calls.group_id`. Soft, as the cost
  cap is: two albums read at once can take a group past its day.

### What a reader says of a record

- **«Хорошо» and «Плохо» under every document** (task 70, the CEO,
  2026-10-06): on the PDF itself, or on the last message of the plain text it
  falls back to, a record a "#word" brings back included; each button names
  the record the document is drawn from (`feedback.keyboard`). Every fault
  fixed before was found by the CEO reading a record against its
  photographs; the groups read every record and said nothing.
- **One row a person a record** (`feedback`): a second press changes the
  rating, never counts twice, and never moves the row to another chat's
  count — it keeps the group it was first given in.
- **Every press asks, either button** (task 103, the CEO, 2026-10-11):
  «Плохо» where the error is, «Хорошо» what was good — in a group naming the
  reader, so Telegram's reply field opens for them alone (`ForceReply`,
  selective). A press is how a reader adds a comment: record 97's author
  pressed «Плохо» before each of nine. **Every comment is an отзыв**, the
  rating one more ("A group's week"). → "Record 97's отзывы, counted as
  one"
- **The answer is a reply to a question, found by its message**, from the
  reader it was asked of: the row's newest (`feedback.prompt_message_id`),
  or an earlier one through the press that asked it, whose `note_rated`
  names it (`feedback._asked_before`). No state in the process, so a
  restart between the two loses nothing. A caption counts; a screenshot is
  copied on as it is.
- **`FEEDBACK_CHAT_ID`**: a record's «Плохо» is sent there with the
  document copied once — and again only when its reader comes back to it
  from «Хорошо»: once a press, one PDF went there eight times — and every
  comment at once, the reader's message copied; each names the record, the
  chat and who. A chat that cannot be written to is a warning in the log,
  never the reader's problem. A press whose notice Telegram refuses — an
  update that waited too long — is kept. Events `note_rated` and
  `note_feedback`; the reader's words stay in `feedback.text`, never in an
  event.

### A lecture's study version

- **A chat gets a record's study version, not the record** (task 80, the
  CEO's, 2026-10-08): the lecture set out by topic for someone who was not
  there, on every capture path and every "#word" that brings a record
  back. The record stays what everything is made from — what a "#word"
  finds, what notebooks merge into — and its own document goes out only
  when no study version can be had, with «Учебная версия» under it to ask
  again (`bot/study_version.py`): a record is never lost over its
  presentation. The two stay separate documents, decided in one place
  (`corpus.deliver`): the CEO wants to be able to split them, one sent and
  the other offered by a button.
- **Made from the record, never instead of it.** Written by the model, the
  document's inventions would read as the lecture — the rule this product
  stands on, marked is the whole licence to add, undone. So the study
  version moves the author's text and marks what it adds.
- **The model arranges, code moves** (`services/study.py`): the record is
  cut into units — its paragraphs, a heading with what follows it, a
  formula or a drawing set apart with the text that leads up to it, no
  formula ever cut — numbered, and one call answers with the topics, each
  its units by number and what it is about, and three to five questions
  with their answers. The author's text never comes back from the model,
  so not a word of it can change, and every unit stands once: one named
  twice keeps its first place, one left out goes back after the unit
  before it, and past a quarter left out the version is refused. What the
  bot writes states no number the record does not carry, and an answer's
  working is checked as a teacher's example is; what fails goes.
- **What is not the lecture's subject is left out, never a line of the
  subject** (task 93, the CEO's, 2026-10-09): the model names the units
  about the course's organisation — contacts, points, admission, dates of
  tests, the schedule — and code leaves out of each its paragraphs before
  the first that holds the subject: a formula, a drawing, a word of what a
  lecture states or is about, as the notebook shortens it too
  (`study._SUBJECT_RE`), the headings right above it staying with it
  (`study.trimmed`): one unit can hold the organisation and the subject
  under it. What is left stands where the unit stood; a unit that opens on
  the subject loses nothing; past a fifth of the record named so, nothing
  goes. A formula never goes, so no number moves, and a box anchored only
  in what went is not printed (`corpus._only_left_out`). The record keeps
  every line, and its own document. → "Record 97"
- **Drawn as the record is** (`corpus.send_study_pdf`), with its summary,
  missing pages, findings and boxes, which follow their units; each topic
  a numbered section with «О чём тема · от бота» under it and its key
  notions — the author's bold words, picked by code, with a formula
  written against one («ε-окрестностью», task 86); the author's sections
  a level down; every main formula keeping the record's number, so an
  explanation's "(3)" still names its formula (`pdf.render`'s `placed` and
  `formula_numbers`); a box that found no line of its own before the
  questions, never after the answers (`pdf.TEXT_END`); the questions at the
  end and their answers on the last page. A lecture of several notebooks
  is studied whole: its base with what the others add, each passage moved
  whole.
- **Built once, kept on the base** (`notes.study`), with a fingerprint of
  the text it was built from and the prompt that arranged it: drawn again
  it pays nothing, and a notebook joining the lecture builds it anew, as
  does the next prompt when the record is next delivered (task 93). One call on the explaining stage's
  model, where that stage is on, inside the day's cost cap (`pages=0`),
  paid by whoever it is delivered to, its `ai_calls` row of
  `kind="study"`. An answer that does not parse is asked for once more, as
  recognition's is, and its row names the finish reason and the shape
  (task 87). While it runs, a second delivery of the record gets the
  record's document — a set in this process ("Scale debt"). For a record
  that joins no lecture the call is made beside the explaining stage's
  (`handlers._explained`, task 104) — from the text it is built from
  anyway, the record waiting for the slower of the two rather than both —
  and `deliver` sends it, or, refused, the record without asking twice;
  a notebook that joins a lecture is studied whole at its delivery. Events
  `study_sent` (`via` delivery or button; `off_topic`, the units left out
  whole or in part), `study_requested`, `study_failed`.

### A group's week

- **Who sent a group's records and who rated them** (task 72, the CEO,
  2026-10-06): `/stats` in a group is the group's week so far, and every
  Saturday at 10:00 Moscow time each group active in the week just ended
  gets it in its chat, unasked (task 73, 2026-10-07) — its dates, two
  totals, ten people at most, two numbers each, ordered by records
  (`rating.py`). A group that sees who brings its records and who reads them
  closely enough to say has a reason to do both, and `/stats` had been
  called once: what a group is not shown it does not see. A private chat's
  `/stats` is as it was.
- **A week runs from Saturday 00:00 UTC**, in the summary and in `/stats`
  alike, whose head names the day it began: the two never show different
  numbers. A record counts for whoever sent its pages (`notes.sender_id`): a
  reply's "#word" under a classmate's photographs is paid for by the replier
  and counted for the photographer, registered on the spot if the bot never
  saw them (`middlewares.registered`); a bot, an anonymous admin or a channel
  counts for the replier. `NULL` is the record's user. **An отзыв is a
  rating and every comment** (task 103, the CEO's of 2026-10-11): a
  `feedback` row, one a person a record, in the week it was first given,
  and every `note_feedback` event in the week it was written — so no count
  ever falls. Counted as one a record, nine comments had been one отзыв.
- **A person is their username**, the CEO's choice, without the @ that would
  notify them every time the week is shown; their first name when they have
  none. The middleware keeps both current, as it keeps a group's title.
- **The bot's one timer** (`rating.saturdays`, started with the process)
  reads the clock every ten minutes and sends from 07:00 UTC on Saturday to
  the day's end. A week is claimed on the group's row (`groups.rating_week`)
  by one conditional update, committed before the message goes: two timers
  at once — a deploy's old process and its new one — send it once, and a
  restart sends nothing twice. A summary that cannot be sent is a warning in
  the log and is not tried again; a deploy between the claim and the
  message, or a Saturday the bot is down for whole, costs that week its
  summary. A quiet week gets nothing; a group divided into topics gets it in
  the general one, the bot keeping no topic yet (task 66). `rating_posted`,
  with no user, counts the summaries.
- **No limit depends on it**: an отзыв worth pages would be worth faking,
  and the отзывы are how a record's errors are found. `/stats` says what is
  left of the group's own day under the week (task 41).
- **The bot's week, in the feedback chat** (task 74, the CEO's,
  2026-10-07): `/stats` in the chat `FEEDBACK_CHAT_ID` names — the CEO's
  own — answers with every chat's week and all time: records and pages, who
  sent and who rated, everyone the bot knows and the new, «Хорошо»,
  «Плохо» and comments, spend today, this week and all time; then each chat
  active in the week — a record, an отзыв or a call — with its spend,
  private chats as one line, and everyone with their week and all their
  time, the week's busiest first (`rating.bot_stats`, task 103): named for
  the week alone, the list emptied every Saturday morning, read as отзывы
  lost.
  Spend is in dollars there and nowhere a student reads; a group's is
  `ai_calls.group_id`, written since 2026-10-07. One read-only message, the
  only exception to "no admin panel"; `stats_viewed` marks it
  `{"scope": "bot"}`.

---

## The document

**A saved record goes out as a PDF**: every capture path ends in
`corpus.deliver`, which sends the record's study version ("A lecture's study
version") and, when there is none to be had, the record's own document
(`corpus.send_record`), which renders in a thread and, if rendering fails
for any reason, sends the record as plain text. A document Telegram refuses
is sent once more after its flood control of up to 30 s, a dropped
connection or its own error, and refused falls back the same way
(`corpus._sent_document`, task 104); the record is saved before it is sent.
A record is never lost over its presentation.

**A record comes as one message** (task 105, the CEO's «присылаем
пользователю все в одном сообщении»): what used to follow its document —
where it was filed or which subject it is, the pages it went out without —
stands in its caption, and only what Telegram's 1024 characters do not hold
goes after it (`corpus._captioned`). While it is made the chat sees one
line, «Работаем…», «Считаю формулы…», «Учусь, чтобы вам не пришлось…»,
changed in place every eight seconds — the CEO's choice over a new message
each time, which would notify and jump in a group — and deleted on every
way out, the record sent, a reason instead, an exception, a deploy
(`waiting.shown`). A .docx shows it while its study version is built. What follows is the look of both: the study version is
the record's document set out by topic. `pdf.py` never raises on a record's content; it receives what
to draw — `Callout`, `Remark`, `Explanation`, `Summary`, `Page`, built by
`corpus` — and knows nothing about where a record came from.

**One document is drawn at a time** (`pdf._DRAWING`, around `render` and
`warm_up`, task 76): matplotlib lays every formula out with one parser for
the whole process, and pyplot numbers its figures from state it shares, so
two documents drawn at once broke each other's formulas. A second document
waits the first one's seconds. → "What the bot spends its time and memory
on"

**Its look follows `docs/BRAND.md`**, the CEO's guide (2026-09-30, v1.1 the
next day). A change to the look changes both files, in one commit; the
values are named constants in `pdf.py`, and its docstrings say why each is
what it is. What a change must not break:

- **Paper, ink and the guide's colours; its three faces; formulas in Computer
  Modern** — never white, never a sixth colour or a fourth face. In the
  guide's monospace a formula's dotted zero read as θ. What Onest lacks —
  `∀ ∈ ⇒ ► ℝ`, Greek, the zero-width space — `pdf._text` sets in DejaVu;
  reportlab has no fallback and prints an empty box. Russian words between
  the parts of a formula in a line are set in Onest, as the text they are
  (`pdf._words_as_text`); words in braces or in an environment stay the
  formula's.
- **A formula is a picture made to sit like text**: lowered by its measured
  depth, a quarter-point stroke to darken Computer Modern, shrunk to the
  column; on the kraft ground when displayed (`pdf._grounded`). A column of
  formulas the author began on the line that introduces it stands on one
  ground: a formula ending a line after a colon goes down to the formulas
  under it when they state a relation of the same left side
  (`pdf._formula_columns`, task 79). The line keeps what it quoted for an
  anchor (`Block.quoted`), or a box anchored on it goes to the end of the
  document. A zero-width space after an inline formula is the only place
  reportlab breaks a line after an image — and it breaks before one too, so
  the comma, the period, the bracket written against a formula are drawn
  with it, as `\text{…}` for mathtext's own space after a comma
  (`pdf._inline`, task 86), or a line opens on «, то есть». A tall one makes
  room in its line, a paragraph's first line included: reportlab set that
  line a font size below the paragraph's top whatever it held, and a column
  vector rose over the line above (`paraFontSizeHeightOffset`, off since
  2026-10-02).
- **Groups are built by hand and flat** — a heading with what it heads, a
  finding with its line, a table whole. reportlab's `keepWithNext` nests one
  `KeepTogether` in another and the inner reports an effectively infinite
  height; a unit that keeps itself whole, a long division, is opened into its
  group (`pdf._opened`). The space between two units is `_space_before`'s,
  which knows what both of them are. The last line of a paragraph never goes
  over a page alone (`allowWidows=0`): allowed, it left a page of one word.
- **Every box has one anatomy** — a bar, a label in spaced capitals
  (`pdf._Label`), lines at the text's size, the bot's title in bold and
  opening with a capital (`texts.explanation_line`, task 86) — **and its tone is its meaning**:
  dark amber what is certainly wrong, kraft what only may be, ink the bot's
  explanation, an amber line with no label a definition
  (`pdf._definition_end`). "Суть", the summary, opens the document on the one
  dark block; the box naming missing pages (`corpus._callouts`) follows it.
- **A main formula is framed, larger and numbered "(1)", "(2)"** through the
  record. Two sources mark one, kept apart: what the author framed is
  perception (`\boxed{…}`, `[рамка: …]`, older `[в рамке: …]` and arrays
  ruled with `\hline`), a section's result is the composing stage's
  interpretation, capped by `compose._cap_marks`. A frame inside a line —
  «[рамка: ?!]» in a sentence, a `\boxed` in a formula set in a line — is
  drawn where it stands, round what it frames, and is no main formula
  (`pdf._inline_frames`, task 78).
- **Under the title stands a name, a date or a page, or nothing**
  (`texts.byline`, task 55): what the margin said of whose lecture, which
  day, which page — the notebook's print, a doodle described and stray
  letters are not that, though the reading puts them among the margin's
  notes. Each once, and a page only when one page gave its number, never
  every page's (task 86). Chosen when the document is drawn, so a record
  stored before the rule is drawn by it too.
- **Every page carries a head and the signature** (`pdf.Page`, built by
  `corpus._page`): the subject as its "#word", the day and "стр. 2/5" — never
  "с. 2", which inside a record means a photographed page; no number on a
  one-page record; no lecture number, which the bot does not know. The
  signature's QR code opens the bot named by `bot.me()` — the one that sent
  the document. Where a formula cannot be drawn — the head, the file's name, a
  chat listing — `pdf.plain` writes it in characters: "2¹⁰⁰¹", never
  "$2^{1001}$". A title's formula written without its dollars is found the
  way a quoted fragment's is (`pdf.as_formula`), drawn in the title and
  written in characters elsewhere (task 78).
- **Markup never prints as its source**: `$$` blocks, `$$…$$` inside a line,
  emphasis across a formula, a line of `~~~` a separator as `---` is; a
  finding's quoted LaTeX through `pdf.as_formula`. «[зачёркнуто]», what
  recognition writes where the author crossed something out, is not printed,
  nor a line that held only it (`pdf._unstruck`): what the author struck out
  is not the lecture. Nor is «~~[неразборчиво]~~», a crossing-out the reading
  could not see through (task 78), nor struck words the reading could read,
  `~~…~~` (task 83) — unless they are all the line has but its number:
  «1.3. ~~Мн-ва Аксиома полноты~~» stays struck, since the reading may strike
  more than the author did. A line struck whole goes, and so does a passage
  struck over two or three lines (task 86).
- **The notebook's line is not the document's** (task 83, the CEO's reading
  of records 88 and 89): a word carried over with a hyphen is whole at the
  end of the first line (`pdf._unhyphenated`, three letters on either side,
  so «мн-ва» stays); a short formula a sentence ends on — «$X_i$» — is set in
  its line, never one of a column (`pdf._tail_formulas`); a sign the author
  ringed, «[схема: ?! в кружке]», «[знак: ?!, обведённый в кружок]» or
  «[?!]» as the reading writes it, is framed in its line (`pdf._ringed`);
  ⩽ and ⩾ are drawn as ≤ and ≥, one sign through the document. One pipeline
  reads a record for render and for the formulas it numbers (`pdf._parsed`),
  so the study version's numbers stay the record's. Two columns the reading
  made one line, «1.1. | $(x+y)+z = …$», print without the bar after the
  item's number, the anchor still finding the line as read (`pdf._unpiped`,
  task 97).
- **A frame is the author's, braces and blank lines and all** (task 97):
  an escaped brace inside `\boxed{…}` is a character, not the frame's end;
  a frame round several lines may hold a blank line, and is drawn then as a
  frame with no number (`Block.loose`) — a number given it would move every
  main formula after it under explanations stored with their numbers.
- **A title that names nothing gives way in the document** (task 97):
  «Лекция», «Матан. Практика» — what the reading called a page of the
  course's organisation — to the record's first heading that names
  something, in the head of every page and the file's name
  (`corpus._document_title`); the record keeps its title, which a "#word"
  lists.

→ "The document as the group got it", "Record 62, record 59's album read
again", "Record 74, a lecture on trees", "Record 86, √2", "Records 88 and
89", "Records 90, 91 and 92", "Record 97", "Moved from CLAUDE.md, 2026-10-10"

**Formulas are drawn by MathJax 4, inside the process** (task 99, the CEO's,
2026-10-09): `services/mathjax.py` runs the vendored bundle
`app/assets/mathjax/tex2svg.js` — built once from `entry.js` beside it, no
Node at build or run time — in V8 through mini-racer, and resvg-py
rasterises its SVG at mathtext's DPI and stroke. mathtext had no matrix, and
every record brought the next command it lacked. `pdf.for_mathjax` keeps
only the document's own decisions — one ≤ and ≥, one ⇒, «\pmod 13» one
modulus, Russian words as text. A display formula wider than its column is
broken to it; an aligned chain is drawn whole. What MathJax refuses — or a
glyph outside its bundled font — goes to mathtext, logged at INFO; the
source only when both refuse, a warning. The warm-up says which: `Formulas:
MathJax 4.1.3 in V8, mathtext behind it`, or mathtext only with why. A
paragraph's line counts every image on it (`pdf.Paragraph`): reportlab
5.0.1 never counted the one a wrapped line begins with. → "Record 102, the
formulas' engine"

**mathtext is not LaTeX, and stands behind MathJax.** `pdf.for_mathtext`
rewrites what the model writes into what mathtext draws — dropping what does
nothing to the layout, mapping LaTeX's second spellings (`pdf._SYNONYMS`),
setting a brace's words under or over its line, bracing an operator alone
in an index, which mathtext would space as an operation — each rewrite at
its pattern in `pdf.py`. Environments become `\left…\substack{…}\right…`,
losing column alignment, which is why a matrix is asked for as a markdown
table, and an aligned chain alone in a display formula is drawn a row at a
time (`pdf.aligned_rows`), since `\substack` sets its rows touching. **A
term the author struck out is drawn struck** (task 77) — `\cancel` rising,
`\bcancel` falling, `\xcancel` both — and **a term framed inside a line is
drawn framed** (task 78): by MathJax itself, and by mathtext, which has
neither, through the formula drawn a second time with the term's place left
empty, the stroke or the frame going round what the two pictures differ by
(`pdf._mark`). One that cannot be placed sends the formula out as its
source, never without its mark: «\cancel{56}^{48}», 56 crossed out and 48
written over it, would read as 56 to the 48th. A command ends where its
letters end, `(?![A-Za-z])`. mathtext draws neither `\ce{…}` nor
`\cancelto`; MathJax draws both. `test_pdf.py` proves each rewrite made
before 2026-09-29 both rewrites and draws — those after it were checked by
drawing the record that showed them, under the decision to add no tests —
and a refusal is a warning in the log with both engines' diagnoses, once
per formula per document. → "mathtext, one record at a time", "Record 74, a
lecture on trees"

**An array ruled inside is drawn as a table** (`pdf.ruled_arrays`) — a long
division "уголком", cells as formulas in their column's alignment, rules under
the cells named, the bar only along rows with something past it; a `tabular`
the same way; an array barred at both ends is still the author's frame. And
**a formula written loosely across lines is still one formula**
(`pdf._loose_formula`) — narrowly: an environment closed within sixty lines,
or two dollars with an environment, row break or column between them. →
"Record 45, a lecture on remainders"

**A drawing comes back as data, not a sentence about itself**: rule 6 of the
recognition prompt asks for a graph as `[граф: 1-2, 2->3]` and a matrix as a
markdown table, `[схема: …]` with its frame for the rest, and `pdf.blocks()`
draws them — a drawing taken from the page, `[рисунок N: …]`, drawn again
(task 101) or cut out (task 54), as the author's drawing in the document's
ink on its paper, at about its size on the page, with no caption;
a `[схема: …]` with no cut-out as the line it always was. A graph goes round
a circle, the same every time; **a tree that branches is drawn as a tree**
(`pdf._tree_positions`) — its root on top, children under their parent in
the order read — since on the circle a tree is chords crossing one
another. A path, a cycle, a loop and an edge read twice keep the
circle. A drawing written inside a line of text is lifted onto its own
(`pdf._lift_drawings`), for the document only. That syntax — like the
composing stage's "### Определение" — is one contract in two files: changed
on one side, the record prints the spec. Nothing yet compares the runs' edge
lists — `docs/PLAN.md` → Known risks. → "Record 74, a lecture on trees"

**A drawing that is data is drawn from its data** (task 94, the CEO's,
2026-10-10), from `prompts-v10.md` on — `v11` asking first whether a
drawing is one of the kinds, «[схема: …]» only for one that is none, since
v10 wrote a number line in words (→ "Record 105, and the prompt that
wrote no chart"): `[график: y = x^2; x от -2 до 2]` —
a function by its formula, a sequence as its terms, a constant as a dashed
level; `[прямая: a, c, X = [a; c), (c; +\infty)]` — a number line, its
points left to right and its intervals, «множество X» for a set whose ends
are not named; `[отображение: A -> B; 1 -> a, 2 -> a, 3 -> b, c]` — a
mapping, its arrows. `charts.py` reads them, never raising; `pdf.py` draws
them as the reference lecture draws its figures — an axis with its arrow,
an interval a bar with a nested one a level up, an open end a ring, a
graph on axes through the origin numbered with the decimal comma, two
ovals and their arrows — names in the formulas' face, at the size they are
set. **A chart is drawn only when another run read the same data**
(`charts.agreed`, in `transcribe_consensus`): a curve by the numbers it
comes to, not its range; a line by its points and intervals; a mapping by
its arrows; a name as one expression however written. Settled at its
place when the runs' drawings line up: one the chosen run described in
words, or read otherwise, is drawn as two other runs read it alike — the
chosen run was chosen for its text. One no two runs read alike, or one
run's alone, goes into the record as its words, `[схема: …]` — an invented
point is drawn as confidently as a real one. The log says every page's
charts by run. The runs are compared without their charts —
the agreements, the divergences, the medoid — so a range one run read
wider is no number misread. A formula with a letter its range does not
give, «y = kx + b», is no data. The checks of the work never read a
chart (`charts.blanked`); to the captions, the study version and the merge
of notebooks it is a drawing. Sets, balls and neighbourhoods sketched are
no data and stay words. → "Drawings that are data"

**The document says nothing about how a page was read** (2026-09-25): no
reading that could have been another, no numbers the runs read differently, no
page read without a second opinion, no "нужна проверка". The columns behind
them — `uncertain`, `numeric_divergences`, `unverified_pages`, `status` — are
still written: the instrument's, not the reader's. Nor does the chat get them;
only the pages an album went out without are named there. Nor which half of
a photograph a text was on: «[Левая страница]», «[Правая страница]», as the
reading marks a spread's halves, are not printed (`pdf._unlabelled`, task
92). → "Remarks about the reading", "Record 97"

**A remark is an error the code found in the work, set where it is.** What
`mathcheck` and `graphcheck` find is a `vision.Finding`: the `Issue` and the
text it is about, taken when the page is checked and stored in `notes.issues`
as `anchor` — a line number would not survive composition. `render` sets it
after the sentence holding its anchor, compared without spaces, dollars and
bold, across the sentence's lines (`pdf._anchored`); one that anchors nowhere
goes to the end. An equality of letters that does not hold is one too
(`algebracheck`, task 84, "An equality that does not hold"). **A box never
stands inside a sentence** (task 83): a record whose composition was refused
is set line by line as the notebook has it, and a box under its line would
cut a sentence in two. The lines of a sentence, as code tells them — a line
in lower case goes on from the one before, a formula or a sign from a line
that does not end a sentence, a blank line before a formula set apart and a
main formula included (task 86), a line that does not end one into the list
it opens at its first item, ten lines at most (`pdf._sentence_end`) — are
one place: a finding, an explanation, a teacher's box after the last, and an
anchor found across them. An idea stands before the line its anchor begins
in — the line its proof begins on — moved up only over lines that go on in
lower case (`pdf._anchor_line`), not to the start of its sentence, which may
be the theorem above the proof. A record stored before anchors is checked
again when rendered. graphcheck's unread cell is not an error in the work
and is not printed (`graphcheck.UNREAD_CELLS`). → "Records 88 and 89",
"Records 90, 91 and 92"

**Adding is not forbidden; adding unmarked is.** That is stage three: a
separate call over the trusted text, stored apart, printed as the bot's —
never the call that reads the photo, where "the main points" of a bad shot is
the fluent retelling itself.

**A passage from another notebook is the lecture's text, marked as set in**
(task 63): `merge.merged` writes it between `pdf.inserted`'s lines into the
text it hands to render, never into a stored record. Drawn at the column's
full width, so its formulas and tables are the base's, with a kraft line in
the margin beside it and its label over it in the grey ink; unnumbered — the
numbers are the base's, and an explanation points at them. A finding of the
other notebook stands under its passage; its explanations and summary are
not the document's.

**A sentence that ran over a page edge is joined by code**
(`albums._continues`) only when both sides are ordinary prose, the first half
unfinished and the second in lower case: joining two things that were not one
sentence is worse than the seam. → "The sentence cut by a page edge"

---

## Concurrency ceilings

Two are settings and three are computed from one of them, so raising one
number never leaves another quietly cutting the work short:

| Constant | Where | Value |
|---|---|---|
| `API_SLOTS` | `services/vision.py` | `10` — Gemini answers a bigger burst with 429s; the semaphore is built from it and `albums.py` counts waves with it |
| `VISION_CALL_TIMEOUT_S` | environment | 30 s by default, 5–180; one call over **one page**, and three ceilings below derive from it |
| `COMPOSE_CALL_TIMEOUT_S` | environment | 240 s, 30–600; one call over **the whole record** — nothing derives from it |
| `EXPLAIN_CALL_TIMEOUT_S` | environment | 240 s, 30–600; the writing call, sized like composing; it takes a slot the same way, after `process_batch` |
| `_SOURCE_TIMEOUT_S` | `services/explain.py` | 90 s — one search; up to eight at once, each on a slot |
| compose's slot | `services/compose.py` | one of the `API_SLOTS`, held for the whole call; after `process_batch`, outside `_ALBUM_TIMEOUT_S` |
| the study version's call | `services/study.py` | one of the `API_SLOTS`, beside the explaining stage's for a record that joins no lecture (task 104), else at delivery or on a press, `EXPLAIN_CALL_TIMEOUT_S` — a call over the whole record, as the explaining one is |
| the sketches' calls | `services/sketches.py` | three on `API_SLOTS` for a page that describes a sketch, after its runs, at `VISION_CALL_TIMEOUT_S`, counted in `_ALBUM_TIMEOUT_S`'s waves (task 101) |
| the captions' call | `services/explain.py` | one of the `API_SLOTS`, beside the explaining stage's first call, `EXPLAIN_CALL_TIMEOUT_S`; thinks `low` and answers in seconds (task 95) |
| `RUN_WORST_CASE_S` | `services/vision.py` | `(pauses + 1) × call + sum(pauses)`, every attempt timing out — 93 s at the default |
| `_AFTER_TIMEOUT` | `services/vision.py` | `2` — a first attempt that timed out is followed by one twice as long, and that is the last: 90 s then 180 s in production, 271 s, inside `RUN_WORST_CASE_S` |
| `_CONSENSUS_TIMEOUT_S` | `services/vision.py` | `RUN_WORST_CASE_S × TIMEOUT_MARGIN` — 120 s, a wave of runs; a page that reads further waits for two |
| `_ALBUM_TIMEOUT_S` | `bot/albums.py` | `waves × RUN_WORST_CASE_S × TIMEOUT_MARGIN`, waves = ⌈`MAX_ALBUM_PAGES` × (`VISION_RUNS` + `MORE_RUNS`) ÷ `API_SLOTS`⌉ — 1813 s, 5323 s at production's 90 s call; raising it is allowed, lowering it is not |
| `_QUIET_SECONDS` | `bot/albums.py` | 3 s of silence since the last `announce` closes an album, once every announced page is in |
| `_CONTINUE_S` | `bot/albums.py` | 60 s of silence closes a send that ends on an album of exactly ten, which the rest of the send may follow (task 81) — three times the 19 s a phone took to upload the next album of a send (task 85) |
| `_COLLECT_MAX_S` | `bot/albums.py` | (⌈`MAX_ALBUM_PAGES` ÷ 10⌉ + 1) × `_CONTINUE_S` from the send's first page — 240 s at thirty pages — so a stream that never goes quiet is not waited on for ever, and a send that keeps coming is not cut |
| `_NOTEBOOK_COLLECT_MAX_S` | `bot/albums.py` | the same for a private chat's send, which may be a whole notebook of `NOTEBOOK_MAX_PAGES` — 660 s at a hundred pages (task 63) |
| `NOTEBOOK_AT_ONCE` | `bot/albums.py` | `4` — a notebook's pages read at a time: twelve runs keep the ten slots full, and another chat's album waits behind one window of them rather than a hundred pages |
| `NOTEBOOK_TIMEOUT_S` | `bot/albums.py` | the album's ceiling for `NOTEBOOK_MAX_PAGES`' waves of runs — raised with it, never lowered |
| `_FETCH_AT_ONCE` | `bot/handlers.py` | `10` — a notebook's photographs downloaded at a time: a hundred fetched at once held a hundred originals in memory |
| `_LECTURES_AT_ONCE` | `bot/handlers.py` | `2` — a notebook's lectures made at a time, each begun when the one two before it is sent, so the first is sent while the rest are made |
| `max_overflow` | `db/session.py` | 15 — every page of an album arrives at once with a session, the winner holding a connection for the whole album; the others commit before they wait (task 81) |

- `TIMEOUT_MARGIN = 1.3` is the ratio the old hand-written 120 s held to 93 s.
  The startup log prints all five timeouts and the repeat after a timeout:
  two are computed, and a deploy has to say what it runs on.
- **A recognition timeout is a page the model thinks about longer, not a line
  that hung** (task 76): the long calls are the ones that think, and the
  same ceiling again timed out again — runs lost, pages compared on two runs
  or one. So the repeat gets the time of the two it replaces. → "What the
  bot spends its time and memory on"
- **The two timeout settings are not interchangeable**: recognition is per
  page and the album ceilings derive from it; composition is over the whole
  record and its wait grows with the album. Three pages compose in about
  43 s on `gemini-3.8-flash`, hence 240 s.
- **Composition does not retry a timeout** — at most two calls a composition,
  the second for a 429, a 503 or a dropped connection; and a second
  composition only when the guards refuse the first. `vision._should_retry` counts a timeout
  worth another call, which is right for a page — once, twice as long; at a ceiling of minutes a call
  that reached it was working, and waiting again doubles the window in which a
  deploy cancels it. Every attempt is written to `ai_calls`.
- **Raising `VISION_CALL_TIMEOUT_S` is not linear**: at 90 s the album ceiling
  is 5323 s. It fires only when calls hang; what it buys is exposure, since any
  deploy cancels the background task an album runs in.
- **The group ceilings use `asyncio.wait`, never `wait_for`**, and cancel the
  stragglers in a `finally`: cancelling the group would discard the
  `CallStats` of runs already billed, and an orphaned run keeps paying for
  results thrown away.
- **Image work runs on two threads of its own** (`images.in_worker`, task
  76) — a page compressed, its frame checked, its drawings cut — however
  many pages an album holds: fanned over the default pool, a thread a page,
  it left 50–100 MB an album the process never gave back.
- **One PDF is drawn at a time** (`images._PDFIUM`, task 100): PDFium may
  not be called from two threads at once, not even over two documents. A
  PDF of more than twice an album's pages is refused before it is drawn
  (`handlers._PDF_DRAWN_ALBUMS`), or it would hold an image thread for
  minutes.
- **One document is drawn at a time** (`pdf._DRAWING`, task 76) — "The
  document".

---

## Scale debt

The product targets many users; these shortcuts are deliberate, and each one
breaks at a knowable point. Don't treat one as settled design, and don't add
the machinery before the point arrives — record what you find here instead.

| Shortcut | Breaks at | What happens |
|---|---|---|
| The album buffer is six module-level dicts in `bot/albums.py`, the pages being read a set in `bot/corpus.py`, and the study versions being built a set in `bot/study_version.py` | **a second replica** | pages of one album land in different processes and become separate records; two calls on one album in two processes read it twice; two presses of «Учебная версия» pay twice |
| An update is processed in a background task | **any deploy** | in-flight updates are cancelled; paid Gemini calls are wasted |
| No deduplication on `update_id` | **a delivery timeout** | Telegram retries: a duplicate record and a second set of paid calls |
| `DAILY_COST_LIMIT_USD` is one cap over every chat, above each group's day in pages | **about four groups at their full day** at today's prices, two once they double on 2027-01-01 | the chats that come later in the day find the bot stopped: the cap has to grow with the groups |
| A group's day is counted from the records already saved | **a group's albums read at once** | the group goes past its day by up to an album |
| A person's day is checked before their record and counted after it | **two records of one person read at once** | both pass the check, and the person goes past their day by up to an album; the count itself is right (task 76) |
| DB pool is 5 + 15, and a record holds its connection for its whole processing, 3–8 minutes | **~20 records in flight** | connection checkout times out after 30 s: new updates fail, and `log_ai_calls` drops the spend rows it cannot write, so the daily cap undercounts in exactly that burst |
| A username or group title the middleware refreshes is written at the update's first statement | **a rename while a record is processed** | that person's or group's other updates wait on the row for the record's minutes, the Saturday summary's claim included |
| `_API_SLOTS` is a per-process `Semaphore(10)` | **tens of active chats** | the queue to Gemini grows into timeouts |
| Stage three searches up to eight explanations at once | **two records finishing together** | the searches hold most of the ten slots for ~20 s, and another chat's pages queue behind them |
| Photos are held whole in memory | **many parallel downloads** | container memory |
| A whole notebook is read and made in one background task, twenty to forty minutes for a hundred pages | **any deploy meanwhile** | its lectures not yet sent are lost and their reading paid for; the notebook does not use the person's day up, and is sent again |
| A notebook's reading keeps the ten API slots full, four pages at a time | **a group's album sent meanwhile** | it waits behind one window of the notebook's pages, a minute or so; two notebooks at once halve each other |
| A private document of a record with its subject asks Telegram about every group the bot is in (`to_group.targets`) — four in production | **hundreds of groups** | every such delivery waits on as many calls, and a few at once reach Telegram's thirty requests a second: ask only the groups the person is known in, and offer the rest by a button |

**One replica is a requirement, not a default.** Scaling the service
horizontally will silently split albums again — the failure looks exactly like
the bug that took three attempts to find. Fix the first row first, with
Postgres as the buffer — a `note_pages` table keyed by `media_group_id`,
assembled by `message_id` — not Redis: the data is already in Postgres, and a
debounce would then only decide *when* to send the PDF, never whether a page
survives.

---

## Ready-made modules

`photoguard.py` (`check_photo_bytes`), `consensus.py` (`compare`,
`compare_text`, `pick_representative`) and `mathcheck.py` (`check`) were
written and tested before this repository. **Import and call them; don't
rewrite or "improve" them.** Found a bug — report it, don't fix it silently.

Five exceptions, four made after the failure was reproduced. Three are in
photoguard's line height: `UNMEASURED_LINE_HEIGHT` names a height that was not
measured, and the criterion is skipped rather than reading `0.0` as a tiny
line; `photoguard._line_height` thresholds by Otsu and takes the pitch as the
median distance between bands of ink, with no three-line minimum (task 35); and
`MIN_LINE_HEIGHT_PX` went from 20 to 16 (task 43), after a legible page of a
dense notebook was cut off at 20. The fourth: `MIN_CONTRAST` went from 28 to
20 (task 75, the CEO's), after a page sharp and filling its frame was refused
as too dark three times. The fifth, the CEO's word with no page refused
(task 102, 2026-10-11): every threshold lowered — sharpness 90 → 15,
contrast 20 → 10, the sheet's share of the frame 0.18 → 0.14, the line's
pitch 16 → 14 px — each where record 106's pages, made worse on purpose,
still read, with a margin before a formula's indices are guessed rather than
read: the old ones refused pages that read whole. → "The line height
photoguard could not measure", "Record 45, a lecture on remainders", "A page
refused as dark", "The frame check against what can be read"

Still open in photoguard: the thresholds are set on one hand's three pages
read by eye, never by the model, and every skip logs its four metrics to
check them by. The line height measures nothing on squared paper — the
grid's rows read as ink, one band the sheet's height, 1141–1256 px on record
106 — so «Текст мелкий» never fires there, and a small hand from afar is
caught by the sheet's share alone. A shake along the lines leaves the grid
sharp: 17 px of it passed the sharpness check, old and new, with nothing
legible. `MIN_CONTRAST`'s measure is the spread of brightness across the
sheet: it counts how much is written as much as the light, so a page of a
few lines is mostly even paper and reads as dark however it is lit. A
measure of ink against paper would not, and would need real pages, good and
bad, to set. `_paper_box` thresholds at `0.82 × percentile99`, so
a bright highlight shrinks the mask to the glare and `paper_fraction`
collapses. All four thresholds apply to the compressed image, so
`IMAGE_MAX_SIDE` silently recalibrates them.

Worked around, not fixed:

- **`mathcheck.check_chains`** reads any line with two "=" as one chain, and a
  line of modular arithmetic set 1001 against 32 across a "⇒" and a "≡".
  `vision.arithmetic_issues` shows the chain check the page with every line
  holding a relation other than "=" blanked, keeping mathcheck's line numbers,
  and blanks a line the check **raises** on (`vision._survives_chain_check`):
  "1 - 1 = 0 = 5" made it overflow. Reported 2026-09-25.
- **`consensus.extract_numbers`** compares every numeric literal, list markers
  and subscripts included. `vision.meaningful_divergences` keeps a position
  only where two runs read different numbers, drops one with no majority and a
  gap among the variants, and prints an identical line once. → "Numbers the
  agreement could not see"

---

## Structure

```
app/
  main.py             FastAPI, the webhook, /health, the startup log
  bot/
    handlers.py       capture — a photo, an album, a PDF, a .docx, a summon — and membership
    texts.py          every user-facing message, and the command list
    middlewares.py    session, user and group; group chatter dropped; what a page is
    albums.py         the album buffer and its assembly
    corpus.py         tags, search, a record or its lecture as a file, scoped to its chat
    subjects.py       a chat's subjects and lectures: where a record is filed, its day
    tags.py           what a #tag is, and a record's topics
    feedback.py       «Хорошо», «Плохо» and where the error is, under every document
    study_version.py  «Учебная версия»: a record's study version built on request
    notebook.py       a whole notebook sent at once: what it is, its lectures, dated
    to_group.py       «В группу «…»»: a private lecture moved into a group
    waiting.py        the line a chat sees while its record is made
    rating.py         a group's week: who sent its records and who rated them, Saturday's summary; the bot's week
  services/
    vision.py         recognition: the prompt, three runs, parsing, the agreements
    compose.py        stage two: the trusted transcription, formatted
    explain.py        stage three: hard places explained with sources, a summary
    study.py          a lecture's study version: the record in units, arranged by topic
    pdf.py            a record as a PDF
    mathjax.py        formulas drawn by MathJax 4 in V8, mathtext behind it
    figures.py        drawings taken from the page, placed back after composing
    sketches.py       where each sketch is and what its labels say, read by three runs
    strokes.py        a sketch drawn again from its page: its lines, the grid taken away
    charts.py         a drawing that is data — a graph, a number line, a mapping: read, agreed
    lectures.py       where a lecture begins on a page; one lecture a record
    merge.py          one lecture from several notebooks: which is one, what each adds
    images.py         compression, a PDF's pages drawn, and the two threads image work runs on
    limits.py         spend limits
    docx.py           .docx → markdown, no model call
    graphcheck.py     a matrix against the graph drawn beside it
    algebracheck.py   an equality of letters that does not hold, counted at random numbers
    photoguard.py, consensus.py, mathcheck.py    ready-made
  assets/fonts/       Onest, Unbounded, JetBrains Mono, and their OFL licences
  assets/mathjax/     MathJax 4 bundled as one script, its source and licence
  db/                 models.py, session.py, migrations/
  core/               config.py — settings and prices; events.py — event logging
tests/
docs/
  PLAN.md             the work: tasks and owners, "State", "Plan changes", contracts
  FINDINGS.md         the evidence behind the rules here
  BRAND.md            how a record looks — pdf.py draws what it says
prompts/              every prompt, read by its file name at import
evidence/             local only, never in git: records, reference notes, Railway logs
CLAUDE.md, README.md  in the root, where Claude Code and GitHub read them
```

**The prompts**: recognition `prompts-v3.md` to `prompts-v12.md` — v5
extraction only, v6 (production) v5 with the author's frames written as
`\boxed{…}`, v7 without the list of numbers, tried and rolled back, v8 v6
with each drawing's frame, measured and asleep (task 54), v9 v6 with where a
lecture begins, measured and asleep (task 64), v10 v6 with a drawing
that is data written as data (task 94), which wrote a number line in
words, v11 (production since 2026-10-10) v10 asking first whether a
drawing is one of the kinds, v12 v11 with v9's lecture starts, a whole
notebook's alone (task 63, `NOTEBOOK_PROMPT_FILE`); composing
`prompts-compose-v1.md` to `v4`, v3 framing a section's main formula, v4
(production since 2026-10-06) v3 with the author's shorthand spelled out
(task 69);
explaining `prompts-explain-v1.md` to `v4`, v2 (production 2026-10-03 to
10-08) adding the teacher's boxes, v3 (production since 2026-10-08) v2 with
an example that is not the lecture's working with another number (task 78),
kept on the CEO's word while the next records' examples are read, v4 v3
with a caption to a formula or a drawing the record says nothing about,
measured and set aside for the teacher's boxes it cost (task 95); with
`prompts-explain-source-v2.md` for the searches — `v1` before it, kept as
the records made with it were — and `prompts-explain-captions-v1.md` for
the captions' call (task 95); the study version `prompts-study-v1.md`
(task 80) and `v2`, v1 naming the course's organisation (task 93), read by
name as the searches' prompt is; the sketches' frames and labels
`prompts-sketch-v1.md` (task 101). Every
prompt stays in `prompts/` once used: a record does not say which made it.
`vision.load_prompt` reads a prompt from `prompts/` by file name at
**import**: the file has to ship with the deploy or the process dies at
startup, and editing it changes the prompt without touching Python.

**`evidence/` is never tracked** — `.gitignore` covers it, `*.pdf` and
`*.log`. It holds what `docs/FINDINGS.md` was read out of; nothing reads it at
runtime or in the suite. A record is a user's page of notes, and the corpus
lives in the database.

---

## Environment variables

Five are required, and a missing one must crash the app at startup, not on
the first request: `BOT_TOKEN`, `DATABASE_URL`, `GEMINI_API_KEY`,
`WEBHOOK_URL`, `WEBHOOK_SECRET`. The rest, with the code's defaults —
production overrides the model, prompt and stage settings ("Where it
stands"):

```
AI_ENABLED=true          kill switch for all model calls
DAILY_PAGES_PER_USER=12  a person's pages a day, the CEO's since 2026-10-06
DAILY_PAGES_PER_GROUP=20 a group's pages a day, everyone in it, the CEO's since 2026-10-07
DAILY_COST_LIMIT_USD=5
VISION_RUNS=3            at least 2
VISION_MODEL=gemini-3.5-flash-lite
VISION_CALL_TIMEOUT_S=30
VISION_MEDIA_RESOLUTION=unset
VISION_THINKING_LEVEL=unset
PROMPT_FILE=prompts-v3.md
SKETCHES_ENABLED=false   a sketch drawn again from its page (task 101)
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
IMAGE_MAX_SIDE=1500
IMAGE_QUALITY=85
ALLOW_UNPRICED_MODEL=false
MIN_MARKDOWN_LEN=40
MAX_ALBUM_PAGES=30       the pages of one send, its albums of ten read as one (task 81)
NOTEBOOK_MAX_PAGES=100   a whole notebook in a private chat, one a person a day (task 63)
NOTEBOOK_PROMPT_FILE=prompts-v12.md   a notebook's pages read with where each lecture begins
LOG_LEVEL=INFO
FEEDBACK_CHAT_ID=        unset: feedback is stored only
```

- **`MALLOC_ARENA_MAX=2` is set on Railway and read by glibc**, not by
  `settings` (task 76): the process grew 50–100 MB an album and gave none of
  it back until a deploy, which is what glibc's arena per thread does under
  threaded image work. Two arenas keep what is freed reusable. Taking it off
  is a measurement on Railway's memory graph, not a cleanup.
- **A model setting is coupled to its price.** A model absent from
  `PRICE_PER_MTOK` writes `cost_usd = NULL`, the `SUM` behind the daily cap
  skips it, and the breaker stops working with nothing to show for it. So a
  validator refuses to start on an unpriced `VISION_MODEL`, `COMPOSE_MODEL` or
  `EXPLAIN_MODEL`, and a model change brings its price in the same commit.
  `PRICED_MODEL_SETTINGS` and `Settings.unpriced_models()` are one list, and a
  test asserts it: a future setting naming a model goes in that tuple and
  nowhere else.
- **A price is the Standard tier's, and an announced change is written down
  with its day.** Batch and Flex are half of it, and one stood in
  `PRICE_PER_MTOK` for three days, letting through twice the cap.
  `PRICE_CHANGES` holds a change already announced — `gemini-3.8-flash`
  doubles on 2027-01-01 — read by the call's day (`config.price_per_mtok`). →
  "What a record costs"
- **`ALLOW_UNPRICED_MODEL=true` runs one anyway**, with a warning on every
  start, so trying a model before its price is published is a state chosen,
  not stumbled into; `DAILY_PAGES_PER_USER` alone guards spend meanwhile. Turn
  it off once the model is priced: left on, it disarms the next swap silently,
  and the rows written can never be priced. → "What a model change broke"
- **`COMPOSE_CALL_TIMEOUT_S` and `EXPLAIN_CALL_TIMEOUT_S` range 30–600**: under
  30 s the stage refuses itself by construction — the shortest composition
  measured took 41 s — and over 600 s the wait outlives the background task a
  deploy cancels.
- **`VISION_MEDIA_RESOLUTION` and `VISION_THINKING_LEVEL` are knobs on *how*
  the model is asked.** `unset` means the field is not sent — Gemini's
  default, bit for bit the call every finding was made on — and an unknown
  value is refused at startup, since a knob that silently does nothing makes
  an experiment compare a setting against itself. Media resolution is inert.
  Recognition thinks at the default: `low` and `medium` read the marks on
  the page worse, `low` seeing a strike-through and a frame that are not
  there — turning it down is an arm, never a budget setting. Composition and
  the source searches think `low` (`COMPOSE_THINKING_LEVEL`,
  `SOURCE_THINKING_LEVEL`) — the same result at half the price in a third of
  the time; a search at `low`
  that ran none is made once more at the default (`explain._search`).
  `gemini-3.8-flash` refuses `"minimal"` with a 400. → "What a record costs"
- **`seed` is deliberately not a setting, and `temperature` stays at 1.0**:
  three identical runs would send `text_agreement` up without touching
  accuracy — the instrument inverted.
- **A bare `TimeoutError` has an empty message**, so `vision._short_error`
  writes the exception's type into `ai_calls.error`. → "What a model change
  broke"
- **`PROMPT_FILE` names the prompt loaded at import**, so a variant is tried on
  the deployed bot and rolled back by one variable; a name not in `prompts/`
  kills the process at startup, deliberately.
- **The startup log is the instrument's label**: `Recognition: <model>, N
  runs`, the prompt file, its word count, where `numeric_agreement` takes its
  numbers, whether drawings are cut out and lectures marked, the image
  compression, both stages, the captions' prompt, the study version's
  prompt, whether a sketch is drawn again from its page, the call knobs,
  the formulas' engine (from the warm-up), the
  five timeouts and the repeat after one, the pages of one send and the day's limits, a notebook's pages, prompt and ceiling, where a reader's «Плохо» is sent, when a
  group's week is summed up, and whether the bot sees a group's photos. What
  a **record** does not say is which prompt made it —
  `docs/PLAN.md` → "Where the quality work stands", gap 3.

---

## Tests

Offline: no network, no Gemini, no Postgres; whatever needs a database runs on
in-memory SQLite through `aiosqlite`. `tests/conftest.py` fills the five
required variables with placeholders and renders `JSONB` as `JSON` for SQLite
only — `app/db/models.py` stays PostgreSQL. `test_spend_survives_main_rollback`
needs two separate real transactions and is skipped unless `TEST_DATABASE_URL`
points at a Postgres.

| File | Covers |
|---|---|
| `test_parse_response.py` | the model's reply: garbage, fences, missing fields, wrong types, single-backslash LaTeX |
| `test_vision_pure.py` | costs, verdicts, the numbers that vouch, the chains mathcheck is not shown, anchors |
| `test_reliability.py` | retries, one owner per album batch, spend surviving a rollback |
| `test_albums.py` | assembly and its markers, why a page is dropped or only marked, an album's tag, refused frames |
| `test_limits.py` | `check_limits` and `consume` — the money-critical path |
| `test_config.py` | settings and bounds (`VISION_RUNS >= 2`), stages off by default, models priced, `PROMPT_FILE` selecting the prompt — in a subprocess |
| `test_compose.py`, `test_explain.py` | stages two and three: off by default, never the photo, every guard, retries, sources from grounding |
| `test_graphcheck.py` | what it must catch, and every shape it must stay quiet about |
| `test_photoguard.py` | the rules this project changed in photoguard |
| `test_handlers.py` | `texts.split_message`, the catch-all, a group's record, membership, a refused frame, nothing about the reading sent |
| `test_middleware.py` | session per update, rollback, the early commit, what a group lets through, the supergroup move, the insert race |
| `test_corpus.py`, `test_tags.py` | filing and finding, topics, the record's boxes, ownership — no query reaches another owner's records |
| `test_pdf.py` | blocks, every mathtext rewrite drawing, frames and numbers, tables and graphs, the rhythm, the boxes, the head and the signature, nothing unreadable sinking the document |
| `test_docx.py`, `test_images.py` | `.docx` to markdown; the 1500 px cap, EXIF, JPEG |
| `test_wiring.py`, `test_webhook.py` | router order, commands described, membership subscribed; the endpoint answering first and checking its secret |

Deliberately **not** covered: `consensus` and `mathcheck` beyond the code that
calls them — their own tests never came into this repository; `photoguard`
beyond the rules changed here; and the photo and document pipelines end to
end, which break on every reordering of a handler while the pipeline is not
settled.

---

## How to work in this project

- **Write the plan of changes first, then the code** — whatever the size; a
  one-line change still gets its plan stated. If the plan leaves no open
  question, carry it out at once; stop and ask only when it holds a decision
  that is the author's — a trade-off with no clear default, a change of scope,
  a conflict with the plan or this file — and give a recommendation with the
  question.
- **Code is written once, to work for good** (the CEO, 2026-10-10: «пишем
  один раз и навсегда»): a change ships whole — every path it touches, every
  way its input can go wrong, what happens when it fails halfway — so that it
  works afterwards without being come back to. Before it is pushed it is run
  against what production holds and against input made to break it, and
  what it leaves behind is let go whatever happens: a figure closed, a
  file freed. No stopgap left to be fixed later; what code cannot make sure
  of — how a model will write — is said so, and measured.
- **One task from `docs/PLAN.md` — one session — one commit**, with its plan's
  lines, its documents and README ("Who decides").
- **No new tests while the project is in active development** — the author's
  decision, 2026-09-29. The suite stays green: a test that pins behaviour
  changed on purpose is changed with it.
- Nothing beyond the current task; an idea goes in the plan's backlog.
- Write code that can be explained out loud; a non-obvious decision gets a
  comment about **why**, not what.
- Russian in user-facing messages, all of them in `bot/texts.py`; English in
  code, logs, commit messages and these documents — `README.md` and
  `docs/BRAND.md` are the Russian ones.
- Don't create abstractions for the future: duplication now is cheaper than
  premature architecture.
- Not one traceback reaches a user: an unhandled error is a clear message to
  them and the details to the log.

---

## What NOT to do at this stage

Shared by both owners. Deliberately postponed — don't suggest or implement:

- An app in the stores, or any interface but the bot and its Mini App. The
  Mini App is phase F (2026-10-02); the stores come once it is used
- Spaced repetition before the app's first version is used. It is the app's
  next tool, built on the exam preparation's material — in the app, never
  in the bot or the document (2026-10-02)
- Payments, subscriptions, pricing tiers
- Custom registration and passwords — identity already comes from Telegram
- An admin panel, save one read-only message, the CEO's of 2026-10-07:
  `/stats` in the chat every «Плохо» goes to answers with the whole bot's
  week (`docs/PLAN.md` → task 74)
- Export to Anki, and any bulk export of the corpus. A record comes back as one
  PDF when a tag matches it — presentation, not an exit door, and no licence
  for "download everything". The one exception is the author's, 2026-09-30: a
  subject's records as one document to study from, opened by an overview the
  model writes over them and marks as the bot's, sent only when somebody asks
  with a command (`docs/PLAN.md` → task 52). An overview, not a download — no
  other format, no archive, no "everything at once"
- A language trainer, text rewriting, or any second feature
- Visual design and styling of **bot responses** — the chat stays plain text.
  This is not the document: the PDF is what the group receives, so its design
  and readability are the product itself — "The document"
- Sharing before the app's first version is used; social features and
  friends at all, save one, the CEO's of 2026-10-06: a group's own week —
  who sent its records and who rated them — shown in that group alone and
  never compared across groups (`docs/PLAN.md` → task 72)
- Caching, queues, microservices, Docker, CI
