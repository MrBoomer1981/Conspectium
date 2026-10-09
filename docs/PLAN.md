# PLAN.md

The work plan. Since 2026-09-30 the work is divided by area: the CEO owns the
interface and the product for students, the CPO the database and the model,
and both push to `main` — `README.md` maps every area to its code. "The
author" in this file is the owner of the area a decision falls in, and both
for what is shared; a decision dated before that day was made when the CEO
was the only author. Since 2026-10-01 the CEO's word is enough in every
area, the CPO's and what is shared included — agreed with the CPO
beforehand; `CLAUDE.md` → "Who decides". Lives in `docs/` with
`FINDINGS.md` and `BRAND.md`; `CLAUDE.md` and `README.md` stay in the repo
root.

**How to work with this file:**

1. A task is named by its owner, or by the owner's line in "State". You do
   **only that one**.
2. Before writing code, describe the plan of changes. When it leaves no open
   question, carry it out in the same turn; ask only when it holds a decision
   that is the author's — `CLAUDE.md` → "How to work in this project".
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
8. A change to this file beyond your task's checkbox and your line in
   "State" goes in a commit of its own (`plan: …`, saying why) with a line
   in "Plan changes", below "State". One the CPO makes in the CEO's area,
   or in what is shared — the order of work, a rule in `CLAUDE.md` — waits
   there for the CEO's word; the CEO's need no one's since 2026-10-01. The
   same holds for a rule in `CLAUDE.md`.

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
- [x] 40. A page somebody else sent becomes the chat's record by a reply with
      its subject. What 40 would mean was the author's to say, and on
      2026-09-29, taking the group up again, the author said this: "#матан" in
      reply to a photo, an image file or any page of an album — the bot's
      name may stand beside it — reads it, files it under the reply's word
      and charges whoever replied. An album is found whole from the
      references kept seven days in `group_pages`, never the photos, so an
      album nobody tagged is no longer downloaded at all; a second call on the
      same pages sends the record already made (`notes.source_key`); naming
      the bot without a subject earns a hint. An image sent as a file is a
      page everywhere
- [ ] 41. Limits and spend counted per group; the scale-debt rows that come due
      with a second person in the chat — the CPO's, in phase D's order, until
      the CEO took it on 2026-10-07: a group's day in pages, 20, and one
      reading of the same pages at a time

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
      and read as well — rolled back to v6. On 2026-09-29 the author ruled
      that the document's quality is not traded for its price, which closes
      fewer runs; `gemini-3.5-flash-lite` for recognition was measured the
      same day (record 52 against 50 and 51) and read worse — closed. Paused
      there by the author: Flex, another provider measured on an album
      already read, and the explanations' writing call at `low` are left

**Phase D — the subject: a course a group builds up and gets back whole.**
Set by the CEO on 2026-09-30, in two tracks, one an owner: **the CEO's 51,
54, 55, 56, 47, 52 and the CPO's 41, 48**, each in that order — 51 moved
first on 2026-10-01, when the CEO's guide to the look came in, and 54 to 56
came in after it the same day, from record 59. 52's overview is a model call
and waits for 41, which gives the chat a day of its own — in pages since
2026-10-07, when the CEO took 41, so what an overview counts for in it is
52's to say. Each task's specification is under "# Task N", after the task
descriptions of week 2; 41 is the one listed under phase C.

- [x] 51. The document's own look: the CEO's guide, `BRAND.md`, the body
      included — the CEO's
- [ ] 54. Drawings cut out of the page: recognition names each drawing's
      frame, the code cuts it out of the photograph, keeps its ink and sets
      it in the document — the CEO's. Built, measured on record 59's album
      the same evening (record 60), read as worse and put to sleep:
      production back on `prompts-v6.md`, the code waiting without frames
- [x] 55. What record 59 showed besides its drawings: a record with no
      headings, the margin line «фор · 21:27 (0, 1)», a forum among an
      explanation's sources — the CEO's
- [ ] 64. One lecture, one record: recognition names where a lecture begins
      on a page, and the code cuts the lecture before and the one after off
      the album's edges, where every run agrees — the CEO's. Taken before
      56 on 2026-10-03, built and measured the same day (record 66): the
      model named no start, for nothing on these pages tells a lecture from
      a section, and put to sleep — the code waiting under prompts-v6.md.
      The page photographed twice, at the end of one album and the start of
      the next, goes to 63
- [x] 56. The bot as a teacher: «Идея», «Зачем условие», «Пример», each a
      box of its own, the bot's reasoning printed without a source under its
      own label and checked by code — the CEO's
- [x] 47. The bot added to a group chat in one tap, and seeing its pages
      there without being made an admin — the CEO's
- [ ] 52. A subject's records as one document to study from — the course,
      opened by an overview the model writes over it, sent only when
      somebody asks for it with a command — the CEO's
- [ ] 48. A subject's materials: a PDF sent with its "#word" is kept as
      Telegram's reference and its text, its topics are read out of what is
      in it, and a "#word" finds it the way it finds a record — the CPO's

Put off on 2026-09-30 — the CPO's area, not to be started without the CPO's
word:

- 49. The teacher's drive by link — Yandex Disk and Google Drive files and
      folders read into a subject's materials
- 50. The subject's context in the explaining stage — explanations that know
      the course's earlier records and cite its materials. Discussed, not
      scheduled

Specified on 2026-10-01 and not scheduled — the CEO's, taken up when the CEO
comes back to it:

- [ ] 53. SUM's site: one page, outside this repository, that shows the
      document and puts the bot into a group's chat with one button; the bot
      counts the starts it brings

**Phase E — a record from any material, and the subject whole.** Set by
the CEO on 2026-10-02, after 56 and 47, the CEO's: a lecture's board, its
recording and its film become records as its notebook does, and a subject
becomes its lectures in the order they were given, the earlier ones
included. "Where this is going, decided 2026-10-02" says why.

- [ ] 65. A page read whole: two runs that stopped short of the page's end
      no longer outvote one that read it — the CEO's. Taken on 2026-10-04
      from record 67, between 63's parts
- [x] 69. What record 74 showed: formulas spaced apart and set in a serif,
      trees drawn as tangles, «[зачёркнуто]» printed, a page of one word,
      and the author's shorthand spelled out by the composer — the CEO's.
      Taken on 2026-10-06 from record 74, closed on the CEO's word the same
      day
- [x] 70. A record rated: «Хорошо» and «Плохо» under every document, and
      the reader's own words on where the error is — the CEO's. Taken on
      2026-10-06, so the records' quality is read off the groups rather than
      found one record at a time; closed on the CEO's word the next day
- [ ] 71. A lecture dated by a day it could not have been given on: a
      margin's day after the pages came no longer makes it last year's —
      the CEO's. Taken on 2026-10-06 from record 79, headed 10.11.2025
- [x] 72. A group's week: who sent its records and who rated them, in
      `/stats` and summed up in the chat once a week — the CEO's. Taken on
      2026-10-06, so a group sees what it brings and what it says of it;
      closed on the CEO's word the next day
- [ ] 73. The week's summary on Saturday: at 10:00 Moscow time, in every
      group with a record or an отзыв that week, the week Saturday to
      Friday in `/stats` too — the CEO's. Taken on 2026-10-07
- [ ] 74. The bot's week for whoever reads the отзывы: `/stats` in the
      feedback chat counts every chat — records, people, отзывы, spend,
      every group and the week's people — the CEO's. Taken on 2026-10-07
- [ ] 75. A page refused as dark that was not: `MIN_CONTRAST` 28 → 20 —
      the CEO's. Taken on 2026-10-07 from an album whose page 2, sharp and
      filling its frame, was refused three times at 26.1 to 27.8
- [ ] 76. What the bot spends its time and memory on: a timeout repeated
      once at twice the ceiling, one document drawn at a time, the day's
      pages counted by the database, image work on two threads — the
      CEO's. Taken on 2026-10-07 from a week of production
- [ ] 77. Two formulas the document printed as their source: a term the
      author struck out, `\cancel{…}`, drawn struck, and an arrow with its
      condition under it, `\xrightarrow[k \to \infty]{}` — the CEO's. Taken
      on 2026-10-07 from the production log
- [ ] 78. What record 86 showed: a title's formula printed as its source,
      the author's frame inside a line, «1))» refusing a composition, and
      a teacher's example that was the lecture's working with another
      number — the CEO's. Taken on 2026-10-08 from a reader's «Плохо»
- [ ] 79. Record 86 sent again: a theorem's parts numbered «1 Существование»
      read as numbers the composer lost, and three cases in a column begun
      on a line of text — the CEO's. Taken on 2026-10-08 from record 87
- [ ] 81. A lecture sent at once is one record: the albums of ten that
      Telegram cuts a send of more pages into are read as one album — the
      CEO's. Taken on 2026-10-08 from twelve pages that came back as two
      records
- [ ] 82. Records 88 and 89: compositions refused for an item's number
      after a bullet, a number the author struck out and a formula the
      composer corrected — the CEO's. Taken on 2026-10-08 from the two
      records of task 81's twelve pages
- [ ] 83. What the CEO read in records 88 and 89: the bot's boxes set
      inside a sentence, a word carried over with a hyphen, struck
      words printed, ⩽ beside ≤, a short formula alone on its ground, a
      ringed sign printed as words — the CEO's. Taken on 2026-10-08
- [ ] 84. An equality that does not hold, found by code: both sides
      counted at random numbers, with what the lecture defined — the
      CEO's. Taken on 2026-10-08, after 83
- [ ] 85. Thirty-two pages sent at once: an album of ten waits a minute
      for the rest of its send, the ceiling following the send — the
      CEO's. Taken on 2026-10-09 from a lecture that came back as three
      records
- [ ] 86. What records 90, 91 and 92 showed in the document: a box
      between a sentence and its formula, «Идея» pages before its proof, a
      comma opening a line, a ringed sign and struck lines printed, a
      margin's page numbers under the title — the CEO's. Taken on
      2026-10-09
- [ ] 87. A study version asked again when its answer does not parse,
      its row saying why — the CEO's. Taken on 2026-10-09 from record 91
- [ ] 88. Numbered items in lower case: a run of numbers 1, 2, 3 opening
      lines is a list to the numbers guard, whatever follows each — the
      CEO's. Taken on 2026-10-09 from records 91 and 92, measured on them
      before it ships
- [ ] 63. The subject's base: every lecture at the date it was given, the
      earlier ones added, the teacher's materials with them, and one
      lecture from several notebooks, what one lacks set in from another —
      the CEO's. Taken first on 2026-10-04: it needs no material the CEO
      does not have, and the board's photographs are still to be taken.
      Its first part shipped the same day; the rest waits for a
      classmate's notebook to measure on
- [ ] 60. A board photographed: a frame check and a reading of its own,
      measured on real boards — the CEO's
- [ ] 61. A lecture recorded: the bot's notes from what was said, marked as
      the bot's on their first page — the CEO's
- [ ] 62. A lecture filmed: its sound by 61's path, the board's stills by
      60's — the CEO's

**Phase F — the app: where a group studies from its records.** Set by the
CEO on 2026-10-02, after phase E, the CEO's: a Telegram Mini App now, the
stores later. Its first version is the library and the exam preparation,
and neither calls a model; spaced repetition, sharing and the stores come
once that version is used.

- [ ] 57. The app's frame: a Telegram Mini App served by the bot's own
      service, opened from the bot, signed in by Telegram, showing a person
      what the bot would show them and nothing more — the CEO's
- [ ] 58. The library: a chat's records by subject and topic, searched, and
      a record read on a phone with its formulas and the bot's boxes — the
      CEO's
- [ ] 59. Exam preparation: a subject's definitions and theorems in one
      place, by topic, each opening its record at its place — the CEO's

Specified on 2026-10-04, the day the first big group added the bot — the
CEO's, not yet scheduled:

- [ ] 66. A group's records in a topic of their own: in a group divided into
      topics, every record goes to one, «Конспекты», which the bot makes
      where there is none — the CEO's
- [ ] 67. Records kept for the next cohorts: the bot asks a group its
      university, year and programme, so a subject's lectures can serve the
      students after it — the CEO's, a mechanism to think through first
- [ ] 68. Pages in their order: an album sent out of order is assembled in
      the order its pages say — their numbers, a sentence across a seam —
      and in the order sent when they do not say — the CEO's, measured first

Specified on 2026-10-08, when the CEO asked whether the bot should make
study materials rather than records — the CEO's, approved the same day and
taken next:

- [ ] 80. A lecture's study version: what a chat gets for a record, in
      place of the record's own document — the lecture set out by topic,
      the author's text moved whole, the bot's sections marked, questions
      to check oneself at the end — the CEO's

Specified on 2026-10-09, from records 90, 91 and 92 and a model's list of
their errors — the CEO's, not yet scheduled:

- [ ] 89. The bot's reasoning that leans on what the lecture proves: an
      explanation or a teacher's box may not assume the statement it
      stands under — the CEO's. Not taken, the CEO's word of 2026-10-09:
      «лекцию можно поправлять» — a box of the bot's may correct the
      lecture, and the CEO reads them
- [ ] 90. The reading against the photographs: the places in records 90,
      91 and 92 where a stroke decides between the author's text and a
      misreading — the CEO's own check, no code, said on 2026-10-09
- [ ] 91. What the lecture uses without defining: whether the bot recalls,
      under its own label, a definition the lecture relies on and does
      not give — not needed, the CEO's word of 2026-10-09

Specified on 2026-10-09, from record 97 and what its author found wrong in
it — the CEO's, not yet scheduled:

- [ ] 92. What the reading writes about the photograph is not printed:
      «[Левая страница]», «[Правая страница]» — the CEO's. Taken on
      2026-10-09
- [ ] 93. What does not belong to the subject is left out: the course's
      organisation — contacts, points, dates of tests — out of the study
      version, chosen by its model and guarded by code — the CEO's. Taken
      on 2026-10-09, measured on record 97 before it ships
- [ ] 94. A drawing that is data, drawn by code: a function's graph by its
      formula, a number line with its points and sets, a mapping of two
      sets with its arrows — the CEO's, measured on an album sent again
- [ ] 95. A formula or a drawing with no word about it gets the bot's
      caption — the CEO's, measured first. Taken on 2026-10-09; a call of
      its own beside the explaining stage's first, measured on seven
      lectures before it ships
- [ ] 96. Three equalities that hold, found not to: a definition read off
      a working, and a formula the author struck out — the CEO's,
      measured over the database before it ships. Taken on 2026-10-09
- [ ] 97. What record 97 showed in the document: a frame closed by «\}»,
      a frame with a blank line inside, an item's «|», a record titled
      «Лекция» — the CEO's. Taken on 2026-10-09 with 92 and 96

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
Computer Modern included. On 2026-10-01 the look moved again, to the CEO's
guide, `BRAND.md` (task 51): Onest, Unbounded and JetBrains Mono live in
`app/assets/fonts/` now, and Computer Modern stays for the formulas.

The order of 33-35 is the author's, made on three albums run through the
deployed bot on 2026-09-23: the seam and the raw LaTeX were in the documents
being read that evening, while the frame check refused nothing at all across
twelve pages. Calibrating it is still worth doing — it is now the only guard
left between a photograph taken from across the room and the corpus — but it
was not what made those records read badly.

## State

Update strictly following this template, adding or removing nothing:

```
Done: 1-40, 42-43, 45-47, 51, 55-56, 69-70, 72
CEO — current: 73, 71, 41, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 92, 96, 97, 93, 95, 90's check of the photographs; next: 94, 65 once there is data for it, 63's rest, then 60
CPO — current: none; next: 48
Blockers: 52's overview waits on 41, and so does the day's cost cap, shared since 2026-10-04 with the first big group; 44 paused on 2026-09-29, the CPO's to take up — Flex, or another provider measured on an album already read; 54 asleep since its measurement on 2026-10-01; 64 asleep since its measurement on 2026-10-03
```

## Plan changes

Every change to this file beyond a task's checkbox and its owner's line in
"State", and every change to a rule in `CLAUDE.md`, is a line here, written
in the same commit — so that the plan's history reads without its diff, and
neither owner learns of a change to their area from one. A change the CPO
makes in the CEO's area, or in what is shared, stands as unaccepted until
the CEO's word is in the last column; the CEO's are accepted as written,
since 2026-10-01.

| Date | Who | What changed, and why | Accepted |
|---|---|---|---|
| 2026-09-30 | the CEO, with Claude Code | Phase D set: 47, 41, 52, 51, 48; 49 put off, 50 not scheduled; this log started | the CEO's own |
| 2026-09-30 | the CEO, with Claude Code | Task 52: the course document opens with an overview the model writes over its records | the CEO's own |
| 2026-09-30 | the CEO, with Claude Code | The work divided by area: the CEO — the interface and the product for students; the CPO — the database and the model; both push to `main`. Phase D in two tracks and "State" in two lines. This replaces the staff developer and "Review" set up earlier the same day | the CEO's own |
| 2026-10-01 | the CEO, with Claude Code | Task 51 rebuilt on the CEO's guide, `BRAND.md` — v1.0 of 2026-09-30, rewritten to v1.1 where the records demanded it: the look goes into the body, where the task said "around the text, never in it". `CLAUDE.md` → "The document" rewritten for it | the CEO's own |
| 2026-10-01 | the CEO, with Claude Code | The CEO's track in the order 51, 47, 52: the guide came in. Nothing of the CPO's moves | accepted: the CEO's word, by the rule of 2026-10-01 |
| 2026-10-01 | the CEO, with Claude Code | "Суть": the explaining stage's summary opens the document. The guide asks for one or two sentences and 35 words; `prompts-explain-v1.md` asks for three to five. Shortening it is a prompt change | the CEO's own, by the rule of 2026-10-01; the shortening not yet made |
| 2026-10-01 | the CEO, with Claude Code | "Проверь себя" proposed, from the guide: a question at the end of a page or a section, written by the model. A new output and its guards are the CPO's, its display the CEO's; it stands next to the flashcards `CLAUDE.md` sets aside, so it is for both. Not scheduled | the CEO's own, by the rule of 2026-10-01; task 56's second step |
| 2026-10-01 | the CEO, with Claude Code | A definition's amber line reads the composing stage's rule 6 heading, "### Определение", which makes that heading part of the contract between the prompts and `pdf.py` | accepted: the CEO's word, by the rule of 2026-10-01 |
| 2026-10-01 | the CEO, with Claude Code | Backlog, from the guide: the pages as PNGs for a phone, the QR code carrying `?start=note_<id>`, "Школа × SUM" | the CEO's own |
| 2026-10-01 | the CEO, with Claude Code | The repository in folders: `PLAN.md`, `FINDINGS.md` and `BRAND.md` in `docs/`; the prompts in `prompts/`, where `vision.load_prompt` reads them — the file names, and so the variables on Railway, unchanged; the records, reference notes and logs kept locally in `evidence/`, out of git | the CEO's; the prompts with the CPO aware |
| 2026-10-01 | the CEO, with Claude Code | `CLAUDE.md` rewritten, and merged into `main` on the CEO's word the same day: the same rules with their reasons, in a third fewer words. The two owners and what production runs come first — its variables differ from the code's defaults, which the old file listed as if they were production's. The history moved to `FINDINGS.md`, four facts with no section there to "Moved from CLAUDE.md, 2026-10-01". Its shared sections and the CPO's areas are the CPO's to read, in `main` now; what the CPO does not accept is changed back there | accepted: the CEO's word, by the rule of 2026-10-01 |
| 2026-10-01 | the CEO, with Claude Code | Task 53, SUM's site, specified and not scheduled: one page outside this repository that shows the document and sends a group to the bot, and the bot writing down the label a start came with. Its audience, domain, host and contact are left open. It goes up after 47 and is promoted after 41; neither task moves. The phase D intro's stale order of the CEO's track corrected to 51, 47, 52, as logged above | the CEO's own |
| 2026-10-01 | the CEO | The CEO's word is enough in every area of the bot — the CPO's included: prompts, the model, the schema and migrations, cost and limits, the infrastructure — and in what is shared, agreed with the CPO beforehand. The CPO's changes in the CEO's area or in what is shared still wait for the CEO, and a migration is still named to the other before it is pushed. `CLAUDE.md` → "Who decides", `README.md` and this file's rules say so, and the lines above that waited for the CPO are settled by it | agreed with the CPO beforehand, per the CEO |
| 2026-10-01 | the CEO, with Claude Code | Task 54, drawings cut out of the page, after record 59 printed nine drawings as nine sentences: recognition names each drawing's frame, the code cuts it out of the photograph and sets its ink in the document; a drawing that is data — a graph, and later a function by its formula, a number line — is still drawn from the data. Rule 3 changes with it: the drawing cut out of a page is kept with its record, the photograph still never | the CEO's own |
| 2026-10-01 | the CEO, with Claude Code | Task 55, record 59's other faults — no headings, the margin line, reddit.com as a source — after 54; the margin line's backlog item moves into it | the CEO's own |
| 2026-10-01 | the CEO, with Claude Code | Task 56, the bot as a teacher — «Идея», «Зачем условие», «Пример»; a fact keeps its source, the bot's reasoning is printed without one under its own label and checked by code wherever there is something to check; «Проверь себя» its second step. After 55. The CEO's track is now 54, 55, 56, then 47 and 52 | the CEO's own |
| 2026-10-01 | the CEO, with Claude Code | Task 54 measured on record 59's album (record 60) and put to sleep: its cut-outs of a light hand came out faint under the grid, one frame took in the text beside it, and the CEO read the document as worse. Production back on `prompts-v6.md` the same hour; the code stays, asleep without frames. The CEO's track: 55, 56, then 47 and 52 | the CEO's own |
| 2026-10-02 | the CEO, with Claude Code | Task 44's "another provider" surveyed, not yet measured: the handwriting and formula readers on GitHub return what the pipeline cannot use — plain text, no formulas, no ℤ or ≡ — and open page models, the only kind that reads a page whole, are unmeasured on Russian cursive and behind Gemini on every independent handwriting benchmark. Three candidates named for an arm on an album already read; `FINDINGS.md` → "Cheaper readers, surveyed 2026-10-02". Nothing scheduled; 44 stays paused | the CEO's own |
| 2026-10-02 | the CEO, with Claude Code | Phase E, the app: the bot delivers the records, a Telegram Mini App collects what a group studies with — the stores later. Its first version is the library and the exam preparation, neither calling a model (57, 58, 59), after 56 and 47; spaced repetition, «Проверь себя» in the app, sharing and the stores once it is used. `CLAUDE.md` → "What NOT to do" and the backlog move the Mini App, spaced repetition and sharing from forbidden to planned; the stores, payments and any export stay out | the CEO's own |
| 2026-10-02 | the CEO, with Claude Code | Task 55 reopened by record 62, record 59's album read again: a tall formula running into the line above, "~~~" printed as text, the words under a brace set as an index, a tail the page's bottom carried in, an explanation calling the author's union «опечатка», dxdy.ru among the sources | the CEO's own |
| 2026-10-02 | the CEO, with Claude Code | Phase E is now a record from any material and the subject whole — a board (60), a recording (61), a film (62), the subject's base with its earlier lectures (63) — before the app, which becomes phase F after 63. A recording's record is the bot's notes, marked on its first page; the board comes first. The records' quality stays first: 55's remainder and 56 before all of it. `CLAUDE.md` → "What NOT to do" and the backlog no longer forbid video and transcription | the CEO's own |
| 2026-10-02 | the CEO, with Claude Code | Task 55: record 62's faults fixed but the tail; `note_processed` gains `explain_judged` ("Contracts"); `CLAUDE.md` → "Stage three" has three guards — an explanation that judges the record is dropped — and "The document" says how a tall formula, a brace's words, an aligned chain and "~~~" are set | the CEO's own |
| 2026-10-03 | the CEO, with Claude Code | Record 62's tail is the next lecture begun at the bottom of its last page — the CEO, from the photograph. It leaves task 55 for the backlog's item on the tail of the previous lecture, which becomes "where a lecture begins and ends"; 55 waits only for the CEO's look at record 62 drawn again | the CEO's own |
| 2026-10-03 | the CEO, with Claude Code | Task 55 accepted on record 62 drawn again — "in order, and better" — with the lecture that is not its own noted once more; the CEO's track: 56 next | the CEO's own |
| 2026-10-03 | the CEO, with Claude Code | Task 64, one lecture one record, taken before 56: recognition names where a lecture begins (`prompts-v9.md`, `lecture_starts`), and the code cuts the lecture before and the one after off an album's edges where every run agrees. Measured on records 46's and 59's albums; the backlog's item on where a lecture begins and ends becomes this task | the CEO's own |
| 2026-10-03 | the CEO, with Claude Code | Task 64 measured (records 65 and 66, two pages under v6 and v9) and put to sleep: the model named no lecture start, nothing on these pages telling a lecture from a section. Production goes back to `prompts-v6.md`; the page photographed twice joins task 63 as the way to one lecture a record. The CEO's track: 56 next | the CEO's own |
| 2026-10-03 | the CEO, with Claude Code | Record 66 lost its composition to the numbers guard, once: asked again six times in the container, it was accepted six times. A refused composition is now asked for once more, and `note_processed` gains `compose_retried` ("Contracts"); `CLAUDE.md` → "Stage two" and "Concurrency ceilings" say so | the CEO's own |
| 2026-10-03 | the CEO, with Claude Code | Task 56 done: the explaining stage writes the teacher's boxes — «Идея» before every proof, «Зачем условие» at every condition, «Пример» at every new notion — without a source, under labels of their own, checked by code (`prompts-explain-v2.md`, production the same day). Measured in three runs on record 64 and accepted by the CEO. «Проверь себя» is the app's, not the PDF's. `BRAND.md` v1.3; `note_processed` gains `elements` and `elements_dropped`. The CEO's track: 47 next | the CEO's own |
| 2026-10-03 | the CEO, with Claude Code | Task 47 done: privacy mode turned off in BotFather by the CEO; `/start` and `/help` carry the button «Добавить в чат группы»; the `/start add` a client sends into the chat is not answered and is counted as `group_invited` ("Contracts"). `CLAUDE.md` → "A group chat". The CEO's track: 60 next | the CEO's own |
| 2026-10-04 | the CEO, with Claude Code | Task 63 taken before 60: it needs no material the CEO does not have, while the board's photographs are still to be taken; the CEO's track is 63, 60, 61, 62, then the app | the CEO's own |
| 2026-10-04 | the CEO, with Claude Code | Task 63 widened by the CEO: a lecture is a row of its own, and a second notebook of it — a classmate's — joins it, what the base lacks set in at its place under «Из другого конспекта», the group getting the lecture's updated document. Decided by code, no model asked: the same lecture at half of one text found in the other, a passage only where the base has no line of its own — measured on the records in production before it was built, no passage on eighteen pairs of one album read again. The board, the recording and the film will be a lecture's materials as they come | the CEO's own |
| 2026-10-04 | the CEO, with Claude Code | Task 63's first part built: subjects and lectures as rows (migration `014_subjects_lectures`, named to the CPO before the push), a lecture's day from the caption, the margin or the day sent, and one lecture from several notebooks set in by code. `note_processed` and `note_tagged` gain `lecture_id` and `lecture_joined`, `note_processed` `explain_skipped` ("Contracts"). `CLAUDE.md` → "The corpus" gains "A subject, its lectures, and one lecture from several notebooks", "The document" the passage from another notebook; `BRAND.md` v1.4. Left: the page photographed twice, the earlier lectures in bulk, and a classmate's notebook to measure on | the CEO's own |
| 2026-10-04 | the CEO, with Claude Code | Task 65, from record 67 — one photograph sent twice, its first reading half the page: two runs that stopped short no longer outvote one that read further. A block one run read and the chosen did not brings two more runs; a block two runs read is on the page, and the runs carrying it are compared. `CLAUDE.md` → "What works" gains the rule, "Concurrency ceilings" the album's at 604 s (1774 s at production's 90 s call), raised by two runs a page; `note_processed` gains `runs_added` and `read_further` ("Contracts"). Recognition is the CPO's area | the CEO's own |
| 2026-10-04 | the CEO, with Claude Code | Task 66 specified, not scheduled: in a group with topics, every record goes to one topic, «Конспекты», which the bot makes where there is none. The first big group, J3115, added the bot the same day and is divided into topics | the CEO's own |
| 2026-10-04 | the CEO, with Claude Code | Task 67 specified as a mechanism to think through: the bot asks a group its university, year and programme, so a subject's records can serve the next cohorts. Its last step is sharing, which "What NOT to do" holds until the app is used — the rule changes first | the CEO's own |
| 2026-10-04 | the CEO, with Claude Code | Task 68 specified, not scheduled: an album sent with its pages out of order is assembled in the order the pages themselves say — the numbers in their margins, a sentence across a seam, numbering that runs on — decided by code, and in the order sent when the evidence is not one-sided; the bot does it by itself, asking nobody (the CEO: «бот решает»); measured on albums already read before it is built | the CEO's own |
| 2026-10-04 | the CEO, with Claude Code | The repository tidied: `CLAUDE.md` → "Structure" lists `prompts-explain-source-v1.md`, kept though unused, and says why — every prompt stays in `prompts/` once used, since a record does not say which made it. Nothing tracked was removed | the CEO's own |
| 2026-10-06 | the CEO, with Claude Code | Task 69, from record 74: formulas spaced apart and in a serif, trees drawn as tangles, «[зачёркнуто]» printed, a page of one word — the document's, fixed in `pdf.py`, stored records included. And the CEO's decision of the day: the author's shorthand is spelled out by the composer (`prompts-compose-v4.md`, rule 10), where its «слова оставляй как есть» held every word — the lecture's own abbreviations, formulas and numbers left as written. Production switches to v4 after it is measured on record 74's album sent again. The composing prompt is the CPO's area | the CEO's own |
| 2026-10-06 | the CEO, with Claude Code | The lecture as structured material — set out by topic, with sections such as «Объяснение», «Ключевые понятия», «Почему?», «Примеры и применение» — specified as the CEO's idea and archived to the backlog the same day: the CEO judged that it does not move the project's result. Nothing scheduled moves | the CEO's own |
| 2026-10-06 | the CEO, with Claude Code | Task 69 closed on the CEO's word, the day it shipped: v4's measurement on record 74's album and the photographs' comparison left undone. 65 waits for data | the CEO's own |
| 2026-10-06 | the CEO, with Claude Code | Task 70 taken: «Хорошо» and «Плохо» under every document, «Плохо» asking where the error is, the reply stored and sent to the CEO (`FEEDBACK_CHAT_ID`) — so faults are read off the groups. A table `feedback` (migration `015_feedback`, the CPO's area — named to the CPO before it is pushed); callback queries get a session; in a group a reply to the bot's own message is heard. Events `note_rated` and `note_feedback` in "Contracts" | the CEO's own |
| 2026-10-06 | the CEO, with Claude Code | Task 71 taken, from record 79: a margin's day after the pages came made the lecture last year's — «10 ноября» on a notebook sent on 6 October headed its document 10.11.2025. Such a day dates nothing now, the lecture taking the day it was sent; the lectures already filed are read again by a data migration, `016_lecture_days`, the CPO's area, named to the CPO before it is pushed. `CLAUDE.md` → "A subject, its lectures…" changes with it | the CEO's own |
| 2026-10-06 | the CEO, with Claude Code | Task 72 taken: a group's week — who sent its records and who rated them, two numbers a person, ordered by records — in `/stats` in a group, and summed up in the chat with the first record of the week after. A record a reply called the bot on counts for whoever sent the photographs (`notes.sender_id`), its cost still the replier's; the week's summary is claimed on the group's row (`groups.rating_week`) — both in `017_rating`, the CPO's area, named to the CPO before it is pushed. The limits do not depend on it. `CLAUDE.md` → "What NOT to do": social features stay out but for this one, inside its group. Event `rating_posted` in "Contracts" | the CEO's own |
| 2026-10-06 | the CEO, with Claude Code | Task 41, the CPO's, gains an item: `/stats` in a group says what is left of the group's day, in pages, under task 72's week | the CEO's own, by the rule of 2026-10-01 |
| 2026-10-06 | the CEO, with Claude Code | A person's day is 12 pages, not 30: `DAILY_PAGES_PER_USER`'s default here and in "Environment variables" — the variable on Railway stands above it and is the CEO's to set — and the startup log says the day's limits. Cost and limits are the CPO's area; built with task 72, item 7 | the CEO's own, by the rule of 2026-10-01 |
| 2026-10-07 | the CEO, with Claude Code | Tasks 70 and 72 closed on the CEO's word, the day after they shipped | the CEO's own |
| 2026-10-07 | the CEO, with Claude Code | Task 73 taken: the week's summary goes to every active group's chat on Saturday at 10:00 Moscow time, sent by the bot's one timer, instead of with a week's first record; the week runs Saturday to Friday, in `/stats` too. Task 72's "no scheduler" gives way to it. No migration: `groups.rating_week` is now the Saturday a summed-up week ends on. "Contracts" → "A group's week" changes with it | the CEO's own |
| 2026-10-07 | the CEO, with Claude Code | Task 41 taken from the CPO's track, which moves on to 48. A group's day is counted in pages — `DAILY_PAGES_PER_GROUP`, 20 — rather than the $2 the task first named: `/stats` then says exactly what is left, and the count does not halve when the prices double on 2027-01-01; the global cost cap stays the breaker. Spend is still counted per group (`ai_calls.group_id`, migration `018_ai_calls_group`, the CPO's area, named to the CPO before it is pushed). One reading of the same pages at a time, the record committed before its pages are free for another: `CLAUDE.md` → "Sessions and transactions" gains that exception, "Scale debt" loses the two rows 41 was for. `note_summoned` gains `reading` ("Contracts"). Task 52's overview, a call with no pages, counts against the group's day as 52 decides | the CEO's own |
| 2026-10-07 | the CEO, with Claude Code | Task 74 taken: `/stats` in the chat `FEEDBACK_CHAT_ID` names — the CEO's own — answers with the whole bot's week and all time: records, people, отзывы and spend, every group active in the week, and the week's people across every chat. `CLAUDE.md` → "What NOT to do": an admin panel stays out but for this one read-only message. `stats_viewed` carries `{"scope": "bot"}` for it | the CEO's own |
| 2026-10-07 | the CEO, with Claude Code | `README.md` is brought up to date with every push, its plan of development first, in a `docs:` commit of the same push — `CLAUDE.md` → "Who decides". Its section on rights in the repository goes: the same rules stand in `CLAUDE.md` | the CEO's own |
| 2026-10-07 | the CEO, with Claude Code | Task 75 taken: an album's page 2, sharp and filling its frame, was refused three times as too dark, at contrast 26.1 to 27.8 against 28 — photoguard's contrast is the spread of brightness across the sheet, low on a page with little written however it is lit. `MIN_CONTRAST` 28 → 20, the CEO's choice over a new measure of ink against paper, which would need real pages, good and bad, to set; the fourth edit to the ready-made `photoguard`, made on a reproduced failure. The frame check is the CPO's area | the CEO's own, by the rule of 2026-10-01 |
| 2026-10-07 | the CEO, with Claude Code | Task 76 taken, from a week of production read on 2026-10-07 — the deploy logs, Railway's metrics, `ai_calls` — and three audits of the code. A recognition call that thinks past 90 s is repeated once at 180 s instead of twice at 90, the run's worst case unchanged; one document drawn at a time, after two drawn at once broke each other's formulas; `check_limits` stops writing the day's rollover and `consume` counts the day in one statement, after a person's first record of the day held their row for minutes; image work on two threads and `MALLOC_ARENA_MAX=2` on Railway, after every album left 50–100 MB the process kept; the SDK's automatic function calling off. "Known risks" → the quota race keeps only its soft half. The model calls, the database and the infrastructure are the CPO's area; "Scale debt" changes with it | the CEO's own, by the rule of 2026-10-01 |
| 2026-10-07 | the CEO, with Claude Code | Task 77 taken: five formulas in two records went out as their source — `\cancel{…}`, which mathtext does not know, and `\xrightarrow` with its condition in brackets, which the rewrite did not match. A struck term is drawn struck, as `~~…~~` is in a line: dropping the command would have made «\cancel{56}^{48}», 56 crossed out and 48 written over it, read as 56 to the 48th. `docs/BRAND.md` v1.6 | the CEO's own |
| 2026-10-08 | the CEO, with Claude Code | Task 78 taken, from a reader's «Плохо» on record 86, the first album after task 76's deploy. Not task 76: the request Gemini receives is the same byte for byte, and the four pages agreed above the week's mean. What the reader saw was a title's formula printed as its source, the author's frame inside a line printed as «[рамка: ?!]», a composition refused twice for «1))» tidied to «1)», and a teacher's example that was the lecture's construction for √3. Two of its items are the CPO's, taken on the CEO's word: the numbers guard counts «1))» opening a line as an item's marker, and `prompts-explain-v3.md` says an example is not the lecture's working with another number — production switches to it on the CEO's word. `docs/BRAND.md` v1.7 | the CEO's own |
| 2026-10-08 | the CEO, with Claude Code | Task 79 taken, from record 87 — record 86's album sent again, its composition refused twice as 86's was. Run twice more on Railway on the CEO's word, the composer lost the same two numbers, and neither was a value: the theorem's parts «1 Существование» and «2 Число…», made the list they are. The numbers guard, the CPO's, counts a number opening a line before a capitalised word as an item's; «1))», task 78's likely cause, was not record 87's. And three cases begun on a line of text are set on one ground | the CEO's own |
| 2026-10-08 | the CEO, with Claude Code | Task 80 specified, not scheduled: the CEO asked whether the bot should make study materials based on the records instead of the records, and chose to build them over the records — the record stays what a group trusts and everything else is made from, and a lecture's study version is built from it when somebody presses a button. Made instead of the record, the material would have changed the rule the product stands on, marked is the whole licence to add, and lifted «text rewriting» from "What NOT to do". It takes up the design of the idea of 2026-10-06, the lecture as structured material, archived that day. The spec waits for the CEO's approval | the CEO's own |
| 2026-10-08 | the CEO, with Claude Code | Task 80 approved and taken next. The study version is for understanding a lecture by someone who was not there — the exam stays the subject's, 52 and 59 — and ends on three to five questions to check oneself, their answers on the last page, marked as the bot's: the decision of 2026-10-02 put «Проверь себя» in the app alone, and now the study version's PDF has its own. The record's document does not change | the CEO's own |
| 2026-10-08 | the CEO, with Claude Code | Task 80 changed the same day, before it shipped: a chat gets the study version, not the record's document — on every capture path and every "#word" that brings a record back, built once and kept, the record's document only when no study version can be had. The CEO's words: «мы не присылаем пользователю конспект, сразу отдаём ему учебную версию», and «в будущем я хочу иметь возможность разделить эти функции и присылать по кнопке» — so the two stay separate, decided in one place. A lecture of several notebooks is studied whole | the CEO's own |
| 2026-10-08 | the CEO, with Claude Code | Task 81 taken: twelve pages sent at once came back as two records, ten pages and two — Telegram puts at most ten in an album and sends the rest as the next. The albums one person sends into one chat are one album while each before the last is full, up to `MAX_ALBUM_PAGES`, 30 by default as in production since that afternoon; an album of exactly ten waits 15 s for the rest of its send; a page left over as a photo of its own joins too, heard in a group without its "#word". A page's update commits before it waits for its album, so the wait holds no connection. `note_processed` gains `album_parts` ("Contracts"); `CLAUDE.md` → "Sessions and transactions", "Updates and albums", "Concurrency ceilings", the environment. The capture path is the CEO's area, the pool and the ceilings the CPO's | the CEO's own |
| 2026-10-08 | the CEO, with Claude Code | Task 82 taken: records 88 and 89, the two records of twelve pages, both went out uncomposed. Composed again on Railway on the CEO's word ($0.16 in all, nineteen rows in `ai_calls`), the composer lost no value of 88's — the numbers were an item's after a bullet and one the author struck out — and squared a formula of 89's, nine times of fourteen. The numbers guard, the CPO's, counts neither of the first two; a formula the composer changed is put back as read rather than refused, counted as `compose_restored` ("Contracts"). `CLAUDE.md` → "Stage two". Five records of fifteen went out uncomposed since `prompts-compose-v4.md` went to production on 2026-10-06 | the CEO's own |
| 2026-10-08 | the CEO, with Claude Code | Tasks 83 and 84 taken, in that order, from the CEO's reading of records 88 and 89 against the photographs — sixteen points, ten in the lecture and six in how it was set out. The CEO asked whether to check them with algorithms rather than a model. 83 is the document's share, all code: a box set after the sentence it is anchored in, found across the lines of one, a word carried over with a hyphen joined, struck words not printed, ≤ for ⩽, a short formula ending a sentence set in its line, a ringed sign framed. 84 is the one class of the lecture's errors code can prove — an equality that does not hold, «(−x)(−x) = x», «c − h = c² − 2ch + h²» — a finding under its line, never the author corrected; measured over every record in the database before it is on, the CEO's word given to read them. The rest of the sixteen is meaning, no code's to find | the CEO's own |
| 2026-10-09 | the CEO, with Claude Code | Tasks 85–88 taken and 89–91 specified, from thirty-two pages the CEO sent at once on the evening of 2026-10-08 and the thirty-eight errors another model listed over the three documents that came back. The CEO asked for the list to be checked and a plan made, and went to sleep: the four are made overnight without a push, and wait for the CEO's word. 85: the albums of the send came 19 s apart, the window was 15 s — an album of ten waits a minute. 86: the document's share of what was found, all code. 87: record 91's study version did not parse and was asked for only by a press of its button. 88: records 91 and 92 went out uncomposed for numbered items in lower case, the guard the CPO's — measured on them, on the CEO's word, before it ships. 89–91 are decisions: the bot's reasoning that assumed what the lecture proves, the photographs against the reading, a definition the lecture relies on and does not give. Checked against the documents, most of the list is the lecture as the notebook has it or one stroke of the reading from it; three points are not there; one is the bot's own. `FINDINGS.md` → "Records 90, 91 and 92" | the CEO's own |
| 2026-10-09 | the CEO, with Claude Code | Task 88 widened while it was made: what the author struck out leaves the count of `[неразборчиво]` and the length as it leaves the numbers — record 91's struck passage held a mark — and an item may stand inside a line, «верно 3) …» | the CEO's own |
| 2026-10-09 | the CEO, with Claude Code | Tasks 92–97 specified from record 97, ten pages of a notebook with lectures and a practice session, and what its author, asked by the CEO, found wrong in its study version: the course's organisation on the first page, set out crookedly; set equality with no word on what it is; formulas where pictures would explain; «Левая страница» and «Правая страница» printed; a drawing described rather than shown. Read against the record's text, on the CEO's word: the page labels are the reading's, written for a photograph of two pages; all three of its equality findings are false — a solution read as a definition two pages on, and a formula the author struck out; a frame of the record's own was closed by «\}» and printed as its source. The CEO's answers: what does not belong to the subject is to be told apart and left out, and the drawings start with what code can draw from data | the CEO's own |
| 2026-10-09 | the CEO, with Claude Code | Tasks 92, 96 and 97 taken, the CEO's word, with the database read for 96 as for 84. Task 97 loses one item: ℕ framed alone keeps its number, since unnumbered it would renumber the main formulas after it under explanations stored with «(4)» | the CEO's own |
| 2026-10-09 | the CEO, with Claude Code | `MAX_ALBUM_PAGES` 20 and a person's day 30 on Railway since 09:35 Moscow time, the CEO's — task 85's acceptance says so | the CEO's own |
| 2026-10-09 | the CEO, with Claude Code | The CEO's answers in the morning: 85 to 87 pushed, and 88 once measured; the CEO's word to read records 90 to 92; `MAX_ALBUM_PAGES` stays 15 on Railway, so a send of more than fifteen pages is several records by design — task 85's acceptance says so; 89 and 91 not taken, «лекцию можно поправлять» — a box of the bot's may correct the lecture, and the CEO reads them; 90 the CEO's own check of the photographs. Task 88 measured on records 91 and 92: the numbers it was made for no longer lost, 16 to 2 and 3 to 1, and both still refused — a number spelled out, a definition's number dropped, a lone item, a formula changed. It ships as an improvement, with what the measurement found taken in, and its acceptance criterion is changed to what it can do | the CEO's own |
| 2026-10-09 | the CEO, with Claude Code | Task 93 taken, the CEO's word, and its design settled on record 97's text: the model names the units about the course's organisation, and code leaves out of each its paragraphs before the first that holds the subject — a guard over whole units would have kept the organisation for the set equality cut into the same unit. More than a fifth of the record named, and nothing goes. A kept study version built by another prompt is built again, so record 97 comes back without its organisation; a box anchored only in what is left out is not printed. Measured on record 97 before it ships | the CEO's own |
| 2026-10-09 | the CEO, with Claude Code | Task 95 taken, the CEO's word, with every record read for its measurement. A caption is the explaining stage's, `prompts-explain-v4.md`, in a list of its own beside the teacher's boxes — records 90 to 92 filled the twelve those may hold — anchored on a formula set apart or a drawing, checked as an idea is, and set before what it names under «Что это · от бота». `note_processed` gains `captions` and `captions_dropped` ("Contracts"). Measured on records 88 to 97 before production switches; a record made before the switch keeps its boxes | the CEO's own |
| 2026-10-09 | the CEO, with Claude Code | Task 95 changed while measured. In the explaining stage's first call, `prompts-explain-v4.md`, the captions were right — record 97's set equality all three times — and the teacher's boxes fell from v3's 59, twice, to 57, 39 and 51 over seven lectures, the ideas of proofs most. The CEO's choice: the captions by a call of their own beside the first, `prompts-explain-captions-v1.md`, thinking `low`, one call more a record; v3 stays as it is, and v4 is kept as measured. The call is read by name and goes to production with its deploy, once measured and read | the CEO's own |

## Where this is going, decided 2026-10-02

**A record from whatever the lecture left, and an app to study from the
records.** The CEO's concept of 2026-10-02: the bot keeps delivering
records to Telegram, makes them from a board, a recording or a film as
well as from a notebook, keeps a subject whole, and an app collects what a
group needs to learn from it all. The record is still what all of it is
made of, and the records' quality comes first: "all the emphasis is still
on improving the records" — 55's remainder and 56 before any of it.

The CEO's decisions of that day:

- **Any material, before the app** (phase E). A board photographed (60)
  first — the nearest to the photo path; then a lecture recorded (61), then
  filmed (62), which is its sound and its board's stills.
- **From a recording the bot condenses rather than transcribes**, so that
  record is the bot's notes and says so on its first page; what was said
  is kept beside it as text, the notes checked against it, and its
  formulas come from what was said or from the board's photos sent with
  it. The recording, like a photo, is never kept.
- **The subject whole, before the app** (63): its lectures at the dates
  they were given, the earlier ones added in bulk, the teacher's materials
  (48) with them. The library and the exam page are views of it, and built
  on tags alone they would be built twice.
- **The app** (phase F): a Telegram Mini App now, the stores later on the
  same API — nothing in it may assume it is called from inside Telegram
  except the sign-in. Its first version is the library and the exam
  preparation (58, 59), both built from what the pipeline already writes,
  so neither calls a model: no cost a use, and nothing in them the author
  did not write. After it, and only once it is used: spaced repetition on
  the exam preparation's material, scheduled by FSRS; «Проверь себя» in
  the app rather than the PDF; sharing; the stores. `CLAUDE.md` → "What NOT
  to do" moves the Mini App, spaced repetition, sharing, video and
  transcription from forbidden to planned; payments and any export stay out.
- **Measured from the first day.** `/notes`, `/search` and four more ways
  into the corpus were built, never used and deleted. Every new way in
  writes its event with the group's id, and the next tool comes only when
  the last one's events show it used. The question stays the project's —
  whether a group uses this weekly.
- **Whose:** all of it the CEO's; the model calls, the schema and the
  limits it needs are the CPO's area, open to the CEO since 2026-10-01,
  each migration named to the CPO before it is pushed.

The CEO's track: 55, 56, 47, 63, 65, 60, 61, 62, 57, 58, 59; 52 when 41 is
in — 63 taken before 60 on 2026-10-04, and 65 the same day from record 67.

## Where this is going, decided 2026-09-30

**From the record to the subject.** Up to phase C the unit was a record: one
lecture, one PDF. Phase D makes it a group's subject — "#матан" — which has
its records, the materials the group uploads for it, and in the end a course
the group gets back as one document. The record is still what all of it is
made of, and every rule about the record stands.

The CEO's decisions of that day, each one what its task is built on:

- **Two tracks, one an owner.** The CEO's — 47, 52, 51: a group that can add
  the bot by itself comes first, because the question the project exists to
  answer needs more than one group. The CPO's — 41, 48: 41 first, because
  with several groups one of them can exhaust the day's budget for all, and
  both 52's overview and 48's topics spend.
- **A course as one document is an overview to study from, not an export**,
  and the barrier `CLAUDE.md` put on any bulk export of the corpus is lifted
  for it — for it alone. It opens with an overview the model writes over the
  records, marked as the bot's like every addition. It is sent only when
  somebody asks with the command; the bot never sends it by itself. Task 52.
- **The document gets a look of its own — the CEO's guide, `BRAND.md`.** The
  first word was "around the text and never in it"; the guide the CEO gave
  the same evening goes into the body too — paper, faces, blocks, a
  signature with a QR code on every page — because the record is SUM's
  advertisement as well as the group's notes. Task 51.
- **Context is uploaded as simply as a page, and found by "#word"** — through
  its subject and through topics read out of what is in it. Task 48.
- **The teacher's drive by link is put off** (49), and so is what context
  would do inside the pipeline (50).
- **The work is divided by area**: the CEO owns the interface and the
  product for students, the CPO the database and the model, and both push to
  `main`. What is shared — the order of work, the rules in `CLAUDE.md`, the
  contract between the prompts and `pdf.py` — is decided by both, and where
  they disagree, what is stays as it is. `README.md` has the map.

**What context does not do, whenever it comes: it never enters recognition.**
The worst failure this project has reproduced is a fluent retelling of a page
the model could not read. With a teacher's slides in the prompt, a bad shot
would come back as the slides — convincing and wrong, and a lecture may
differ from its slides on purpose. If it is ever tried there, it is an arm on
an album already read, and the author's check against the photographs
decides. Where it could help is the explaining stage (50): record 50's
explanation called its m̄ an «описка», with nothing to tell it how the course
writes.

## Where the cost work stands, 2026-09-29

Task 44, its second half, as the sessions of 2026-09-25 and 2026-09-29 left
it — paused by the author on the 29th. The evidence is in `FINDINGS.md` →
"What a record costs"; this is where it stopped.

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

**Settled on 2026-09-29.** The document's quality is not traded for its price
— the author's decision — so the number of runs stays at three, and nothing
that reads worse is a saving. Recognition stays on `gemini-3.8-flash`:
`gemini-3.5-flash-lite` read the album of records 50 and 51 again (record 52)
and made three errors of substance that both readings of 3.8-flash avoided,
and `VISION_MODEL` on Railway goes back to `gemini-3.8-flash`.

**Open, and the author's to decide:**

1. **Flex.** `service_tier: "flex"` bills every token at half price on the
   same model, for 1–15 minutes a call and 503/429 when capacity runs short,
   with no fallback. Before deciding: a probe of the real latency and refusals
   on these calls — and the author's word on a record arriving in tens of
   minutes. Every ceiling in `CLAUDE.md` → "Concurrency ceilings" is sized
   for Standard.
2. **Another provider.** Measured the way flash-lite was: the album of records
   50 and 51 read by the candidate and set against those two readings, the
   places they dispute checked on the photographs. It needs a script outside
   the bot and the album's four photographs kept for it, which is the
   author's to decide under rule 3. Surveyed on 2026-10-02 (`FINDINGS.md` →
   "Cheaper readers, surveyed 2026-10-02"): nothing open replaces the
   reading — handwriting readers return plain text, formula readers cannot
   write ℤ or ≡ — and a GPU of our own is not to be had on Railway nor worth
   renting at this volume. The candidates are Qwen through a per-token API
   with `prompts-v6.md` as it is, the one kind whose three runs still differ,
   and Chandra 2 and Mistral OCR through their own APIs: under $1 in calls
   for one album.
3. Small: the explanations' writing call at `low`, about 3%, testable on
   stored records with no album sent.

**Scoring the next recognition arm.** Send the album of record 46 again and
compare with 46: the numbers page by page, and the six places whose right
reading the author checked against the photographs — the key in `FINDINGS.md`
→ "What a record costs". Or the album of records 50 and 51, which has two
readings of the current model to set a candidate against: where those two
agree and the candidate does not, the candidate is the one to doubt first.

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
DAILY_PAGES_PER_USER=12
DAILY_PAGES_PER_GROUP=20
DAILY_COST_LIMIT_USD=5
VISION_RUNS=3
VISION_MODEL=gemini-3.5-flash-lite
MIN_MARKDOWN_LEN=40
MAX_ALBUM_PAGES=30
LOG_LEVEL=INFO
```

Five required variables: missing any of them and the app **crashes at
startup**, not on the first request.

`WEBHOOK_URL` — **the service's base address without a path**, e.g.
`https://konspekt-bot.up.railway.app`. The app builds the path itself:
`{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}`. Don't put a path in the variable.

`VISION_RUNS` below 2 is forbidden: there would be nothing to compare
against. Validate it in `Settings` and crash at startup.

**All daily boundaries are UTC.** The reset of `pages_used_today`, the
`ai_calls` selection for today, and a group's pages today (task 41) — 03:00
in Moscow, which is what the group is told.

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

Empty corpus → `texts.STATS_EMPTY`. Event `stats_viewed`, no payload —
`{"scope": "bot"}` in the feedback chat since task 74.

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

# Phase D: the tasks

Specified on 2026-09-30. Two tracks: the CEO's 51, 54, 55, 56, 47, 52 — 51
moved first and 54 to 56 came in on 2026-10-01 — and the CPO's 41, 48, each
in that order, 41 the CEO's since 2026-10-07. Where a specification and the
code disagree, the code is what exists and the specification is what was
decided: ask the task's owner before choosing either.

# Task 47. The bot added to a group in one tap

**Owner: the CEO.**

## Why

Today a group gets the bot in two steps: somebody adds it, and then an admin
of the chat makes it an admin — the welcome asks for that, because with
privacy mode on a bot sees nothing else there. The second step is open only
to the chat's admins, and in a course chat the student who wants the bot is
usually not one. Every group but the author's has to be able to do it alone.

## Do

1. **Privacy mode off** — done in BotFather by whoever holds the bot, since
   no code can do it: BotFather → the bot → Bot Settings → Group Privacy →
   Turn off.
   The bot then receives a group's messages as an ordinary member, which is
   what it receives as an admin today and no more, and `middlewares.heard`
   drops what is not addressed to it before a session is opened, as it does
   now. The change takes effect in a group only when the bot is added to it
   afterwards; the course chat it runs in today has it as an admin and
   needs nothing.
2. **A button.** `/start` and `/help` in a private chat carry one inline URL
   button, «Добавить в чат группы», opening
   `https://t.me/<username>?startgroup=add`: Telegram shows its own chat
   picker and adds the bot to the chat picked. The username comes from
   `bot.me()`, never from a constant, and the label lives in `texts.py`. It
   is the first button the bot shows, and it is not styling — the chat stays
   plain text; it is the only way Telegram offers to open its picker.
3. **One welcome, not two.** A group the bot joins through the link gets
   `on_joined`'s welcome, and then a `/start@<bot> add` that the person's
   client sends on its own. In a group a `/start` with a payload is not
   answered; it writes `group_invited` with `{"via": "<payload>"}`, which is
   how the button's use is counted.
4. **The welcome stops asking to be made an admin** where the bot sees the
   chat — `texts.group_welcome(sees)` already leaves the request out when
   `sees` is true. `GROUP_CANNOT_SEE` and `on_promoted` stay, for the day
   privacy mode is turned back on.
5. `CLAUDE.md` → "A group chat", the paragraph on BotFather; `PLAN.md` →
   "Contracts", `group_invited` in the table of a group's events.

## Acceptance criterion

- From a private chat: `/start` shows the button, it opens Telegram's picker,
  and the chat picked gets the bot and **one** welcome, which does not ask
  for admin rights.
- In that chat, the bot an ordinary member, a photo with "#матан" in its
  caption comes back as a PDF, and a message not addressed to the bot gets no
  answer and opens no session.
- The deploy log's `Groups:` line reads "sees every message".
- `events` holds `group_joined` with `sees_photos: true`, and `group_invited`.
- The suite is green.

## Don't do

- Don't put `&admin=…` in the link: Telegram then lists only the chats where
  the person can appoint admins — the very limit this task removes.
- Don't hard-code the bot's username.
- Don't change `heard()`: what reaches the bot in a group stays as it is.

---

# Task 41. Limits and spend counted per group

**Owner: the CEO, since 2026-10-07** — the CPO's until then, taken on the
CEO's word with the CPO's track moving on to 48. Its migration is the CPO's
area and is named to the CPO before it is pushed.

## Why

Two limits exist: a person's pages a day (`DAILY_PAGES_PER_USER`), charged in
a group to whoever brought the pages, and one cost cap for the whole bot
(`DAILY_COST_LIMIT_USD`), a breaker over every chat at once. With the bot in
more than one group — which is what task 47 is for — one busy group can
exhaust the day for every other group and every private chat. That is the
first `CLAUDE.md` → "Scale debt" row to come due. The second comes due with a
second person in one chat: two people calling the bot on one album at once
get two records and two bills, because a call is matched to an earlier record
only once that record is saved.

## Do

1. **A group's day has a cap of its own, in pages** — the CEO's decision of
   2026-10-07, over the $2 this task first named: a student reads pages,
   `/stats` then says exactly what is left rather than an estimate, and the
   count does not halve when the prices double on 2027-01-01. A new setting,
   `DAILY_PAGES_PER_GROUP`, default 20, the CEO's. A group's pages today are
   the pages of its records made since 00:00 UTC — `notes.page_count`, what
   was read and charged; a `.docx` costs nothing and is not counted — so
   nothing new is stored for the count, and two albums at once lose none of
   it. `limits.check_limits` refuses pages that would take the group past it,
   with a line of its own in `texts.py`, in this order: the kill switch, the
   global cost cap — the breaker over every chat — the group's pages, the
   person's. A person's page quota stays as it is. The group's count is
   checked when pages come and never for a record's later stages
   (`pages=0`): a record let in is composed and explained whatever the
   count says by then.
2. **Spend counted per group.** `ai_calls.group_id`, in migration
   `018_ai_calls_group`: the group a call was made for, `NULL` in a private
   chat. `vision.log_ai_calls` takes it, and every call made for a group's
   record writes it. What a group costs is read off it; the cap does not
   read it.
3. **One reading of the same pages at a time.** While a group's pages are
   being read — `corpus.source_key` names them, a tagged album and a reply's
   call alike — a second call on them starts no second reading: it is told in
   a line that the record is on its way, and the record goes to the chat once.
   An in-process set of the keys being read is enough while the bot is one
   replica. It is emptied in a `finally`, and only once the record is
   committed, so that a second call finds the one or the other.
   `note_summoned` gains the outcome `reading`.
4. **What is left of the group's day, in `/stats`** — added by the CEO on
   2026-10-06, with task 72: under the group's week, how many pages the
   group can still send today. In pages, never dollars: a screen a student
   reads shows no cost (task 14). The lines in `texts.py` are the CEO's,
   agreed on 2026-10-07.
5. The startup log names the group's day beside a person's.
6. `CLAUDE.md`: "Scale debt" — the two rows this closes, and the new set
   beside the album buffer in the row a second replica breaks; "Sessions and
   transactions" — the record committed before its pages are free;
   "Environment variables", and the limits sentence of "A group chat".

## Acceptance criterion

- A group whose pages today reached its cap gets the new line for its next
  page and nothing is spent; another group and a private chat go on as
  before.
- An album longer than what is left of the group's day is refused whole,
  the line saying how many pages are left.
- The global cap still stops every chat.
- Two replies "#матан" to one untagged album a second apart: one record, one
  set of `ai_calls` rows, one PDF in the chat.
- The `ai_calls` rows of a group's record carry its `group_id`.
- `/stats` in a group says how many pages are left of its day.
- The suite is green.

## Don't do

- Don't reserve budget ahead of a call, and don't lock rows: the cap stays
  soft, as `PLAN.md` → "Known risks" says.
- Don't move the album buffer or the new set out of the process — that is the
  first row of "Scale debt" and a task of its own.
- Don't cut a record's composing or explaining for the group's count: its
  pages were let in, and the document is not traded for a count.

---

# Task 52. A course as one document, on command

**Owner: the CEO.** The overview's call — its prompt, model and guard — is in
the CPO's area: written by the CPO or agreed with the CPO, and after 41.

## Why

A group builds a subject up lecture by lecture, and before an exam it wants
the course, not twenty files. The author ruled on 2026-09-30 that such a
document is an overview to study from, not an export, and lifted the barrier
`CLAUDE.md` put on bulk export of the corpus — for this document alone, and
only when somebody asks for it. The same day the author decided that the
group gets it with an overview the model writes over the records: the map of
the course a student needs before reading twenty lectures of it.

## Do

1. **A command**, `/report <subject>` — `/report матан` or `/report #матан`,
   and in a group `/report@<bot> матан` as well. On the menu and in `/help`
   through `texts.COMMANDS` («отчёт по предмету одним PDF»), which
   `test_wiring` requires of every command. Without a subject it answers with
   the chat's subjects (`corpus.known_tags`) and how to ask; a subject with
   no records gets a line saying so, with the subjects there are.
2. **What it collects:** the chat's records (`corpus._owned`) whose subject
   is that word — `Note.tag`, not the topics, which would pull in other
   subjects' lectures — oldest first.
3. **The document**, one PDF:
   - **a cover** — the subject, the chat's title in a group, the dates of the
     first and the last record, how many records and pages;
   - **contents** — every record's date and title, with the page of this
     document it starts on;
   - **an overview of the course**, after the contents and before the
     records — the one text in the document a model writes for it, set in
     the box the bot's summary has, in the tone no other box has, under a
     label of its own in `texts.py` («Обзор курса · составлен ботом по
     записям»);
   - **the records**, each from a new page and each exactly as
     `corpus.send_record` draws it alone: the title, the margin line, the
     missing-pages box, the text, the findings, the explanations, the
     summary. `pdf.render` is split so that a record's story can be built on
     its own and set into one document;
   - **an index of the terms defined** — under every heading «Определение»,
     the term the definition sets in bold (rule 3 of `prompts-compose-v3.md`
     has the composer bold the term it defines, once, where it is
     introduced), with the date of its record and its page. A definition with
     no bold term is left out rather than guessed;
   - pages numbered through the whole document ("12 / 87"), and a running
     head naming the record the page belongs to.
4. **The overview is one call, and every rule of a call holds.** Text only,
   over the records as they are stored, oldest first, each headed by its date
   and title; never the photographs. What it is asked for, in a prompt file
   of its own (`prompts-overview-v1.md`): what the course covered and in what
   order, how the topics build on one another, the main definitions and
   results, what to go back to before an exam — a page or two, in
   paragraphs, as JSON. On `EXPLAIN_MODEL` at the model's default thinking —
   it is text of the document, and its quality is not traded for price —
   within `EXPLAIN_CALL_TIMEOUT_S`. Limits are checked before it (rule 6);
   the chat's own day is counted in pages since task 41, and what an
   overview, a call with no pages, counts for in it is decided here when
   this task is taken. Every attempt is written to `ai_calls` with
   `kind="overview"` and the chat's group (rule 4); its answer is parsed
   without trust (rule 7).
5. **Its guard is the summary's, by code.** The overview says what the
   records say, so a paragraph that states a number no record carries is
   dropped — `explain`'s summary check, applied to each paragraph against
   the numbers of all the subject's records — and counted. Off
   (`AI_ENABLED=false`), over the limits, failed, or with nothing left after
   the guard, the document goes out without the overview, exactly as it
   would have without the step.
6. **Nothing sinks it.** A record whose drawing raises stands as its plain
   text, the way `send_record` falls back, and the document goes on. It is
   drawn in a thread, like a record, and the chat is told first that it is
   being put together — a course of fifteen records and its overview take a
   while.
7. **An event**, `report_requested`: `{"tag": str | null, "records": int,
   "overview": bool, "overview_dropped": int}` — whether the overview went
   in, and how many of its paragraphs the guard took out — added to
   "Contracts".
8. `CLAUDE.md`: "What NOT to do" already names the exception; "The document"
   gets the course document and its overview beside stage three's summary;
   "Structure", "Concurrency ceilings" and "Tests" whatever changed.

## Acceptance criterion

- `/report матан` in the course chat the bot runs in: one PDF — the cover,
  the contents
  with the right pages, the overview in its box, every "#матан" record oldest
  first, each from a new page and drawn as it is alone, the index, the pages
  numbered through.
- The overview's call is in `ai_calls` with its cost; with `AI_ENABLED=false`
  the same command sends the document without the overview; a paragraph
  given a number no record carries, in a local run, is dropped and counted.
- `/report` alone lists the subjects; an unknown subject says so.
- A record made to raise in a local run comes out as text, and the rest of
  the document is whole.
- `report_requested` is in `events`.
- The suite is green.

## Don't do

- The model writes the overview and nothing else: the records go into the
  document as they are stored, never rewritten, re-read or re-explained.
- Don't keep an overview to use it again: a report is asked for rarely, and
  each one is written over the records as they stand. If repeated reports
  start to cost, that is for both owners to decide.
- Nothing is sent that nobody asked for — not after a record, not on a day.
- No other format and no archive: no Markdown, no ZIP, no "every subject at
  once". This document is the one exception to the barrier.
- Don't design the cover and the contents beyond the system task 36 fixed:
  task 51 does that.

---

# Task 51. The document's own look

**Owner: the CEO.**

## Why

The group gets a document from the bot, and the document is SUM's
advertisement as well: it is forwarded to a group's chat, and whoever opens
it has to see where it came from and how to get one. Until 2026-09-30 it
looked like the notes it was copied from — task 36, `матан 24.09.2026.pdf` —
with no face of its own.

## The brief: the CEO's guide, `BRAND.md`

Given on 2026-09-30:

- the name SUM and the bot `@sum_konspictiumbot`;
- paper, ink and amber off the logo;
- Onest, Unbounded and JetBrains Mono;
- "Суть" on top and numbered sections;
- an amber line beside a definition, formulas on kraft;
- a signature with a QR code on every page.

It goes past this task's first specification — "around the text, never in
it" — and into the body. That is the CEO's call: the document's look is the
CEO's area. On 2026-10-01 the guide was rewritten to v1.1 where the records
demanded it, with what changed and why at its end:

- the formulas stay in Computer Modern;
- the QR code is 16 mm;
- "Суть" is marked as the bot's;
- nothing the bot does not know goes in the head;
- the boxes the guide did not have are in its palette.

## Done, 2026-10-01

- **`pdf.py` draws the guide:**
  - paper, and the three faces bundled with their licences (Lato removed);
  - the scale and the colours;
  - the head, and the signature with its QR code — the bot's name taken from
    `bot.me()`;
  - "Суть" first, numbered sections, a definition's amber line;
  - formulas on kraft, the boxes in the guide's palette.
- **`CLAUDE.md` → "The document"** describes it, and `BRAND.md` is the
  reference.
- **The QR code** was read back by a decoder off every page of a sample, at
  72 to 150 dpi.
- **The suite is green.** The tests that pinned the old look pin the new one,
  and none was added.

## Left before the checkbox

- **The CEO's word on a real record** delivered by the deployed bot, the
  guide's check — the QR code scanned with a phone — included.
- **The chat's face in BotFather**, done by whoever holds the bot: SUM's name,
  picture and description.

## Waiting for the CPO — see "Plan changes"

- **"Суть" is the explaining stage's summary.** The guide asks for one or two
  sentences and 35 words; `prompts-explain-v1.md` asks for three to five.
- **"Проверь себя"**: a question the model writes at the end of a page or a
  section. Its output and guards are the CPO's; its display is the CEO's.
- **The definition's line reads the composing stage's rule 6**, "###
  Определение", so that heading is part of the contract between the prompts
  and `pdf.py`.

## Don't do

- **No cover on a single record**: a sheet of paper for a page of notes. The
  course document's cover is task 52's.
- **Nothing invented for the look**: no lecture number, no lecturer the
  margin did not name, no question, no "Суть" without a summary.
- **No fourth face**, and no colour outside the guide's.

---

# Task 48. A subject's materials: kept, read into topics, found

**Owner: the CPO.** What the replies say and how a search shows its results
are in the CEO's area, and agreed with the CEO.

## Why

A group has more for a subject than its own notes: the teacher's slides, a
problem set, a chapter of a textbook. The author asked on 2026-09-30 for that
context to be uploaded as simply as a page is and found again easily — by its
tags and by what is in it. The teacher's drive by link is task 49, put off;
this one takes a file.

## Do

1. **Upload.** A PDF sent with "#subject" in its caption, in a group or a
   private chat, is a **material** of that subject, owned the way a record
   is: by the group in a group, by the user in a private chat. Without a
   "#word" a private chat is asked for one in a line and a group gets
   nothing, as with an untagged photo. Up to 20 MB, what a bot can download.
   A `.docx` stays what it is today, a record.
2. **What is kept** — a `materials` table, in a migration: the owner
   (`group_id`; `user_id`, who brought it), the subject, the file's name,
   Telegram's `file_id` and `file_unique_id`, the page count, the text of its
   text layer, when. **Not the file:** it stays on Telegram, and the bot sends
   it back by its `file_id` — the pattern `group_pages` set for rule 3. The
   same file (`file_unique_id`) sent again under the same subject is the same
   material. The text is read by code, with `pypdf` — pure Python, the one new
   dependency, and this task is its reason. A PDF with no text layer — a scan
   — is kept all the same and found by its subject and its name, and the
   reply says that what is in it could not be read; reading a scan with the
   model is not this task.
3. **Its topics, from what is in it.** One text-only model call over the
   text: its main terms, five to ten, in the nominative, as JSON — on
   `COMPOSE_MODEL`, the text stage's model. Every rule of a model call holds:
   limits checked before it (rule 6) and its cost counted against the chat's
   cap from task 41, written to `ai_calls` with `kind="topics"` (rule 4), its
   answer never trusted (rule 7). A term the text does not contain is dropped
   — checked by code, word stems against the text, the way the summary's
   numbers are checked against the record. Nothing is recognised, so a
   material's pages count against nobody's page quota. The terms are stored
   in `material_topics` — a table, for the reason `note_topics` is one —
   normalized by `tags.normalize`, and the reply names them: «Добавил в
   материалы #матан: «Лекция 5.pdf», 24 стр. Темы: #ряд #признак_даламбера …»
   — the user sees what the bot will find it by, as with a record's topics.
4. **Found by "#word", like a record.** `corpus.on_tag` searches the chat's
   records and materials together: a material matches by its subject, by a
   topic, or by a word of its file name. One match that is a material comes
   back as the file itself; several are one list, the materials marked as
   such. When no tag matches, the word is looked for in the text of the
   chat's records and materials — PostgreSQL full-text search with the
   Russian configuration, so that «ряды» finds «ряд» — kept behind one
   function, since the suite's SQLite has none. `topic_searched` gains
   `materials` beside `found`.
5. **An event**, `material_added`: `{"material_id": int, "tag": str, "pages":
   int, "has_text": bool, "topics": int}`, added to "Contracts".
6. `CLAUDE.md`: rule 3 (what a material keeps), "The corpus", "Structure",
   and the new dependency.

## Acceptance criterion

- A PDF of slides with "#матан" in a group: the reply names it, its pages and
  its topics; the database holds its text and its reference, not the file.
- "#матан" lists the chat's records and the material; one of its topics
  brings the file back; a word that stands only inside its text finds it
  through the full-text search.
- A scanned PDF is kept, the reply says its content could not be read, and
  "#матан" finds it.
- The same file sent twice is one material.
- `ai_calls` holds the topics call with its cost, and a chat over its cap
  gets no call.
- The suite is green.

## Don't do

- No drive links (49), and no reading of a scan by the model.
- Nothing from a material goes into recognition, composition or the
  explanations — that is 50, not scheduled — and into recognition never
  without an arm (`PLAN.md` → "Where this is going, decided 2026-09-30").
- No embeddings and no vector search: a "#word" is the way in.
- Don't change what a `.docx` or a photo becomes.

---

# Task 53. SUM's site: one page that sends a group to the bot

**Owner: the CEO.** Specified on 2026-10-01 and not scheduled: the CEO comes
back to it after the document. Its open decisions, at the end, are the CEO's.

## Why

Whoever hears of SUM outside Telegram — from a classmate, at an
accelerator's demo day, from the deck — finds a bare link to the bot and
nothing that shows what it makes. A page has a minute to say what SUM is, to
show a real document and to put the bot into a group's chat with one button.
It is a storefront, not a second interface: everything is still done in the
bot, and `CLAUDE.md` → "What NOT to do" stands. Putting the records on the
web would change that section, which is for both owners.

## Do

1. **One page, in Russian, for a phone first** — people arrive from
   Telegram:
   - the sign SUM ✦, one sentence of what it is, and two buttons:
     «Добавить в чат группы» (`https://t.me/<bot>?startgroup=site`) and
     «Открыть бота» (`https://t.me/<bot>?start=site`);
   - three steps: a page photographed into the chat with its "#subject", the
     bot reads it and checks its arithmetic, the group gets a PDF that the
     "#word" finds again;
   - the document itself, the page's centre: two or three pages of a sample
     as pictures, and the sample to download;
   - what the bot adds and how it shows — "Суть" and the explanations in
     marked boxes with their sources, the author's text never rewritten;
   - questions: is it free, which subjects, what becomes of a photo (not
     kept — only the text), what the bot sees in a chat (only what is
     addressed to it);
   - a footer: the bot, a contact, the privacy policy.
2. **Every claim true of the bot on the day the page goes up.** The deck
   lists as working what is not built — the course's memory (50), a
   lecture's audio ("What NOT to do"), uploading slides and books (48) — and
   the team's charter (`SUM-ustav-komandy.docx`, outside this repository)
   says that what is planned is called a plan.
3. **The sample is one of the CEO's own records**, with no classmate's or
   lecturer's name on it.
4. **Built outside this repository**, a static page with no framework: every
   push to `main` deploys the bot and cancels what it is processing, and the
   site shares nothing with the bot's code but the look.
5. **The look is `BRAND.md`'s**: paper, ink and amber; Onest, Unbounded and
   JetBrains Mono, served by the site itself, not Google Fonts. A link to it
   in a chat shows a card in the same look (Open Graph).
6. **Nothing collected** — no forms, no cookies, no third-party scripts or
   analytics. What the page brings is counted by the bot.
7. **The bot writes down the label a start came with.** `/start` reads no
   payload today. In a private chat a start with one writes it to `events`;
   in a group, task 47's `group_invited` carries it as `via`; named in
   "Contracts" when built. "How many groups came from the site, and do they
   use it a week later" is then a query on our own tables — the question the
   project exists to answer.
8. **A privacy policy and terms of use**, written with a lawyer and linked
   from the footer and from the bot's profile. They wait on the lawyer's
   answer about where the data lives: the database is on Railway, outside
   Russia, and 152-FZ asks for the personal data of Russia's citizens to be
   stored in Russia. The charter already sends the CEO to a lawyer about it.
9. **A host that opens from Russia** on mobile internet without a VPN —
   some foreign CDNs are throttled there; a Russian static host, such as
   Yandex Cloud, by default.

## Before it goes public

- **47 first.** The page's main button adds the bot to a group, where
  without 47 it asks to be made an admin — the step 47 removes.
- **41 before it is promoted widely.** The day's spend cap is one for the
  whole bot, and a stream of groups from the page could exhaust it for
  everyone on their first day.

## Acceptance criterion

- The page opens over HTTPS on its domain from a Russian mobile network
  without a VPN.
- One button opens the bot, the other Telegram's chat picker.
- A link to it in a Telegram chat shows its card.
- Every claim on it is true of the bot that day.
- A start from the page is in `events` with its label.
- The page makes no request to a third party.

## Don't do

- No login, account, records on the web, photo upload, prices or payment:
  the bot is the one interface.
- Don't change the document's QR code: it opens the bot directly, the
  shorter way.
- Nothing of the site in this repository but item 7.

## Open — the CEO's to decide

1. Who the page is for. Recommended: a student group first, and a short
   block for tutors and schools, with a contact and no prices.
2. The domain, and whose name it is in: the charter puts the brand in the
   company's; until the company exists, the CEO's, moved later.
3. The host. Recommended: a Russian one.
4. The contact on the page: a personal Telegram, or an account of SUM's.

---

# Task 54. Drawings cut out of the page

**Owner: the CEO.** Decided on 2026-10-01, after record 59. The prompt, the
schema and rule 3 are in it, on the CEO's word in every area.

## Why

Record 59, a lecture on compactness, carried its proof in its drawings —
balls round points, a set covered by them, a point outside with its
neighbourhood, the ε-strip round a limit — and the document gave each of the
nine a sentence: «схема: множество, покрытое шарами». Two stood inside a line
with their brackets, and the arrows of one came out as lines of text. A
drawing the record only describes is one the reader does not have. Redrawn
from what the model says about it, a sketch would be the model's picture of
the topic rather than the author's — exactly where it invents. So the drawing
is taken from the page. Where a drawing is data — a graph's edges, and later
a function by its formula or a number line — it is still drawn from the data.

## Do

1. **Recognition names each drawing's frame** — `prompts-v8.md`, v6 with rule
   6 extended: a drawing that is not a graph or a table stays one line
   `[схема: …]` where it stands, and its frame goes into a new answer key,
   `drawings`: `[top, left, bottom, right]` in thousandths of the photo's
   sides, one per `[схема: …]`, in their order. Labels and arrows inside a
   drawing are part of it and are not written out as text. The frames are not
   in `markdown`, so neither agreement moves.
2. **`parse_response` trusts no frame**: four integers from 0 to 1000, top
   above bottom and left before right, or `None` in its place, so a bad frame
   never shifts the ones after it. Without the key the list is empty, and
   every prompt before v8 reads as it did.
3. **The code cuts each drawing out** (`figures.py`), in both photo paths,
   from the compressed image the model saw: the best run's frames paired with
   its `[схема: …]` lines in order — none at all when the two counts differ.
   A frame too small to hold a drawing, or covering most of the page, is not
   cut. What is kept is the darkness of the page's ink, not its colours: the
   paper's light, a shadow across it included, is measured and divided out,
   the ink stays whole — dashes and hatching too — a notebook's grid stays
   faint, the sheet's other side showing through goes, and the edges fade.
4. **Placed after composing, by its words**: composition sees `[схема: …]`
   as it always has, and afterwards each cut-out is placed at the
   `[схема: …]` that carries its words, in order, which becomes
   `[рисунок N: …]` — N through the whole record. A drawing whose line the
   composition changed is not placed: a picture never lands at the wrong
   line.
5. **Stored with the record** — `note_figures`, migration
   `013_note_figures`: the record, the number, the PNG. Rule 3 says what
   changed: the drawing cut out of a page is kept, the photograph never is.
   The document is drawn from what is stored, so a record a "#word" brings
   back months later still has its drawings.
6. **The document draws it** (`pdf.py`): `[рисунок N: …]` with its PNG is the
   author's drawing in the document's ink on its paper, at about the size it
   had on the page, never wider than the column, set apart like a graph, with
   no caption — the author wrote none. Without one, it is the line «схема: …»
   of today. A drawing written inside a line of text is lifted onto a line of
   its own, `[граф: …]` included.
7. `note_processed` gains `drawings` (the `[схема: …]` lines recognition
   wrote) and `figures` (those placed) — "Contracts". `CLAUDE.md`: rule 3,
   the pipeline, "The document", "Structure"; `BRAND.md`: how a drawing
   looks.

## Measured, 2026-10-01: worse, put to sleep

Record 59's album under v8 became record 60: nine drawings described, eight
cut out and placed. The hand is light, the cut-outs came out faint with the
grid over the strokes, one frame took in the words beside its drawing, and
the arrows' labels were still written out as text. The CEO read the document
as worse than 59's sentences, and production went back to `prompts-v6.md`
within the hour. What a next try needs first — a cleaning that holds for a
light hand, a frame the model draws tighter — is in `FINDINGS.md` → "Drawings
cut out of the page". The code stays: without frames it cuts nothing, and
the lifting of a drawing out of a line of text works for v6 too.

## How it is tried

The deploy changes nothing while production reads `prompts-v6.md` — no
frames, no cut-outs, `[схема: …]` as today — except that a drawing inside a
line moves onto its own. `PROMPT_FILE=prompts-v8.md` on Railway turns it on,
and the album of record 59 sent again is the measurement: the CEO compares
the new record with 59 and with the photographs — every drawing there,
nothing cut off, no text doubled as handwriting, the text read no worse. One
variable takes it back.

## Acceptance criterion

- Record 59's album under v8: its drawings in the document, cut from the
  page, clean on its paper.
- A record under v6 reads as before, a drawing inside a line on a line of
  its own.
- A record found again by its "#word" has its drawings.
- The suite is green.

## Don't do

- No redrawing a sketch from the model's words, and no picture the page did
  not have.
- Don't keep the photograph, or any of it but a drawing's ink.
- No new setting: the prompt file is the switch.

---

# Task 55. What record 59 showed besides its drawings

**Owner: the CEO.** After 54.

## Why

Record 59, the first read in the new look, had three faults that are not its
drawings:

- **No heading at all**, so no numbered section either: «Теорема Больцано -
  Вейерштрасса» and «Понятие компактности» stand as lines of text. Headings
  are the composing stage's; on 59 it either did not run or was refused.
- **«фор · 21:27 (0, 1)» under the title** — what the model put in
  `margin_notes`, which on real pages is mostly not a margin note: the
  notebook's print ("DATE", "BRAUBERG®" — records 38, 40, 41), a doodle
  described ("рисунок: солнце и смайлик в правом верхнем углу"), stray
  letters, once a whole `[схема: …]`. Rule 8 of the prompt asks for the
  lecturer, the date and the page number only, and does not hold.
- **reddit.com among an explanation's sources.** Sources are ranked, never
  filtered (`explain._TIERS`), so a forum stands under an explanation when
  the search found one.

## Do

1. **Why 59 has no headings**, read off its `note_processed` (`composed`,
   `compose_refused`, `compose_drift`) and its `ai_calls`, and fixed where
   the cause lies — the stage, its guard, or what it was given.
2. **A margin line is a name, a date or a page number, or nothing** — a rule
   in code over `margin_notes`, so records already stored are drawn by it
   too.
3. **A forum is not a source**: reddit and its kind are dropped from an
   explanation's sources, and an explanation left with none is dropped by
   the rule that already holds (`explain_unsourced`).
4. `CLAUDE.md` → "Stage three" and "The document".

## Done, 2026-10-01

- **The headings**: record 59's composition was refused for "numbers" —
  reproduced in the production container, the one change was
  "Примеры: 1) …" made into a list. Item markers no longer count as
  numbers wherever they count items; an interval, an answer and a value
  changed are still refused (`FINDINGS.md` → "The composition record 59
  lost").
- **The margin line**: `texts.byline` keeps a name, a date or a page and
  nothing else, for records already stored too.
- **The sources**: forums, social networks and videos are dropped
  (`explain._NOT_SOURCES`).

## Done, 2026-10-02

Record 59's album, read again on 2026-10-02, became record 62: composed,
its headings numbered, nothing under the title. What the CEO's look found
besides, fixed the same day and checked by drawing record 62 again
(`FINDINGS.md` → "Record 62, record 59's album read again"):

- **A tall formula rose over the line above** — reportlab set a
  paragraph's first line a font size below its top; it now sits by its own
  ascent.
- **"~~~"** is a separator, as "---" is.
- **The words under a brace** are set under it (`\underset`), not as an
  index beside it.
- **An aligned chain** alone in a display formula is drawn a row at a
  time; its rows touched.
- **An explanation that judges the record** — «опечатка», «описка», the
  author's mistake — is dropped before its search (`explain_judged`), in a
  stored record too.
- **dxdy.ru and askfilo.com** are no source.

## Accepted, 2026-10-03

The CEO looked at record 62 drawn again after the deploy: in order, and
better — but for the lecture it touched that is not its own, again.

The tail at its end, «A = ((0, 2) ∖ {[неразборчиво]} …», is the next
lecture begun at the bottom of the last page — the CEO, from the
photograph. Record 59 left it out and record 62 carried it in, and nothing
on the page but the author's wavy line says where one lecture ends: it
joins the backlog's item on where a lecture begins and ends, not this task.

## Acceptance criterion

- Record 59's album read again: its headings numbered, nothing under the
  title that is not a name, a date or a page, no forum among the sources.
- The suite is green.

---

# Task 64. One lecture, one record

**Owner: the CEO.** Taken before 56 on 2026-10-03. The prompt is the CPO's
area, open to the CEO; measured on two albums already read.

## Why

A notebook runs on, and an album of a lecture rarely begins and ends where
the lecture does: record 46 opened with the end of the lecture before, and
record 62 closed on the next one begun — "we touched the wrong lecture
again", the CEO, 2026-10-03. Every reading carries the first in and some
the second. Nothing in the code can tell where a lecture begins; the model
sees the page — the date, «Лекция N», the line the author drew — and can
say so.

## Do

1. **Recognition names where a lecture begins** — `prompts-v9.md`, v6 with
   a rule and a key: `lecture_starts`, the first line of every lecture that
   begins on the page, written as the page's `markdown` writes it. Outside
   `markdown`, so neither agreement moves; under v6 the list is empty and
   nothing is cut.
2. **`parse_response` trusts none of it**: a list of strings or nothing.
3. **Only what every run agrees on**: a start the chosen run names is kept
   when every other run read names it too (`lectures.agreed`, in
   `transcribe_consensus`, where the runs are compared); a page read by one
   run has nothing to agree with and is not cut.
4. **Cut at the album's edges only** (`albums._assemble`): on its first page
   what stands above the first start, the lecture before; on its last page
   the last start and everything after it, the lecture after — in an album
   of two pages or more, the first and the last the album's own. Never a
   whole page, never a single photograph, which says nothing of which
   lecture is meant, and nothing in the middle of an album. What is cut is
   not kept; the findings of a cut page are found again on what stays, and
   a title read off the part cut away is taken from what stays.
5. `note_processed` gains `lecture_head_cut` and `lecture_tail_cut`, the
   lines cut — "Contracts". The startup log says whether the prompt marks
   lectures. `CLAUDE.md` → the pipeline, "Structure".

## How it is tried

The deploy changes nothing while production reads `prompts-v6.md`.
`PROMPT_FILE=prompts-v9.md` on Railway turns it on, and two albums sent
again are the measurement: record 46's, which opens on the lecture before,
and record 59's, which closes on the lecture after. One variable takes it
back.

## Acceptance criterion

- Record 46's album without the lecture before, record 59's without the
  lecture after; the rest read no worse — 46's six known places, the
  numbers page by page.
- A lecture that begins at the top of its first page loses nothing.
- The suite is green.

## Don't do

- Don't cut where the runs disagree: a line of the lecture lost is worse
  than a line of another kept.
- Don't move what is cut into another record yet — that waits for the
  subject's base (63).

## Measured, 2026-10-03: asleep

Two pages sent twice — record 65 under v6, record 66 under v9 — the end of
a proof, «Последовательности в метрическом пр-ве», and the next lecture's
first line after the author's wavy line. Under v9 the chosen run named no
start on either page, and nothing was cut. Nothing on these pages tells a
lecture from a section: no date, no «Лекция N»; the title of the next part
is written as every section is, and the next lecture's first line has no
title at all. The CEO knows where the lecture ends from having been there.
A rule that took a new heading for a new lecture would cut sections out of
lectures, which is worse than a line of another kept. The code stays,
asleep without starts; v9 is not production's.

What could tell it, outside the page: **the page photographed twice** — the
last page of one album is often the first of the next, and code can find a
record's first page repeating the end of the subject's record before it.
That needs a subject's records in order: task 63.

---

# Task 56. The bot as a teacher: the idea, why a condition, an example

**Owner: the CEO.** Decided on 2026-10-01; after 55.

## Why

"I don't want to just retell lectures mindlessly" — the CEO, 2026-10-01. The
bot explains at most eight hard places a record, and only what a search
confirms. The CEO's reference, `матан 24.09.2026.pdf`, has sixteen remarks in
fourteen pages, an idea before a step, examples, a summary — and its remarks
are of a kind the bot does not write: what a condition is for and what breaks
without it, where a lemma will be used, the plan of a proof. Record 59 has
four explanations in five pages, and the one that teaches — why the
neighbourhoods of p are intersected, not joined — is the kind a search can
barely confirm. The source rule fits a fact; a teacher's reasoning about one
proof has no page on the web to cite.

## Do

1. **Three elements, each a box of the bot's under its own label**:
   - «Идея» — the plan of a proof in one or two sentences, set before it;
   - «Зачем условие» — what a definition's or a theorem's condition is for,
     and what breaks without it;
   - «Пример» — an example or a counterexample the lecture did not give.
   Written by the explaining stage over the composed text, never the photo.
2. **A fact keeps its source; the bot's reasoning is printed without one,
   under its own label, and checked by code wherever there is something to
   check** — an example's arithmetic by `mathcheck`, a number it states
   against the record or its own working. One that fails a check is dropped
   and counted. Explanations of hard places stay as they are, with sources.
3. **How many**: by section rather than by record — about one element a
   section, the reference's density — measured on an album already read.
4. **The look** — `BRAND.md`: the three labels in the ink of the bot's
   explanation, each where it belongs: an idea before its proof, a
   condition's box under it, an example after what it shows.
5. «Проверь себя» is the second step, once these three have been read.
6. A new prompt file, `prompts-explain-v2.md`, behind `EXPLAIN_PROMPT_FILE`;
   `CLAUDE.md` → "Stage three" and "The document".

## Acceptance criterion

- An album already read — record 59's, or 45's — under v2: the three
  elements where they belong, none saying what the record or a check
  contradicts; the CEO compares it with v1's document.
- What a record costs before and after, in `FINDINGS.md` → "What a record
  costs".
- The suite is green.

## Don't do

- Nothing woven into the author's text, and nothing about how the page was
  read: the reference's «В рукописи стоит …» stays out (2026-09-25).
- Don't correct the author.
- No flashcards, no spaced repetition.

---

# Task 60. A board photographed

**Owner: the CEO.** After 47. The prompt and the frame check are the CPO's
area, open to the CEO; measured on real boards before production.

## Why

A lecture is written on the board as much as in a notebook, and a student
who did not write photographs the board. The bot is built for a notebook
page: `photoguard` measures a page's paper and its lines of handwriting,
and the recognition prompt reads «страница студенческого конспекта». A
board — chalk or marker, at an angle, across the room, with glare — is
another picture, and the frame check would most likely refuse it.

## Do

1. **Evidence first**: the board photographs of one or two real lectures,
   sent as the bot is today — what `photoguard` measures on them and why it
   refuses, and how recognition reads them — written in `FINDINGS.md`.
2. **Which is a board**: told apart by the frame check's own measurements
   if they separate a board from a page cleanly, by the sender otherwise —
   decided on the evidence.
3. **A board's own frame check**, never a bypass: a board shot that cannot
   be read — too far, glare across the writing, blurred — is still refused
   before the model, with thresholds set on the evidence.
4. **A board's own reading**: the same rules as a page — what is written,
   nothing added, `[неразборчиво]` where it cannot be read — with what a
   board adds: columns, something wiped half off, the lecturer's hand. A
   new prompt file, measured on the boards before production.
5. An album may hold board and notebook pages together; it is one record.
6. `CLAUDE.md` → the pipeline and `photoguard`'s rules.

## Acceptance criterion

- One real lecture's board photographs become a record the CEO checks
  against the photographs.
- A board shot that cannot be read is refused before the model.
- A notebook album already read reads as before.
- The suite is green.

## Don't do

- Don't loosen the notebook's frame check to let a board through.
- No retelling of a board that cannot be read.

---

# Task 61. A lecture recorded

**Owner: the CEO.** After 60. The model calls, their prompts and guards,
and the limits are the CPO's area, open to the CEO.

## Why

Not every lecture is written down, and many are recorded on a phone. A
recording holds what the notebook drops — the lecturer's explanations, the
examples said aloud, why a step is taken. On 2026-10-02 the CEO decided
the bot makes a record of it, and that the record is the bot's notes,
marked as such: from speech the bot condenses rather than transcribes, and
"marked is the whole licence to add".

## Do

1. **What comes in**: an audio file or a voice message with its "#word" in
   the caption — in a group only with it, like a page. A bot can download
   20 MB from Telegram: a voice message of an hour or more fits, a phone
   recorder's file of a lecture usually does not. A file too large is
   answered with how to send it, never dropped in silence; a route for
   large files is 62's.
2. **Limits before the call** (rule 6): a recording's cost is known from
   its length — Gemini counts 32 tokens a second, 1 920 a minute, about
   173 000 for a lecture of ninety minutes — and it is checked against the
   quota and the day's cap before anything is sent.
3. **Two calls, as for a page**: what was said, written down literally,
   `[неразборчиво]` where it cannot be heard; then the notes, written over
   that text and never over the sound — headings, definitions, formulas.
   The text of what was said is kept beside the record; the recording
   never is (rule 3).
4. **Checked by code against what was said**: the notes state no number
   the text does not hold — the guard the summary has.
5. **Marked as the bot's**: the document says on its first page that the
   bot made these notes from a recording, in a box of the bot's under a
   label in `texts.py`.
6. **Formulas**: from what was said; when photographs of the board or a
   notebook come with the recording, the formulas are theirs and the
   recording explains them — the second step of this task.
7. Whether a recording is heard once or three times — three texts give the
   agreement, at three times the price — is measured here. Its cost an
   hour is written in `FINDINGS.md`.
8. `CLAUDE.md` → rule 3, the pipeline, "The document"; `PLAN.md` →
   "Contracts".

## Acceptance criterion

- A recorded lecture of the CEO's course comes back as a document marked
  as the bot's, every number of it in what was said; the CEO checks it
  against the recording.
- A file too large gets an answer that says how to send it.
- What an hour costs is written down.
- The suite is green.

## Don't do

- Don't present the bot's notes as the author's.
- Don't keep the recording.

---

# Task 62. A lecture filmed

**Owner: the CEO.** After 61.

## Why

A film of a lecture holds its board and its speech at once. Sent whole to
the model it costs the most, and the board is legible only on sharp
stills.

## Do

1. **A film is taken apart by code**: its sound goes by 61's path, and
   stills of the board — one each time the board changes — by 60's. The
   record is the board read, with the notes from what was said marked as
   in 61.
2. **Large files**: a film of a lecture rarely fits the 20 MB a bot can
   download. The route is decided here — a link to the file, or Telegram's
   own Bot API server, which raises the limit to 2 GB but is a second
   service.
3. `ffmpeg`, to cut sound and stills, is the explicit need for the
   dependency.

## Acceptance criterion

- A filmed lecture becomes one record: the board read, the speech
  condensed and marked; what it costs is written down.
- The suite is green.

## Don't do

- Don't send the whole film to the model when its parts will do.
- Don't keep the film.

---

# Task 65. A page read whole

**Owner: the CEO.** Taken on 2026-10-04, from record 67. Recognition is the
CPO's area, open to the CEO since 2026-10-01.

## Why

The CEO sent one photograph twice, and the second document was "much better
and fuller". It was the reading: record 67 holds the top half of the page,
record 68 the whole of it, the proof under the line included. Three runs
vote by agreement, and two that stop short at one place agree with each
other perfectly: the third, which read further, is outvoted. Over the 138
pages read since 2026-09-23 that happened twice; the five times one run
stopped short alone, the other two outvoted it, as they should.
`FINDINGS.md` → "Record 67, half a page".

## Do

1. **A block the chosen run did not read**: what another run has and the
   chosen lacks, where the chosen has nothing in its stead — a dozen words
   or more, merge.py's alignment, the page's edges included.
2. **Two more runs settle it**: a block two runs read is on the page, and
   the runs that carry it are the ones compared — the agreement, the
   numbers, the chosen reading. A block one run alone read stays out, and
   the first comparison stands: invention does not write the same block
   twice.
3. The more runs are the page's reading, like a retry: the limits were
   checked before the page; every call is in `ai_calls`. The album ceiling
   counts them.
4. `note_processed` counts `runs_added` and `read_further`; the consensus
   log line prints the words each run read.
5. `CLAUDE.md` → "What works", "Concurrency ceilings".

## Acceptance criterion

- Records 67's and 68's texts standing for the runs: two short and one
  whole, with the two more whole, give the page whole; with the two more
  short, the half stays; three whole ask for nothing.
- A page the CEO sends again comes back whole, or its log line says the
  three runs stopped at one place — which this does not catch.
- The suite is green.

## Don't do

- Don't take a block only one run read.
- Don't ask for more runs on every page: only where the runs disagree on
  how much of it there is.

---

# Task 63. The subject's base: every lecture in its place

**Owner: the CEO.** Taken before 60 on 2026-10-04 — it needs no material
the CEO does not have — and before the app. Its schema and migration are
the CPO's area, open to the CEO, the migration named to the CPO before it
is pushed.

## Why

A subject today is a word on each record, `Note.tag`, and a record's date
is the day it was sent. A course is more: its lectures in the order they
were given, the ones given before the group found the bot, what the
teacher handed out. The library and the exam page (58, 59) are views of
it; built on tags alone, they would be built twice.

And a lecture is more than one notebook. The CEO, 2026-10-04: "каждый
досланный материал по лекции (если одну и ту же прислали 2 и более
человека) объединялся и при необходимости дополнял блок по этой теме" —
what a second notebook has and the first lacks goes into the lecture, at
its place.

## Do

1. **A chat's subject as a row of its own** — its "#word" and its chat —
   which records belong to; today's tags become such rows.
2. **A lecture as a row of its own**: one class on one day, in its
   subject, every material of it pointing at it — the notebooks now; the
   board (60), the recording (61), the film (62) and the teacher's files
   (48) as they come.
3. **A lecture's date** — the day it was given, not sent: from the
   caption ("#матан 12.09"), else from the margin when it names one date
   and only one, else the day the pages were sent. The course is ordered
   by it, and the head of the document carries it.
4. **One lecture from several notebooks**, decided by code, no model asked:
   - **The same lecture**: the same subject, a day within a week, and at
     least half of one text found in the other. Measured on 2026-10-04 on
     the 66 records in production: the same pages read again agree at
     0.70–1.00, different lectures of one course at 0.40 at most. Unsure,
     it is a lecture of its own — two documents are better than one mixed.
   - **The base is the fullest notebook**: the most text read, a place it
     could not read counting against it.
   - **What another notebook adds goes in where the base has nothing in
     its stead**, aligned word by word: a line the base wrote its own way
     is a variant and is not set in — the bot never chooses between two
     readings and says nothing about them, the base stays. Nor is what the
     base already has elsewhere, a drawing's description, a heading with
     nothing under it, or what the other notebook carries past a line
     across the page at its first or last edge — the lecture before or the
     next one begun. Each passage stands at its place under the label «Из
     другого конспекта», the CEO's words of 2026-10-04, as its author wrote
     it.
   - **The group gets the lecture's updated document**, the CEO's decision
     of 2026-10-04, and a line saying it is a lecture already there.
   - **A notebook that only adds is not explained**: no explaining call
     for a record that will not be the base.
5. **Earlier lectures added in bulk**: albums and files of old notes with
   their "#word", the date in the caption where the page has none, each
   record set at its date.
6. **One lecture, one record, by the page photographed twice** (task 64's
   finding): where a record's first page repeats the end of the subject's
   record before it — the same notebook page sent with both albums — the
   repeat is cut by code, no model asked; and the end of the record before,
   which was the next lecture begun, is cut from it. Cut only where the
   code is sure — the album before was sent before the next lecture was
   given, or the author's line stands between the two on that page; a line
   of another lecture kept is better than a line of this one lost.
7. **The teacher's materials** (48) belong to the subject; 52's course
   document reads the subject in the order the lectures were given.
8. `CLAUDE.md` → "The corpus", "The document"; `BRAND.md` → the passage
   from another notebook; `PLAN.md` → "Contracts".

## Measured before it was built, 2026-10-04

On the records in production, which hold the same albums read many times:
records 59, 60 and 62–66 are one album on the Bolzano–Weierstrass theorem,
read whole or in part seven times; 46–49 one practice, 50–53 one lecture;
the group's two records, 54 and 61, one page sent twice three days apart.

- **Which text is one lecture**: the share of one text's five-letter runs
  found in the other, the larger of the two ways, a drawing's description
  left out — 0.70 to 1.00 on eighteen pairs of one album read again, 0.02 to
  0.40 on fifteen pairs of different lectures. 0.5 separates them; two
  notebooks of one lecture were not there to measure. Records 45 and 46,
  taken for two lectures, came out at 0.83: one practice of 25.09, its
  album sent twice.
- **What another notebook adds, by paragraph, failed both ways**: a reading
  breaks a page into paragraphs its own way, so a paragraph of one stood
  against two of the other, and a line read two ways looked missing from
  both. Aligned word by word, a passage set in only where the base has no
  line of its own: what still went in on the eighteen pairs was a line of
  record 64 read another way — «покажем радиус [неразборчиво] носителя
  шарик» against 62's «покажем рецепт как найти шарик», a variant the base
  hid inside a long paragraph, so a base's own line is judged by the line —
  and 62's «A = ((0, 2) ∖ …» after the author's wavy line at its end, the
  next lecture's first line, which 59 rightly lacks. With both rules, no
  passage on the eighteen pairs.
- **What it gives back**: five chunks cut from one reading at random places,
  sixty times over ten pairs, came back whole from the other reading 33
  times and in part 13. What does not come back is what the base still has
  elsewhere in other words, or what a variant beside the cut hides.

## Acceptance criterion

- A subject's lectures, the earlier ones included, are listed in the order
  they were given, and a "#word" finds them as it does today.
- One album sent again joins its lecture and adds nothing the lecture's
  document does not have; a page of another lecture does not join it.
- Two notebooks of one lecture, the CEO's and a classmate's, become one
  document: the CEO checks against both that what one lacks stands at its
  place from the other, and nothing twice.
- The suite is green.

## Don't do

- No new way into the corpus from the chat beyond the "#word".
- No export.
- Don't let a model merge notebooks: the text of a lecture is what its
  authors wrote.

---

# Task 57. The app's frame: a Mini App the bot opens

**Owner: the CEO.** After 63. Its queries are the CPO's area, open to the
CEO since 2026-10-01.

## Why

The concept of 2026-10-02 puts a group's studying in an app beside the bot.
Before a library or an exam page can be in it, the app has to exist: open
from the bot, know who is looking without a password, and show that person
what the bot would show them and nothing more. Everything after it is a
screen in this frame.

## Do

1. **Served by the bot's own service.** FastAPI serves the app's files and
   a JSON API under a path of its own, on the Railway domain the webhook
   already has, HTTPS included: no second service. The app's address is
   registered in BotFather — the bot's Mini App and its menu button — by
   whoever holds the bot.
2. **Signed in by Telegram.** Every API request carries the Mini App's
   `initData`; the server checks its signature with the bot's token and its
   age, and takes the person's Telegram id from it. An id the page sends is
   not an identity. No account, password or session of our own.
3. **The bot's ownership, unchanged** (`corpus._owned`): a person sees
   their own records that belong to no group, and the records of every
   group chat they are a member of — asked of Telegram (`getChatMember`)
   when the app opens, never inferred from who brought pages.
4. **Opened from the bot**: the menu button in a private chat; a button
   under a record delivered in a private chat; in a group, where Telegram
   allows no Mini App button, a link to the app (`t.me/<bot>/<app>`) — the
   username from `bot.me()`, the labels in `texts.py`. The chat stays plain
   text otherwise.
5. **The first screen**: the person's chats, each with its subjects and how
   many records — what the library (58) opens into. The look is
   `BRAND.md`'s; where the guide does not decide, Telegram's light or dark
   theme.
6. **Events from the first day**: `app_opened`, with where it was opened
   from and the group's id when there is one.
7. **No build step to start with**: HTML, CSS and JavaScript modules served
   as they are. The first version's screens are lists, a search field and a
   reader; a framework is a dependency to argue for when a screen needs it,
   and whether the stores' app wraps this one or is written anew is decided
   with the stores.
8. `CLAUDE.md` → "Stack", "Structure", the startup log; `PLAN.md` →
   "Contracts", the app's events.

## Acceptance criterion

- The menu button opens the app on a phone, and it shows the person's
  chats and their subjects.
- A member of a group sees it; a person who is not sees nothing of it, the
  group's id in hand or not.
- A request with forged or stale `initData` is refused.
- `events` holds `app_opened` with where it came from.
- The suite is green.

## Don't do

- No account, password or registration of our own.
- No second service, no Docker, no frontend build before a screen needs one.
- Nothing the bot would not show that person.

---

# Task 58. The library

**Owner: the CEO.** After 57.

## Why

A group's records reach the chat one PDF at a time and sink under the
messages after them; a "#word" brings one back to whoever knows the word.
The library is where a student finds the lecture they missed a month ago:
every record of their chats, by subject, searched, read on a phone.

## Do

1. **A chat's records by subject** (`Note.tag`), newest first, each with its
   date, title and pages; records with no subject under a heading of their
   own; a subject's topics (`note_topics`) as filters.
2. **Search** over subjects, topics and the records' text — words, not a
   model.
3. **A record read on a phone**: its blocks as `pdf.blocks()` parses them,
   set as HTML in `BRAND.md`'s look, formulas by KaTeX — real LaTeX rather
   than mathtext's subset; the bot's boxes where the PDF has them — the
   findings, the explanations with their sources, «Суть»; the PDF one tap
   away. Drawn from what is stored, like the PDF.
4. **Events**: `app_record_opened`, and `app_search` with whether it found
   anything — never the words.
5. `CLAUDE.md` → "The document": a record's second presentation, one
   contract with `pdf.blocks()`; "The corpus": a second way in beside the
   "#word".

## Acceptance criterion

- A group's member finds a record by its subject, by a topic and by a word
  in it, and reads it on a phone with its formulas and boxes.
- A formula the PDF draws, the app draws.
- A chat the person is not in never shows, in a list or a search.
- The suite is green.

## Don't do

- No editing a record in the app.
- No export, download-all or archive — `CLAUDE.md` → "What NOT to do".
- Nothing about how a page was read, the document's rule.

---

# Task 59. Exam preparation

**Owner: the CEO.** After 58. If theorems are marked by the composing
stage, that rule is a prompt change — the CPO's area, open to the CEO —
measured on an album already read.

## Why

Before an exam a student wants the course's definitions and theorems, not
twenty lectures. The pipeline already marks a definition (`### Определение`,
the amber line) and a main formula (framed and numbered); a theorem it does
not mark yet.

## Do

1. **A subject's page**: every definition and theorem in its records,
   grouped by topic, each with its record's date and opening the record at
   its place in the library.
2. **From the markup, not from a model**: definitions from
   `### Определение`; theorems, lemmas and corollaries from a heading the
   composing stage writes for them as it does for a definition
   (`### Теорема`), or from code over the headings that already name one —
   chosen at the task's start on the records stored; the main formulas as
   the document numbers them. No model call: nothing the author did not
   write, and no cost a use.
3. **Events**: `app_exam_opened`, with the subject.
4. `CLAUDE.md` → the contract between the prompts and `pdf.py`, if the
   composing stage gains a theorem's heading.

## Acceptance criterion

- Record 59's subject: every definition and theorem its records hold, each
  opening its place.
- Nothing on the page that the records do not say.
- The suite is green.

## Don't do

- No summary, rewording or question written by a model — a later tool,
  marked as the bot's when it comes.
- No spaced repetition yet: it is built on this page's material once the
  page is used.

---

# Task 66. A group's records in a topic of their own

**Owner: the CEO.** Specified on 2026-10-04, not yet scheduled. What the bot
does in a chat is the CEO's; the column it needs is the CPO's schema, open to
the CEO, its migration named to the CPO before the push.

## Why

The first big group, J3115, added the bot on 2026-10-04, and it is divided
into topics — Telegram's forum, several chats in one group. A record goes
today wherever its pages were posted, so a course's records would scatter
across its topics among everything else said there. The CEO: one topic,
«Конспекты», holds every record of the group.

## Do

1. **The topic**: in a group with topics (`is_forum`), the bot keeps the one
   it posts records to (`groups.records_topic_id`) and makes «Конспекты»
   itself (`createForumTopic`). That needs the right to manage topics, so in
   such a group the bot is an admin with it, and says so once when it is
   not, as the welcome does for privacy mode. The Bot API cannot list a
   chat's topics: a «Конспекты» made before the bot came is found from its
   creation notice if the bot saw it, or named by an admin from inside it —
   decided when built.
2. **Every record of the group goes there**, whichever topic its pages came
   from; where the pages were posted, the bot answers one line pointing at
   the record.
3. **A "#word" search**: whether the document found goes to «Конспекты» or
   to the topic the search was typed in — the CEO's to decide when built.
4. **The topic deleted or closed by the chat**: the bot makes it again, or
   answers where the pages came from — decided when built.
5. A group without topics works as today.
6. `CLAUDE.md` → "A group chat"; `PLAN.md` → "Contracts".

## Acceptance criterion

- In a group with topics, a page sent with its "#word" in any topic comes
  back as a record in «Конспекты», with one line where it was posted.
- A group without topics works as before.
- The suite is green.

## Don't do

- Nothing in «Конспекты» but the records and what the bot says of them.
- No topic beyond that one.

---

# Task 67. Records kept for the next cohorts

**Owner: the CEO.** Specified on 2026-10-04 as a mechanism to think through
before anything is built: what the bot asks, when and whom, what it keeps,
and how a later cohort reaches the records. The schema is the CPO's, open to
the CEO.

## Why

A course is taught every year, and next year's students of the same
programme study the same subjects. A group's records are worth to them what
they were to the group — when the bot knows whose course they are. The CEO,
2026-10-04: the bot asks — «ВУЗ, курс, направление».

## To think through

1. **Whom and when the bot asks.** A group is never asked today
   (`CLAUDE.md` → "A group chat"): a course chat is mostly memes. The person
   who added the bot, in a private chat right after it joined — Telegram
   says who did — or once in the group, with buttons.
2. **What it keeps**: the university, the programme, the year of study and
   the year it was asked in — so the third year of 2026 is the cohort that
   began in 2024, which next year's third year is not.
3. **Words typed differently**: «МГУ» and «МГУ им. Ломоносова», «ПМИ» and
   «Прикладная математика и информатика» — a list to choose from, or free
   text matched later.
4. **How a later cohort reaches the records**: the same programme at the
   same university, the subjects it shares — in the app (phase F), with the
   earlier group's consent. That is sharing, which "What NOT to do" holds
   until the app's first version is used: the rule changes, with its date,
   before this is built.
5. **A record of an earlier cohort in a document**: marked as such — the
   lecture of 2025, not this year's.

## Acceptance criterion

- The mechanism agreed with the CEO and written here: the questions, when
  and to whom, the columns, how a later cohort finds the records, and the
  consent.

## Don't do

- No sharing before "What NOT to do" changes.
- No question in a group chat before the CEO decides how it is asked.

---

# Task 68. Pages in their order

**Owner: the CEO.** Specified on 2026-10-04, not yet scheduled; to be
measured before it is built. What the chat is told is the CEO's; the order a
record is assembled in is the album pipeline's, the CPO's, open to the CEO.

## Why

The CEO, 2026-10-04: an album sent with its pages out of order. The record
is assembled in the order the photos came (`message_id`), so a proof can
stand before its theorem, and a sentence cut by a page's edge continues
three pages on. Telegram gives an album's order as the sender picked the
photos and nothing more: a photo sent as a photo loses the time it was
taken.

## To think through, then do

1. **What tells the order, by code** — the model is not asked to order
   pages:
   - the page's number in its margin, as recognition reads it into
     `margin_notes` (`texts.byline` already picks page numbers out of them);
   - a sentence cut at one page's foot and finished at the top of another
     (`albums._continues` recognises such a seam already);
   - numbering that runs across pages — «1)», «2)», a theorem's or a
     section's number, the author's own numbers of formulas;
   - where a lecture begins — a date, «Лекция N» — on what should be the
     first page.
2. **Reordered only when the evidence is one-sided**: page numbers that make
   one sequence, or seams that chain the pages one way. Contradicting
   evidence, or none, and the sender's order stands: a wrong reordering is
   worse than the order the photos came in.
3. **Where**: after recognition, when each page's text is known, and before
   assembly (`albums._assemble`) — so seams, the lecture's edges (task 64)
   and the page photographed twice (task 63) all see the pages in order.
4. **The bot puts the pages in order by itself**, asking nobody — the
   CEO, 2026-10-04: «самим», «бот решает». Whether a line under the document says so —
   «страницы 3 и 2 стояли не по порядку — поставил по номерам на полях» —
   or nothing does is the CEO's to settle when it is built.
5. **Measured first**: albums already read, their pages put out of order on
   purpose, and the share each signal orders back right — and how often a
   real album's pages carry their numbers at all.

## Acceptance criterion

- An album of the CEO's sent out of order on purpose comes back in order
  where its pages say so, and in the order sent where they do not.
- An album sent in order never comes back reordered.
- The suite is green.

## Don't do

- Don't let a model decide the order.
- Don't reorder on one weak sign.

---

# Task 69. What record 74 showed

**Owner: the CEO.** Taken on 2026-10-06, from record 74, a lecture of
discrete mathematics on trees: «ошибки в формулах, странные сокращения,
какие то графики». The composing prompt is the CPO's area, open to the CEO
since 2026-10-01.

## Why

Record 74 went out on 2026-10-05 with:

- **Formulas spaced apart**: the in-degree as «ρ ⁻ (v)», the edge swapped
  out of a spanning tree as «(i *, j *)», Pascal's «array [1. . p]»; and the
  Russian words inside a formula — «∃! узел», «∀ узел достижим из корня» —
  in Computer Modern, a serif, in a line of Onest.
- **Trees drawn as tangles**: every `[граф: …]` goes round a circle, and a
  binary tree of seven vertices came out as six crossing chords; the
  ordered tree and its binary form after it the same.
- **«[зачёркнуто] и [зачёркнуто]»** in the middle of a line of a proof.
- **A page holding one word**, «старого.», the last line of the last
  paragraph.
- **The author's shorthand**: «мн-во», «св-вами», «сод-ся», «непересек.»,
  «кр. остов», «Сл. шаг ] на этом шаге доб …», where «]» is «пусть».
  Recognition writes the page as it stands and the composer keeps every
  word, so the document reads like the notebook, and a student who missed
  the lecture decodes it.
- **Lines cut short** — «гамильтонов цик-», «Центральная вершина (вершина
  ec(v) =» — and an edge b–d in the ordered tree that makes it a graph with
  a cycle: the reading's or the author's, which only the photographs tell.

## Do

1. **Formulas**: an operator alone in an index braced, a range «1..p» set in
   `\text`, the Russian words between the parts of a formula in a line set
   as text. `pdf.py`.
2. **A tree that branches is drawn as a tree** — its root on top, children
   under their parent in the order read; a path and a graph with a cycle
   stay on the circle. `pdf.py`.
3. **«[зачёркнуто]» is not printed**, nor a line that held nothing else.
4. **The last line of a paragraph never goes over a page alone.**
5. **The author's shorthand spelled out by the composer** — rule 10 of
   `prompts-compose-v4.md`, the CEO's decision of 2026-10-06: an ordinary
   word written short is written whole, in the form the phrase needs; «]»
   is «Пусть»; a ∀ or ∃ standing for a word in a sentence is the word. Left
   as written: the abbreviations the lecture itself introduces (ОД, БД,
   УД), «т.е.» and «т.к.», formulas, numbers, and whatever the composer is
   not sure of. The guards stand as they are — the numbers, the
   «[неразборчиво]», the length. Measured on record 74's album sent again;
   production switches `COMPOSE_PROMPT_FILE` after the CEO's look.
6. **The lines cut short and the extra edge** compared with the album's
   photographs: the reading's, or the author's.
7. `CLAUDE.md` → "Stage two" and "The document"; `BRAND.md` v1.5;
   `FINDINGS.md` → "Record 74, a lecture on trees".

## Closed, 2026-10-06

On the CEO's word, the day it shipped: the document's faults fixed and
deployed (`58dfca6`), stored records drawn by them too; `prompts-compose-v4.md`
shipped, its switch on production's `COMPOSE_PROMPT_FILE` the CEO's, and the
startup log says which composer runs. What was not done: the shorthand under
v4 is not measured on record 74's album, and the lines cut short and the
extra edge were not compared with the photographs — task 70's reviews are
where such faults are to be found from now on.

## Acceptance criterion

- Record 74 drawn again, as a "#word" brings it back after the deploy: «ρ⁻(v)»
  and «(i*, j*)» set close, «[1..p]» whole, the words of its formulas in the
  text's face, its binary trees as trees, no «[зачёркнуто]», no page of one
  word.
- Record 74's album sent again under v4: the shorthand spelled out and
  nothing else reworded, its numbers and «[неразборчиво]» those of the
  reading; the CEO reads it against the photographs.
- The suite is green.

## Don't do

- Don't spell out what the lecture defines or anything inside a formula,
  and don't write a number as a word.
- Don't straighten a graph with a cycle into a tree: a tree with an edge
  too many is a reading to compare with the photograph, not a picture to
  correct.
- Mind task 63 while v3 and v4 both stand in the corpus: two notebooks of
  one lecture are matched by the words they share (`merge.same_lecture`),
  and one composed under v4 shares fewer with one composed under v3.

---

# Task 70. A record rated, and where its error is

**Owner: the CEO.** Taken on 2026-10-06. What the chat says is the CEO's;
the table is a migration, `015_feedback`, in the CPO's area, open to the
CEO and named to the CPO before it is pushed.

## Why

The CEO, 2026-10-06: two buttons under the document, «хорошо» or «плохо»,
and a place to write — «чтобы могли быстрее собирать качество работы», and
«чтобы мы могли реально видеть, где ошибка в конспекте». Every fault fixed
so far was found by the CEO reading a record against its photographs, one
record at a time (55, 69); the groups read every record and say nothing,
and the event table cannot tell a record that was read from one that was
wrong.

## Do

1. **Two buttons under every document the bot sends** — «Хорошо» and
   «Плохо», on the PDF itself, or on the last message of the plain text it
   falls back to; a record a "#word" brings back carries them too. Words,
   no emoji: the chat stays plain text. A button names the record the
   document is drawn from (`rate:good:<id>`, `rate:bad:<id>`).
2. **A press is stored**: a row of `feedback` — the record, who, the group,
   the rating, the reader's words, the chat and the bot's question — one a
   person a record: a second press changes the rating. `note_rated`
   ("Contracts"). «Хорошо» is thanked in the button's own notice and adds
   nothing to the chat.
3. **«Плохо» asks where**: the bot answers in the chat «что не так в
   конспекте №N?» — in a group naming the reader, with Telegram's reply
   field opened for them alone (`ForceReply`, selective) — and asks for the
   page, the line or the formula and what it should be.
4. **The answer is a reply to that question**, found by its message in the
   `feedback` rows, nothing kept in the process: its text — or a photo's
   caption, a screenshot of the error — goes into the row, and the bot
   thanks for it. `note_feedback` ("Contracts").
5. **Straight to the CEO**: `FEEDBACK_CHAT_ID`, unset by default — every
   «Плохо» and every answer is sent there at once: which record, which
   chat, who, and the document itself copied, then the reader's message
   copied. A failure to send there is logged and never reaches the reader.
6. **What lets it through**: callback queries get a session like messages
   (`DbSessionMiddleware`, the group read off the message the button is
   on); in a group `middlewares.heard` lets through a text that replies to
   the bot's own message, and a reply that answers no question of the
   bot's gets no answer. The feedback router stands before the corpus's: a
   reply to the bot's question is feedback whatever it says.
7. `CLAUDE.md` → the middleware, "A group chat", the routers, "Environment
   variables", the revision ids; a section on feedback.

## Closed, 2026-10-07

On the CEO's word, the day after it shipped (`102e8d5`). Whether the groups
use the buttons is read off `note_rated` and `note_feedback`, and what they
say off `feedback`.

## Acceptance criterion

- In a private chat and in a group: a record's «Хорошо» and «Плохо» are
  stored, one a person, changed by a second press; «Плохо» asks, and the
  reply is stored with the row and sent to `FEEDBACK_CHAT_ID` with the
  document.
- A restart between the question and the reply loses nothing.
- The suite is green.

## Don't do

- No form, no web page, no score shown to the group: two buttons and a
  reply.
- Don't keep the question in the process: the row is the state.
- Don't ask «что не так» after «Хорошо».

---

# Task 71. A lecture dated by a day it could not have been given on

**Owner: the CEO.** Taken on 2026-10-06, from record 79. The lectures already
filed are put right by a data migration, `016_lecture_days` — the CPO's
area, open to the CEO, named to the CPO before it is pushed.

## Why

The CEO, 2026-10-06: «бот маркирует все 2025 годом». Record 79, sent on 6
October 2026, came with «10 ноября» in its margin, and its document is
headed 10.11.2025. `subjects.day_of` reads a margin's day without a year as
the latest such day not after the day the pages came — in January "12.12"
is last December's — and a day in November is last year's by that rule. A
lecture cannot have been given after its notebook was photographed: a
margin's day after it is a misreading, the notebook's print or a day the
author noted for something else, and the rule turned it into a date a year
back. The day stands in the head of every page of the document, and two
notebooks are one lecture only within a week of each other.

## Do

1. **A margin's day after the day the pages came** — a day's grace for the
   timezone — is not the lecture's: the lecture is dated by the day it was
   sent, as with no date at all. A margin's day before it is taken as now,
   in the year written or the year the pages came. The caption keeps its
   rule: the sender typed it, and a notebook of last year is dated there —
   «#матан 10.11.2025».
2. **The lectures already filed** by the old rule are read again from their
   notebooks' margins (`016_lecture_days`); one no margin dates any more
   takes the day its first notebook was sent.
3. `CLAUDE.md` → "A subject, its lectures, and one lecture from several
   notebooks"; `FINDINGS.md`.

## Acceptance criterion

- Record 79's document headed by the day it was sent, 06.10.2026.
- A margin's day before the day sent dates a lecture as before, and so does
  a caption's.
- The migration run on a PostgreSQL holding a lecture of each kind.
- The suite is green.

## Don't do

- Don't guess the year of a day the page cannot have meant.

---

# Task 72. A group's week: who sent its records, who rated them

**Owner: the CEO.** Taken on 2026-10-06. What the chat says is the CEO's;
two columns, in a migration `017_rating`, are the CPO's area, open to the
CEO and named to the CPO before it is pushed.

## Why

The CEO, 2026-10-06: «рейтинг, кто сколько конспектов отправил и сколько
было дано обратной связи для группы». Task 70 put «Хорошо» and «Плохо»
under every document so that the groups say where a record is wrong; a
group that sees who brought its records, and who read them closely enough
to say, has a reason to do both. The project's question is whether a group
uses the bot weekly, and the week is what is counted. `/stats` had been
called once by 2026-09-23: what a group is not shown it does not see, so the
week is also summed up in the chat, unasked. Whether either moves anything
is read off the tables two weeks on: `stats_viewed` in groups, and a group's
`feedback` rows a week before the first `rating_posted` and a week after.

## Do

1. **Who sent a record.** `notes.sender_id`: whose message carried the
   pages, when that is not who called the bot on them — a reply's "#матан"
   under a classmate's photographs (task 40). The record still costs the
   one who replied (`user_id`), and counts for the one who photographed.
   `NULL` is the record's `user_id`, so no other path writes anything new,
   and the records called on before the column count for whoever replied:
   who photographed them was not kept. The sender of a single photograph
   may be somebody the bot has never seen, and is registered as an album's
   sender already is when its pages arrive — the middleware's registration
   taken out of its class for it. A bot, an anonymous admin or a channel as
   the sender counts for whoever replied. The middleware keeps a person's
   username and name current, as it keeps a group's title: they are now
   shown to the group.
2. **What is counted** — for one group, in a week from Monday 00:00 UTC, as
   every day here is counted:
   - a person's records: the group's records made that week, by
     `coalesce(sender_id, user_id)`;
   - a person's отзывы: their `feedback` rows in the group created that
     week — one a person a record, so a second press counts nothing;
   - ordered by records, then by отзывы; ten people at most, then «и ещё
     N». A person is shown by their username in Telegram, the CEO's choice,
     without the @ that would notify them every time; by their first name
     when they have no username.
3. **`/stats` in a group is the group's week**; in a private chat it stays
   as it is:

       J3115 · эта неделя
       14 конспектов, 9 отзывов

       1. anna_k — 6 конспектов, 3 отзыва
       2. petrov_g — 5 конспектов, 4 отзыва
       3. Иван — 3 конспекта
       4. masha_s — 2 отзыва

       За всё время: 41 конспект, 23 отзыва

   A week with nothing in it yet says so above the line for all time; a
   group with no record and no отзыв gets `STATS_EMPTY`. `stats_viewed` as
   before.
4. **The week summed up in the chat, unasked.** The first record a group
   makes in a new week, on any capture path, is followed — after the record
   and all that is said of it — by the week before: its dates, its two
   totals, its people as in `/stats`, and a line saying what an отзыв is,
   «Хорошо» or «Плохо» under a record. No scheduler: the week is claimed on
   the group's row, `groups.rating_week`, the Monday of the week the last
   summary went out in, by one conditional update — of two records at once,
   one wins. A week before with nothing in it is claimed and says nothing;
   a week followed by a silent one is never summed up, since a summary is of
   the week just ended. A record a "#word" brings back is not a new one and
   brings none. `rating_posted` ("Contracts").
5. **Nothing of it costs the record.** The summary comes after the record is
   delivered, in a savepoint: a query that fails or a chat that cannot be
   written to is a warning in the log, the record and its events stay, and
   the week stays claimed.
6. **The limits do not depend on it** (the CEO, 2026-10-06). A group's day
   is task 41's, and `/stats` shows what is left of it once 41 is built —
   task 41, item 4.
7. **A person's day is 12 pages, not 30** — the CEO's decision of the same
   day. `DAILY_PAGES_PER_USER`'s default; the variable on Railway stands
   above it — 30 since 2026-09-25 — and is the CEO's to set. The startup
   log says the day's limits, so what production runs is read off it. In a
   group the pages are charged to whoever brought them to the bot, so the
   one who calls it on the classmates' photographs reaches 12 first.
8. `CLAUDE.md` → "The corpus", a section on a group's week; "Structure"; the
   revision ids; "Environment variables" and the startup log. "What NOT to
   do" is narrowed in this task's `plan:` commit.

## Closed, 2026-10-07

On the CEO's word, the day after it shipped (`81cf601`). Whether it moves
anything is still read two weeks on, as "Why" says. The same day the CEO
asked for the week's summary on Saturday, which is task 73.

## Acceptance criterion

- In a group, `/stats` lists the week's people as above; in a private chat
  it is unchanged.
- A record called on by a reply counts for whoever sent the photographs, and
  the reply's author is still charged.
- A group's first record of a week is followed by the summary of the week
  before, once — two records at once included; the week's second record
  brings none.
- A summary that fails leaves the record and its events in place.
- The startup log says a person's day is 12 pages.
- `017_rating` run on a PostgreSQL at `016_lecture_days`.
- The suite is green.

## Don't do

- No points, no medals, no emoji: two numbers a person, the chat plain text.
- Never across groups: a group sees its own people, and nothing compares
  groups.
- Don't tie a limit to it. An отзыв worth pages would be worth faking, and
  the отзывы are how a record's errors are found.
- No scheduler, no background loop: the summary rides on the week's first
  record.
- No cost and no tokens on the screen (task 14).

---

# Task 73. The week's summary on Saturday

**Owner: the CEO.** Taken on 2026-10-07. No migration: `groups.rating_week`
keeps the week claimed, now the Saturday the week ends on.

## Why

The CEO, 2026-10-07: «хочу, чтобы SUM присылал в субботу в чат статистику
по самым активным недели». Task 72 sent a group the week before with the
group's first record of the next, which a quiet Monday delays and a quiet
week loses; a summary at a fixed hour is one a group comes to expect.
Saturday morning closes the teaching week, so the week becomes Saturday to
Friday — in `/stats` too, so that the two never show different numbers.

## Do

1. **A week runs from Saturday 00:00 UTC** to the next — the night before
   Saturday in Moscow — in the summary and in `/stats`, whose head names its
   first day: «J3115 · неделя с 3 октября».
2. **Every Saturday at 10:00 Moscow time** — 07:00 UTC, Moscow keeping no
   summer time — each group with a record or an отзыв in the week just
   ended gets the week's summary in its chat, as task 72 wrote it: its
   dates, its two totals, ten people at most. A group with neither gets
   nothing. In a group divided into topics it goes to the general one: the
   bot keeps no topic yet (task 66).
3. **The bot's one timer**, started with the process (`rating.saturdays`):
   every ten minutes it reads the clock, and from 07:00 UTC on a Saturday to
   the day's end sends what is due. The week is claimed on the group's row
   before the summary is sent, so a restart or a second replica never sends
   it twice. A summary that cannot be sent is a warning in the log and is
   not tried again; a deploy that falls between the claim and the message,
   or a Saturday the bot is down for whole, costs that week its summary.
4. **The summary no longer follows a week's first record**: one summary a
   week, Saturday's.
5. `rating_posted` is written by the bot on its own, `user_id` NULL
   ("Contracts"); the startup log says when the summaries go out.
6. `CLAUDE.md` → "A group's week".

## Acceptance criterion

- On a Saturday after 10:00 Moscow time each group active in the week just
  ended has its summary once — two timers at once included — and a group
  with nothing in it has none.
- A deploy on that Saturday after the summaries went out sends nothing
  again.
- `/stats` in a group counts from Saturday and says so.
- A record no longer brings a summary.
- The suite is green.

## Don't do

- No queue, no cron outside the process, no table of jobs: one loop, and
  the group's row says what was sent.
- Don't send a week's summary on any other day: a summary is Saturday's.
- Don't compare groups, or send one group's week to another chat.

---

# Task 74. The bot's week, for whoever reads the отзывы

**Owner: the CEO.** Taken on 2026-10-07.

## Why

The CEO reads every «Плохо» in the feedback chat and has no view of the
bot as a whole short of the production database, which a working session
cannot read. Whether a group uses the bot weekly — the question the
project exists to answer — is counted there, group by group, and so is
what each costs.

## Do

1. **`/stats` in the feedback chat** — the chat `FEEDBACK_CHAT_ID` names,
   the CEO's own chat with the bot — answers with the whole bot's week
   instead of the records of whoever asked. Everywhere else `/stats` is as
   it was; with `FEEDBACK_CHAT_ID` unset, no chat gets it.
2. **What it says**, the CEO's choice of 2026-10-07: the week from Saturday
   00:00 UTC, as a group's, and all time —
   - records and pages; the people who sent a record and who rated one,
     everyone the bot knows and the new; «Хорошо» and «Плохо»; spend today,
     this week and all time, in dollars — the operator's screen, not a
     student's (task 14);
   - every group active in the week, by records: its records, pages,
     people, отзывы and spend, and private chats as one line; ten groups
     at most, the rest counted;
   - the week's people across every chat, two numbers each as in a group's
     week, fifteen at most, the rest counted.
3. A group's spend is `ai_calls.group_id`, written since task 41's deploy
   on 2026-10-07: the week it went out in counts a group's spend from that
   day only, and private chats carry the rest.
4. `stats_viewed` carries `{"scope": "bot"}` for it, so the operator's
   views are not read as a person's.
5. `CLAUDE.md` → "What NOT to do": an admin panel stays out but for this
   one message.

## Acceptance criterion

- `/stats` in the feedback chat: the week and all time, the groups, the
  people, the spend; in a group and in any other private chat, as before.
- With `FEEDBACK_CHAT_ID` unset, no chat gets it.
- The suite is green.

## Don't do

- No buttons, no actions, no second command: one read-only message.
- Nothing of it to any chat but the feedback chat.
- No new table or column: everything is counted from what is stored.

---

# Task 75. A page refused as dark that was not

**Owner: the CEO.** Taken on 2026-10-07. The frame check is the CPO's area,
open to the CEO; `photoguard` is a ready-made module, edited only on a
reproduced failure.

## Why

On 2026-10-07 page 2 of the CEO's album was refused before anything was
read, with «Слишком темно или блик — добавьте света», three times in two
minutes: contrast 26.1, 26.4 and 27.8 against 28, while sharpness stood at
1337 to 1636 against 90 and the sheet filled 91 to 100% of the frame. The
photograph was good. photoguard's contrast is the spread of brightness
across the sheet, and it measures how much is written as much as the light:
a page of a few lines is mostly even paper, and its spread stays low however
it is lit, so a retake measures the same. In the deploy logs Railway still
holds, from 2026-10-03, the frame check saw 75 album pages and refused this
one alone.

## Do

1. `MIN_CONTRAST` 28 → 20: under the lowest legible page measured, with a
   margin, as `MIN_LINE_HEIGHT_PX` went from 20 to 16 in task 43. A frame
   where the ink all but merges with the paper is still refused.
2. `CLAUDE.md` → "Ready-made modules": the fourth exception, and what stays
   open — the measure still depends on how much is written, and on this
   page the line height came out at 1161 to 1280 px, the sheet's own
   height: no lines found, so «Текст мелкий» could not fire on such a page.
3. `FINDINGS.md`: the page and its numbers.

## Acceptance criterion

- The album sent again goes through, page 2 read with the rest.
- The suite is green.

## Don't do

- No new measure of contrast: its threshold would need real pages, good
  and bad, and the bot keeps no photograph.
- Nothing else in `photoguard` moves.

---

# Task 76. What the bot spends its time and memory on

**Owner: the CEO.** Taken on 2026-10-07. Most of it is the CPO's area —
the model calls, the database, the infrastructure — open to the CEO.

## Why

Read off a week of production on 2026-10-07 — the deploy logs from
2026-10-03, Railway's metrics, `ai_calls` — and three audits of the code:

- **Recognition waited on calls that think past their ceiling.** 46 of 348
  recognition calls in seven days timed out at 90 s, none before
  2026-10-04. The successful ones took 18.5 s at the median, 64 s at the
  95th percentile and 89 s at most, and every one over 50 s thought 12,000
  to 21,000 tokens for an answer of 400 to 600: a timeout is a page the
  model thinks about longer, not a line that hung. Repeated at the same
  90 s, it timed out again 14 times of 25, and the third time 7 of 14.
  Seven runs were lost, so those pages were compared on two runs or one,
  and the albums they were in — 7 of 12 since 2026-10-03 — read for 269 to
  393 s where the rest read for 37 to 112.
- **Two documents drawn at once break each other's formulas.** matplotlib
  lays formulas out with one parser for the whole process: drawn in two
  threads at once, 36 of 72 formulas failed and would print as their
  source; in four, 136 of 144; some were drawn wrong without a word. Not
  seen in production yet — it comes with the second busy group.
- **A person's first record of the day locked their row until it was
  saved.** `check_limits` wrote the day's rollover, the next event flushed
  it, and the row stayed locked for the record's 3 to 8 minutes: a second
  album from the same person — a lecture of twelve pages is two — waited
  for the first to finish, then zeroed its pages.
- **Every album left 50 to 100 MB the process never gave back** until a
  deploy: 0.28 GB after one, 0.74 GB after a day's albums, held for 15
  hours with nothing running. No leak in the code — rendering stays flat,
  the album buffer empties — but image work fanned out over a thread per
  page, and glibc gives each thread an arena it keeps. The peaks of 1.0 to
  1.5 GB are the minutes of a deploy, two containers at once.
- **The SDK's automatic function calling ran on every call**: a fifth of
  the log was its line, «AFC is enabled».

## Do

1. **A timeout earns one more attempt, twice as long, and that is the
   last**: 90 s, then 180 s — 271 s at worst, inside the 273 s three
   attempts took, so every ceiling derived from a run stays where it is.
   Any other transient failure is retried as before.
2. **One document drawn at a time**: a lock around `pdf.render` and
   `pdf.warm_up`. The look does not change; a second document waits 1 to
   3 s.
3. **The day's pages counted by the database**: `check_limits` only reads,
   and `consume` writes the day in one statement, a new day started where
   the stored one is over. The row is locked from the record's saving to
   its commit, seconds, and two records saved at once both count.
4. **Image work on two threads of its own** — a page compressed and its
   frame checked — and `MALLOC_ARENA_MAX=2` on Railway, read by glibc. The
   memory after the next albums says whether it held.
5. **Automatic function calling off** on every call; search grounding is
   not it and is untouched.
6. "Scale debt": the row on `consume` goes; what the audits found and this
   does not fix comes in — a pool connection held for a record's whole
   processing.
7. `CLAUDE.md` → "Concurrency ceilings", "Sessions and transactions", "The
   document", "Scale debt", "Environment variables"; `FINDINGS.md` → "What
   the bot spends its time and memory on".

## Acceptance criterion

- The suite is green.
- After the deploy: no run waits on a third attempt after a timeout, and
  memory after the next albums stays near where the process started.

## Don't do

- No change to how a page is read: thinking stays at the model's default,
  three runs stay three.
- Nothing more from the audits — a formula parsed five times, a cache of
  formulas, the PDF's encoding, the connection held for a record: noted in
  `FINDINGS.md`, not done.

---

# Task 77. Two formulas the document printed as their source

**Owner: the CEO.** Taken on 2026-10-07. The document is the CEO's area.

## Why

The production log since 2026-10-03 names five formulas mathtext refused,
each printed as its LaTeX in two records:

- `- 105 - \cancel{56}^{48} - 72 = …`, `- \cancel{120} - \cancel{158} - …`
  and a determinant's working struck out whole, `\cancel{\Delta = …}`, on
  2026-10-05: mathtext has no `\cancel`. What the model writes for what the
  author crossed out — 56 struck, 48 written over it.
- `\boxed{\frac{1}{2^{k-1}}} \xrightarrow[k \to \infty]{} 0`, twice, on
  2026-10-06: `\xrightarrow{…}` is rewritten to `\overset`, but not with its
  condition under the arrow, in brackets.

## Do

1. **`\xrightarrow[below]{above}`** and `\xleftarrow` alike: the condition
   under the arrow by `\underset`, the label over it by `\overset` as
   before, either one empty.
2. **A struck term drawn struck**: `\cancel{…}` with a stroke from its
   lower left to its upper right, as LaTeX draws it; `\bcancel` the other
   way, `\xcancel` both. mathtext has no strike, so the formula is drawn a
   second time with the term's place left empty (`\phantom`), and the
   stroke goes across the pixels the two drawings differ by — wherever the
   term stands: under a power, in a fraction, round a matrix. A stroke
   that cannot be placed sends the formula out as its source, as before:
   the command is never dropped silently, because «\cancel{56}^{48}»
   without its stroke reads as 56 to the 48th.
3. `docs/BRAND.md` v1.6; `CLAUDE.md` → "The document"'s paragraph on
   mathtext; `FINDINGS.md` → "mathtext, one record at a time".

## Acceptance criterion

- The five formulas from the log drawn, the struck terms struck.
- The suite is green.

## Don't do

- No `\cancelto` until a record writes one.
- A struck term is not dropped from the formula: what the author struck
  out and the reading kept is shown struck, as `~~…~~` is in a line.

---

# Task 78. What record 86 showed

**Owner: the CEO.** Taken on 2026-10-08, from a reader's «Плохо» on record
86. The document is the CEO's area; the composer's numbers guard and the
explaining prompt are the CPO's, taken on the CEO's word under the rule of
2026-10-01.

## Why

Record 86 — a proof that √2 is irrational, an album of four pages read on
2026-10-07, the first after task 76's deploy. The reader wrote: the title
in the wrong format, «3 instead of 2» in 1.3, formulas wrongly set off in
1.4, the «неразборчиво» marks. The CEO suspected task 76. It is not:

- The request Gemini receives is the same byte for byte with automatic
  function calling off — captured for a reading, a composition and a
  search. The image is compressed by the same function with the same
  arguments, on another thread. No call timed out, so the new repeat never
  ran.
- All four pages came back from all three runs, at a text agreement of
  0.94 to 0.99 and a numeric one of 0.90 to 0.99 — above the 55 pages of
  the week before, whose means were 0.84 and 0.89.

What the reader saw:

- **The title printed as its source**, «Теорема об иррациональности
  \sqrt{2}», at the top, in the head of every page and in the file's name:
  the model wrote the title's formula with no dollars round it, and nothing
  marked it as one.
- **«3 instead of 2»** is the bot's «Пример» under 1.3: the lecture's own
  construction, done for √3. The prompt asks for an example unlike the
  lecture's — another set, another space — and the reader took this one for
  the lecture misread.
- **The formulas in 1.4** are a record that went out uncomposed. The
  numbers guard refused the composition twice, one number lost and then
  two, so the document is recognition's text: the notebook's line breaks,
  «1))», the first of three cases in its line and the other two on the
  kraft ground, the shorthand as written, the bot's boxes between the
  halves of a sentence. «1))» opening a line is the number 1 to the guard
  and «1)» an item's marker, so a composer tidying the one into the other
  loses a number: the first refusal, most likely; the second lost one more,
  which the log does not name. One record on 2026-10-06 was refused twice
  the same way, before task 76.
- **«[рамка: ?!]» printed twice in its proof**: the author ringed «?!»
  inside a line, and the document draws a frame only round a line that
  holds nothing else. A `\boxed` inside a line loses its frame as well.
- **Five «[неразборчиво]»**, one of them struck out — the author crossed
  something out and the reading marked it — and printed struck. Whether
  the others were legible, only the photographs tell.

## Do

1. **A formula in a title written without its dollars is drawn as one**,
   found the way a quoted fragment's is (`pdf.as_formula`), and written in
   characters in the head, the file's name and a chat's listing: «√2».
   Stored records included.
2. **The author's frame inside a line is drawn round what it frames** —
   «[рамка: …]» standing in a line, and a `\boxed{…}` in a formula set in a
   line — with a hairline, found as task 77's strike is: the formula drawn
   again with the term's place left empty. One that cannot be placed sends
   the formula out as its source, as before. A frame round a whole line
   stays as it is, set apart and numbered when it holds a formula.
3. **«[неразборчиво]» struck out is not printed**, as «[зачёркнуто]» is
   not: what the author struck out is not the lecture.
4. **«1))» opening a line is an item's marker** to the numbers guard, as
   «1)» is.
5. **A teacher's example is not the lecture's working with another
   number**: rule 6 of `prompts-explain-v3.md` says so. Production switches
   `EXPLAIN_PROMPT_FILE` on the CEO's word.
6. `CLAUDE.md` → "The document", "Stage two", "Stage three", "Structure";
   `docs/BRAND.md` v1.7; `FINDINGS.md` → "Record 86, √2".

## Acceptance criterion

- Record 86 drawn again by «#матан»: «√2» in its title and its head, «?!»
  framed in its proof, no struck «[неразборчиво]».
- The suite is green.

## Don't do

- Record 86 is not composed again: a stored record is drawn again, never
  read again, and a composed one needs its album sent again.
- The numbers guard is not loosened beyond «1))»: which number the second
  attempt lost is not known, and a number lost for real is what the guard
  is for.
- Nothing about the «[неразборчиво]» until the photographs are compared.

---

# Task 79. Record 86 sent again

**Owner: the CEO.** Taken on 2026-10-08, from record 87 — record 86's album
sent again by the CEO after task 78's deploy. The document is the CEO's
area; the numbers guard is the CPO's, taken on the CEO's word.

## Why

Record 87 went out uncomposed as record 86 had: refused twice, two numbers
lost each time. Run twice more on Railway over record 87's text, on the
CEO's word ($0.017, two rows in `ai_calls`), the composer lost the same two
numbers both times, and neither was a value. The author numbered the
theorem's two parts «1 Существование» and «2 Число не является
рациональным», with no dot after the number; the composer made them the
list they are, «1.» and «2.», and the guard — which counts a number opening
a line unless a dot or a bracket follows it — read both as lost. «1))»,
which task 78 named the likely cause on record 86, was not it on record 87.
Everything else the composition kept.

And 1.4 again: the author set three cases in a column begun on the line
that introduces them — «Возможно 3 случая: c² < 2», with c² > 2 and c² = 2
under it. Read as written, the first stands in the line and the other two
alone on theirs, so the document set two on the kraft ground and left the
first in the text — «в рамке только 2 из 3», the CEO wrote.

## Do

1. **A number opening a line before a capitalised word is an item's
   number** to the numbers guard, as «1.» and «1)» are: «1 Существование».
   Before a lower-case word it is still a value — «2 мн-ва» spelled out as
   «два множества» is still refused.
2. **A column of formulas begun on the line that introduces it is set as
   one** (`pdf.py`): a line ending in a colon and one formula, followed by
   a formula alone on its line with the same left side — c² < 2 over
   c² > 2 — gives its formula to the ground the others stand on. Stored
   records included.
3. `CLAUDE.md` → "Stage two", "The document"; `FINDINGS.md` → "Record 86,
   √2", corrected on what refused its composition.

## Acceptance criterion

- Record 87 drawn again by «#матан»: the three cases of 1.4 on one ground.
- The suite is green.

## Don't do

- The guard learns no other shape. A value opening a line before a
  capitalised word — «10 Ом» — goes uncounted, and that is the price.
- No formula moves without a relation to compare: «Пусть дано: $f(x)$»
  over a formula of another left side stays as written.

---

# Task 80. A lecture's study version

**Owner: the CEO.** Specified on 2026-10-08 and approved by the CEO the
same day, taken next. The document and the bot's buttons are the CEO's
area; the model call, the schema and the limits it needs are the CPO's,
open to the CEO — the migration it needs named to the CPO before it is
pushed.

## Why

The CEO asked whether SUM should make study materials based on the records
rather than the records. Two ways were weighed:

- **The material instead of the record.** The model writes the document and
  the author's text becomes its quotations. That changes the rule the
  product stands on — marked is the whole licence to add — and lifts «text
  rewriting» from `CLAUDE.md` → "What NOT to do"; every record costs 20 to
  40% more; and what the model invents reads as the lecture, the failure
  the project was built to keep out. Code can check the material's numbers
  and formulas, never whether an explanation is true.
- **The material over the record.** The record stays what it is — the text
  a group trusts, what a "#word" finds, what two notebooks of a lecture
  merge into, what the app's library will show — and a study version is
  built from it when somebody asks for one.

The CEO chose the second on 2026-10-08. It takes up the design of the idea
of 2026-10-06, the lecture as structured material, archived that day.

## Do — the first version

1. **«Учебная версия», a button under every document**, beside «Хорошо»
   and «Плохо». A press builds the lecture's study version from the record
   and sends it as a second PDF. Never built unasked: the presses are the
   measure.
2. **What it holds**: the lecture set out by its topics rather than in the
   lecturer's order. The author's text cut into units — a paragraph, a
   formula, a drawing, a list — each moved whole and never reworded. Between
   them, under the bot's label: what a topic is about, its key notions — the
   author's words, picked from the markup — and the record's explanations
   and teacher's boxes where their anchors went. At the end, three to five
   questions to check oneself, their answers on the last page.
3. **How**: one text-only call over the record numbered by units, answering
   with the arrangement by number and the bot's own texts, never the
   author's text back. Code checks that every unit is placed once and that
   the bot's texts state no number the record does not carry, as stage
   three's are checked; a question whose answer fails is dropped. A
   version that fails is not sent; the reader is told it could not be
   built.
4. **Stored** beside the record — the arrangement and the bot's texts — so
   a second press sends it again and pays nothing.
5. **Paid inside the day's limits**, checked before the call: about a
   composition's price, $0.03 to $0.05 a press.
6. **Measured**: `study_requested` and `study_sent`, with the group's id.
   The subject's version (52) and the exam preparation (59) come after,
   and only once the presses show it is used.

## The CEO's decision of 2026-10-08, the same day: the study version is sent

**A chat gets the study version, not the record.** Every capture path and
every "#word" that brings a record back delivers its study version, built
the first time and kept on the record after; the record's own document goes
out only when there is no study version to be had — the cap reached, the
call refused, the drawing failed — with «Учебная версия» under it to ask
again: a record is never lost over its presentation. The record stays what
everything is made from and what a "#word" finds. The two stay separate
functions, decided in one place (`corpus.deliver`): the CEO wants to be
able to split them later, one sent and the other by a button. A lecture of
several notebooks is studied whole — its base with what the others add.
Built where the explaining stage is on, on its model.

## The CEO's answers, 2026-10-08

- **For understanding a lecture**, by someone who was not there: what each
  topic is about, its key notions, how the parts hold together. The exam
  is the subject's level — 52 and 59.
- **Questions to check oneself at the end of the PDF**, three to five,
  their answers on the last page, marked as the bot's — the study version
  is a document of its own, and the record stays clean. This changes the
  decision of 2026-10-02 that put «Проверь себя» in the app alone; the app
  can still have its own.

## Acceptance criterion

- A press on a record with headings sends a study version in which every
  unit of the author's text stands once, every text of the bot is marked,
  and a second press costs nothing.
- The suite is green.

## Don't do

- The record is not replaced, and its document does not change.
- No unit of the author's text is reworded: the model arranges and adds,
  and what it adds is marked.

---

# Task 81. A lecture sent at once

**Owner: the CEO.** Taken on 2026-10-08, from twelve pages of a lecture sent
at once. What a chat gets is the CEO's area; the pool and the concurrency
ceilings are the CPO's, taken on the CEO's word.

## Why

Telegram puts at most ten photographs in an album. A send of twelve arrives
as two albums, ten and two, each with a media group of its own, and the bot
made a record of each: two documents, two compositions, two study versions,
the lecture cut after its tenth page. Two such sends that day, at 11:27 and
14:28 UTC, each came as ten and two, the second album's first page 0.07 s
and 0.45 s after the first album's last. Raising `MAX_ALBUM_PAGES` to 30 and
a person's day to 50 pages, as was done at 14:23, joins nothing: the bot
never saw an album of more than ten.

In a group it is worse. The caption, and the "#word" in it, rides on one of
the albums, and the bot takes an album only with its "#word": ten pages of
twelve are read and the rest is dropped without a word.

A page left over after the tens — the eleventh, the twenty-first — can come
as a photo of its own, with no media group: an album holds two items at
least. Not seen in production yet.

## Do

1. **The albums of one send are one album** (`albums.collect`): the albums
   one person sends into one chat, in page order, while every one before
   the last holds ten pages — Telegram fills every album of a send but the
   last. Decided when the batch closes, over every album of that person
   still waiting, not when a page arrives: the order the pages are
   registered in is the order their updates finish their database work.
2. **A send ends**: at an album of fewer than ten pages; at
   `MAX_ALBUM_PAGES`, the next album beginning a send of its own — 35
   pages are two records, 30 and 5, never one refused; and before an album
   whose "#word" is not the send's — two subjects are two sends.
3. **An album of exactly ten waits for the rest of its send**:
   `_CONTINUE_S`, 15 s of quiet against `_QUIET_SECONDS`' 3 — some thirty
   times the gaps measured, for a slow upload. It waits whether or not more
   comes; an album that comes later than that is a record of its own, as
   every album was.
4. **A photo sent apart continues a send** (`handlers.handle_photo`): a
   photo the same person sends while an album of theirs is being collected
   goes into the buffer as an album of one page. In a group it is heard
   without a "#word" for that reason (`middlewares.heard`); a photo that
   continues nothing is then its own album, and in a group, without a
   "#word", nobody's.
5. **The record is the send's**: its pages in message order across the
   albums, its subject from whichever album carries one, its source key in
   a group the first album's.
6. **A page waiting for its album holds no connection**: its update commits
   before it waits, as a group's page already did after writing itself
   down (`_remember_page`). A send of thirty pages is thirty updates
   waiting at once, and the pool is twenty.
7. **`MAX_ALBUM_PAGES` is the pages of one send**, 30 by default — the
   value production runs since 2026-10-08. At 10 nothing would ever join.
   The album ceiling follows it: 1813 s at the default call, 5323 s at
   production's.
8. `note_processed` gains `album_parts`, the albums and photos the send
   arrived as ("Contracts"); the log line that closes a batch names how
   many and the gap before each — what `_CONTINUE_S` is to be measured
   against.
9. `CLAUDE.md` → "Sessions and transactions", "Updates and albums",
   "Concurrency ceilings", the environment; `FINDINGS.md` → "A lecture sent
   at once".

## Acceptance criterion

- Twelve pages sent at once in a private chat: one record of twelve pages,
  one «Обрабатываю», one study version.
- Twelve pages with «#матан» in a group: one record of twelve pages.
- Two albums of four and three sent seconds apart: two records.
- The suite is green.

## Don't do

- A reply's "#word" under one album of an untagged send in a group still
  reads that album alone: what is written down of a group's pages
  (`group_pages`) does not say who sent them — a column and a migration,
  taken when a group needs it.
- No guess at an album that came after `_CONTINUE_S`: it is a record of its
  own.
- A group's day stays 20 pages: a send of more in a group is refused whole
  by its day, where its first ten used to be read alone.

---

# Task 82. Records 88 and 89

**Owner: the CEO.** Taken on 2026-10-08, after the two records twelve pages
came back as (task 81) both went out uncomposed. The numbers guard and the
composing stage are the CPO's area, taken on the CEO's word.

## Why

Both compositions were refused by the numbers guard, twice each, and both
records went out without a heading. Composed twice more on Railway over
their text, on the CEO's word ($0.044, four rows in `ai_calls`):

- **Record 89**, two pages: the composer wrote $(c-h)^2$ where the record
  reads «$c-h = c^2 - 2ch + h^2 =$» — the square the working needs and the
  reading does not have — nine times of the fourteen it was asked on
  Railway, most of them making one formula of that line and the next,
  «$= c^2 - … = 2$». The guard was right to refuse a formula changed, and
  the record lost every heading for one exponent.
- **Record 88**, ten pages, lost no value. The composer set the author's
  numbered items as a bulleted list, «* 2) …», «* 1 База индукции», and the
  guard knows an item's number only at the start of a line; it dropped what
  the author struck out, «~~3.1 Строгое~~», whose number the guard counted;
  and once it dropped the «1)» after it, an item's number the struck words
  before it hid. Once it also merged «Теорема $\sqrt{2}$ — …», written
  twice, into one: a sentence lost, and that refusal stands.

Since `prompts-compose-v4.md` went to production on 2026-10-06, five
records of fifteen went out uncomposed, the last four in a row: 86 and 87
(tasks 78 and 79), 88 and 89.

## Do

1. **An item's number after a bullet is an item's number** — «* 2)»,
   «- 1.», «• 3 База»: the composer's list over the author's.
2. **What the author struck out is not counted**: the numbers inside a
   `~~…~~` the source carries leave the count on both sides, so the
   composer may drop the struck words. A struck span the composer adds is
   still counted.
3. **A formula the composer changed is put back, not refused**
   (`compose._restore_formulas`, after the repairs and before the guards):
   when the numbers differ, a formula of the composition the source does
   not carry is matched against the source's formulas, and against runs
   of them standing one after another — the lines of one working, which
   the composer makes one formula. The closest, four-fifths of its
   characters alike at least, is put back as recognition read it, each
   source formula once, and only where that brings the numbers closer to
   the source's. A short formula a character or two from several is too
   ambiguous to put back, and stays refused. Counted: `compose_restored`
   in `note_processed` ("Contracts"), "formulas put back" in the log
   line.
4. `CLAUDE.md` → "Stage two"; `FINDINGS.md` → "Records 88 and 89".

## Acceptance criterion

- Record 88 composed again on Railway under the new guard: accepted three
  times of three.
- Record 89's composition as the composer wrote it on Railway — two lines
  of the working made one formula, and squared — accepted with the
  author's formula put back.
- The lecture sent again at once, twelve pages: one record, composed.
- The suite is green.

## Don't do

- No number the author wrote is let go: a value the composer spells out,
  «2 мн-ва» as «два множества», is still refused, and so is a sentence it
  drops.
- The prompt does not change: it already says formulas stay as written,
  and code puts them back.

---

# Task 83. What the CEO read in records 88 and 89

**Owner: the CEO.** Taken on 2026-10-08, from the CEO's reading of the
study versions of records 88 and 89 against the photographs. The
document is the CEO's area.

## Why

The CEO wrote down sixteen points: ten in the lecture itself, six in how
it was set out, and asked whether algorithms rather than a model should
find them. Of the six, these are the document's own, and code does them:

- **The bot's boxes cut sentences and formulas**: «Существует элемент
  1 ∈ ℝ, 1 ≠ 0», a box, «такой, что x·1 = x». A record whose composition
  was refused goes out line by line as the notebook has it, and a box
  stood under the line its anchor is in.
- **A box pages from its place**: «Корректность определения через
  пересечение» is anchored on «Множеством натуральных чисел называется»,
  which runs over two lines of the notebook; found on neither, it went
  to the end of the text, into the proof about √2.
- «множес-» over «твом», «предполо-» over «жению»: words carried over
  with a hyphen.
- «~~3.1 Строгое~~» printed struck; ⩽ beside ≤.
- «$X_i$», the end of a sentence, alone on a formula's ground.
- «[схема: ?! в кружке]» printed as a line of words.

The rest is the lecture's — task 84 takes the class code can prove —
or the meaning of the bot's own texts, which no code reads.

## Do

1. **A box goes after the sentence it is anchored in** (`pdf._sentence_end`):
   the lines of a sentence as code can tell them — a line that goes on in
   lower case; a formula or a sign after a line that does not end one;
   the list a line opens — are one place for the boxes, ten lines at most.
   An anchor is found across them; a box set under is set under the
   last; «Идея», set before, before the first. A finding too.
2. **A word carried over with a hyphen is joined**, three letters on
   either side at least: «мн-ва» and «док-во» stay as written, and so do
   «во-», «по-», «кое-», «из-» and «-то», «-либо», «-нибудь».
3. **What the author struck out is not printed**, as «[зачёркнуто]» is
   not — unless it is all the line has but its number: «1.3. ~~Мн-ва
   Аксиома полноты~~» stays struck, since the reading may have struck more
   than the author did.
4. **⩽ and ⩾ are drawn as ≤ and ≥**: one sign through the document.
5. **A short formula ending a sentence is set in its line** — «$X_i$»,
   «$P(k+1)$» — never one of a column.
6. **A sign the author ringed**, «[схема: ?! в кружке]», is drawn framed
   in its line, as «[рамка: ?!]» is.
7. `CLAUDE.md` → "The document"; `BRAND.md` v1.9; `FINDINGS.md` →
   "Records 88 and 89".

## Acceptance criterion

- Record 88's study version drawn again: no box inside a sentence,
  «Корректность определения через пересечение» under the definition of
  ℕ, «множеством», ≤ alone, «3.1 Строгое» gone, «?!» framed.
- The suite is green.

## Don't do

- No word of the author's changes but by a hyphen's join; the numbering
  stays the author's — «1.2» of the axioms and «1.2» of the sections.
- The bot's own texts are not checked here: task 84 and the guards.

---

# Task 84. An equality that does not hold

**Owner: the CEO.** Taken on 2026-10-08, after 83. A check of code like
`mathcheck`, which the CEO's area takes on the CEO's word.

## Why

Two of the ten errors the CEO found in the lecture of records 88 and 89
are equalities that do not hold — «(−x)(−x) = x» and «c − h = c² − 2ch +
h²» — and code can prove that, where it cannot tell what a proof lacks.

## Do

1. Every «=» whose two sides carry the same letters, with what the
   lecture defined before it substituted («положим h = b/3c», «:=»),
   both sides counted at random numbers: two that differ are an
   equality that does not hold. An equation, «x + a = b», a claim about
   one number, «c² = 2», and a contradiction reached on purpose, «1 = 0»,
   carry different letters, or none, and are left alone; so is whatever
   the code does not read.
2. A finding under its line, as `mathcheck`'s are, with the numbers it
   was refuted at — the reader can count them; the text stays as read.
3. Measured over every record in the database before it is on (the
   CEO's word, 2026-10-08): in the container, only the equalities found
   come out. On only if none of them is false.

## Don't do

- No model; no new library.
- The author is not corrected: a finding says the equality does not
  hold, not what was meant.

---

# Task 85. Thirty-two pages sent at once

**Owner: the CEO.** Taken on 2026-10-09, from the lecture the CEO sent at
once the evening before. The capture path is the CEO's area; the ceilings
the CPO's, taken on the CEO's word.

## Why

Thirty-two pages sent at once came back as three records, 90, 91 and 92:
ten pages, ten and twelve. Telegram cut the send into albums of 10, 10, 10
and 2, and the phone sent each album once its photographs were uploaded:
the next album's first page came 19.1 s after the last page of the one
before, twice, and the album of two 9.1 s after its ten. An album of
exactly ten waits `_CONTINUE_S`, 15 s, for the rest of its send (task 81),
so the first two closed alone, and the last ten and the two joined. The
sends of twelve that set the window had come 0.07 s and 0.45 s apart —
photographs uploaded before the first album went.

A cut costs the lecture: record 91 opens on the last lines of record 90's
proof and was titled after them, «Иррациональность числа и плотность», over
nested segments and metric spaces.

## Do

1. **An album of ten waits a minute for the rest of its send**:
   `_CONTINUE_S` 15 → 60 s, three times the 19 s measured — an upload twice
   as slow as that evening's still joins. A send that ends on ten pages
   starts 45 s later than it did; one that ends on fewer starts as before,
   3 s after its last page.
2. **The ceiling follows the send** (`albums._COLLECT_MAX_S`): one
   `_CONTINUE_S` for every album a send of `MAX_ALBUM_PAGES` holds, and one
   more — 240 s at 30 pages, 300 s at 40, from the send's first page. At
   60 s it would cut a send of four albums that keeps coming.
3. `CLAUDE.md` → "Updates and albums", "Concurrency ceilings";
   `FINDINGS.md` → "Records 90, 91 and 92".

## Acceptance criterion

- A send of eleven to twenty pages whose last album comes slowly: one
  record. `MAX_ALBUM_PAGES` was kept at 15 on Railway on the CEO's word of
  2026-10-09, and set to 20 the same morning, with a person's day at 30
  (the deploy of 09:35 Moscow time): a send of more than twenty pages is
  several records by design — the thirty-two pages of records 90 to 92
  included.
- Ten pages sent alone: «Обрабатываю» about a minute after the last page.
- The suite is green.

## Don't do

- No reading begun before the send has ended, the rest added while it
  runs: it would spare the minute, and it is another pipeline — a batch
  whose pages change while they are read, its limits and its refused
  frames counted twice. Taken up if a minute proves too long.
- Nothing said in the chat while the bot waits.

---

# Task 86. What records 90, 91 and 92 showed in the document

**Owner: the CEO.** Taken on 2026-10-09, from the three study versions of
the thirty-two pages and the errors another model listed over them for the
CEO. The document is the CEO's area.

## Why

Of what was found in the three documents, these are how the record is set
out, and code does them:

- **A box between a sentence and its formula**: «…существует единственное
  k ∈ ℤ такое, что:», «Зачем условие», then (4); «множество X называется
  ограниченным», the box, then the condition. A formula set apart stands
  after a blank line — how the composer writes it, and how a study version
  joins a formula to the text that leads up to it — and a blank line ended
  the sentence (task 83). So did a main formula.
- **«Идея» pages before its proof**: the idea of a proof's second part set
  before the last line of its first, «Точка x — произвольная…», since that
  line's «мн-во» did not end its sentence and ran into «2) Пусть …»; the
  idea of a proof of compactness set above the theorem, ten lines up.
- **A comma opening a line**: «…выполнялось бы −n ≥ c», and «, то есть
  n ≤ −c» on the next. reportlab breaks a line on either side of an
  inline image.
- **«[знак: ?!, обведённый в кружок]» printed as words**, and «[?!]» in
  its brackets: task 83 knew «[схема: ?! в кружке]» only.
- **Two struck lines printed struck**: a passage struck over two lines,
  which the rule that drops struck words reads line by line — and a line
  struck whole was kept, as a line that would lose its words.
- **«4 · 16 · 17 · 8 · 2 · 19 · 2» under the title**: the page numbers of
  every page's margin, where one page's number says which page and seven
  say nothing.
- **A box's title in lower case**, «внутренние точки множества.», in every
  box of record 92.
- **«-окрестностью точки» among the key notions**, its ε lost: the formula
  stood before the bold.

## Do

1. **A formula set apart goes on from a line that does not end its
   sentence**, a blank line between them or not; so does a main formula,
   and ends it (`pdf._sentence_end`). **A list goes on from a line only at
   its first item** — «1)», «1.», a bullet.
2. **«Идея» stands before the line its anchor begins in**, moved up only
   over the lines that go on in lower case: a proof begins on a line of
   its own.
3. **Punctuation after a formula stays with it**: a comma, a period, a
   semicolon, a closing bracket drawn with the formula, so that no line
   opens with one.
4. **A ringed sign however the reading wrote it** — «[знак: ?!,
   обведённый в кружок]», «[?! в кружке]», «[?!]» — framed in its line,
   as «[рамка: ?!]» is.
5. **What the author struck out is not printed over two lines either**,
   and a line struck whole goes with it. A line struck but for its number
   keeps its words, struck, as task 83 decided.
6. **Under the title, one page's number or none**: page numbers from
   several pages' margins are left out; a name and a date stay, each once.
7. **A box's title begins with a capital letter.**
8. **A key notion keeps the formula written against it**: «ε-окрестностью».
9. `CLAUDE.md` → "The document"; `BRAND.md` v1.10; `FINDINGS.md` →
   "Records 90, 91 and 92".

## Acceptance criterion

- Records 90, 91 and 92 drawn again: no box between a sentence and its
  formula, no comma opening a line, «?!» framed, no struck line, nothing
  under the titles, every box's title capitalised, «ε-окрестностью» among
  the notions.
- Records 88 and 89 drawn again: what task 83 fixed stays fixed.
- The suite is green.

## Don't do

- No word of the author's changes; the numbering stays the author's.
- The title stays as read: the composer spells out the body's
  abbreviations, not the title's («Введение в мат.анализ. Модуль веществ.
  числа» over «Введение в математический анализ») — how a record is
  titled is a change of its own.
- Not here: the lecture's own errors and the bot's own reasoning — tasks
  89 to 91.

---

# Task 87. A study version asked again

**Owner: the CEO.** Taken on 2026-10-09, from record 91. The model's call
is the CPO's area, taken on the CEO's word.

## Why

Record 91's study version came back from the model, 1048 tokens of
answer, and did not parse as the JSON asked for. The record's own document
went out with «Учебная версия» under it; the CEO pressed it, and the
second call parsed. The call's row in `ai_calls` says `success` and
nothing else: rule 7's finish reason and shape were never written for it.

## Do

1. **An answer that does not parse is asked for once more**, as
   recognition's is (`vision._worth_asking_again`) — never after `SAFETY`,
   `MAX_TOKENS` or `RECITATION`. Two calls at most, as now.
2. **Its row says why**: `success` false, `error` the finish reason and the
   shape (`vision._unparseable`), as recognition's rows do.
3. **A raw line break inside the answer's strings is read**
   (`json.loads(…, strict=False)`), by the explaining stage's parser too.
4. `CLAUDE.md` → "A lecture's study version".

## Acceptance criterion

- The suite is green.
- In production, a study version that did not parse is followed by a
  second call in the log.

## Don't do

- The prompt does not change.

---

# Task 88. Numbered items in lower case

**Owner: the CEO.** Taken on 2026-10-09, from records 91 and 92. The
numbers guard is the CPO's area, taken on the CEO's word.

## Why

Records 91 and 92 went out uncomposed, refused by the numbers guard twice
each: sixteen numbers lost of record 91, four and three of 92, none
gained. Both are written as the notebook has them, and the notebook
numbers in lower case — a metric's axioms «1 тождественность», «2
симметричность», «3 нер-во треугольника», a norm's «1 невырожденность»,
«2 однородность», examples «1 $A = [1; 2) \cup \{3\}$», «2 $A = [0; 1] \cap
\mathbb{Q}$». A number opening a line before a word in lower case or a
formula is a value to the guard (task 79: «2 мн-ва» written «два
множества» is refused); made into the list it is, each seemed to vanish.
Counted off the documents, record 91 carries fourteen such numbers and 92
three — about the size of the refusals. An uncomposed record keeps every
abbreviation (rule 10, the CEO's) and has no heading: that is how 91 and
92 read.

## Do

1. **A run of numbers opening lines, 1, 2, 3 in order, is a list**,
   whatever follows each: the guard leaves its numbers out on both sides,
   as it leaves «1)» and «1.». A run begins at 1, holds two numbers at
   least, and each next number opens one of the six lines after the one
   before. A number alone before a word in lower case stays a value:
   «2 мн-ва».
2. **What the author struck out over two lines** is left out of the count
   too, as over one (task 82) — and out of the count of `[неразборчиво]`
   and of the length, which the guard compared whole: record 91's struck
   passage held a mark, and a composition that dropped it would have been
   refused for it. A later item may stand inside a line, «верно 3) …», as
   record 91 has it, unless its bracket closes one opened before it.
3. **Measured before it ships**: records 91 and 92 composed again on
   Railway under the new guard, on the CEO's word to read them — accepted,
   or the numbers it still loses counted.
4. `CLAUDE.md` → "Stage two"; `FINDINGS.md` → "Records 90, 91 and 92".

## Acceptance criterion

- Records 91 and 92 composed again under the new guard: the numbers it
  was made for no longer lost — measured below.
- The suite is green.

## Measured, 2026-10-09

Records 91 and 92 composed again on Railway, on the CEO's word to read
them ($0.13, six rows in `ai_calls`), each composition judged by the
deployed guard and by this one. Record 91 lost 16 numbers twice under
the old guard and 2 under the new; record 92, 3 and 3 under the old, 1
and 1 under the new, one of its compositions also gaining 2. Neither was
accepted: what is left is not a numbered item —
- «Для 3х метрик» written «трёх метрик»: a number spelled out, which the
  guard refuses by design;
- «Определение 7:» made a heading, «### Определение», its 7 dropped;
- «1 $A \subset X$ — ограниченное мн-во», a lone item made «1.»;
- a formula changed: $\varepsilon_k$ written $\varepsilon_1$, the marks
  under an inequality made a clause «где …» that repeats $x_{j_0}$.

So it ships as what it is, and the rest is a question of its own: the
composer told to keep a label's number, «3х» and a formula as written, or
code putting a dropped label's number back as task 82 puts back a formula.
Found while measuring, and taken in: the item's number is read alike
however the composer sets it — «**1.** …», «### 1. …», «(1) …» — an
interval «[1; 2)» is no item, and what `\phantom{…}` only measures is no
value.

## Don't do

- No number the author wrote is let go: «2 мн-ва» spelled out is still
  refused, and so is a value inside an item.

---

# Task 89. The bot's reasoning that leans on what the lecture proves

**Owner: the CEO.** Specified on 2026-10-09, not scheduled: the CEO's
decision. The explaining stage's prompt is the CPO's area.

## Why

Under the proof that ℝⁿ is complete, record 92's explanation reads
«Используется … теорема о вложенных замкнутых шарах в полном пространстве»
— the completeness being proved, assumed. Record 91's example of the
integral norm says its axioms hold «благодаря линейности и монотонности
интеграла», where non-degeneracy rests on the functions being continuous.
Both were sourced: a source shows the words exist, not that they fit the
lecture. A wrong box is worse than none — it is marked as the bot's, and
the reader trusts the mark.

## Do — a proposal

1. `prompts-explain-v4.md`: an explanation and a teacher's box do not use
   the statement they stand under, nor one the lecture proves after them.
2. Measured on records 88 to 92: the boxes it drops or changes, read by
   the CEO, before production switches to it.

## Don't do

- No model checking the boxes: a verification call does not work
  (`CLAUDE.md` → "What the model is not trusted with").

## The CEO's word, 2026-10-09

«Лекцию можно поправлять»: a box of the bot's may correct the lecture —
«для всех векторов X, а не только для ℝ», «подразумевается бесконечное
множество» — and the CEO reads them. Not taken; the author's text itself
is still never rewritten.

---

# Task 90. The reading against the photographs

**Owner: the CEO.** Specified on 2026-10-09: the CEO's to do, no code.

## Why

Most of the thirty-eight points are the lecture as the record reads it, and in
some of them one stroke decides between what the author wrote and a
misreading: A for H, x for X, r for n in «√2 = r(α − q)», ℝ for X in the
equivalence of norms, k for m, «лемме 4» for 2, «Теория Кантора» for
«Теорема», «D-во» for «Д-во», «пл-ть» for «п-ть», «имеет предел» without
«единственный», «Такая послед-ть» with nothing before it, «q² ⋮ 2» for p²,
the open ball's proof with its lines interleaved, the closedness proof
with p and q exchanged. And record 91 holds two proofs that a finite
intersection of open sets is open: the first in whole sentences, the
second in the notebook's shorthand. If the page holds only the second,
the first was written by the reading model — the fluent retelling
`CLAUDE.md` fears most, which nothing after the fact catches.

## Do

1. The CEO checks those places against the photographs — the CEO's own
   check, said on 2026-10-09.
2. What the photographs say decides what follows: misreadings are a
   question for recognition, the CPO's, asked with data — the prompt, the
   model, the runs; the author's text is kept as it is.

---

# Task 91. What the lecture uses without defining

**Owner: the CEO.** Specified on 2026-10-09, not scheduled: a decision
first.

## Why

Record 90's lecture uses an upper bound, [x] and {x} without defining
them; record 92's «Такая послед-ть наз-ся бесконечно малой» follows
nothing. The model the CEO asked wrote the definitions into the lecture,
and added a proof the lecture left out — what the bot never does: the
author is not corrected, and an addition is marked.

## The question

Whether the bot recalls, in a box under its own label, a definition the
lecture relies on and does not give — a fourth teacher's box beside
«Идея», «Зачем условие» and «Пример», written by the same call, its
numbers checked as theirs are. A gap in a proof stays the lecture's: the
bot does not fill it.

Not needed, the CEO's word of 2026-10-09.

---

# Task 92. What the reading writes about the photograph

**Owner: the CEO.** Specified on 2026-10-09, from record 97.

## Why

Record 97's album held photographs of two pages each, and recognition
marked their halves, «[Левая страница]», «[Правая страница]». The document
printed them as notes in the grey of a drawing's description. Its author:
useful to them, to see where the bot errs, and to a student studying from
it a distraction. The document never talks about how a page was read
(`CLAUDE.md` → "The document").

## Do

1. A note that only says which half of a photograph a text was on —
   «[Левая страница]», «[Правая страница]», «[левая часть разворота]» —
   is not printed (`pdf.blocks`), in a record stored before too.
2. `CLAUDE.md` → "The document"; `BRAND.md`.

## Don't do

- The recognition prompt does not change here: a prompt is measured, and
  a line of code ends the fault for every record already made.

---

# Task 93. What does not belong to the subject

**Owner: the CEO.** Specified on 2026-10-09, from record 97; the CEO's
word: «нам нужно решить, как отделять то, что не относится к предмету и
выкидывать». Taken the same day.

## Why

Record 97 opens on the course's organisation — the teacher's contacts,
the points for each grade, a test, a colloquium, the exam in January —
written in two columns that the reading flattened into «лекции |
практика», «40 б. - допуск | 60 б.». The study version made one topic of
it and of injective maps, «Организация курса и виды отображений
множеств». Its author: either leave it out or set it out properly; the
CEO: tell it apart and leave it out.

Cut into the study version's units, the organisation is three of them,
and the third carries more than the organisation: the set equality
«$A = B$ ⇔ …» stands under it with no line between, and a formula set
apart goes with the text before it (`study.units`). A guard over whole
units would keep that unit for its formula, and the organisation with
it.

## Do

1. **The study version's model names the units about the course's
   organisation** — contacts, points and grades, admission, dates of
   tests and exams, the schedule — in `organization` of its answer, and
   puts them in no topic; `prompts-study-v2.md`, v1 with that. A unit
   where the organisation stands with the lecture is named too. Homework,
   a practice session's problems, a remark on history are the lecture's.
   Its topics' «о чём» and its questions are about the subject alone.
2. **Code leaves out, of each unit named, its paragraphs before the
   first that holds the subject** — a formula, a drawing, or a word of
   what a lecture states: a definition, a theorem, a proof, an axiom, an
   example, «называется», «пусть», a problem, homework (`study._SUBJECT_RE`).
   What is left stands where the model put the unit, or else after the
   unit nearest before it that stands somewhere; a unit with nothing left
   is not in the study version. A unit opening on the subject loses
   nothing. More than a fifth of the record named so, and nothing is left
   out. A formula is never left out, so no main formula's number moves.
3. **The record keeps every line** — what a "#word" finds, what notebooks
   merge into, its own document. A box of the bot's or a finding whose
   anchor stands only in what the study version left out is not printed
   in it, rather than at the end of the text.
4. **A kept study version built by another prompt is built again** when
   the record is next delivered: the prompt's name is in the fingerprint
   (`study.fingerprint`), so record 97, brought back by «#матан», comes
   without its organisation. One call a record, paid as a first build is.
5. Counted: `off_topic` — units left out whole or in part — and
   `off_topic_kept` — named and kept whole — in `study_sent`, and in the
   log line.
6. Measured on record 97 (the CEO's word to read it) before it ships: the
   organisation gone, the set equality kept, nothing of the lecture lost.
7. `CLAUDE.md` → "A lecture's study version"; `FINDINGS.md` → "Record 97".

## Don't do

- No model removes a line from the record: the record stays what the
  group trusts.
- No check of the bot's own texts for words of the organisation: the
  prompt asks, and the measurement reads them.

---

# Task 94. A drawing that is data, drawn by code

**Owner: the CEO.** Specified on 2026-10-09, from record 97; the CEO's
choice of the three ways to the drawings it asked for.

## Why

Record 97 printed «схема: график параболы $y = x^2$ …», «схема: числовая
прямая … множествами X, Y и точкой c» and «схема: отображение множества A в
B со стрелками» — what its author read as the bot failing to draw their
drawing. Drawings cut out of the page sleep since record 60 (task 54). But
much of what a lecture draws is data — a graph by its formula, a number
line, a mapping — and data is drawn by code, the way a graph is drawn from
its edges (`[граф: 1-2, 2-3]`) and was never a picture of the model's.

## Do — a proposal

1. **Recognition writes such a drawing as data**, `prompts-v10.md` (v6
   with it): `[график: y = x^2; x от -2 до 2]`, `[ось: …]` with its points
   and intervals, `[отображение: A → B; a1 → b1, …]`. A drawing that is
   not data stays `[схема: …]`.
2. **`pdf.py` draws them** in the document's ink on its paper, as it draws
   a graph: matplotlib, already a dependency.
3. **Measured on an album sent again** — record 97's — with the prompt set
   by `PROMPT_FILE` on Railway, against the photographs: production
   switches only if the drawings are right and the reading did not get
   worse (the two agreements, `docs/PLAN.md` → "Where the quality work
   stands").
4. The contract between the prompt and `pdf.py` changes — what is shared;
   the CEO's word is enough, the CPO told.

## Don't do

- No drawing redrawn from the model's description: what is drawn is what
  the data says.

---

# Task 95. A formula or a drawing with no word about it

**Owner: the CEO.** Specified on 2026-10-09, from record 97. Taken the same
day, the CEO's word, with every record read for its measurement; changed
while measured, the CEO's choice, from the explaining stage's first call
to a call of its own.

## Why

Record 97's second page opens on «A = B ⇔ a ∈ A ⇒ a ∈ B, b ∈ B ⇒ b ∈ A, A ⊂
B, B ⊂ A» with not a word on what it is — the notebook has none — and its
author asked for one. The explaining stage explains the hard places and
adds a teacher's boxes; a block with no caption is neither.

Asked in the stage's first call, `prompts-explain-v4.md` — v3 with
captions — the model wrote them right, record 97's set equality all three
times, and wrote fewer teacher's boxes: 57, 39 and 51 over seven
lectures, where v3 wrote 59 twice, one run beside v4 in the same hour —
the ideas of proofs most. So the captions have a call of their own and v3
stays as it is.

## Do

1. **A call of its own, `prompts-explain-captions-v1.md`**, made beside
   the stage's first call, at the same time, over the same numbered
   record: to a formula or a drawing the record says not a word about —
   no heading over it, no phrase leading into it — what it is, in two to
   five words, and one sentence on what it states or shows, anchored on
   the formula itself, a quote of it or its number, or on the drawing's
   description. A step of a working, and a formula or a drawing a phrase
   beside it names, get none. Thinking `low`. Read by name, as the
   searches' prompt is.
2. **Checked by code as an idea is** — no number the record does not
   carry, nothing that judges the record — **and standing at a formula
   set apart or a drawing**, where the document finds it
   (`pdf.on_formula_or_drawing`): at a line of words a caption would be
   an explanation printed without a source. A drawing is quoted with its
   brackets and a column of formulas whole, and both are found as the
   document finds them; a table is neither. Six a record at most.
3. **Printed as the bot's, over what it names**: «Что это · от бота»,
   over the formula or the drawing its anchor is in and the formulas
   right above it in one column, whichever one it quotes — never over the
   words before them, which name something else. Never at the end of the
   text: a caption that found no formula names nothing. Kept
   in `notes.explanations` as `kind: "caption"`, so the record's
   document, its study version and its lecture's carry it. The call
   failed, or its answer not the JSON asked for, and the record goes out
   without captions, the rest of the stage as it was.
4. Counted: `captions` and `captions_dropped` in `note_processed`
   ("Contracts") and the log line; the call's `ai_calls` row is
   `kind="caption"`; the startup log names its prompt and thinking.
5. **Measured before it ships**, on the CEO's word to read every record:
   v4 three times and v3 beside it on lectures 88 to 92, 97 and 99; then
   the call of its own on the same seven and on 94 and 98, which are not
   lectures — each caption, where it stands and what it says, read by
   the CEO. It goes to production with its deploy.
6. A record made before keeps its boxes: the stage runs once, when a
   record is made.
7. `CLAUDE.md` → "Stage three"; `BRAND.md` v1.12; `FINDINGS.md` →
   "Captions".

## Don't do

- No caption in the author's text: the box is the bot's, marked so.
- No search for a caption: it names what the lecture writes, as an
  idea's plan does.
- No change to `prompts-explain-v3.md`: the teacher's boxes stay as the
  CEO accepted them.

---

# Task 96. Equalities that hold, found not to

**Owner: the CEO.** Specified on 2026-10-09, from record 97. The check is
task 84's.

## Why

All three of record 97's equality findings are false:

- «$y = b + (-a) = x \Rightarrow x = y$», the end of a proof that a
  solution is unique, was taken for a definition of y, and two pages on
  «$xy \cdot (-1) \cdot (-1) = xy \cdot (-1) \cdot a$», where the author
  meant a = −1, was counted with y = b − a: two findings.
- «[зачёркнуто: $-x = (-1) \cdot x + x$]», which the author struck out,
  was checked — the check knows a struck span as `~~…~~` only — and its
  finding, anchored on a line the document does not print, went to the
  end of the text.

A false finding says the lecture is wrong where it is not, under the
bot's own mark: the one error this check must not make.

## Do

1. **A definition is a statement of two sides**, a letter and what it
   stands for — «положим h = b/3c» — never a chain of a working.
2. **A definition holds to the next heading**: a lecture's next statement
   uses its letters afresh.
3. **What the author struck out is not checked**, «[зачёркнуто: …]» too.
4. Measured over every record in the database, as task 84 was, on the
   CEO's word: the seven true findings kept, record 97's three gone.
5. `CLAUDE.md` → "An equality that does not hold"; `FINDINGS.md`.

---

# Task 97. What record 97 showed in the document

**Owner: the CEO.** Specified on 2026-10-09, from record 97.

## Why

- The axiom of completeness, framed by the author, printed as its source:
  «$$\boxed{\left.\begin{aligned} … \end{aligned}\right\} \exists c …}$$»
  — the frame took the escaped «\}» for its own closing brace.
- A frame round four lines with a blank line between them printed as
  «[рамка:», the lines, and «]».
- ℕ, framed alone, became main formula (3).
- The field axioms, written «1.1. | $(x+y)+z = …$», printed their «|».
- The record is titled «Лекция», what the reading called its first page,
  where the lecture begins «Глава 1. Введение в мат. анализ».

## Do

1. `pdf.boxed_contents` passes over «\{» and «\}».
2. A frame may hold a blank line (`pdf._frame_lines`).
3. An item's «|» after its number is not printed; an anchor quoting the
   line as read still finds it.
4. A title that names nothing — «Лекция», «Практика», «Конспект», a
   subject's name with one of them — gives way, in the document and its
   file's name, to the record's first heading that does. The record keeps
   its title.
5. `CLAUDE.md` → "The document"; `BRAND.md`.

## Don't do

- ℕ framed alone keeps its number: unnumbered, it would renumber every main
  formula after it, and an explanation stored with «(4)» would stand under
  another formula — records 90 and 97 carry such anchors.

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
| `drawings` | list of `[top, left, bottom, right]`, integers 0–1000 (v8 on) | `[]`; an element that is not four numbers with top above bottom and left before right becomes `None` in its place, so the ones after it keep their order |
| `lecture_starts` | list of strings, a line of `markdown` each (v9 on) | `[]`; anything not a string, or an empty one, is dropped |

`uncertain`'s element has exactly one required key — `text`. An element
without it is dropped silently, the whole response isn't discarded.

Extra fields are ignored. Prompt v3 returns `confidence` — deliberately
unused: the model's self-assessment turned out to be a useless signal.

## `PageInput`

Album buffer fields: `data`, `message_id`, `chat_id`, `media_group_id`,
`bytes_before`, `bytes_after`, `width`, `height`, `tag`, `file_id`.

A page enters the buffer as Telegram's reference: `file_id` set, `data` empty,
both byte counts 0. The update that claims the batch downloads the pages
(`handlers._fetch_pages`) once the album is known to be read, and fills `data`
and the byte counts then; a page that cannot be fetched stays empty and is
reported as a page that could not be opened. `width` and `height` are `None`
for an image sent as a file.

`tag` is the "#word" in that page's caption, `None` on most pages: Telegram
puts an album's caption on one page only. `albums.tag_of` takes the first one
in page order, and in a group chat an album without one is not processed —
unless a reply calls the bot on it, and then the reply's word is the tag.

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
| `drawings` | the `[схема: …]` lines recognition wrote | over every page read | — |
| `figures` | drawings cut out and placed (task 54) | over the record | — |
| `explain_judged` | explanations dropped for judging the record (task 55) | over the record | — |
| `compose_retried` | the guards refused the first composition and a second was asked for | the same, over the record | — |
| `compose_restored` | formulas the composer changed a number in, put back as read before the guards (task 82) | the same, over the record | — |
| `elements`, `elements_dropped` | the teacher's boxes kept, and those a check of code threw away (task 56) | over the record | — |
| `captions`, `captions_dropped` | the bot's captions to a formula or a drawing the record says nothing about, written by a call of their own, kept, and those a check of code threw away (task 95) | over the record | — |
| `lecture_head_cut`, `lecture_tail_cut` | — | lines cut off the first page and off the last (task 64) | — |
| `lecture_id`, `lecture_joined` | the lecture the record was filed into, and whether it had a notebook already — `None`, `false` with no subject (task 63) | the same | the same |
| `explain_skipped` | stage three not asked: the record joined a lecture whose base is fuller (task 63) | the same | `false` |
| `runs_added`, `read_further` | runs asked for beyond the three because one read a block the chosen did not, and whether a second run read it and the page was read further (task 65) | summed over the pages; `read_further` the pages read further | — |
| `album_parts` | — | the albums, and photos sent apart, that one send arrived as (task 81); `1` for an album that came whole | — |

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

`note_tagged`: `{"note_id": int, "tag": str, "lecture_id": int,
"lecture_joined": bool}` — the subject the user answered with, stored without
its "#", and the lecture the record was filed into: `lecture_joined` when it
had a notebook already (task 63).

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

## Event `note_summoned`

Written when a reply in a group calls the bot on a page or an album somebody
else sent (task 40). The one event to count to know whether the call is used.

    {"outcome": "read", "pages": 4}
    {"outcome": "existing", "note_id": 52}
    {"outcome": "reading"}
    {"outcome": "album_unknown"}
    {"outcome": "no_tag"}

`read`: the pages go through the pipeline, and `note_captured` and
`note_processed` follow as for any record. `existing`: a record of the same
pages was already made in the chat and was sent again, nothing spent.
`reading`: the same pages were being read for the chat at that moment — by
their own tagged album or by an earlier call — and the record goes to the
chat once, nothing spent (task 41).
`album_unknown`: the bot never saw that album whole, or saw it more than seven
days ago, and asked for it again with its subject. `no_tag`: the reply named
the bot without a subject and got a hint.

## Events `note_rated` and `note_feedback`

Task 70. `note_rated` is written on every press of «Хорошо» or «Плохо»
under a document; `note_feedback` when a reply to the bot's question «что
не так» comes in. The reader's words are in `feedback.text`, never in an
event.

    note_rated     {"note_id": 74, "rating": "bad", "changed": false}
    note_feedback  {"note_id": 74, "chars": 58, "photo": false}

`changed`: the person had rated the record before and pressed the other
button. `chars`: the length of what they wrote, a caption included;
`photo`: the reply carried a photo, a screenshot of the error.

## A group's week, and event `rating_posted`

Tasks 72 and 73. A week runs from Saturday 00:00 UTC to the next — from
Monday under task 72, until 2026-10-07. A record counts for
`coalesce(notes.sender_id, notes.user_id)` in the week of its `created_at`;
an отзыв is a `feedback` row, counted for its `user_id` in the week it was
created, however often its buttons are pressed again. `notes.sender_id` is
set only when the pages' sender is not the record's `user_id` — a reply's
call on somebody else's photographs. `groups.rating_week` is the Saturday the
group's last summed-up week ended on, `NULL` before the first; a Monday
task 72 left there is earlier than the Saturday the next week ends on, and
holds nothing back. `rating_posted` is written when a summary is sent, by
the bot on its own — `user_id` `NULL` — and never for a week with nothing in
it.

    rating_posted  {"week": "2026-10-03", "records": 14, "feedback": 9, "people": 4}

`week`: the Saturday the week summed up began on. `people`: everyone with a
record or an отзыв in it, the names past ten included.

## The group an event happened in

`events.group_id` is the group chat, `NULL` in a private chat — set on every
event a group's update writes, so a group's week can be counted from the
table alone. Three events are the bot's own membership:

| Event | payload |
|---|---|
| `group_joined` | `{"sees_photos": bool}` — false when privacy mode is on and the bot was added as an ordinary member, which is when the welcome asks to be made an admin |
| `group_promoted` | `{}` |
| `group_invited` | `{"via": "<payload>"}` — the `/start@<bot> add` a person's client sends into a chat after adding the bot through the button; not answered (task 47) |
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
`pages_used_today`, `consume` increments it, and there are minutes of
model work in between. Two parallel processing runs for the same user can
both pass the check, and the person goes past their day by up to an album:
soft, as the cost cap is. The count itself no longer comes out short: since
task 76 `consume` adds to the day in one statement, read and written by the
database, and `check_limits` writes nothing.

**The cost limit is soft.** `DAILY_COST_LIMIT_USD` is only checked before
processing starts, no budget is reserved. The cap can be exceeded by the
cost of one album — at current prices, that's cents.

**So is a group's day** (task 41). `DAILY_PAGES_PER_GROUP` is checked when
pages come, against the group's records already saved: two albums read at
once both pass, and the group goes past its day by up to an album.

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

- An app in the stores — after the Mini App is used (phase F)
- A targeted re-ask to the model about found discrepancies
- Payments, subscriptions
- Export to Anki, and any export of the corpus as data. A subject's course as
  one document to study from, sent on command, is task 52 — the one
  exception, made by the author on 2026-09-30
- Styling and design of responses
- The record's pages as PNGs for a phone, beside the PDF — `BRAND.md` sizes
  them; a second format of one document
- The QR code carrying `?start=note_<id>`, so the bot sees which record a
  newcomer came from; the visible name stays as it is
- "Школа × SUM": a school's logo beside the sign in the signature
- Caching, queues, workers, Redis — until the album buffer has to leave
  process memory (`CLAUDE.md` → Scale debt), and then Postgres first
- Merging the three runs block by block instead of picking the medoid.
  Two readings of every page are thrown away today, and on a matrix the
  majority per cell is exactly what you would want — but aligning blocks
  across runs is a second algorithm, `consensus` is a module we only call,
  and `graphcheck` already settles the matrix case better than a vote,
  because the graph beside it decides rather than the count
- Where a lecture begins and ends. The first page of an album often opens
  with the end of the lecture before — record 46 began with an
  associativity check from the week before "Практика" — and the last may
  close on the next one begun: record 62 ended on «A = ((0, 2) ∖ …» after
  the author's wavy line, which record 59, the same pages, left out. Every
  reading carries the first in and some the second; nothing on a page says
  where a lecture begins but a line, a date or a title, and one album is
  too little to make a rule of them — task 64 asks the model, which sees the
  page. The subject's base (63), lectures at their dates, is where the two
  halves could meet
- The lecture as structured material, not its digitization — the CEO's
  idea of 2026-10-06, specified the same day and archived: the CEO judged
  that it does not move the project's result. The document set out by the
  lecture's topics, not the lecturer's sequence: a significant topic with
  sections such as «Объяснение», «Ключевые понятия», «Почему?», «Примеры и
  применение» — examples, not a template — and its proofs and drawings in
  place; key concepts the author's words picked by code from the markup, an
  application printed only with its source, no icons. The design drafted:
  the author's text cut into units moved whole, a text-only call answering
  with their arrangement by number and the bot's own texts under its label,
  code checking that every unit is placed once; stage three becoming that
  call, the arrangement stored with the record
- Detecting a page photographed rotated. Nothing corrects one today:
  `images.compress` honours EXIF and a physically turned page carries none.
  Suspected of costing time on the model, never reproduced
- Deduplication on `update_id`
- Row locking, two-phase spend accounting
- Docker, CI
- End-to-end tests of the photo and document handlers — the unit
  suite was extended by decision, these were left out on purpose
  (see `CLAUDE.md` → Tests)
