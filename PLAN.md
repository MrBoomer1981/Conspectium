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
- [x] 17. The record as a PDF
- [x] 18. The webhook answers before it processes
- [x] 19. Graphs and tables drawn, not described
- [x] 20. Heading steps, callouts, and a prompt variant behind a switch
- [x] 21. Remarks beside the line, figure rows, and readable flags
- [x] 22. The matrix checked against the graph, by code

**The six-item quality plan, and what real use asked for after it:**

- [x] 23. A row names its own model; a page refused by the frame check keeps
      its numbers; a line height that could not be measured is not a small one
- [x] 24. Stage two — the trusted transcription, formatted (`compose.py`),
      its guards, and two prompts for it
- [x] 25. The instrument: `numeric_agreement` as a column, the thinking half
      of the budget recorded, the output ceiling raised, `gemini-3.8-flash`
      priced, and an unparseable answer that names why the model stopped
- [x] 26. Six commands deleted, one gesture kept: a subject you choose, five
      topics the bot reads, and a "#word" that files or finds

**What production asked for next:**

- [x] 27. Stage two waits on a ceiling of its own, and a 503 earns a second
      call — a page's timeout was being applied to a call over the whole record
- [x] 28. A heading that is half a sentence is not a heading: the composer's
      invented sections are taken back by code, so they stop becoming topics
- [x] 29. A page is no longer thrown away for its layout: when the runs'
      numbers are identical, `rejected` becomes `needs_review`

**Phase A — reliability. A record has to exist:**

- [x] 30. An answer that would not parse is asked for again, and the log says
      what shape came back
- [x] 31. An album with an unreadable page is delivered with the hole named in
      the document; only an album with nothing read asks to be taken again
- [x] 32. A legible page is not dropped: disagreement between the runs marks
      it instead, and one readable run is enough to keep it
- [x] 33. A sentence that ran over the edge of a page is put back together
      instead of coming out as two halves with a rule between them
- [x] 34. A PDF that does not print raw LaTeX where `\substack` can draw it:
      `cases`, every matrix environment, `aligned`, `array`
- [x] 35. `photoguard._line_height` rewritten against pages of known pitch:
      Otsu instead of a rank, the median gap between bands instead of the page
      height over a count, and no three-line minimum

**Phase B — the ideal record:**

- [x] 36. The document's design and readability: the typographic scale and the
      rhythm it sets, the page's furniture, callouts and remarks as one system,
      tables and figures that sit on the page rather than float through it.
      Revisited the same day after record 42: the style of
      `матан 24.09.2026.pdf` copied — Lato, Computer Modern, its column and
      its greys. And after record 43: main formulas framed, larger and
      numbered — the author's frames read by recognition (`prompts-v6.md`),
      a section's result marked by the composer (`prompts-compose-v3.md`),
      two a section at most
- [x] 37. Stage three: hard passages explained and implied context restored,
      over the trusted text, with `google_search` and sources that are
      required rather than decorative. Built as the author decided on
      2026-09-24: explanations in the flow of the material, and a short
      summary at the end whose numbers must all be the record's
- [x] 38. The explanation as a marked box in the PDF, with its sources, never
      in the body of the record — in the system task 36 establishes

**Phase C — the group:**

- [x] 39. `groups` and `notes.group_id`: the bot lives in a course chat and a
      record belongs to the chat. Built as the author decided on 2026-09-25:
      in a group the bot takes a photo, an album or a `.docx` only with a
      "#word" in its caption, and that word is the record's subject — so a
      group is never asked, and what is not addressed to the bot is dropped
      before a session is opened
- [ ] 40. The tag question rebound to its record — the stateless trick does not
      survive several people answering in one chat. 39 took the question out
      of groups: a record is made there only with its subject, and a "#word"
      in a group only searches. What 40 still means is the author's to say
- [ ] 41. Limits and spend counted per group; the scale-debt rows that come due
      with a second person in the chat

**Back to the record — what record 45 showed.** The author put the group on
hold on 2026-09-25, after 39 shipped: every effort goes to the records first,
and the group is tested later. These come before 40 and 41.

- [x] 42. What record 45 printed as source: `\pmod` and its kin, a long
      division drawn as a ruled table, a bold word inside `\text`, a quote, a
      title's formula; a LaTeX command written with one backslash repaired
      before recognition's JSON is parsed; and a congruence no longer read by
      mathcheck as a chain of equalities
- [x] 43. A page the frame check refuses is asked for again before anything is
      read: the album is not read with a hole in it but asked for again,
      whole, with nothing charged — the author's choice on 2026-09-25 over
      delivering now and inserting the page later. `MIN_LINE_HEIGHT_PX` 20 → 16
      on this notebook's evidence
- [x] 45. A formula the document still printed as its source when the page
      wrote it loosely: an environment bare across lines with no `$$`, a `$`
      opened on one line and closed on another, `tabular` for two columns of
      working, Russian words inside one formula — all four on record 47, which
      printed 103 lines as source and prints none
- [x] 46. Remarks only for errors in the work, at their place. The author's
      decision on 2026-09-25: nothing about how a page was read — no reading
      that could have been another, no "в рукописи", no boxes "прочитано без
      сверки" and "числа прочитаны по-разному", no "нужна проверка" — in the
      document or in the chat after it; what mathcheck and graphcheck find is
      set under the text it is about, which each finding now carries. Records
      19, 45, 46 and 47 re-rendered: 27 pages became 23
- [ ] 44. What a record costs, and what can be cut without cutting the
      document. First half done: the accounting was wrong both ways — the
      model priced at the Batch/Flex rate (half of Standard, so the cap let
      twice its figure through), the search fee per call at the Gemini 2.5
      price instead of per query at Gemini 3's — and the dated doubling of
      2027-01-01 written down. Second half, in part: composition and the
      source searches think `low`, measured on record 45 — same document and
      grounding, about half the price, a third of the time. What is left is
      recognition's own thinking, the largest line of a record and the one
      that changes how a page is read. Run once on 2026-09-25, the album of
      record 46 sent again at `low` (record 47): a third cheaper to read, and
      worse to look at — environments written bare across lines printed as
      source. Recognition stays at the model's default; a `low` search that
      did not look is asked again at the default. Priced stage by stage the
      same day: recognition is 84% of a record's bill, its thinking 40%, and
      the list of numbers the prompt asks for a third of its answer. The
      author then checked 47 against 46 on the photographs: `low` reads every
      number alike and the marks worse, five places to one — rejected on
      reading, not only on layout. `medium` on the same album (record 48)
      thought almost as long as the default, cost 7% less and read worse
      still — closed; recognition stays at the default. `prompts-v7.md` on
      the same album (record 49), no list of numbers and no doubtful spots:
      the answer 44% shorter, the thinking 69% longer, recognition 14% dearer
      and read as well — rolled back to v6. What is left is Flex and the
      number of runs, both the author's to decide
      Flex — half price for 1–15 minutes a call — and fewer runs are the
      author's to decide after

### Why the design comes before the explaining stage

The author asked for it as a mandatory item, and it goes first in phase B for
three reasons, of which the third is the one that decides.

The document **is** the deliverable. A group does not receive a pipeline; it
receives a PDF, and how readable that PDF is *is* the product rather than a
coat of paint on it.

It has a feedback loop that needs nobody: records 37, 39 and 40 are in
production with headings, formulas, tables, graphs, callouts and remarks in
them, so a change can be rendered before and after and looked at.

And task 38 inherits it. An explanation box designed before there is a system
to put it in is a box designed twice — once on its own, once again when the
page around it is settled.

**The boundary, because design is work that absorbs whatever time it is
given.** In scope: the scale of body, headings, tables and captions and the
vertical rhythm between them; margins and the page's furniture (the title
block, page numbers, what a continued record looks like on page four); the
callouts and the anchored remarks as one visual system rather than two; how a
figure, a table and a display formula sit in the column. Out of scope: a
colour system wider than the tones that exist, anything per-subject or
per-user, and the styling of chat messages — those stay plain on purpose.

The fonts were in that list — "nothing beyond the DejaVu family already
bundled" — until the author moved the reference on 2026-09-24: record 42 came
back heavy, and the document is now a copy of `матан 24.09.2026.pdf`, Lato and
Computer Modern included. Lato 2 lives in `app/assets/fonts/`.

The order of 33-35 is the author's, made on three albums run through the
deployed bot on 2026-09-23: the seam and the raw LaTeX were in the documents
being read that evening, while the frame check refused nothing at all across
twelve pages. Calibrating it is still worth doing — it is now the only guard
left between a photograph taken from across the room and the corpus — but it
was not what made those records read badly.

## State

Update strictly following this template, adding or removing nothing:

```
Done: 1-39, 42-43, 45-46
Current task: 44
Next task: none
Blockers: 44 waits on the author — Flex, and the number of runs
```

## Where the cost work stands, 2026-09-25

Task 44, its second half, as the session of 2026-09-25 left it. The evidence
is in `FINDINGS.md` → "What a record costs"; this is where it stopped.

**What a record costs.** Record 46, five pages: $0.222 in tokens, $0.320
with the search queries, which the cap counts and which are not billed under
5,000 a month. Recognition is 84% of the tokens — its thinking 40%, its
visible answer 35%, its input 8% — composition 7.5%, the explanations 6%,
the source searches 2.5%. On 2027-01-01 `gemini-3.8-flash` doubles.

**Four readings of one album** — the five pages of record 46, sent again:

| record | what changed | recognition | thinking | answer | read |
|---|---|---|---|---|---|
| 46 | nothing: v6, default thinking | $0.185 | 23 693 | 20 767 | the reference |
| 47 | thinking `low` | $0.125 | 7 026 | 21 298 | worse, five known places to one |
| 48 | thinking `medium` | $0.172 | 19 836 | 21 155 | worse, digits and notes lost |
| 49 | `prompts-v7.md`, no list of numbers | $0.211 | 40 110 | 11 669 | as well |

**Settled.** Recognition stays at the model's default thinking and on
`prompts-v6.md` — on Railway `VISION_THINKING_LEVEL=unset` and
`PROMPT_FILE=prompts-v6.md`. Composition and the source searches stay at
`low`. A shorter answer does not make a cheaper call while the model decides
how long to think.

**Open, and the author's to decide:**

1. **Flex.** `service_tier: "flex"` bills every token at half price on the
   same model, for 1–15 minutes a call and 503/429 when capacity runs short,
   with no fallback. Before deciding: a probe of the real latency and refusals
   on these calls — and the author's word on a record arriving in tens of
   minutes. Every ceiling in `CLAUDE.md` → "Concurrency ceilings" is sized
   for Standard.
2. **The number of runs.** Two runs take 28% off the bill, one 56%. Since task
   46 the runs' agreement shows nowhere a reader looks; they still pick the
   most typical of three readings, cover a failed call (8% fail), and are the
   instrument every arm is scored on. Before deciding: keep the three readings
   of a few albums — text, not photos — and count how often the one chosen
   beats a single run.
3. Small: the explanations' writing call at `low`, about 3%, testable on
   stored records with no album sent.

**Scoring the next recognition arm.** Send the album of record 46 again and
compare with 46: the numbers page by page, and the six places whose right
reading the author checked against the photographs — the key in `FINDINGS.md`
→ "What a record costs".

**Kept, and why.** Records 46–49 are four readings of one album and stay in
the corpus: they are the evidence these arms were judged on and, with the
author's check of the photographs, the benchmark for the next one — the
author's decision, 2026-09-25. `DAILY_PAGES_PER_USER` stands at 30 on Railway,
raised from 10 for the test albums; the author sets it back.

---

## Where this is going, decided 2026-09-23

The product is a bot **in a university group chat**. One person photographs a
handwritten page; the chat gets a PDF it can study from. `CLAUDE.md` → "What
this is" carries the definition; this section carries the decisions behind it
and what they cost.

**A record belongs to the chat, not to the person who sent it.** Any member
searches it by tag and gets the PDF. That is one line to say and it undoes an
assumption the schema is built on: every query today is scoped by `user_id`,
and a test asserts that none of them can reach another user's records. Phase C
replaces the owner, it does not add a sharing feature.

**What the explaining stage may add: hard passages and the context the page
implied.** Not only the places the record already marks as doubtful — a
classmate who missed the lecture is not helped by knowing that one word was
illegible — and not a self-contained textbook chapter either, which is the
shape of the worst failure this project has reproduced. Explain what is hard,
restore what was assumed, say where it came from.

**Sources are the guard, because the reader cannot be one.** We cannot check a
claim by code. We can require that every added box carries the links Gemini's
grounding metadata returns, and refuse to print one that carries none. In a
group this matters more than it did for one author: the person who most needs
the explanation is the one who was not there.

**Order: reliability, then the record, then the group.** Eight albums of
forty-five attempts have been lost, two of them this evening. In a group a lost
album is not one person's inconvenience, it is a course without a lecture.

**Known to break in phase C, and worth designing around now.** The tag question
is stateless on purpose: if the newest record has no subject, the question is
open. In a chat the newest record is everyone's, and the person who answers may
not be the one who sent it. The answer will have to be bound to its record —
a reply, or a button under the message — and that is a change to `corpus.py`,
not a setting.

Task 39 answered it for groups by not asking there. The author chose on
2026-09-25 that a group chat's page comes with its subject in the caption —
"#матан" under the photo — which is also what tells the bot a photo is a page
of notes rather than a meme. A record in a group is therefore tagged from
birth, and a "#word" in a group only searches. The stateless question stays
the private chat's.

---

## Where the quality work stands

The recognition experiments are **paused, not finished** — the arms were
stopped mid-question by decision. The conclusions are in CLAUDE.md →
"Established experimentally" and the run-by-run record each of them came from
is in FINDINGS.md; this section is the shortest path back in. Read it before
running anything.

**What production runs**, read off the startup log and the Railway variables on
2026-09-23:

```
Recognition: gemini-3.8-flash, 3 runs
Prompt:  prompts-v5.md, 235 words
Compose: on, gemini-3.8-flash, prompts-compose-v2.md, 226 words
Call:    media_resolution=unset, thinking_level=unset
Timeouts: call 90s, compose 240s, consensus 354s, album 1064s
VISION_RUNS=3, IMAGE_MAX_SIDE=1500, IMAGE_QUALITY=85
DAILY_PAGES_PER_USER=1000, DAILY_COST_LIMIT_USD=5, ALLOW_UNPRICED_MODEL=false
```

Read again at 19:25 UTC, after the evening's deploys. Three lines moved:
`Recognition:` exists now (gap 1), the compose call has a ceiling of its own
(task 27), and `ALLOW_UNPRICED_MODEL` is off (gap 4).

**Moved on 2026-09-24, and it matters for the next arm.** Recognition reads
with `prompts-v6.md` — v5 plus one rule, the author's frames written as
`\boxed{...}` — composition with `prompts-compose-v3.md`, and stage three is
on (`EXPLAIN_ENABLED=true`, `gemini-3.8-flash`). The open v4-against-v5
question is now v4 against v6: the added rule is about frames, not about
reading, but a record made after this date was not made with v5.

### The open question: v4 against v5

Every v5 album so far scored above every v4 album on the mean of
`numeric_agreement` — 0.941 against 0.860, a gap three times the 0.027 the
instrument wobbles by between two runs of one configuration. That is the shape
of a real effect and it is four observations against two, on one album of one
subject. CLAUDE.md calls it a suspicion on purpose. **Two more v4 albums settle
it.**

The arm is cleaner than the ones already run, and that is worth knowing before
designing a wider one. `numeric_agreement` is computed inside
`transcribe_consensus`, from the three recognition runs, **before `compose` ever
sees the text** — so the composing stage cannot move this number and does not
have to be switched off to keep the arm one-variable. The whole arm is:

```
PROMPT_FILE=prompts-v4.md      # everything else left exactly as it is
```

two albums, then compare the means. Switch it back afterwards.

### How to read the result

- **The mean, never the minimum.** The per-page minimum of `numeric_agreement`
  wobbles by ~0.02 between two runs of the same prompt; the mean reproduces to
  a thousandth for `text_agreement` and to ~0.03 for `numeric_agreement`.
- **0.027 is the floor.** An arm that moves the numeric mean by less than that
  on one album has said nothing.
- **`numeric_agreement`, not `text_agreement`,** whenever a prompt changes how
  a page is laid out. `compare_text` measures shape; v5 changes shape by
  design, and that confound made the first v5 measurement unreadable.
- **Never against a threshold.** A page of matrices scores low because a
  repetitive sequence has many equally good alignments, not because it was read
  badly. Compare arms with each other.

### What must not move while an arm is running

- `VISION_MEDIA_RESOLUTION` — measured inert on this model at this image size
  (`tokens_in` identical at 1809). Carrying it in an arm makes that arm compare
  a setting against itself.
- `VISION_THINKING_LEVEL` — stays `unset` until `ai_calls.tokens_thought` has a
  few albums in it. Turning it down is a change to how the model reads, made to
  solve a budget problem.
- `seed` and `temperature` — deliberately not settings. Three runs made
  identical would send `text_agreement` up without touching accuracy: the
  instrument inverted rather than merely broken.
- `IMAGE_MAX_SIDE` — it silently recalibrates all four `photoguard`
  thresholds, which are applied to the compressed image.

### The queries

Agreements of the albums of the last day, newest first:

```sql
SELECT id, created_at, status,
       round(text_agreement::numeric, 3)    AS txt,
       round(numeric_agreement::numeric, 3) AS num,
       pages
FROM notes
WHERE created_at > now() - interval '1 day'
ORDER BY id DESC;
```

What a day of calls cost and how much of it was thinking:

```sql
SELECT model, kind, count(*),
       round(avg(tokens_in))      AS avg_in,
       round(avg(tokens_out))     AS avg_answer,
       round(avg(tokens_thought)) AS avg_thinking,
       round(sum(cost_usd)::numeric, 4) AS spend
FROM ai_calls
WHERE created_at > now() - interval '1 day'
GROUP BY 1, 2;
```

### Gaps in the instrument, found on 2026-09-23

Three of the four are closed; the one that matters most for the next arm is
not — a record still does not carry the prompt that made it.

1. ~~**`VISION_MODEL` is never printed at startup.**~~ Fixed. The line reads
   `Recognition: <model>, N runs`, and the run count is on it because a page
   scored on two runs agrees more easily than one scored on three.
2. ~~**The unpriced warning covers `VISION_MODEL` only.**~~ Fixed, and not by
   editing the second loop: `PRICED_MODEL_SETTINGS` is one list,
   `Settings.unpriced_models()` reads it, and both the validator that refuses to
   start and the warning that replaces it under `ALLOW_UNPRICED_MODEL` go
   through that one method. A test asserts the two cover the same settings, so
   a third priced setting added to one and not the other fails.
3. **A record does not carry the prompt that produced it.** Still open, and it
   is the one to decide before the next arm rather than after.
   `numeric_agreement` was made a column precisely so that comparing two prompts
   would be a query rather than a grep through logs that roll off — and the half
   that says *which prompt* is still only in the logs. Until `notes` carries it,
   an arm is attributed by the wall clock.

   What it costs to leave open: the v4/v5 question is four albums against two,
   so the arm that settles it has to pool albums run on different days, and
   every one of them is attributed by remembering what the variable was set to
   at the time. That is the failure mode this whole section exists to prevent.
4. ~~**`ALLOW_UNPRICED_MODEL=true` is still set**~~ Fixed on 2026-09-23: it is
   `false` in the Railway variables now, both models are priced, and the daily
   cost cap is a cap again. The rule it was breaking is the one to keep:
   turning it on is a decision, and leaving it on after a model is priced
   disarms the next swap silently.

### Fixed since: the ceiling the composer waited on

`compose` waited on `VISION_CALL_TIMEOUT_S`, the ceiling of one recognition
call over **one page**, while being itself one call over **the whole record**.
On 2026-09-23 a four-page album reached exactly 90 s (`ai_calls` id 361,
`latency_ms` 90000, `TimeoutError`) and note 37 went into the corpus with the
flat text `prompts-v5.md` produces: three headings over 2866 characters,
against nine over 1603 in note 36, which composed. Topics come from headings,
so the record is also the harder one to find again.

`COMPOSE_CALL_TIMEOUT_S` is its own setting now, 240 s by default against a
measured 43 s for three pages, and the stage makes a second call on a 429, a
503 or a dropped connection — but never on a timeout, where a second wait of
the same minutes buys the same answer and doubles the window a deploy can
cancel the record in. Both attempts are written to `ai_calls`.

### Fixed since: the sections the composer invented

`prompts-compose-v2.md` on `gemini-3.8-flash` **over-structures**: it split
`Спектры атомов (полосочки) для каждого атома уникальны` — one sentence — into
a `##` heading and a body line, and promoted a line of body text
(`$10^{-7}$ м и меньше — НАЧИНАЕТСЯ КВАНТОВАЯ МЕХАНИКА`) to a section of its
own. Topics come from headings, so an invented section is an invented topic —
a handle the corpus is searched by, produced by the one stage in the pipeline
that interprets.

`compose._demote_invented_headings` takes the marker off three shapes and
leaves every word in place: no letters in the heading, a heading that does not
open with a word or a number, and prose below it that begins in lower case.
Measured over every record in production on 2026-09-23 it takes **11 headings
of 111**, and the eleven are the cases named by hand in CLAUDE.md and here,
plus `## 4.` from note 27, which normalised to the topic "4".

It repairs rather than refuses because a refusal costs the whole composition —
note 36 had two invented headings among nine good ones — and because what it
removes is markup the stage added, never a word. `compose_demoted` in the
`note_processed` payload is how often it fires.

What is still not watched: a heading invented in a *shape* none of the three
rules describe — a plausible two-word section the page never had. Nothing in
code can see that one, and it stays a thing to check by eye.

And it is expensive: 15079 thinking tokens for 593 of output, 41 seconds and
$0.0298 on one album — two thirds of what all nine recognition calls of the
same album cost together. `compose._one_call` builds its own config and sends no
`thinking_config`, so `VISION_THINKING_LEVEL` does not reach it. If a thinking
cap is ever worth having, this is the call that wants one first: transformation
over trusted text is the job in this system with the least to think about.

**It has already reached the corpus, and that is no longer a prediction.** Note
36 in production carries eight topics, and two of them are the failure:
`спектры_атомов_полосочки` is the sentence CLAUDE.md names, and
`и_меньше_начинается_квантовая_механика` was the line
`$10^{-4}$ м / $10^{-8}$ м и меньше — НАЧИНАЕТСЯ КВАНТОВАЯ МЕХАНИКА`, body
text in every earlier record of the same album, promoted to a section here. The
record is searched by that word now.

### What production says, read on 2026-09-23

Three facts worth having before the next arm, all from the deployed database
rather than from reasoning.

**The `photoguard` sentinel fix is confirmed on real traffic.** Six albums were
lost between 17:49 and 19:01 UTC on 22-09, four of them to
`"Текст мелкий — снимите одну страницу крупным планом"` on pages whose numbers
say the opposite: `sharpness 1736` against a threshold of 90, `paper_fraction
0.967` against 0.18, `contrast 54.7` against 28 — and `line_height_px 0.0`, the
sentinel. The fix deployed at 19:23 UTC and there has not been one since; the
six albums after it went through. Those four metric sets are also the only real
calibration data this project has for the rewrite PLAN.md → Known risks
describes, and they live in `events` where they do not roll off.

**An album of five pages was lost to a measure of layout, and that is what
task 29 fixed.** 17:37 UTC, `album_incomplete`: `pages_ok 3`, `cost_usd
0.085437`, nothing saved. Pages 2 and 3 were refused for "прогоны распознавания
разошлись" at `text_agreement` 0.428 and 0.419 — while `sharpness` read 4033
and 3257 against a threshold of 90, `paper_fraction` 0.958 and 0.971, and
`numeric_agreement` 0.881 and 0.959 with **zero** reported divergences. The
runs read the same page and laid it out differently, which is exactly what
`prompts-v5.md` leaves them free to do.

What cannot be checked afterwards, and is the instrument gap to fix next: the
runs' own texts are not stored anywhere, and a rejected album stores nothing at
all, so "what did the three runs actually disagree about" is answerable only
while the lines are still in Railway's log.

**Two things seen in the records of 19:06 and 19:09 and not fixed.** Both were
found by reading the documents rather than the logs, and neither has a test
that would have caught it.

*Topics go generic on a page with many subsections.* Record 39 came back with
`основные_понятия` and `практика` among its five. The ranking prefers deeper
heading levels, which is what makes the five "main" — but on a page where
`### Пример` and `### Определение` repeat, the deep levels are exactly the
words every record carries, and a handle that matches everything finds
nothing. The fix is not obvious: ranking by position brings back the problem
that ordering was invented to solve. Worth measuring first — how often a topic
in the corpus is a word shared by more than half the records.

*`graphcheck` is structurally blind on the page it was built for.* Record 39's
adjacency matrix sits in the case the check refuses to judge — 5 vertices, 5
edges and a 5×5 table read as either matrix with equal force — and its cells
are half dashes, which `_value` reads as "could not make this out". Row 3 is
all dashes while row 1 says $a_{13} = 1$; nothing reported the asymmetry. The
silence is deliberate and still right, but a square table could be settled by
trying both readings and speaking only when **neither** agrees with the graph.
That keeps the "never confidently wrong" property and is a real check on the
page type this album is made of.

**One compose call in three timed out, and that is what task 27 fixed.** The
three calls on `gemini-3.8-flash` read 41.3 s, 43.7 s and one at exactly
90000 ms with `TimeoutError` — the four-page album. The two that returned were
three-page albums, so the successful case was already at half the ceiling it
was given.

**The five-topic cap has never run on the deployed bot.** Note 36 was created at
06:09 and the cap deployed at 06:18, so its eight topics are the old behaviour.
One photographed page next session confirms it.

**`ai_calls` cannot be summed across 22-23 September.** 115 of 133 recognition
rows from that day carry `cost_usd = NULL`, written while the model was
unpriced, and `SUM` skips them — any day total spanning the change reads far
too low. The per-call figures from the 18 priced rows are the usable ones:
recognition **$0.00504**, composition on `gemini-3.8-flash` **$0.03145**. One
formatting call costs what six recognitions cost.

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
 10. markdown shorter than MIN_MARKDOWN_LEN            ← texts.NO_TEXT_FOUND, exit
10a. verdict == "rejected", or one run only           ← kept, marked unverified
12. check calculations (vision.findings: mathcheck and graphcheck, each finding with the text it is about)
12a. limits again (pages=0), then stage two (compose.compose)  ← refused: the text from step 7
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

**Step 12a cannot fail the record.** It is a second model call, over the text
step 7 produced and never over the photograph, and its output is checked
against its input by code. Off, refused, or failed, the record is the one
step 12 already had — so the worst case of the stage is the pipeline without
it. It gets its own `check_limits` because rule 6 admits no exception for a
second call, and `pages=0` because the page budget belongs to the recognition.

It runs **after** step 12, not before: `mathcheck` and `graphcheck` judge what
was *read*, and step 12a is presentation.

**Step 15 goes strictly between `consume` and the reply to the user.** The
event means "processing finished successfully end to end," so it can't be
written before the record and the quota have been saved.

What's sent at step 16: the record as a PDF, and nothing after it about the
record — what the checks found stands in the document under the text it is
about, and how the page was read is not the reader's (task 46, the author's
decision on 2026-09-25; until then a second message listed the needs-review
flag, the arithmetic report, the numbers the runs read differently and the
uncertain spots). An album that went out without some of its pages says which,
in `texts.album_partial`. The question which subject the record belongs to
follows in a private chat.

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
| `ALBUM_INCOMPLETE` | an album where not one page was read |
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
| `< 0.70` | `rejected` | save, marked "прочитано без сверки" (task 32) |

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
10. markdown shorter than MIN_MARKDOWN_LEN  -> texts.NO_TEXT_FOUND, exit
    (task 32: "rejected" no longer exits — the page is kept and marked)
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
    # Added after this task, in the order the migrations did it:
    #   numeric_agreement (005), tag (007) and the note_topics table,
    #   missing_pages (008), unverified_pages (009).
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

> Changed by tasks 31 and 32, and this paragraph is kept as what was planned.
> A page that was read is no longer lost to its neighbours: the record is
> delivered with a marker where each unread page would have been and their
> numbers in `notes.missing_pages`. Only an album where **nothing** was read
> asks to be taken again, and the text it asks with is `texts.ALBUM_INCOMPLETE`
> — `REJECTED_QUALITY` went out with the rule that used it. Fewer pages are
> skipped, too: disagreement between the runs marks a page instead of dropping
> it (`notes.unverified_pages`).

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
| one model call | `VISION_CALL_TIMEOUT_S`, 30 s | typical response ~6 s on `gemini-3.5-flash-lite` |
| one run's worst case | 93 s | 3 attempts × 30 s + 1 and 2 s pauses |
| `transcribe_consensus` | 120 s | the worst case above, plus margin |
| a whole album | 362 s | three waves of that worst case, plus margin |

Only the first of these is a number anybody writes down. **The other three are
computed from it**, because raising the call timeout alone — which is what a
slower model needs — would leave the two ceilings cutting the retries short
while looking untouched. The arithmetic is in the code, not in these comments:
`vision.RUN_WORST_CASE_S`, `vision._CONSENSUS_TIMEOUT_S`, and
`albums._ALBUM_TIMEOUT_S` over `albums._waves(...)`.

The consensus timeout must be greater than the worst case of a single run
with retries, otherwise it would cut processing short before the retries
themselves finish.

The album timeout must cover the worst-case page schedule under
`Semaphore(10)`: for 10 pages at 3 runs each, that's three waves. **The margin
over that is a normative value, not an approximation**, and it must not be
lowered — the ceiling may only ever move up, which is what it did when the
hand-written 300 became a derived 362.

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

> **Tasks 11-13 were built, shipped, and deleted on 2026-09-23.** `/notes`,
> `/note`, `/search`, `/retitle`, `/delete` and `/pdf` all worked and were
> covered by tests; the `events` table then showed that not one of them had
> ever been used, against 34 records captured. They were replaced by a single
> gesture — the bot asks which subject a record belongs to, and a "#word"
> either answers that or searches. The specifications below are kept as the
> record of what was built and why, not as a description of the bot. Task 14
> (`/stats`) survives unchanged; it had been used once.
>
> The lesson is cheap to state and was expensive to learn: **before adding an
> interface to the corpus, look at whether the last one was ever touched.**

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

Rewritten on 2026-09-23 against what the bot actually does. The list it
replaced described six commands, five of which the event table showed had
never been used.

- [ ] A delivered record is followed by the question of which subject it is
- [ ] The question shows the topics read off the record and the subjects
      already in use
- [ ] A "#word" answers that question; the same word later searches instead
- [ ] An untagged record from last week is not filed by a search typed today
- [ ] A search matches the subject and the topics alike
- [ ] One match comes back as the document, several as a list that names what
      to type next
- [ ] Every corpus query is scoped to its owner: the group in a group chat,
      the user in a private one
- [ ] A record nobody tagged is still findable by its topics
- [ ] `/stats` counts records, pages and the streak
- [ ] The bot answers on an empty corpus without an error

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

- a call's own cost is `(tokens_in × price_in + (tokens_out + tokens_thought)
  × price_out)`. **Thinking is billed at the output rate**, because that is how
  it is priced; left out, a call that thinks fifteen times as long as it speaks
  is recorded at a fifteenth of its price. An absent `tokens_thought` counts as
  zero rather than voiding the price: the field is missing exactly when the
  model did not think
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
`bytes_before`, `bytes_after`, `width`, `height`, `tag`.

`tag` is the "#word" in that page's caption, `None` on most pages: Telegram
puts an album's caption on one page only. `albums.tag_of` takes the first one
in page order, and in a group chat an album without one is not processed.

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

## Event `album_incomplete`

Written when an album had at least one page the pipeline could not read, and
therefore saved nothing. Transactional, like every event but `note_failed`.

    {"pages": 4, "pages_ok": 3, "reasons": ["не удалось распознать"],
     "latency_ms": 11686, "cost_usd": 0.0031}

`pages` is what arrived, `pages_ok` what was recognised; the difference is
what has to be photographed again. There is no `note_id` — no record was
saved, which is the point of the event.

---

## Event `note_failed`

Written **only on an unhandled exception**, from the global handler, via
`log_event_standalone`.

Normal rejections — a limit, `AI_DISABLED`, a bad frame, `rejected`,
`NO_TEXT_FOUND`, an album page skip — **are not `note_failed`**. They're
already reflected in their own events and in the reply to the user.

payload: `{"reason": <exception type>, "where": <handler name>}`.

## Events `note_tagged` and `topic_searched`

The two halves of the one gesture the bot has, and the pair that says whether
it is being used at all — which is the question the five deleted commands
could not answer until someone thought to ask the event table.

`note_tagged`: `{"note_id": int, "tag": str}` — the subject the user answered
with, stored without its "#".

`topic_searched`: `{"tag": str, "found": int}`. The tag is stored for the same
reason the search query used to be: what a person looks for is the most direct
signal of what the corpus is for. `found: 0` is the interesting row — a search
that missed is either a topic the bot never wrote or a subject spelled a
second way.

## Event `album_retake_requested`

Written when the frame check refused a page of an album before any page was
read. Nothing was read, nothing charged, no record saved; the reply names the
pages and asks for the album again.

    {"pages": 5, "refused": [{"page": 1, "reason": "Текст мелкий — …",
      "line_height_px": 19.75, "sharpness": 1681.9,
      "paper_fraction": 0.705, "contrast": 41.9}]}

`refused` has the shape of `album_incomplete`'s `skipped`: the four numbers
are the evidence each refusal was made on.

## The group an event happened in

`events.group_id` is the group chat, `NULL` in a private chat — set on every
event a group's update writes, so a group's week can be counted from the
table alone. Three events are the bot's own membership:

| Event | payload |
|---|---|
| `group_joined` | `{"sees_photos": bool}` — false when privacy mode is on and the bot was added as an ordinary member, which is when the welcome asks to be made an admin |
| `group_promoted` | `{}` |
| `group_left` | `{}` |

## Testing boundaries

The tests from tasks 5 and 8 are required, and so are the three integration
tests below. Together they are the floor: a bug in any of them costs real
money, so none may be dropped.

1. **Retry.** `429`, then success → two `CallStats` elements and two rows
   in `ai_calls`.
2. **Batch ownership.** Two concurrent handlers with the same
   `media_group_id` process it exactly once.
3. **Independence of spend.** Rolling back the main transaction doesn't
   remove already-committed `ai_calls`.

One gap is deliberate and has now been paid for three times, so it is
written down rather than rediscovered: **both photo paths copy fields into
`Note` and run the checks by hand**, and nothing proves they do. Dropping
`margin_notes=` or `graphcheck.check(...)` from `handle_photo` leaves the
whole suite green. `albums.process_page` is covered because it takes bytes
and returns a `PageResult`; `handle_photo` is not, because covering it means
a Telegram message, a session, a download and four stubbed services. The
cost is a class of one-line omissions that shows up on the first record
instead of in CI.

The "nothing else" that stood here was a first-week scope limit, and it was
lifted by decision: the suite now covers album assembly, the middleware, the
webhook, the corpus commands and the PDF as well. What is covered, and what
is left out on purpose, lives in `CLAUDE.md` → Tests — in one place, so the
two files cannot drift apart.

---

# Known risks

Found, discussed, left as is. **Don't fix on your own initiative** — if
one of these actually bites, it becomes its own task.

**`photoguard` cannot measure a line height on a sparse page, and the reason
is upstream of where it shows.** `_line_height` thresholds ink at
`np.percentile(region, 35)`, which assumes ink covers at least 35% of the
paper. Measured on synthetic pages, real ink covers 4-14%: the percentile then
lands *in the paper*, the mask takes 97-99% of the sheet, and the profile it
builds is paper texture rather than lines. Fewer than three transitions
follow, and the function returns its sentinel.

Both halves are fixed now. The sentinel stopped being read as a verdict first;
the measurement was rewritten in task 35 along exactly the three lines this
paragraph laid out — the median gap between bands of ink, Otsu instead of a
rank, and no three-line minimum. It is checked against pages whose pitch is
known by construction and lands within 5% from 28 px to 220 px, with a drawing
on the page, on pale ink and on a dark photograph.

`MIN_LINE_HEIGHT_PX` did **not** move, and that part of the paragraph still
stands: 20 px is defensible reasoning rather than evidence, and settling it
needs a folder of real pages through `photoguard`'s own CLI. The bench that
replaced the measurement cannot replace that — a synthetic page says what the
estimator measures, not what a student's handwriting looks like at arm's
length.

**A recognition run is sometimes lost to an answer that will not parse, and it
is not our ceiling.** (Task 30 changed the second half of this: such a call is
asked again now, unless the finish reason is `SAFETY` or `MAX_TOKENS`. The
diagnosis below stands and is what made the difference between the two
legible.) `unparseable model response` cost a whole run, because a
200 that parsed badly was never retried; three runs became two. The suspect was
`max_output_tokens=8192`. **It is our ceiling, and the column we checked it
against cannot see why.**

The first reading of the evidence said otherwise and was wrong. Across 298
calls in three days, 12 came back unparseable with `tokens_out` between 312 and
714, averaging 518 against 520 for the calls that succeeded — no row anywhere
near 8192, which reads as "nothing was truncated". Then the instrumentation
caught its first live sample and the model named the reason itself:

```
unparseable model response (finish_reason=MAX_TOKENS)
tokens_out 498, latency 37440 ms
```

498 visible tokens, 37 seconds, and the answer stopped because it ran out of
budget. The missing ~7700 tokens went to **thinking**, which draws on the same
`max_output_tokens` and is reported as `thoughts_token_count` — a field
separate from `candidates_token_count`, which is what `ai_calls.tokens_out`
stores. So every truncated call looks innocent in our own table, and the
historical query was blind to the half of the budget that actually overflowed.

`VISION_THINKING_LEVEL` is `unset`, so this is `gemini-3.8-flash`'s own default
thinking, and it is evidently large.

**Both halves are fixed; the third is deliberately not.**
`ai_calls.tokens_thought` records the thinking on every call, and
`MAX_OUTPUT_TOKENS` went 8192 → 32768 for recognition and composition alike — a
cap costs nothing until it is reached, and the one that was reached cost a
whole run. What is *not* done is capping the thinking itself.
`VISION_THINKING_LEVEL` stays `unset` until the new column says how much of it
there is: turning it down is a change to how the model reads, made to solve a
budget problem, and every quality finding in this project was made with that
field absent.

The query that settles it, once a few albums have run:

```sql
SELECT model,
       count(*), round(avg(tokens_out)) AS avg_answer,
       round(avg(tokens_thought)) AS avg_thinking, max(tokens_thought)
FROM ai_calls
WHERE kind = 'transcribe' AND created_at > now() - interval '1 day'
GROUP BY 1;
```

And the one for the failures themselves:

```sql
SELECT coalesce(error, 'ok') AS what, count(*),
       min(tokens_out), max(tokens_out), round(avg(tokens_out))
FROM ai_calls
WHERE created_at > now() - interval '3 days'
GROUP BY 1 ORDER BY 2 DESC;
```

**A redelivered update is processed twice.** Nothing deduplicates on
`update_id`. If Telegram decides an update went undelivered, the retry
arrives as a new update and produces a second record for the same photo:
extra Gemini calls and a second quota debit. The tell is two identical
`notes` rows a minute apart and doubled `ai_calls`.

Until task 18 this was not a risk but a certainty — the endpoint replied 200
only after `feed_update` finished, which at the default call timeout is up to
120 seconds for a photo and 362 for an album, while Telegram gives up after
roughly a minute. It answers
immediately now, so a retry takes an actual delivery failure. The consequence
survived the fix; only its likelihood changed.

⚠️ **For an album the duplicate is a whole record.** The atomic `pop`
protects against two handlers within a single delivery, but redelivered pages
arrive as new messages and assemble into a fresh batch under a
`media_group_id` the first handler has already taken. Same tell: duplicated
records and spend.

Answering the webhook first put a different exposure in place of the old one.
An update is now processed in a background task, so **a deploy cancels
whatever is in flight** and the Gemini calls already paid for are thrown
away. That one is listed with the rest of what a single replica costs in
`CLAUDE.md` → Scale debt.

**A race between checking and debiting the quota.** `check_limits` reads
`pages_used_today`, `consume` increments it, and there are seconds of
model work in between. Two parallel processing runs for the same user
could both pass the check and both debit the quota, and the page count comes
out short. Row locking is deliberately not introduced yet; the point at which
that stops being affordable is in `CLAUDE.md` → Scale debt.

**The cost limit is soft.** `DAILY_COST_LIMIT_USD` is only checked before
processing starts, no budget is reserved. The cap can be exceeded by the
cost of one album — at current prices, that's cents.

**The album buffer lives in the process's memory.** Railway restarts the
container and an unfinished batch is silently lost. The heavier half is that
**a second replica splits albums** — which is why one replica is a
requirement and not a default, and why the buffer goes to Postgres rather
than Redis when it has to leave the process. Both in `CLAUDE.md` → Scale
debt.

**Escalating a disagreed page to a stronger model is still not built, and the
groundwork for it now is.** This entry used to read "`CallStats` does not carry
its model"; it does, along with its `kind`, and `log_ai_calls` writes what the
stats say rather than what the settings say — so a second stage on another
model is already recorded and priced as itself, which is what `compose` needed
and got. What remains is the escalation itself: a page whose three runs disagree
is the obvious candidate for a re-read on a stronger model, and nothing does it.
Deferred rather than forgotten — the reason it is not automatic is that
`meaningful_divergences` has never been calibrated against how often a second
opinion would actually change the text.

**A graph read off a drawing is unchecked.** Rule 6 of the prompt asks for
`[граф: 1-2, 2->3]` and `pdf.py` draws it. Reading the structure of a
hand-drawn graph is interpretation, and interpretation is where the model
invents — but unlike invented prose, an invented edge carries no tell. It is
drawn as confidently as a real one. `parse_graph` refuses text that doesn't
read as vertices, which catches prose, not a plausible wrong edge. The fix
is the one that already works for numbers: compare the three runs' edge
lists and mark the record `needs_review` when they disagree. Deferred on
purpose — its own task.

**Closed by task 46: a remark whose anchor was a single character landed on
the first line that contained it** — "f" found `\frac` above the word it was
about (record 36), "2" stands in half the lines of a page on graphs (record
39). Those were reading remarks, anchored on the text the model read, and the
document no longer prints them. A finding of a check is anchored on the whole
formula or line it was found on, or on a graph's whole spec, and is found
under the three-character floor an explanation's anchor already had.

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
- [ ] The album timeout covers every wave of runs, and was derived rather
      than written down
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
- Export to Anki, and any bulk export of the corpus (`/pdf` renders one
  record for reading — not a download-everything button)
- Styling and design of responses
- Caching, queues, workers, Redis — until the album buffer has to leave
  process memory (`CLAUDE.md` → Scale debt), and then Postgres first
- Merging the three runs block by block instead of picking the medoid.
  Two readings of every page are thrown away today, and on a matrix the
  majority per cell is exactly what you would want — but aligning blocks
  across runs is a second algorithm, `consensus` is a module we only call,
  and `graphcheck` already settles the matrix case better than a vote,
  because the graph beside it decides rather than the count
- Leaving the tail of the previous lecture out of a record. The first page
  of an album often opens with the end of the lecture before — record 46
  began with an associativity check from the week before "Практика" — and
  every reading carries it in: nothing tells where a lecture begins
- Detecting a page photographed rotated. Nothing corrects one today:
  `images.compress` honours EXIF and a physically turned page carries none.
  Suspected of costing time on the model, never reproduced
- Deduplication on `update_id`
- Row locking, two-phase spend accounting
- Docker, CI
- End-to-end tests of the photo and document handlers — the unit
  suite was extended by decision, these were left out on purpose
  (see `CLAUDE.md` → Tests)
- What stands under a record's title is whatever the model put in
  `margin_notes`, and on real pages that is mostly not a margin note: the
  notebook's own print ("DATE", "BRAUBERG®" — records 38, 40, 41), a
  description of a doodle ("рисунок: солнце и смайлик в правом верхнем углу"),
  single stray letters ("м", "u", "f") and once a whole `[схема: …]`. Rule 8
  of `prompts-v5.md` asks for the lecturer, the date and the page number only.
  A recognition question — the prompt, or a rule about what a margin line may
  be — not the document's design, which prints the line it is given
