"""Album assembly — app/bot/albums.py.

Batch ownership already has its own test in test_reliability.py. What is
covered here is _assemble, where every aggregate is over the surviving pages
only, and the part of process_batch that decides what counts as a survivor.
"""

import asyncio
import time

import pytest

from app.bot import albums, texts
from app.services import consensus, mathcheck
from types import SimpleNamespace

from app.services import vision
from app.services.vision import CallStats, Transcription, Uncertain


def _transcription(**overrides) -> Transcription:
    fields = dict(
        title="Заголовок",
        subject=None,
        markdown="текст",
        margin_notes=[],
        uncertain=[],
        numeric_tokens=[],
        unreadable_count=0,
    )
    fields.update(overrides)
    return Transcription(**fields)


def _page(number: int, **overrides) -> albums.PageResult:
    fields = dict(
        stats=[],
        transcription=_transcription(),
        report=mathcheck.Report(issues=[]),
        verdict="clean",
        text_agreement=1.0,
        numeric_agreement=1.0,
        numeric_divergences=[],
        photo_sharpness=100.0,
        photo_line_height=20.0,
        photo_paper_fraction=0.9,
        photo_contrast=0.8,
    )
    fields.update(overrides)
    return albums.PageResult(page=number, **fields)


def _page_input(message_id: int) -> albums.PageInput:
    return albums.PageInput(
        data=b"x",
        message_id=message_id,
        chat_id=1,
        media_group_id="grp",
        bytes_before=10,
        bytes_after=5,
        width=100,
        height=100,
    )


# ── process_page: the checks a page goes through ─────────────────────────────


def _frame_ok() -> SimpleNamespace:
    """A frame that passes every threshold, so the page reaches the model."""
    return SimpleNamespace(
        ok=True,
        reason=None,
        sharpness=100.0,
        line_height_px=20.0,
        paper_fraction=0.9,
        contrast=0.8,
    )


async def test_a_page_carries_both_agreements_off_the_consensus(monkeypatch):
    """The album's two columns are no better than this hand-off.

    A page that reads text_agreement into both fields leaves the rest of the
    suite green: _assemble takes minima of whatever it is given, and the
    record then reports a page's layout agreement as its numeric one — the
    experiment would compare the wrong measure without anything failing.
    """
    monkeypatch.setattr(albums.photoguard, "check_photo_bytes", lambda data: _frame_ok())

    async def _runs(data):
        return (
            vision.TranscriptionResult(
                best=_transcription(
                    markdown=(
                        "Сумма степеней вершин связного графа равна "
                        "удвоенному числу его рёбер."
                    )
                ),
                text_agreement=0.99,
                numeric_agreement=0.60,
                numeric_divergences=[],
                verdict="clean",
            ),
            [],
        )

    monkeypatch.setattr(albums.vision, "transcribe_consensus", _runs)

    page = await albums.process_page(_page_input(1), 1)

    assert page.text_agreement == 0.99
    assert page.numeric_agreement == 0.60


async def _page_from(monkeypatch, **result_fields):
    """One page through process_page with a consensus of the test's choosing."""
    monkeypatch.setattr(
        albums.photoguard, "check_photo_bytes", lambda data: _frame_ok()
    )
    fields = {
        "best": _transcription(
            markdown=(
                "Сумма степеней вершин связного графа равна удвоенному "
                "числу его рёбер."
            )
        ),
        "text_agreement": 0.99,
        "numeric_agreement": 0.99,
        "numeric_divergences": [],
        "verdict": "clean",
        **result_fields,
    }

    async def _runs(data):
        return vision.TranscriptionResult(**fields), []

    monkeypatch.setattr(albums.vision, "transcribe_consensus", _runs)
    return await albums.process_page(_page_input(1), 1)


async def test_runs_that_diverged_keep_the_page_and_mark_it(monkeypatch):
    """The correction of 2026-09-23. A "rejected" band used to drop the page,
    and the album with it — while the author, looking at the photographs behind
    those refusals, said the text on them was perfectly legible. What the band
    measures is the shape the runs gave the page, not whether they read it."""
    page = await _page_from(monkeypatch, text_agreement=0.195, verdict="rejected")

    assert page.ok  # not a skip any more
    assert page.unverified_reason == texts.UNVERIFIED_DIVERGED
    assert page.verdict == "needs_review"


async def test_a_page_read_by_one_run_is_kept_and_says_so(monkeypatch):
    # Agreement is a comparison; one reading has nothing to be compared with.
    page = await _page_from(
        monkeypatch,
        text_agreement=None,
        numeric_agreement=None,
        verdict="needs_review",
    )

    assert page.ok
    assert page.unverified_reason == texts.UNVERIFIED_ONE_RUN
    assert page.text_agreement is None


async def test_a_page_that_read_well_is_not_marked(monkeypatch):
    page = await _page_from(monkeypatch)

    assert page.unverified_reason is None
    assert page.verdict == "clean"


async def test_an_empty_page_is_still_dropped(monkeypatch):
    # Three reasons remain to drop a page, and this is one of them: there is
    # no text to keep.
    page = await _page_from(monkeypatch, best=_transcription(markdown="—"))

    assert page.skip_reason == texts.SKIP_NO_TEXT


async def test_the_unverified_pages_reach_the_record(monkeypatch):
    record = albums._assemble(
        [
            _page(1),
            _page(2, verdict="needs_review", unverified_reason=texts.UNVERIFIED_ONE_RUN),
        ],
        [],
    )

    assert record.unverified_pages == [
        {"page": 2, "reason": texts.UNVERIFIED_ONE_RUN}
    ]
    assert record.status == "needs_review"


def test_an_album_agreement_ignores_a_page_that_has_none():
    """A page read by a single run contributes no agreement, and the album's
    number is the worst of those that do — not None, and not a zero."""
    record = albums._assemble(
        [
            _page(1, text_agreement=0.95, numeric_agreement=0.90),
            _page(2, text_agreement=None, numeric_agreement=None),
        ],
        [],
    )

    assert record.text_agreement == 0.95
    assert record.numeric_agreement == 0.90


async def test_a_matrix_contradicting_its_graph_sends_the_page_for_review(
    monkeypatch,
):
    # The matrix check has to run on the album path and not only on the single
    # photo one: an album is where matrices actually arrive, four pages at a
    # time.
    markdown = (
        "[граф: 1-2, 2-3, 3-4]\n\n"
        "|   | 1 | 2 | 3 | 4 |\n|---|---|---|---|---|\n"
        "| **1** | 0 | 1 | 1 | 0 |\n| **2** | 1 | 0 | 1 | 0 |\n"
        "| **3** | 1 | 1 | 0 | 1 |\n| **4** | 0 | 0 | 1 | 0 |\n"
    )

    monkeypatch.setattr(albums.photoguard, "check_photo_bytes", lambda data: _frame_ok())

    async def _runs(data):
        return (
            vision.TranscriptionResult(
                best=_transcription(markdown=markdown),
                text_agreement=0.99,
                numeric_agreement=0.99,
                numeric_divergences=[],
                verdict="clean",
            ),
            [],
        )

    monkeypatch.setattr(albums.vision, "transcribe_consensus", _runs)

    result = await albums.process_page(_page_input(1), 1)

    assert result.verdict == "needs_review"
    assert [i.kind for i in result.report.issues] == ["matrix"]


# ── _assemble: text ──────────────────────────────────────────────────────────


def test_title_comes_from_the_first_page():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(title="Первая")),
            _page(2, transcription=_transcription(title="Вторая")),
        ],
        [],
    )
    assert record.title == "Первая"


def test_subject_is_the_first_non_empty_one():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(subject=None)),
            _page(2, transcription=_transcription(subject="Физика")),
            _page(3, transcription=_transcription(subject="Химия")),
        ],
        [],
    )
    assert record.subject == "Физика"


def test_margin_notes_of_every_page_end_up_in_the_record():
    # What stood in the margin of page three is still a margin note of the
    # album, in the order the pages were photographed.
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(margin_notes=["Шиманская Г. С."])),
            _page(2, transcription=_transcription(margin_notes=[])),
            _page(3, transcription=_transcription(margin_notes=["с. 4", "важно"])),
        ],
        [],
    )
    assert record.margin_notes == ["Шиманская Г. С.", "с. 4", "важно"]


def test_subject_is_none_when_no_page_has_one():
    record = albums._assemble([_page(1), _page(2)], [])
    assert record.subject is None


def test_pages_are_joined_by_a_horizontal_rule():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(markdown="Первая страница.")),
            _page(2, transcription=_transcription(markdown="Вторая страница.")),
        ],
        [],
    )
    # Whole runs are concatenated, never spliced.
    assert record.markdown == "Первая страница.\n\n---\n\nВторая страница."


# ── the seam: a sentence that ran over the edge of the page ──────────────────


def _joined(first: str, second: str) -> str:
    return albums._assemble(
        [
            _page(1, transcription=_transcription(markdown=first)),
            _page(2, transcription=_transcription(markdown=second)),
        ],
        [],
    ).markdown


def test_a_sentence_broken_by_the_page_edge_is_put_back_together():
    """From the record of 2026-09-23: "Если граф ориентирован, то ребро" and
    "учитывается один раз" came out as two halves with a horizontal line
    between them, which is what made the document read as broken."""
    markdown = _joined(
        "### Доказательство\n\nЕсли граф ориентирован, то ребро",
        "учитывается один раз как исходящее, другой как входящее.",
    )

    assert "---" not in markdown
    assert "то ребро учитывается один раз" in markdown


def test_a_finished_sentence_keeps_its_page_break():
    markdown = _joined("Степень вершины равна 5.", "она же число рёбер.")

    assert "---" in markdown


def test_a_new_sentence_keeps_its_page_break():
    markdown = _joined("Степень вершины равна", "Число рёбер равно четырём.")

    assert "---" in markdown


def test_a_table_is_never_joined_to_the_next_page():
    # Joining two things that were not one sentence is worse than the seam.
    markdown = _joined(
        "| 1 | 2 |\n|---|---|\n| 0 | 1 |", "продолжение таблицы на следующей"
    )

    assert "\n\n---\n\n" in markdown


def test_a_list_is_never_joined_to_the_next_page():
    markdown = _joined("Свойства:\n\n- первое свойство", "второе свойство")

    assert "\n\n---\n\n" in markdown


def test_a_formula_is_never_joined_to_the_next_page():
    markdown = _joined("$$\n\\sum_{i=1}^{p} \\rho(v_i) = 2q\n$$", "четная сумма")

    assert "\n\n---\n\n" in markdown


def test_a_page_that_could_not_be_read_is_never_joined():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(markdown="и тогда ребро")),
            _page(3, transcription=_transcription(markdown="считается дважды.")),
        ],
        [albums.PageResult(2, [], skip_reason=texts.SKIP_UNRECOGNIZED)],
    )

    # The marker stands between them, so neither half joins across the hole.
    assert record.markdown.count("---") == 2
    assert texts.page_missing_marker(2) in record.markdown


def test_only_the_seam_that_continues_is_closed():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(markdown="первое предложение,")),
            _page(2, transcription=_transcription(markdown="которое продолжилось.")),
            _page(3, transcription=_transcription(markdown="Новая страница.")),
        ],
        [],
    )

    assert record.markdown.count("---") == 1
    assert "предложение, которое продолжилось." in record.markdown


def test_page_count_counts_surviving_pages_only():
    assert albums._assemble([_page(1), _page(3)], []).page_count == 2


# ── _assemble: verdict ───────────────────────────────────────────────────────


def test_one_page_needing_review_marks_the_whole_record():
    record = albums._assemble([_page(1), _page(2, verdict="needs_review")], [])
    assert record.status == "needs_review"
    assert record.verdict == "needs_review"


def test_all_clean_pages_give_a_ready_record():
    record = albums._assemble([_page(1), _page(2)], [])
    assert record.status == "ready"
    assert record.verdict == "clean"


# ── _assemble: per-page tagging ──────────────────────────────────────────────


def test_uncertain_entries_carry_their_page_number():
    record = albums._assemble(
        [
            _page(1),
            _page(
                2,
                transcription=_transcription(
                    uncertain=[Uncertain("щ", "поле", "двоится", [])]
                ),
            ),
        ],
        [],
    )
    assert record.uncertain == [
        {"text": "щ", "where": "поле", "why": "двоится", "alternatives": [], "page": 2}
    ]


def test_issues_carry_their_page_number():
    issue = mathcheck.Issue(kind="constant", severity="critical", message="не сходится")
    record = albums._assemble([_page(1, report=mathcheck.Report(issues=[issue]))], [])
    assert record.issues[0]["page"] == 1
    assert record.issues[0]["severity"] == "critical"


def test_divergences_carry_their_page_number():
    divergence = consensus.Divergence(position=0, variants={"5": 2, "6": 1}, context="x")
    record = albums._assemble([_page(4, numeric_divergences=[divergence])], [])
    assert record.numeric_divergences[0]["page"] == 4
    assert record.numeric_divergences[0]["variants"] == {"5": 2, "6": 1}


# ── _assemble: aggregates ────────────────────────────────────────────────────


def test_unreadable_counts_are_summed():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(unreadable_count=2)),
            _page(2, transcription=_transcription(unreadable_count=3)),
        ],
        [],
    )
    assert record.unreadable_count == 5


def test_text_agreement_is_the_worst_page():
    # The record is only as trustworthy as its least certain page.
    record = albums._assemble(
        [_page(1, text_agreement=0.99), _page(2, text_agreement=0.72)],
        [],
    )
    assert record.text_agreement == 0.72


def test_the_worst_page_by_text_is_not_the_worst_page_by_numbers():
    """Both agreements take the worst page, and it is not the same page.

    The biology album of 2026-09-22, which is why both are stored rather than
    one: page 2 read 0.917 text / 0.939 numeric, page 3 read 0.990 / 0.600.
    The prose on page 3 agreed almost perfectly and its numbers did not, so a
    record carrying only the minimum of one of them describes the wrong page.
    """
    record = albums._assemble(
        [
            _page(1, text_agreement=0.917, numeric_agreement=0.939),
            _page(2, text_agreement=0.990, numeric_agreement=0.600),
        ],
        [],
    )

    assert record.text_agreement == 0.917
    assert record.numeric_agreement == 0.600


def test_frame_metrics_take_the_worst_page():
    record = albums._assemble(
        [
            _page(1, photo_sharpness=500.0, photo_contrast=0.9),
            _page(2, photo_sharpness=120.0, photo_contrast=0.4),
        ],
        [],
    )
    assert record.photo_sharpness == 120.0
    assert record.photo_contrast == 0.4


def test_missing_metrics_are_skipped_not_treated_as_zero():
    record = albums._assemble(
        [_page(1, photo_sharpness=None), _page(2, photo_sharpness=300.0)],
        [],
    )
    assert record.photo_sharpness == 300.0


def test_metric_is_none_when_no_page_reported_it():
    record = albums._assemble([_page(1, photo_sharpness=None)], [])
    assert record.photo_sharpness is None


# ── process_batch ────────────────────────────────────────────────────────────


async def test_one_failing_page_does_not_take_down_the_others(monkeypatch):
    async def fake_process_page(page_input, page):
        if page == 2:
            raise RuntimeError("boom")
        return _page(page)

    monkeypatch.setattr(albums, "process_page", fake_process_page)

    outcome = await albums.process_batch([_page_input(i) for i in (1, 2, 3)])

    assert outcome.record is not None
    assert outcome.record.page_count == 2
    assert [(p.page, p.skip_reason) for p in outcome.skips] == [(2, texts.SKIP_ERROR)]


async def test_skipped_pages_are_reported_in_page_order(monkeypatch):
    async def fake_process_page(page_input, page):
        if page in (3, 1):
            return albums.PageResult(page, [], skip_reason=texts.SKIP_NO_TEXT)
        return _page(page)

    monkeypatch.setattr(albums, "process_page", fake_process_page)

    outcome = await albums.process_batch([_page_input(i) for i in (1, 2, 3)])

    assert [p.page for p in outcome.skips] == [1, 3]


async def test_no_surviving_page_means_no_record(monkeypatch):
    async def fake_process_page(page_input, page):
        return albums.PageResult(page, [], skip_reason=texts.SKIP_UNRECOGNIZED)

    monkeypatch.setattr(albums, "process_page", fake_process_page)

    outcome = await albums.process_batch([_page_input(1), _page_input(2)])

    assert outcome.record is None
    assert len(outcome.skips) == 2


async def test_spend_is_collected_from_every_page(monkeypatch):
    # The calls were billed whether or not the page survived, so a skipped
    # page must still contribute its stats.
    async def fake_process_page(page_input, page):
        stats = [
            CallStats(
                kind="transcribe",
                model="gemini-3.5-flash-lite",
                tokens_in=10,
                tokens_out=20,
                tokens_thought=None,
                cost_usd=0.001,
                latency_ms=100,
                success=True,
                error=None,
            )
        ]
        if page == 2:
            return albums.PageResult(page, stats, skip_reason=texts.SKIP_DIVERGED)
        return _page(page, stats=stats)

    monkeypatch.setattr(albums, "process_page", fake_process_page)

    outcome = await albums.process_batch([_page_input(i) for i in (1, 2)])

    assert len(outcome.stats) == 2


# ── collect: the debounce that keeps an album whole ──────────────────────────
# An album arrived as four one-page records because pages land in the buffer
# only after handle_photo has downloaded and compressed each photo, which on a
# slow link takes longer than the old one-second window. Timings here are
# scaled down by monkeypatching _QUIET_SECONDS; what matters is the ratio of
# the arrival gap to the quiet window.


def _input(message_id: int, group: str = "grp") -> albums.PageInput:
    return albums.PageInput(
        data=b"x",
        message_id=message_id,
        chat_id=1,
        media_group_id=group,
        bytes_before=1,
        bytes_after=1,
        width=1,
        height=1,
    )


async def _arrive(group: str, message_id: int, delay: float):
    """One page of an album, landing in the buffer `delay` seconds from now."""
    await asyncio.sleep(delay)
    albums.add_page(group, _input(message_id, group))
    return await albums.collect(group)


def _reset() -> None:
    albums.reset()


async def test_pages_trickling_in_stay_in_one_batch(monkeypatch):
    # The regression: gaps shorter than the quiet window must keep the album
    # together. At the old 1.0 s this split into four separate records.
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.4)
    _reset()

    gap = 0.2
    results = await asyncio.gather(
        *(_arrive("grp", i, i * gap) for i in range(4))
    )

    batches = [r for r in results if r is not None]
    assert len(batches) == 1
    assert len(batches[0]) == 4


async def test_a_simultaneous_album_is_still_one_batch(monkeypatch):
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.2)
    _reset()

    results = await asyncio.gather(*(_arrive("grp", i, 0.0) for i in range(5)))

    batches = [r for r in results if r is not None]
    assert len(batches) == 1
    assert len(batches[0]) == 5


async def test_exactly_one_caller_owns_a_trickling_album(monkeypatch):
    # The single-owner invariant has to survive the longer window: every other
    # caller must get None and reply nothing.
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.4)
    _reset()

    results = await asyncio.gather(
        *(_arrive("grp", i, i * 0.15) for i in range(4))
    )

    assert sum(1 for r in results if r is not None) == 1
    assert sum(1 for r in results if r is None) == 3


async def test_a_fast_album_is_not_delayed_by_the_poll_interval(monkeypatch):
    # The wait is shortened to land when the window expires, so a quick album
    # is not rounded up to the next poll tick.
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.2)
    monkeypatch.setattr(albums, "_POLL_SECONDS", 5.0)
    _reset()

    started = time.monotonic()
    albums.add_page("grp", _input(1))
    pages = await albums.collect("grp")

    assert pages is not None and len(pages) == 1
    assert time.monotonic() - started < 1.0


async def test_the_ceiling_closes_an_album_that_never_goes_quiet(monkeypatch):
    """A stream that keeps arriving must not hold its DB session for ever.

    What the ceiling guarantees is a *bounded wait*, so that is what is
    asserted. Checking only that several pages came back would pass with the
    ceiling removed — the batch would still close, just one whole quiet window
    after the stream finally stopped."""
    quiet, ceiling = 10.0, 0.5
    monkeypatch.setattr(albums, "_QUIET_SECONDS", quiet)
    monkeypatch.setattr(albums, "_COLLECT_MAX_S", ceiling)
    monkeypatch.setattr(albums, "_POLL_SECONDS", 0.05)
    _reset()

    async def keep_feeding():
        for i in range(100, 140):
            await asyncio.sleep(0.05)
            albums.add_page("grp", _input(i))

    albums.add_page("grp", _input(1))
    feeder = asyncio.create_task(keep_feeding())
    started = time.monotonic()
    pages = await albums.collect("grp")
    elapsed = time.monotonic() - started
    feeder.cancel()

    assert pages is not None
    assert len(pages) > 1  # closed mid-stream, not after the first page alone
    # Bounded by the ceiling, nowhere near the 10 s quiet window.
    assert elapsed < quiet / 2


async def test_the_bookkeeping_does_not_leak(monkeypatch):
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.1)
    _reset()

    albums.add_page("grp", _input(1))
    await albums.collect("grp")

    assert albums._buffer == {}
    assert albums._first_page_at == {}
    assert albums._last_page_at == {}


async def test_two_albums_at_once_do_not_mix(monkeypatch):
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.3)
    _reset()

    first, second = await asyncio.gather(
        _arrive("a", 1, 0.0), _arrive("b", 2, 0.05)
    )

    assert first is not None and second is not None
    assert first[0].media_group_id == "a"
    assert second[0].media_group_id == "b"


def test_the_quiet_window_stays_wide_enough_for_a_slow_page():
    """What actually fixed the split album is this value, not the shape of the
    loop: a debounce cannot tell a finished album from a slow one, so the only
    defence is a window wider than the gap between arrivals. The observed gap
    was around 1.5 s — download plus compression of one photo, not Telegram's
    delivery — so the window keeps roughly double that as headroom.

    Telegram does not report how many items a media group holds, so there is
    nothing better than a debounce to wait on."""
    assert albums._QUIET_SECONDS >= 3.0


async def test_the_batch_closes_one_window_after_the_last_page(monkeypatch):
    # Measuring silence from the last arrival rather than from the start of a
    # fixed sleep is what keeps this tight: the old loop could run up to two
    # windows past the final page before claiming.
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.3)
    monkeypatch.setattr(albums, "_POLL_SECONDS", 0.02)
    _reset()

    started = time.monotonic()
    last_page_at = 0.2
    results = await asyncio.gather(
        _arrive("grp", 1, 0.0), _arrive("grp", 2, last_page_at)
    )
    elapsed = time.monotonic() - started

    assert [len(r) for r in results if r is not None] == [2]
    assert elapsed < last_page_at + 0.3 * 2


# ── the two-step registration ────────────────────────────────────────────────
# The album that kept arriving as four separate records. Telegram delivers the
# four updates milliseconds apart, but a page only reaches the buffer once it
# has been downloaded and compressed — seconds per photo. Timing the debounce
# from the buffer measured our own download speed, so the first page to finish
# saw a quiet album and took the batch while the rest were still in flight.


async def _announce_then_deliver(group: str, message_id: int, download_takes: float):
    """A page announced at once, its bytes arriving `download_takes` later."""
    albums.announce(group, message_id)
    await asyncio.sleep(download_takes)
    albums.add_page(group, _input(message_id, group))
    return await albums.collect(group)


async def test_a_slow_download_does_not_split_the_album(monkeypatch):
    # The regression. One page takes far longer than the quiet window to
    # fetch; the batch must wait for it rather than go out without it.
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.3)
    monkeypatch.setattr(albums, "_POLL_SECONDS", 0.02)
    _reset()

    results = await asyncio.gather(
        _announce_then_deliver("grp", 1, 0.05),
        _announce_then_deliver("grp", 2, 0.10),
        _announce_then_deliver("grp", 3, 0.15),
        _announce_then_deliver("grp", 4, 1.20),  # the straggler
    )

    batches = [r for r in results if r is not None]
    assert len(batches) == 1
    assert len(batches[0]) == 4


async def test_the_batch_waits_for_every_announced_page(monkeypatch):
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.2)
    monkeypatch.setattr(albums, "_POLL_SECONDS", 0.02)
    _reset()

    albums.announce("grp", 1)
    albums.announce("grp", 2)
    albums.add_page("grp", _input(1))

    # Only one of the two announced pages is ready, so nothing may close yet.
    collector = asyncio.create_task(albums.collect("grp"))
    await asyncio.sleep(0.5)
    assert not collector.done()

    albums.add_page("grp", _input(2))
    pages = await collector
    assert len(pages) == 2


async def test_a_page_arriving_after_its_batch_went_out_is_dropped(monkeypatch):
    # Otherwise the straggler opens a second record — the very thing the whole
    # fix is about.
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.1)
    monkeypatch.setattr(albums, "_POLL_SECONDS", 0.02)
    _reset()

    albums.announce("grp", 1)
    albums.add_page("grp", _input(1))
    first = await albums.collect("grp")
    assert first is not None and len(first) == 1

    albums.add_page("grp", _input(2))  # too late
    assert albums._buffer == {}
    assert await albums.collect("grp") is None


async def test_an_album_whose_pages_never_download_yields_nothing(monkeypatch):
    # The ceiling fires with an empty buffer. Returning an empty list here
    # would send process_batch into asyncio.wait with nothing to wait on.
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.05)
    monkeypatch.setattr(albums, "_COLLECT_MAX_S", 0.2)
    monkeypatch.setattr(albums, "_POLL_SECONDS", 0.02)
    _reset()

    albums.announce("grp", 1)
    albums.announce("grp", 2)

    assert await albums.collect("grp") is None


async def test_announce_is_idempotent_for_the_same_page(monkeypatch):
    _reset()
    albums.announce("grp", 1)
    albums.announce("grp", 1)
    assert albums._announced["grp"] == {1}


async def test_a_page_never_announced_announces_itself(monkeypatch):
    # The buffer must never be fed behind the registry's back.
    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.05)
    _reset()

    albums.add_page("grp", _input(3))
    pages = await albums.collect("grp")

    assert pages is not None and len(pages) == 1


# ── the album ceiling follows the call timeout ───────────────────────────────


def test_the_album_ceiling_covers_every_wave_of_runs():
    # A ceiling under the waves cancels pages whose calls were already paid
    # for, which is why PLAN.md task 10 calls this value normative.
    assert albums._ALBUM_TIMEOUT_S > albums._WAVES * vision.RUN_WORST_CASE_S


def test_the_wave_count_comes_from_the_settings_it_depends_on():
    assert albums._WAVES == albums._waves(
        albums.settings.MAX_ALBUM_PAGES,
        albums.settings.VISION_RUNS,
        vision.API_SLOTS,
    )


def test_a_partly_full_last_wave_still_counts_as_a_wave():
    # 10 x 3 / 10 divides evenly, so the defaults cannot tell rounding down
    # from rounding up. Seven pages can: 21 calls is three waves, and a
    # ceiling built on two would cancel the last one mid-call.
    assert albums._waves(7, 3, 10) == 3
    assert albums._waves(10, 3, 10) == 3
    assert albums._waves(1, 3, 10) == 1


def test_the_album_ceiling_never_dropped_below_where_it_started():
    # 300 s was the hand-written value. The rule is one-way: raising it is
    # allowed, lowering it is not.
    assert albums._ALBUM_TIMEOUT_S >= 300


# ── one line per closed batch, so a split album is visible in the log ────────


async def test_closing_a_batch_is_logged_once_with_both_counts(monkeypatch, caplog):
    """Two of these lines for one media_group_id means the batch was claimed
    twice and the album split into separate records. Nothing in the log could
    previously tell that from a single slow page."""
    import logging

    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.05)
    _reset()
    albums.announce("grp", 1)
    albums.announce("grp", 2)
    albums.add_page("grp", _input(1))
    albums.add_page("grp", _input(2))

    with caplog.at_level(logging.INFO, logger="app.bot.albums"):
        pages = await albums.collect("grp")

    assert pages is not None and len(pages) == 2
    closed = [
        r.getMessage() for r in caplog.records if "batch closed" in r.getMessage()
    ]
    assert len(closed) == 1
    assert "grp" in closed[0]
    assert "2 of 2 pages" in closed[0]


async def test_the_two_counts_in_the_line_are_not_the_same_count(monkeypatch, caplog):
    # Downloaded against announced. With a whole album they are equal and
    # printing one of them twice would look right, so the case that tells them
    # apart is the one where a page never arrived.
    import logging

    monkeypatch.setattr(albums, "_COLLECT_MAX_S", 0.05)
    _reset()
    albums.announce("grp", 1)
    albums.announce("grp", 2)
    albums.announce("grp", 3)
    albums.add_page("grp", _input(1))
    albums.add_page("grp", _input(2))

    with caplog.at_level(logging.INFO, logger="app.bot.albums"):
        pages = await albums.collect("grp")

    assert pages is not None and len(pages) == 2
    closed = [
        r.getMessage() for r in caplog.records if "batch closed" in r.getMessage()
    ]
    assert len(closed) == 1
    assert "2 of 3 pages" in closed[0]


async def test_the_caller_that_loses_the_batch_logs_nothing(monkeypatch, caplog):
    import logging

    monkeypatch.setattr(albums, "_QUIET_SECONDS", 0.05)
    _reset()
    albums.announce("grp", 1)
    albums.add_page("grp", _input(1))

    with caplog.at_level(logging.INFO, logger="app.bot.albums"):
        first, second = await asyncio.gather(
            albums.collect("grp"), albums.collect("grp")
        )

    assert [first, second].count(None) == 1
    closed = [r for r in caplog.records if "batch closed" in r.getMessage()]
    assert len(closed) == 1


# ── a refused page has to leave its numbers behind ───────────────────────────


def _verdict(**overrides):
    fields = dict(
        ok=True,
        reason="Фото годится для распознавания",
        line_height_px=25.0,
        sharpness=200.0,
        paper_fraction=0.9,
        contrast=40.0,
    )
    fields.update(overrides)
    from app.services import photoguard

    return photoguard.PhotoVerdict(**fields)


def test_the_log_name_of_each_threshold_is_the_one_that_refused_the_frame():
    # photoguard's own reason is the Russian sentence shown to the user.
    # Recomputing the name from the numbers keeps the log from going wrong the
    # day that wording changes, and the order matches photoguard's own.
    assert albums.reason_en(_verdict(ok=False, paper_fraction=0.01)) == "paper fraction"
    assert albums.reason_en(_verdict(ok=False, sharpness=1.0)) == "sharpness"
    assert albums.reason_en(_verdict(ok=False, contrast=1.0)) == "contrast"
    assert albums.reason_en(_verdict(ok=False, line_height_px=12.0)) == "line height"
    assert albums.reason_en(_verdict()) == "none"


def test_a_height_that_could_not_be_measured_names_no_threshold():
    # photoguard stopped refusing on it, so naming it here would blame a check
    # that did not make the decision — and this function exists precisely so
    # the log cannot drift away from photoguard's own order.
    from app.services import photoguard

    unmeasured = _verdict(line_height_px=photoguard.UNMEASURED_LINE_HEIGHT)
    assert albums.reason_en(unmeasured) == "none"


def test_the_first_failing_threshold_is_the_one_named():
    # Two below at once: the name has to follow photoguard's own order, or the
    # log will blame a check that did not make the decision.
    both = _verdict(ok=False, paper_fraction=0.01, line_height_px=0.0)
    assert albums.reason_en(both) == "paper fraction"


async def test_a_page_refused_by_the_frame_keeps_its_four_metrics(monkeypatch):
    """This is the whole point. A page turned away by the frame check used to
    leave nothing but a Russian sentence, so the one rejection nobody could
    argue with was the album one — while a single photo wrote all four numbers
    to photo_rejected."""
    refusal = _verdict(ok=False, line_height_px=0.0, reason="Текст мелкий")
    monkeypatch.setattr(
        albums.photoguard, "check_photo_bytes", lambda data: refusal
    )

    result = await albums.process_page(_input(1), 1)

    assert not result.ok
    assert result.skip_reason == "Текст мелкий"
    assert result.photo_line_height == 0.0
    assert result.photo_sharpness == 200.0
    assert result.photo_paper_fraction == 0.9
    assert result.photo_contrast == 40.0
    assert result.stats == []  # refused before any model call


async def test_a_refused_frame_is_logged_against_its_thresholds(monkeypatch, caplog):
    import logging

    monkeypatch.setattr(
        albums.photoguard,
        "check_photo_bytes",
        lambda data: _verdict(ok=False, line_height_px=0.0, reason="Текст мелкий"),
    )

    with caplog.at_level(logging.WARNING, logger="app.bot.albums"):
        await albums.process_page(_input(1), 1)

    line = next(m for m in (r.getMessage() for r in caplog.records) if "frame check" in m)
    assert "line height" in line
    # the number and the threshold it missed
    assert f"0.0/{albums.photoguard.MIN_LINE_HEIGHT_PX}" in line


async def test_a_page_that_failed_recognition_keeps_them_too(monkeypatch):
    # The frame passed, so the numbers were measured anyway; dropping them
    # here bought nothing.
    monkeypatch.setattr(
        albums.photoguard, "check_photo_bytes", lambda data: _verdict()
    )

    async def nothing_came_back(image_bytes):
        return None, []

    monkeypatch.setattr(albums.vision, "transcribe_consensus", nothing_came_back)

    result = await albums.process_page(_input(1), 1)

    assert result.skip_reason == texts.SKIP_UNRECOGNIZED
    assert result.photo_line_height == 25.0
    assert result.photo_contrast == 40.0


# ── the subject an album was sent with ───────────────────────────────────────
# Telegram puts an album's caption on one page, and in a group chat that one
# caption decides whether the bot takes the album at all.


def _tagged(message_id: int, tag: str | None) -> albums.PageInput:
    return albums.PageInput(
        data=b"x",
        message_id=message_id,
        chat_id=1,
        media_group_id="grp",
        bytes_before=1,
        bytes_after=1,
        width=1,
        height=1,
        tag=tag,
    )


def test_an_album_takes_the_tag_of_whichever_page_carries_it():
    pages = [_tagged(3, None), _tagged(2, "матан"), _tagged(1, None)]
    assert albums.tag_of(pages) == "матан"


def test_between_two_tags_the_earlier_page_decides():
    # The pages arrive in any order; the page order is the message order.
    assert albums.tag_of([_tagged(2, "дз"), _tagged(1, "матан")]) == "матан"


def test_an_album_nobody_tagged_has_no_tag():
    assert albums.tag_of([_tagged(1, None), _tagged(2, None)]) is None


# ── refused_frames: every frame checked before any page is read ──────────────
# A refused frame is the one loss only the photographer can fix, and before
# the album is read nothing has been spent. Record 45 came back without its
# first page and "send it separately"; the album is asked for again instead.


async def test_the_frames_an_album_is_refused_for_are_named_with_their_metrics(
    monkeypatch,
):
    verdicts = {
        b"p1": _verdict(ok=False, line_height_px=12.0, reason="Текст мелкий"),
        b"p2": _verdict(),
        b"p3": _verdict(ok=False, contrast=10.0, reason="Слишком темно"),
    }
    monkeypatch.setattr(albums.photoguard, "check_photo_bytes", lambda data: verdicts[data])
    pages = [_input(i) for i in (1, 2, 3)]
    for page, data in zip(pages, verdicts):
        page.data = data

    refused = await albums.refused_frames(pages)

    assert [(p.page, p.skip_reason) for p in refused] == [
        (1, "Текст мелкий"),
        (3, "Слишком темно"),
    ]
    assert refused[0].photo_line_height == 12.0
    assert refused[0].stats == []  # nothing was spent


async def test_an_album_whose_frames_all_pass_is_not_held_back(monkeypatch):
    monkeypatch.setattr(albums.photoguard, "check_photo_bytes", lambda data: _verdict())

    assert await albums.refused_frames([_input(1), _input(2)]) == []


async def test_a_frame_that_cannot_be_opened_is_left_to_the_page_that_failed():
    # b"x" is not an image. process_page reports such a page as it always has;
    # the album is not held back over it.
    assert await albums.refused_frames([_input(1)]) == []
