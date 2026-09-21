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


# ── _assemble: text ──────────────────────────────────────────────────────────


def test_title_comes_from_the_first_page():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(title="Первая")),
            _page(2, transcription=_transcription(title="Вторая")),
        ]
    )
    assert record.title == "Первая"


def test_subject_is_the_first_non_empty_one():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(subject=None)),
            _page(2, transcription=_transcription(subject="Физика")),
            _page(3, transcription=_transcription(subject="Химия")),
        ]
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
        ]
    )
    assert record.margin_notes == ["Шиманская Г. С.", "с. 4", "важно"]


def test_subject_is_none_when_no_page_has_one():
    record = albums._assemble([_page(1), _page(2)])
    assert record.subject is None


def test_pages_are_joined_by_a_horizontal_rule():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(markdown="первая")),
            _page(2, transcription=_transcription(markdown="вторая")),
        ]
    )
    # Whole runs are concatenated, never spliced.
    assert record.markdown == "первая\n\n---\n\nвторая"


def test_page_count_counts_surviving_pages_only():
    assert albums._assemble([_page(1), _page(3)]).page_count == 2


# ── _assemble: verdict ───────────────────────────────────────────────────────


def test_one_page_needing_review_marks_the_whole_record():
    record = albums._assemble([_page(1), _page(2, verdict="needs_review")])
    assert record.status == "needs_review"
    assert record.verdict == "needs_review"


def test_all_clean_pages_give_a_ready_record():
    record = albums._assemble([_page(1), _page(2)])
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
        ]
    )
    assert record.uncertain == [
        {"text": "щ", "where": "поле", "why": "двоится", "alternatives": [], "page": 2}
    ]


def test_issues_carry_their_page_number():
    issue = mathcheck.Issue(kind="constant", severity="critical", message="не сходится")
    record = albums._assemble([_page(1, report=mathcheck.Report(issues=[issue]))])
    assert record.issues[0]["page"] == 1
    assert record.issues[0]["severity"] == "critical"


def test_divergences_carry_their_page_number():
    divergence = consensus.Divergence(position=0, variants={"5": 2, "6": 1}, context="x")
    record = albums._assemble([_page(4, numeric_divergences=[divergence])])
    assert record.numeric_divergences[0]["page"] == 4
    assert record.numeric_divergences[0]["variants"] == {"5": 2, "6": 1}


# ── _assemble: aggregates ────────────────────────────────────────────────────


def test_unreadable_counts_are_summed():
    record = albums._assemble(
        [
            _page(1, transcription=_transcription(unreadable_count=2)),
            _page(2, transcription=_transcription(unreadable_count=3)),
        ]
    )
    assert record.unreadable_count == 5


def test_text_agreement_is_the_worst_page():
    # The record is only as trustworthy as its least certain page.
    record = albums._assemble(
        [_page(1, text_agreement=0.99), _page(2, text_agreement=0.72)]
    )
    assert record.text_agreement == 0.72


def test_frame_metrics_take_the_worst_page():
    record = albums._assemble(
        [
            _page(1, photo_sharpness=500.0, photo_contrast=0.9),
            _page(2, photo_sharpness=120.0, photo_contrast=0.4),
        ]
    )
    assert record.photo_sharpness == 120.0
    assert record.photo_contrast == 0.4


def test_missing_metrics_are_skipped_not_treated_as_zero():
    record = albums._assemble(
        [_page(1, photo_sharpness=None), _page(2, photo_sharpness=300.0)]
    )
    assert record.photo_sharpness == 300.0


def test_metric_is_none_when_no_page_reported_it():
    record = albums._assemble([_page(1, photo_sharpness=None)])
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
    assert outcome.skips == [(2, texts.SKIP_ERROR)]


async def test_skipped_pages_are_reported_in_page_order(monkeypatch):
    async def fake_process_page(page_input, page):
        if page in (3, 1):
            return albums.PageResult(page, [], skip_reason=texts.SKIP_NO_TEXT)
        return _page(page)

    monkeypatch.setattr(albums, "process_page", fake_process_page)

    outcome = await albums.process_batch([_page_input(i) for i in (1, 2, 3)])

    assert [number for number, _ in outcome.skips] == [1, 3]


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
        stats = [CallStats(10, 20, 0.001, 100, True, None)]
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
