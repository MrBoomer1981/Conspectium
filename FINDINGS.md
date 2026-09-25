# FINDINGS.md

The evidence behind the rules in `CLAUDE.md`: what was measured or what
failed, on which album, on which day, and what it did and did not settle.

`CLAUDE.md` keeps the rules and says each one's reason in a sentence; a
`→ "…"` after a rule there names the section here that holds its evidence.
`PLAN.md` → "Where the quality work stands" is how to run the next arm.

Read it as a journal rather than as a specification. Entries carry the model
of the day, because a finding that was true of `gemini-2.5-flash-lite` is
evidence rather than law about whatever the startup log names today. The first
part is the recognition experiments, in the order they were made; the second,
from "Unparseable answers" on, is what production cost before a pipeline rule
existed.

---

## The prompt's length

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

## The three arms

**Three arms on one album. A and B are run; C is not.**

| | `PROMPT_FILE` | `VISION_MEDIA_RESOLUTION` | `COMPOSE_ENABLED` | |
|---|---|---|---|---|
| **A** — baseline | `prompts-v4.md` | `unset` | `false` | run |
| **B** — the knob | `prompts-v4.md` | `high` | `false` | run, knob inert |
| **C** — two stages | `prompts-v5.md` | `unset` | `true` | not run |

One thing moves between arms; `VISION_CALL_TIMEOUT_S=90`, `VISION_MODEL` and
`IMAGE_MAX_SIDE` stay put. Compare **`numeric_agreement`**, not
`text_agreement`: v5 changes the shape of the text and `compare_text` measures
shape, which is the confound that made the v5 measurement unreadable the first
time. `ai_calls.tokens_in` confirms whether `media_resolution` applied at
all — more detail is more tokens for the same image. It said it did not, which
is why arm C carries `unset` rather than the `high` it was first written with:
a setting proven to change nothing does not belong in an arm that is trying to
measure something else.

Arm C moves two things at once — the prompt and the second stage — and that is
deliberate rather than an oversight: v5 exists *because* there is a second
stage to hand the formatting to, and running it alone would measure a prompt
with half its job removed. The cost is that a difference cannot be attributed
to one of the two without a fourth arm.

In arm C the first number to look at is how many records reached composition:
if `compose` refuses most of them, three arms come back looking alike and the
conclusion would be about the guard rather than about the architecture.
`compose_refused` and `compose_drift` are in the `note_processed` payload for
exactly that.

**Arm A, measured 2026-09-22 on a three-page album on quantum mechanics**,
with the timeout at 90 s and the frame check fixed: `text_agreement` 1.000 /
0.917 / 0.990, `numeric_agreement` 1.000 / 0.939 / **0.600**. The third page is
what the whole instrument was built for — the prose agreed to 0.990 and the
numbers to 0.600, and under the old rule it would have gone into the corpus as
clean.

**Arm B was run and the knob did nothing.** Same album, same evening,
`VISION_MEDIA_RESOLUTION=high` confirmed in the startup log. The check this
file specified — input tokens per image — came back *identical*: every call of
arm A and every call of arm B reports `tokens_in` of exactly 1809, min equal to
max in both. The instrument is a sensitive one, because 1809 is what every
photograph has cost since the prompt last changed; the number moves with
`PROMPT_FILE` (1609 on v3, 1809 on v4, about 200 words apart) and not with the
picture. So the image contributes a constant, any change in tiling would show,
and none did. Either `gemini-3.8-flash` ignores the field, or at
`IMAGE_MAX_SIDE=1500` there is no detail left for a higher setting to keep.
**`media_resolution` is not a lever on this model at this image size**, and the
arm-C comparison should not carry it as though it were.

**What arm B did measure is the instrument at rest, and that is worth more.**
Two runs of what turned out to be the same configuration, on the same album:

| | mean `numeric_agreement` | worst page | mean `text_agreement` |
|---|---:|---:|---:|
| arm A | 0.846 | 0.600 | 0.969 |
| arm B (same settings) | 0.873 | 0.619 | 0.974 |

So the mean of `numeric_agreement` wobbles by about **0.03** between two runs
that differ in nothing. Read against the v3 → v4 shift of 0.048 in the mean of
`text_agreement`, that is not a comfortable margin: an arm that moves the
numeric mean by less than 0.03 on one album has said nothing. `text_agreement`
is quieter here, 0.005 between the two, which matches this file's earlier note
that its mean reproduces to a thousandth. The two numbers do not have the same
noise floor, and the noisier one is the one the arms are compared on.

**Arm C was run, and the second stage accepted the text without composing
it.** Same album again, `prompts-v5.md` and `COMPOSE_ENABLED=true` confirmed in
the startup log, `compose_refused` null and `composed` true in the event. The
guards passed it because there was nothing for them to object to:

```
compose: accepted, 1536 -> 1538 chars, word drift 0
```

Two characters on fifteen hundred and a word multiset that did not move is the
signature of a stage that returned its input. The record it produced carries
*less* markup than the one-stage record of the same album:

| | headings | bold | display formulas |
|---|---:|---:|---:|
| arm A/B — v4, one stage | 7 | 1 | 5 |
| arm C — v5 + compose | **2** | **0** | **2** |

v5 did its half correctly: flat text is what it is for. Nothing lifted it back.
So arm C says nothing about the two-stage architecture yet — it measured a
composer that did not compose.

On reading, arm C is inside the noise: mean `numeric_agreement` 0.889 against
arm B's 0.873, a difference of 0.016 where two runs of one configuration
differed by 0.027. `text_agreement` fell 0.974 → 0.922, which is the confound and not a
finding — v5 changes the shape of the text and `compare_text` measures shape.

## The composer

**The diagnosis is the prompt's own shape, and it is the finding worth
keeping.** Of ten rules in `prompts-compose-v1.md`, **eight are
prohibitions** — don't change a number, don't fill in the mark, don't add
words, don't touch the author's mistake, don't make a list of an ordinary
phrase, leave this verbatim, keep that. Two say what to do. A model told eight
times to change nothing satisfies all eight most safely by returning the input,
which is exactly what the log shows.

What makes that fixable rather than a dilemma: **the code already guards those
prohibitions.** Numbers, `[неразборчиво]`, and length are `_refusal`'s job, and
a rule the code enforces need not also occupy the prompt. This is the same
economy as the recognition prompt — every extra rule steals attention from the
main task — except here the main task is markup, and v1 barely spoke about it.
`prompts-compose-v2.md` inverts the ratio: seven rules about what to do, one
worked example, and only the three prohibitions nothing in code watches — don't
write your own text, don't change words, leave `[граф: ...]` alone.

**`prompts-compose-v2.md` moved it, and not far enough.** Same album a fourth
time, `compose: accepted, 1505 -> 1519 chars, word drift 2`:

| | headings | bold | display formulas |
|---|---:|---:|---:|
| v4, one stage | 7 | 1 | 5 |
| v5 + compose v1 | 2 | 0 | 2 |
| v5 + compose v2 | **4** | **1** | **3** |

So the prompt's shape was a real cause: inverting the ratio of bans to
instructions doubled the structure the stage produces. It is still short of
what one stage does on its own, and the way it falls short is the tell — the
rules are applied in some places and not others. Two sections keep their
heading and two do not; one pair of lines is joined into a sentence and the
next pair is left broken; the bold lands on `Волновая **ф-ция в квант.
механике**` instead of on the term. That is not a prompt that failed to say
something, it is a model applying what it was told about half the time. The
next suspect is `COMPOSE_MODEL`, which is `gemini-3.5-flash-lite` — the
weakest model in the system doing the job that was supposed to justify a
second call.

**It was the model. `COMPOSE_MODEL=gemini-3.8-flash` composes.**

| | headings | bold | display formulas |
|---|---:|---:|---:|
| v4, one stage | 7 | 1 | 5 |
| v5 + v2, flash-lite | 4 | 0-1 | 3-5 |
| **v5 + v2, 3.8-flash** | **7** | **6** | 4 |

Same prompt, same album, same everything else: the headings match what one
stage produces and the bold lands on six terms instead of one. The two-stage
architecture works, and what it was waiting on was neither the prompt's length
nor its shape but a model strong enough to hold ten rules at once.

**What it costs is the finding to keep.** That single formatting call thought
**15079 tokens to produce 593** — twenty-five to one, 41 seconds, and
**$0.0298**, two thirds of what all nine recognition calls of the same album
cost together ($0.0450). The album went from about 4.7 to 7.5
cents and from 22 to 61 seconds, for markup over text that was already correct.
Note also that 15672 output tokens would have been **truncated under the old
8192 ceiling**: the raise made an hour earlier for recognition is the only
reason this call returned at all, and a truncated composition would have been
refused by the length guard and silently thrown away.

`VISION_THINKING_LEVEL` does not reach this call — `compose._one_call` builds
its own config and sends no `thinking_config`. If a thinking cap is ever worth
having, this is the call that wants one first: transformation over trusted text
is the job in this system with the least to think about.

**And it over-structures, which is the predicted failure and worth watching.**
`Спектры атомов (полосочки) для каждого атома уникальны` is one sentence; the
composer split it into a `##` heading and a body line. Same for `Волновая
ф-ция ($\Psi$)`. Rule 1 says a section heading, and the model is deciding what
a section is — interpretation, on a page it cannot see. It is the mild version
of the failure this stage exists to avoid, it is checkable by eye, and no guard
in `_refusal` looks for it.

## What the arms left open

**A suspicion the arms left behind, deliberately not called a finding.** Across
every album run on 22-23 September, mean `numeric_agreement` by prompt:

| prompt | albums | mean of the means |
|---|---|---:|
| v4 | 0.846, 0.873 | 0.860 |
| v5 | 0.889, 0.980, 1.000, 0.894 | **0.941** |

Every v5 album scored above every v4 album, and the 0.08 gap is three times the
0.027 the instrument wobbles by at rest. That is the shape of a real effect —
and it is four observations against two, on one album of one subject, with one
v5 page scored on two runs instead of three, which makes agreement easier. **It
is a reason to run two more v4 albums, not a reason to believe v5 reads
better.** Whoever picks this up: the arms are paused here on purpose, not
finished. `PLAN.md` → "Where the quality work stands" is the way back in — what
the deploy is running, how to run that arm as a one-variable one, what must not
move while it runs, and the three gaps in the instrument found while writing it
down.

---

**What production cost.** Each section below is the failure a rule in
`CLAUDE.md` was written against, kept here so that file can state the rule in
a sentence. The section names are the ones `CLAUDE.md` points to.

## Unparseable answers

**A lost run used to cost a tap and now costs the album.** An answer that
would not parse was never retried, reasoned from a cost the pipeline no longer
has: a lost run cost a tap of "try again" then. One album on 2026-09-23 spent
four of its fifteen runs on unparseable answers, one page lost all three, and
nothing was saved; eleven calls in the same minute parsed fine. That is why
the call is made again now.

The finish reason and the shape of the answer went into the `ai_calls` row
because three different problems — our own ceiling, a model that answered
without JSON, a refusal — used to arrive as one sentence, and "not JSON at
all" and "JSON without a `markdown` field" read identically while having
different fixes.

**One output column hid the truncations.** `max_output_tokens` is shared by
the visible answer and the model's thinking, and the table recorded only the
first. A call stopping at the ceiling with 498 visible tokens looked exactly
like a short answer, for a week, and the price of that call was understated
fifteenfold — which is the daily cap's problem rather than the log's. Hence
`tokens_thought` and the raised ceiling; the diagnosis and its queries are in
`PLAN.md` → Known risks.

## The two agreement numbers

`numeric_agreement` lived in the log alone at first, which made comparing two
prompts a grep through Railway's logs — and those roll off, so an arm measured
last week stopped being checkable. Both numbers are columns on `notes` now,
each the album's worst page, and the worst page is rarely the same one twice:
on the album of 2026-09-22 the text minimum came from page 2 and the numeric
minimum from page 3, which is the whole argument for keeping both.

`difflib`'s autojunk heuristic is off because, left on, it calls the common
digits noise: a page of matrices is hundreds of numbers drawn from a handful
of digits, and it reported four changes in four hundred as total
disagreement.

## What `uncertain` came back with

The prompt asks for places where a symbol "действительно читается двояко".
One album came back with seven entries and not one named a second reading:
"слово обрезано краем страницы", "написано на полях", "частично смазано" — the
state of the paper, and in one case a word that had been read in full. Stating
the test in the prompt did not work, which is why `vision.meaningful_uncertain`
enforces it in code.

## Pages refused for their layout

**The `rejected` band was measuring layout and calling it illegibility.** The
bands are `text_agreement`, which compares markdown and therefore measures how
a page was laid out rather than how it was read. That was sound while the
prompt prescribed the layout; `prompts-v5.md` deliberately hands layout to the
composing stage, and the bands stayed where task 6 put them. On 2026-09-23 a
five-page album lost two pages at `text_agreement` 0.428 and 0.419, and under
"a record is all its pages or none" the other three went with them: $0.085 of
paid calls, five photographed pages, nothing saved. The frames were fine —
sharpness 4033 and 3257 against a threshold of 90, the page filling 96% of the
frame — and the text on them is perfectly legible. The numbers those runs
extracted were **identical**: `consensus.compare` reported not one divergence,
not even a number against a gap.

It produced two rules in turn. First the numbers were allowed to vouch for a
page (task 29); then a `rejected` band stopped dropping a page at all (task
32), which left the vouching to decide only whether a kept page is flagged as
read without a second opinion.

`_VOUCH_MIN_NUMBERS` is 5 because the corpus's median page carries 7.5 numbers
and its thinnest albums 5.7, while agreement on one or two numbers is cheap.

## Numbers the agreement could not see

**A digit barely moves `text_agreement`.** Two runs reading a matrix cell as 6
and as 8 differ by one character, so the page came back `clean` with the
disagreement sitting in it — twice in one evening's logs. That is why a
surviving numeric divergence downgrades a page.

**Most reported divergences were not misreadings.**
`consensus.extract_numbers` treats every numeric literal as a value to
compare, list markers and subscripts included, so `compare()` reports a
divergence wherever the runs happen to align differently. On a real page of
lecture notes that produced eight reported divergences of which one was
genuine; without `vision.meaningful_divergences` every record would have worn
the flag. The filter's two later rules — a position with no majority and a
gap among its variants is dropped, an identical line is printed once — came
from a second album.

**The uncertainty sits on the matrices.** Of six numeric divergences in one
album, five sat on the single page with two hand-drawn matrices, and every one
of them was a single digit. Whether a cell is 0 or 1 is not a matter of
opinion and not something a vote can settle — the edges of the graph beside
it decide, which is what `graphcheck` was built to use.

## The album that came back as four records

Telegram never says how many items a media group holds, so the album buffer
closes on silence. Timed from the moment a page had *downloaded*, that silence
measured our own network speed: the first page to finish fetching claimed the
batch while the rest were still in flight, and each of them then opened a
record of its own. It happened twice on the deployed bot — a four-page album
came back as four records, each with its own reply, its own PDF and its own
three paid recognition runs. No value of `_QUIET_SECONDS` survives timing the
downloads; timing the announcements, which Telegram delivers milliseconds
apart, does.

## Albums lost over one page

A record used to be all its pages or none, and the reason was sound: a page
silently left out made the record read as a whole one, with nothing in it to
say what was gone. The cost turned out to be worse than the disease — on
2026-09-23 two five-page albums were lost in one evening over a single page
each, and in a group chat a lost album is a course without its lecture. The
reason was kept and the remedy replaced: the hole is named in the document.

## The sentence cut by a page edge

Pages are read one at a time and joined by a rule, so a sentence the author
carried onto the next sheet came out as two halves with a horizontal line
between them — "Если граф ориентирован, то ребро" / `---` / "учитывается один
раз". Nothing downstream repaired it: the composing stage sees the rule as the
hard boundary it is, and by then it is right to. Checked against the record
that prompted it, `albums._continues` fires on that one seam and stays quiet
on the other three of the same album.

## mathtext, one record at a time

**Three rounds cost three records.** `\sum\limits_{i=1}^p` went out on a
deployed record as raw backslashes while the same sum written `\sum_{i=1}^p`
drew perfectly two pages later. Then `\le` and `\ge`: every inequality on a
page about nested intervals went out as raw source while the formulas around
them drew. Then the environments: `cases` is ordinary mathematics, and on
2026-09-23 it went out on a real record as a line of backslashes. Only then
was mathtext asked the whole question at once — about 120 constructs put
through `pdf.for_mathtext` and then through the parser — which produced the
table in `CLAUDE.md`. What had been missed about the environments is that
mathtext *does* have `\substack`, which stacks rows at full size, and
`\left...\right`, which puts a delimiter around them.

`\xrightarrow` mattered most for these notes: an arrow with its condition
written above is most of the reactions on a page of biology.

**All three rounds were found by the author, not by the log.** The line
reporting a refused formula existed the whole time at `logger.debug`, and
`LOG_LEVEL` is `INFO` — produced and thrown away. It is a warning now.

**A longest-first sort of the drop list survived every mutation**, which is
what dead sophistication looks like: the boundary `(?![A-Za-z])` already makes
a short match fail where a letter follows, so `\bigl` backtracks out of `big`
on its own.

## Why reading and composing are two calls

Sort the failures of the first model into the ones where it *misread*
something and the ones where it *interpreted*: a semicolon read as a letter
and a digit in a hand-drawn matrix are perception; the fluent retelling of a
distant photograph, "possibly a typo by the author", the silently fixed
arithmetic, the invented discrepancy, `confidence: 0.95`, and `uncertain` as a
complaint about the paper are all the interpretive faculty leaking into the
literal job. Six of eight. They were fought with words in the prompt — "не
пересказывай", "не дополняй", "не исправляй" — and every such word also stole
attention from the reading. So the interpretive half got a call of its own,
over text, with no photograph to invent from.

## Headings the composer invented

The split is not a judgement call: the composer writes the same content
correctly elsewhere in the same corpus — `**Принцип неопред. Гейзинга**: если
мы знаем…` as a bold term and a colon in one record, and as a heading with the
sentence running on below it in another. The page did not change; the markup
did. Measured against the whole corpus the day `_demote_invented_headings` was
written, it takes **11 headings of 111**, each a case already named by hand.
It repairs rather than refuses because a refusal costs the whole composition:
note 36 had two invented headings among nine good ones. Which topics had
already reached the corpus is in `PLAN.md` → "Fixed since: the sections the
composer invented".

## The line height photoguard could not measure

**The sentinel was read as a measurement.** `photoguard` refused a good page —
sharpness nineteen times its threshold, the page filling 97% of the frame —
three times, with byte-identical numbers. `_line_height` returned `0.0` when
it could not build a line profile at all, and `0.0` was read as a very small
line. A page written *large* has few lines, so it sat nearer that cliff than a
page written small: the check was inverted exactly where it mattered, and
while a record was all its pages or none, one such page cost a whole album.
Production confirmed the fix: `PLAN.md` → "What production says".

**Then the bench showed the estimator could not measure an ordinary page at
all.** It thresholded ink at the 35th percentile of brightness, and a real
page is about 5% ink, so the threshold landed on the paper, the mask covered
the whole sheet, the profile came out flat and the answer was the sentinel.
Every synthetic page — 28 px pitch to 260 — came back 0.0. The pitch was the
height of the paper region over the number of lines, and on a page with a
drawing mean and median spacing ran 2.5 to 16 times apart. The replacement was
chosen against pages whose pitch is known by construction rather than against
anybody's impression of a photograph, and it lands within 5% from 28 px to
220 px, on pale ink, on a dark photograph and with a drawing on the page.

## What a model change broke

**The timeout.** 30 s was tuned against a model that answered in about six
seconds; a slower one turned every call into a timeout — three attempts wasted
per run and pages of an album silently dropped — and the log of that failure
carried nothing but empty error messages, because `str(TimeoutError())` is
`""`. That is why `VISION_CALL_TIMEOUT_S` is a setting.

**The price.** `gemini-3.8-flash` ran unpriced under `ALLOW_UNPRICED_MODEL`
from the model change until 2026-09-23, so every `ai_calls` row it wrote
carries `cost_usd = NULL`, and no recomputation will recover them — the tokens
are there, the price of the day is not. Priced at 0.375 in / 1.875 out per
Mtok, a three-page album costs about **4.2 cents**: 14481 tokens in, 19807
out, and **two thirds of the bill is thinking**. At `DAILY_COST_LIMIT_USD=5`
that is roughly 117 albums a day, so the cap is not binding at this volume.

**The warning.** The validator checked both models from the day `compose`
shipped, while the warning that stands in for it under `ALLOW_UNPRICED_MODEL`
named `VISION_MODEL` alone, so swapping `COMPOSE_MODEL` for an unpriced one
started in silence with half the day's spend writing `NULL`. Hence one list,
read twice.

**The label.** The startup log named the prompt, the compose model, both call
knobs and all four timeouts — and not `VISION_MODEL`, the attribute every
finding carries and the one that had already changed twice, retiring a page
of them.

## The document as the group got it

Records 37–40, rendered on 2026-09-24 with the code of the day and laid beside
the author's own write-up of the same lecture on graphs, before task 36:

- **Markup printed as its source.** Record 39 carried seven display formulas
  as `$$`, the LaTeX, `$$` again: the composing stage writes the dollars on
  lines of their own, and the parser read line by line. `$$…$$ — формула
  Ридберга` left a dollar at either end (records 30, 32, 33), `~~она~~` went
  out with its tildes on six records of twelve, and `**…$n$…**` with its
  asterisks. A remark quoted `\rho^-(v)` as source, because `uncertain`
  quotes the inside of a formula without its dollars.
- **A line could not be told from a paragraph.** 4 pt under every line and
  9 pt under a paragraph, at a leading of 1.7: a record composed line by line
  read as double-spaced.
- **Ten records of twelve were `needs_review`**, so nearly every document
  opened on a tinted panel, and the tint had stopped meaning anything.
- **Things came apart across pages.** "Пример" stood at the foot of a page
  with its graph on the next one; "A =" sat alone on a line with its matrix
  further down.
- **A graph was drawn in a square as wide as its layout circle**, a third of a
  triangle's picture empty under it, and a matrix was a wall of boxed cells.
- **Nothing on a printed page four said which lecture it was.**

Two traps in reportlab were met while fixing those, and each shaped the code.
`keepWithNext` wraps a heading and the flowable after it in a `KeepTogether`;
when that flowable is itself a `KeepTogether` — a line with its remark, a
whole table — the inner one reports its height as 0xffffff and the heading
stays behind. "Пример" was still orphaned with `keepWithNext` set on its
style, which is why the groups are built by hand and never nested. And a line
is not broken at a space that follows an inline image: once a long formula was
shrunk to the column, the word after it stayed on its line and ran off the
paper, 15 pt past the edge in a bench case. A zero-width space, which DejaVu
carries at zero width, is a place reportlab does break.

**Record 42 came back heavy, and the reference moved.** The first record
rendered after task 36 was a page of complex numbers, and the author called it
heavy beside `матан 24.09.2026.pdf`, a write-up of their own set in Lato and
KaTeX. Laid side by side the difference was the faces rather than
the layout: DejaVu Sans and DejaVu Serif are dense and dark, and the table the
composing stage had used to put two columns of algebra side by side came out
as a ruled grid of 9 pt type with `<br>` printed in its cells. The reference's
own numbers were read out of the PDF — Lato 12 pt at 1.6, `#24292f` and
`#6b7480`, a 3 pt `#d0d7de` bar, a 463 pt column — and copied. Two more traps
were met on the way. Computer Modern drawn as pixels came out a pale grey
beside vector Lato, which a quarter-point stroke evens out; and reportlab's
frame pads its content by 6 pt inside the page margins, so the column had
always been 12 pt narrower than every width computed from it, and a box as
wide as the column ran past its right edge by that much.

## What the model did with a search tool

Stage three was built as one call with Google Search switched on, and on
2026-09-24 it was run against record 43 from inside the production container
before being turned on for anyone. `gemini-3.8-flash` answered well — seven
explanations and an accurate summary in 30 s for $0.014 — and searched for
nothing: no grounding metadata at all, so every explanation would have been
dropped by the rule that an explanation needs a source.

Three variants and the same answer. Telling it to check every explanation
with a search changed nothing. Asking for a verbatim quote from the found
source produced quotes — one read "U(1) (унитарная группа порядка 1) в
математике — мультипликативная абелева группа всех комплексных чисел, равных
по модулю единице", in the voice of an encyclopedia — with, again, no search
behind any of them: text from memory, formatted as a citation. That is the
failure the source rule exists for, and the rule caught it, because it reads
sources from the grounding metadata and not from the answer. A single call
asking for sources for all seven explanations at once came back empty.

The same model searches reliably when a short question asks it to — "what is
today's rate", "find the definition on Wikipedia" — and one call per
explanation, "find a source that confirms this", grounded seven of seven:
mccme.ru, spbu.ru, bmstu.ru, mephi.ru, wikipedia.org and others, 26 s in
parallel, $0.041 of tokens. That is the design now: one call writes, one call
per explanation searches.

One more thing the live runs showed. Without the strict JSON mode, which the
search tool cannot be combined with, the model now and then wrote LaTeX into
a JSON string with a single backslash: "\varphi" made an answer unparseable,
and "\frac", "\rho", "\text", "\nu" are escapes JSON has, which parse into a
form feed, a carriage return, a tab and a newline without a word. The writing
call is strict JSON now, and the parser repairs lone backslashes anyway.

Of the diagnostic calls made that evening, one is not in `ai_calls`: the
script that made it failed on the unparseable answer before writing its row.
About $0.015, and no row was invented to stand in for it.

**The sources, ranked (2026-09-25).** The first run with the stage switched
on, record 43 on 2026-09-24, grounded five explanations of seven, and printed
their sources in the search's own order: `codechick.io` ahead of `nsc.ru`
under one explanation, `academic.ru` ahead of `ox.ac.uk` under another, and a
file on `githubusercontent.com` and a shop's page, `my-shop.ru`, ahead of
`studfile.net` under a third. The author's decision was to rank rather than
to filter.

The second run, the same record with the sources ranked and the search asked
for universities and scientific publications first
(`prompts-explain-source-v2.md`), grounded seven of seven, and six of the
seven explanations opened with a university's site — `spbu.ru`, `msu.ru`,
`hse.ru`, `unn.ru`, `bsu.edu.ru`, `eku.edu`. One run each, so the difference
in grounding is an observation, not a measurement. Eight calls, $0.307, of
which $0.245 was the grounding fee on seven searches; the longest search took
45 s.

It showed two things the code now holds. The Gemini API names a site by its
registered domain — `wolfram.com`, `msu.ru`, never `math.msu.ru` — so a list
written in hostnames matched nothing, and the tier lists are written in
registered domains. And a site the search returned twice was printed twice
under one name, "wikipedia.org, wikipedia.org" and "unn.ru, unn.ru", which a
reader takes for a duplicate; an explanation carries one link a site. Replayed
through the new code, that run's searches give every explanation distinct
sites, a university's first wherever the search found one.

## Record 45, a lecture on remainders

On 2026-09-25 the author sent five pages of a lecture on congruences and
polynomial division — `gemini-3.8-flash`, `prompts-v6.md`, compose v3, stage
three on — and said the quality had dropped sharply. It had, and nearly all
of the drop was the document failing to draw what the page said.

**27 of the record's 93 formulas printed as their own source.** Put through
the renderer one by one: 21 for `\pmod`, which mathtext does not know and
which a lecture on remainders writes on nearly every line; five long
divisions written as `\begin{array}{l|l}` with `\cline` — mathtext draws no
rules at all; and one `\phantom{... корня "c"}`, refused for the double
quote, not for the Cyrillic. The title carried `$2^{1001}$` onto every page
head, and the file went out as `45-Найти-остаток-от-деления-21001.pdf`.
Re-rendered from the production row after task 42: none refused.

**"¤extbfполином" was mathtext, not the JSON.** The first reading blamed the
recognition parser, which had no repair for a LaTeX command written with one
backslash; the stored markdown carries `\text{ - \textbf{полином}}` intact.
Inside `\text` mathtext reads no command at all: the backslash comes out as an
empty box and the name as letters. The bold word is now lifted out of the
`\text` round it into `\mathbf`. The parser did need the repair anyway, on
other evidence: over the four days before, 17 of about 280 recognition calls
on `gemini-3.8-flash` came back unparseable, 9 of them with
`finish_reason=STOP` — the model finished and the JSON did not read, which is
what a lone `\pmod` or `\varphi` does to it.

**A congruence was read as a chain of equalities.** mathcheck compares
neighbouring numbers on any line with two "=", so
`1001 = 12·83 + 5 ⇒ 2^1001 = (2^12)^83·2^5 ≡ 1^83·2^5 = 32` set 1001 against 32
across an implication and a congruence, and the record carried a critical
"звенья цепочки не сходятся" and `needs_review` for it.

**The missing page was refused by a hair.** Page 1 was turned away as
"Текст мелкий": line height 19.75 px against `MIN_LINE_HEIGHT_PX` = 20,
sharpness 1682, the sheet 71% of the frame. The four pages read from the
same notebook at the same distance measured 22.75 px and read well. The
photos arrived at 960×1280 — Telegram's own compression of a photo — and this
notebook is written densely: every earlier record measured between 54 and
213 px. A synthetic page on squared paper measured the handwriting's pitch,
not the grid's, so the number was real, not the paper's. Retaken from the same
distance it would have measured the same. The bot's reply named the page and
the reason, then said "send it separately and it will be a separate record";
the author read that, rightly, as not being asked to retake it. Offered the
choice between delivering at once and inserting the retaken page later, or
asking first, the author chose asking first: every frame is now checked
before the album is read, and a refused one brings the album back unread and
unpaid (task 43). The threshold went to 16 px, below the 19.75 that was cut
off and above the 15.0 of the one single photo refused so far.

**What it cost.** $0.337: twelve recognition calls $0.080, composition $0.021,
the explaining call $0.013, and six grounded searches $0.223 — two thirds of
the record, almost all of it the $0.035 fee a search.

## What a record costs

**The accounting was wrong in both directions until 2026-09-25.** Checked
against the price page that day: `gemini-3.8-flash` bills a plain call at the
Standard tier, $0.75 in and $3.75 out per million tokens through 2026-12-31
and double that from 2027-01-01. The $0.375 / $1.875 set on 2026-09-23 "from
the published rate" is the Batch and Flex row, which this bot never asks for.
Every row since carries half its real token cost, and `DAILY_COST_LIMIT_USD`
let through twice its figure. The search fee went the other way: the $0.035
per grounded call is Gemini 2.5's price per prompt, while a Gemini 3 model is
billed $14 per 1,000 search queries it runs, with the first 5,000 a month free
across the key. At this bot's volume — 24 grounded calls in two days — the
searches have so far cost nothing at all, and "two thirds of record 45 was the
search fee" was an artefact of the old constant.

**Re-priced, record 45's tokens were about $0.25**, not $0.11: recognition
$0.160 over twelve calls, composition $0.042, the explaining call $0.025, the
searches' own tokens $0.027. Its searches ran at least six queries — about
$0.08 once the free 5,000 are used up.

**Most of the token spend is thinking.** Over the two days before, thinking
was 67% of what a recognition call produced (2135 tokens of 3177), 85% of a
composition's (12388 of 14525), 83% of the explaining call's and 91% of a
search call's (2913 of 3200): the call that only has to find a page and quote
one sentence from it thinks nine tokens for every one it writes. Thinking is
billed as output.

**Thinking `low`, measured on record 45 the same day.** Its five
explanations were searched for twice each, at the model's default and at
`low`:

| | default | low |
|---|---|---|
| explanations grounded | 5 of 5 | 5 of 5 |
| search queries run | 14 | 8 |
| cost, fee included | $0.268 | $0.115 |
| one search | 16–32 s | 4–7 s |

The sources were of a kind: mathnet.ru, msu.ru, kpfu.ru, berkeley.edu at
`low`; hse.ru, mathnet.ru, msu.ru, tusur.ru at the default. `minimal` is
refused by `gemini-3.8-flash` with a 400. The composing call, given record
45's text with the composer's own markup taken off, came back at `low` with
the same ten headings and two frames as at the default — two lines differed,
a bullet where the default wrote `$\cdot$` — for $0.015 against $0.033, in
9 s against 24. One record each: an observation, but the price and the time
are the structure of the call, not noise.

**Ten probe calls are not in `ai_calls`.** The script that ran the first
thinking-level probe on record 45's explanations called a function the
deployed code did not have yet, after the calls had returned; the rows were
never written. About $0.15–0.30, and no rows were invented to stand in for
them.

**Recognition at `low`, once (records 46 and 47, 2026-09-25).** The author sent
the same five pages twice: record 46 at the model's default thinking, record
47 with `VISION_THINKING_LEVEL=low`, everything else equal.

| | 46, default | 47, `low` |
|---|---|---|
| recognition, 15 calls | $0.185 | $0.125 |
| thinking a call | 1580 tokens | 468 tokens |
| worst page, numeric agreement | 0.809 | 0.550 |
| worst page, text agreement | 0.488 | 0.700 |
| numeric divergences / uncertain spots | 6 / 4 | 7 / 7 |
| pages read without a second opinion | 4 and 5 | none |

The numbers read on the page were the same where the two could be set side by
side; what moved the numeric agreement was the long divisions, whose digits
inside `\cline{1-1}` and `\phantom{...}` that instrument counts as numbers —
it was confounded on exactly the page it scored worst. What decided it was the
document: at `low` the model wrote environments bare across lines with no
`$$`, opened a `$` on one line and closed it on another, used `tabular` for
two columns of working and put Russian words inside a formula, and all of it
printed as source. The author had called record 46 "much better". One album:
an observation — enough to leave recognition at the default, not enough to
say `low` reads worse.

**Three of the six searches at `low` on record 47 ran no search at all.**
Their cost was the tokens alone, about $0.001, and their explanations were
dropped for having no source; record 46, searched at `low` an hour earlier,
grounded six of six, and no call at the default has yet skipped the search.
Such a search is now made once more at the default.

**Record 47's loose formulas, drawn (task 45).** Put through the renderer, the
record printed 103 lines as LaTeX source and refused no formula — the lines
never reached mathtext at all, because nothing in them said they were one: the
environments carried no dollars, and a `$` opened on one line closed twelve
lines later. Joined into formulas, with the `tabular` drawn as a table of text
and the Russian words inside a formula set as words, it prints none; records
45 and 46 printed none before and none after.

**Stage by stage (record 46, 2026-09-25).** Five pages; recognition at the
model's default, composition and the source searches at `low`; the Standard
tier's prices.

| stage | calls | tokens in / out / thinking | cost |
|---|---|---|---|
| recognition | 15 | 24 660 / 20 767 / 23 693 | $0.185 |
| composition | 1 | 4 133 / 3 629 / 0 | $0.017 |
| explanations, writing | 1 | 4 133 / 943 / 1 970 | $0.014 |
| explanations, searches | 6 | 1 079 / 1 313 / 0 | $0.006 |
| search queries | 7 | | $0.098 |

$0.222 in tokens, $0.320 with the queries: $0.044 and $0.064 a page.
Recognition is 84% of the tokens' bill — its thinking 40%, its visible answer
35%, its input 8%. Over the 178 recognition calls on `gemini-3.8-flash` that
recorded their thinking, the average call is 1 631 tokens in, 939 out and
2 148 thinking: 63% of a call's price is thinking, billed at the output rate.

The queries are counted and, at this volume, not billed: the first 5,000 a
month are free, and the bot runs a few hundred. `DAILY_COST_LIMIT_USD` counts
them on purpose, so the counted price of a record stands 45% over the bill
until the volume reaches the free allowance.

**What the answer is made of.** Counted with the API's own tokenizer on
record 46: the markdown is 3 630 tokens, 3 897 as the JSON string it travels
in; the doubtful spots 251; the recognition prompt 580. A run's answer came to
about 6 900 tokens, and about 2 200 of them — by difference — were the list of
numbers the prompt asks for, numbers the markdown already carries: a third of
the answer, three runs a page, read by nothing but `numeric_agreement`.

**Failures are not where the money goes.** 31 of 399 calls on
`gemini-3.8-flash` failed — timeouts, unparseable answers, five 400s from
probing "minimal" — and their tokens cost $0.111 of $4.25.

**Flex, read on 2026-09-25.** `service_tier: "flex"` bills every token at
half the Standard price on the same model, `gemini-3.8-flash` included, for a
target latency of 1–15 minutes a call and best-effort capacity: 503 or 429 when
it runs short, with no fallback to Standard. The page does not say whether
grounding runs under it. Every ceiling here is sized for Standard, and the
choice — a record in minutes or a record at half the price — is the author's.

**Record 47 against 46, checked on the photographs.** The same five pages read
at `low` (47) and at the default (46). About 575 numbers, every one read alike.
Ten places differed in words and marks, and the author checked them against
the photographs. The default was right in five: `low` put a strike-through
over two notes and a frame round "III" that are not there, called an
illegible word crossed out, wrote "=" where a line ended in "≡", and lowered a
capital X. `low` was right in one ("≡" between 16¹¹¹¹ and 5¹¹¹¹, where 46 wrote
"="); three were ties and one answer was unclear. `low` is rejected on reading,
not only on layout; `medium` is the next arm on the same album. Both readings
carried the tail of the previous lecture into the record, and both misread
the heading "Полная теория Ферма".

**Record 48 against 46: `medium`, the same album again.** Recognition thought
19 836 tokens against 23 693 at the default and 7 026 at `low` — `medium`
thinks almost as long as the default — and cost $0.172 against $0.185, 7% less.
Where the answer is known it read worse than the default: a lowered capital
X, as `low` did; "[зачёркнуто]" put before a "≡" where nothing is crossed out;
and the two notes the author did not cross out left out altogether. Three
things 46 and 47 had read alike it read otherwise — "4b" as "ab", "по модулю
7" without its 7, "9)" as "1)". It kept the "≡" at a line's end, the
"[неразборчиво]" and an unframed "III". Closed: recognition stays at the
model's default, and a lower level buys back 7% at best for reading worse.

**Record 49 against 46: `prompts-v7.md`, the same album again.** The answer
without the list of numbers and the doubtful spots, at the default thinking.
The visible answer fell as predicted — 11 669 tokens against 20 767, −44% —
and the thinking rose by more: 40 110 against 23 693, +69%. Not one call
running away: every call thought longer, the median 2 244 against 1 214, the
least 810 against 0. Recognition cost $0.211 against $0.185, 14% more, at
15.0 s a call at the median against 13.6. It read as well as the default —
every number alike, five of the six known places right, as 46 did, with its
miss in another place. The list was doing work: written down, the numbers are
checked in the answer; left out, they are checked in the thinking, which the
model spends more freely than it writes. Rolled back to v6 the same evening.
One album, an observation — but the direction was a saving, and this is not
one. What is left of the second half of the cost work is Flex and the number
of runs, both the author's to decide.

## Remarks about the reading

**What the documents carried (production, 2026-09-25, 47 records).** 36
records carried reading remarks from `uncertain` — "В рукописи, с. 2: «Дьюринг»
— двоится; другое прочтение: Тьюринг" — set under their lines; 26 opened with
a box of numbers the runs read differently; 6 with a box of pages read without
a second opinion; 32 were `needs_review` and said "нужна проверка" under the
title, with a box saying the same wherever nothing more exact filled one. Four
records carried a finding of a check at all: records 19–21, the same album
three times, with a matrix its graph contradicts, and record 45, with the
congruence read as a chain that task 42 had already stopped reporting. The
chat got every one of those lists again after the record.

The author ruled on it the same day: nothing in the text like "I read Дьюринг,
not Тьюринг"; a remark only for an error in the work; nothing about what the
author wrote; the boxes "прочитано без сверки" and "числа прочитаны по-разному"
gone; and the arithmetic check moved to the place it checked (task 46).

**Re-rendered from production with the change:**

| record | pages before → after | boxes and remarks before | after |
|---|---|---|---|
| 19 | 5 → 4 | 2 boxes, 7 remarks | one finding, under its graph and matrix |
| 45 | 7 → 6 | 4 boxes, 5 remarks | the missing-page box; the stale chain finding dropped |
| 46 | 7 → 7 | 2 boxes, 4 remarks | none |
| 47 | 8 → 6 | 1 box, 7 remarks | none |

Record 47 lost two pages and not only to the boxes: its page 4 ended at 38% of
its height before a long division. The division kept itself whole with a
`KeepTogether`, and set in one group with the heading over it — or, then, a
reading remark under it — that was a group inside a group, which reportlab
sends to the next page even where it fits. Opened into the one group, every
page but the last fills 83–92%.

**mathcheck raises on a chain whose link comes to 0.** Found while writing the
anchor tests: "1 - 1 = 0 = 5", and a list item "- 2 + 2 = 4 = 5" whose marker
it reads as a minus, make `check_chains` take the ratio of the next link to 0
and round the logarithm of infinity — `OverflowError: cannot convert float
infinity to integer`. Nothing caught it: on the photo path the record was lost
to "Не смог обработать фото" after the recognition was paid for, and on an
album the page became "ошибка обработки" and a hole. Production has no
`note_failed` event at all, so no record is known to have hit it. Worked
around in `vision`, the module left as it is.
