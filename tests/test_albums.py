"""Album assembly — app/bot/albums.py.

Batch ownership already has its own test in test_reliability.py. What is
covered here is _assemble, where every aggregate is over the surviving pages
only, and the part of process_batch that decides what counts as a survivor.
"""

import asyncio

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
