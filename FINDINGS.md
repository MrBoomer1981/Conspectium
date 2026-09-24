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
