# FINDINGS.md

The run-by-run record of the recognition experiments: what was measured, on
which album, on which day, and what it did and did not settle.

`CLAUDE.md` → "Established experimentally" keeps the conclusions a change to
the code has to obey; this file is how each of them was measured. `PLAN.md` →
"Where the quality work stands" is how to run the next arm.

Read it as a journal rather than as a specification. Entries are kept in the
order they were made, with the model of the day named in them, because a
finding that was true of `gemini-2.5-flash-lite` is evidence rather than law
about whatever the startup log names today.

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
**$0.0298**, which is more than half again what all nine recognition calls of
the same album cost together ($0.0450). The album went from about 4.7 to 7.5
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
