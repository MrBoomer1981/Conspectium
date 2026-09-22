"""The pure decision functions of app/services/vision.py.

parse_response has its own file; this one covers the four helpers that decide
whether money is spent again, how much was spent, and how the result is
judged. All of them are pure, so they are cheap to pin down exactly.
"""

import asyncio

import httpx
import pytest
from google.genai import errors as genai_errors

from app.services import vision
from app.services.vision import CallStats


def _api_error(code) -> genai_errors.APIError:
    """A Gemini APIError with a chosen status, built without the SDK
    constructor — its signature shifts between versions."""
    err = genai_errors.APIError.__new__(genai_errors.APIError)
    err.code = code
    err.message = "test"
    err.details = None
    return err


def _stats(cost) -> CallStats:
    return CallStats(None, None, cost, 0, cost is not None, None)


# ── _should_retry ────────────────────────────────────────────────────────────
# "When it is unclear whether a failure is transport-level or logical, do not
# retry" — an extra call costs money, an extra rejection costs one tap.


def test_timeout_is_retried():
    assert vision._should_retry(TimeoutError()) is True


def test_asyncio_timeout_is_the_same_class_since_311():
    # wait_for raises asyncio.TimeoutError; since 3.11 it *is* TimeoutError.
    assert vision._should_retry(asyncio.TimeoutError()) is True


def test_transport_errors_are_retried():
    assert vision._should_retry(httpx.ConnectError("dns")) is True
    assert vision._should_retry(httpx.ReadTimeout("slow")) is True
    assert vision._should_retry(httpx.RemoteProtocolError("reset")) is True


def test_rate_limit_and_server_errors_are_retried():
    for code in (408, 429, 500, 502, 503, 504):
        assert vision._should_retry(_api_error(code)) is True, code


def test_client_errors_are_not_retried():
    for code in (400, 401, 403, 404):
        assert vision._should_retry(_api_error(code)) is False, code


def test_api_error_without_a_usable_code_is_retried():
    # An SDK error carrying no HTTP status is treated as transport-ish.
    assert vision._should_retry(_api_error(None)) is True
    assert vision._should_retry(_api_error("500")) is True


def test_unknown_exceptions_are_not_retried():
    assert vision._should_retry(ValueError("nonsense")) is False
    assert vision._should_retry(KeyError("missing")) is False


# ── _cost_usd ────────────────────────────────────────────────────────────────
# "We don't invent numbers": an unknown price is None, never a guess of zero.


def test_cost_of_a_priced_model():
    # flash-lite is (0.10, 0.40) per Mtok: 1M in + 1M out = 0.50.
    assert vision._cost_usd("gemini-2.5-flash-lite", 1_000_000, 1_000_000) == 0.50


def test_cost_is_none_for_an_unpriced_model():
    # This is the silent failure mode behind the daily cost cap: NULL rows are
    # skipped by SUM, so an unpriced model disables the circuit breaker.
    assert vision._cost_usd("gemini-3-something", 1000, 1000) is None


def test_cost_is_none_when_a_token_count_is_missing():
    assert vision._cost_usd("gemini-2.5-flash-lite", None, 1000) is None
    assert vision._cost_usd("gemini-2.5-flash-lite", 1000, None) is None


def test_zero_tokens_cost_zero_not_none():
    assert vision._cost_usd("gemini-2.5-flash-lite", 0, 0) == 0.0


# ── total_cost ───────────────────────────────────────────────────────────────


def test_total_cost_sums_the_known_values():
    assert vision.total_cost([_stats(0.1), _stats(0.2)]) == pytest.approx(0.3)


def test_total_cost_ignores_unknown_values():
    assert vision.total_cost([_stats(0.1), _stats(None)]) == 0.1


def test_total_cost_is_none_when_nothing_is_known():
    assert vision.total_cost([_stats(None), _stats(None)]) is None


def test_total_cost_of_no_calls_is_none():
    assert vision.total_cost([]) is None


# ── _verdict ─────────────────────────────────────────────────────────────────
# Non-overlapping bands from PLAN.md task 6. The boundaries are inclusive
# downwards, so 0.90 is still clean and 0.70 is still needs_review.


def test_verdict_bands():
    assert vision._verdict(1.0) == "clean"
    assert vision._verdict(0.90) == "clean"
    assert vision._verdict(0.8999) == "needs_review"
    assert vision._verdict(0.70) == "needs_review"
    assert vision._verdict(0.6999) == "rejected"
    assert vision._verdict(0.0) == "rejected"


# ── _short_error ─────────────────────────────────────────────────────────────


def test_short_error_includes_the_message():
    assert vision._short_error(ValueError("boom")) == "ValueError: boom"


def test_bare_exception_has_no_trailing_colon():
    # A bare TimeoutError() stringifies to "", which would leave ": " in the
    # ai_calls.error column.
    assert vision._short_error(TimeoutError()) == "TimeoutError"


def test_short_error_is_truncated_to_500_chars():
    assert len(vision._short_error(ValueError("x" * 1000))) == 500


# ── meaningful_divergences ───────────────────────────────────────────────────
# consensus.extract_numbers takes every numeric literal on the page, list
# markers and subscripts included, so most reported positions say only that one
# run emitted a number where another emitted nothing. The cases below are taken
# verbatim from what the bot actually sent for a page of lecture notes.

from app.services.consensus import Divergence  # noqa: E402


def _div(variants: dict, context: str = "x") -> Divergence:
    return Divergence(position=0, variants=variants, context=context)


def test_a_real_disagreement_is_kept():
    # Two runs read 5, one read 1 — the page really was read differently.
    kept = vision.meaningful_divergences([_div({"5": 2, "1": 1}, "5")])
    assert len(kept) == 1


def test_a_number_against_a_gap_is_dropped():
    # An alignment artefact: nothing here says the page was misread.
    assert vision.meaningful_divergences([_div({"1": 1, "— (пропущено)": 1})]) == []


def test_a_gap_winning_the_vote_is_still_dropped():
    assert vision.meaningful_divergences([_div({"— (пропущено)": 2, "5": 1})]) == []


def test_the_observed_noise_collapses_to_its_one_real_line():
    observed = [
        _div({"1": 1, "— (пропущено)": 1}, "1"),
        _div({"2": 1, "— (пропущено)": 1}, "2"),
        _div({"3": 1, "— (пропущено)": 1}, "3"),
        _div({"— (пропущено)": 2, "5": 1}, "5"),
        _div({"— (пропущено)": 2, "4": 1}, "4"),
        _div({"5": 2, "1": 1}, "5"),
        _div({"5": 2, "— (пропущено)": 1}, "5"),
        _div({"6": 2, "— (пропущено)": 1}, "6"),
    ]
    kept = vision.meaningful_divergences(observed)
    assert [d.variants for d in kept] == [{"5": 2, "1": 1}]


def test_three_different_readings_are_kept():
    kept = vision.meaningful_divergences([_div({"9.8": 1, "9.3": 1, "8.9": 1})])
    assert len(kept) == 1


def test_decimals_and_exponents_count_as_values():
    kept = vision.meaningful_divergences([_div({"6.626e-34": 2, "6.67e-34": 1})])
    assert len(kept) == 1


def test_nothing_in_nothing_out():
    assert vision.meaningful_divergences([]) == []


def test_the_filter_does_not_depend_on_the_modules_wording():
    # The "missing" bucket is matched by not being a number, not by its Russian
    # text, so consensus.py rewording it cannot silently break the filter.
    assert vision.meaningful_divergences([_div({"7": 1, "whatever": 1})]) == []
    assert vision._is_value("— (пропущено)") is False
    assert vision._is_value("7") is True
    assert vision._is_value("-2.5e3") is True


def test_a_split_with_a_gap_and_no_majority_is_dropped():
    # "6 (1 of 3) or 2 (1 of 3) or missing (1 of 3)". The three runs did not
    # read one number three ways — they produced different counts of numbers,
    # so the position they were aligned on is not the same position.
    assert vision.meaningful_divergences([_div({"6": 1, "2": 1, "— (пропущено)": 1})]) == []


def test_a_gap_is_survivable_where_a_reading_has_a_majority():
    # Five runs: three read 6, one read 2, one saw nothing there. The majority
    # is a real reading, so the line still says something worth checking.
    kept = vision.meaningful_divergences([_div({"6": 3, "2": 1, "— (пропущено)": 1})])
    assert len(kept) == 1


def test_three_numeric_readings_survive_without_a_majority():
    # No gap among them: the runs were aligned on one number and read it three
    # ways. That is the worst case, not a reason to hide it.
    assert len(vision.meaningful_divergences([_div({"9.8": 1, "9.3": 1, "8.9": 1})])) == 1


def test_the_same_line_twice_is_printed_once():
    # Two cells of a matrix read "6 against 2" produce two identical lines, and
    # the position that tells them apart never reaches the message.
    kept = vision.meaningful_divergences(
        [_div({"6": 2, "2": 1}, "6"), _div({"6": 2, "2": 1}, "6")]
    )
    assert len(kept) == 1


def test_the_same_numbers_in_a_different_context_are_both_kept():
    kept = vision.meaningful_divergences(
        [_div({"6": 2, "2": 1}, "p ="), _div({"6": 2, "2": 1}, "q =")]
    )
    assert len(kept) == 2


# ── meaningful_uncertain ─────────────────────────────────────────────────────
# The prompt asks for places where a symbol "действительно читается двояко".
# What came back on one album was the state of the paper: a word cropped by the
# edge, a smudge, an abbreviation, something written in the margin — seven
# entries, not one of which named a second reading.


def _unc(text="щ", why="двоится", alternatives=("ш",)) -> vision.Uncertain:
    return vision.Uncertain(
        text=text, where="", why=why, alternatives=list(alternatives)
    )


def test_a_spot_that_names_another_reading_is_kept():
    assert len(vision.meaningful_uncertain([_unc()])) == 1


def test_a_spot_that_names_no_other_reading_is_dropped():
    assert vision.meaningful_uncertain([_unc(why="слово обрезано краем", alternatives=())]) == []


def test_a_blank_alternative_does_not_count_as_one():
    assert vision.meaningful_uncertain([_unc(alternatives=("", "   "))]) == []


def test_a_spot_already_marked_unreadable_in_the_record_is_dropped():
    # "[неразборчиво]" stands in the text itself, in place. A list repeating it
    # adds a line without adding a fact.
    assert vision.meaningful_uncertain([_unc(text="Дискретна[неразборчиво]")]) == []


def test_nothing_uncertain_in_nothing_out():
    assert vision.meaningful_uncertain([]) == []


# ── the filter is actually wired in ──────────────────────────────────────────
# meaningful_divergences being correct is worth nothing if transcribe_consensus
# forgets to call it, and that omission is invisible to every test above.

from app.services.vision import Transcription  # noqa: E402


def _transcription(markdown: str) -> Transcription:
    return Transcription(
        title="Графы",
        subject=None,
        markdown=markdown,
        margin_notes=[],
        uncertain=[],
        numeric_tokens=[],
        unreadable_count=0,
    )


async def _stub_runs(monkeypatch, markdowns: list[str]) -> None:
    """Make each transcribe() call hand back the next prepared run."""
    remaining = list(markdowns)

    async def fake_transcribe(image_bytes):
        return _transcription(remaining.pop(0)), []

    monkeypatch.setattr(vision, "transcribe", fake_transcribe)
    monkeypatch.setattr(vision.settings, "VISION_RUNS", len(markdowns))


async def test_consensus_does_not_report_alignment_noise(monkeypatch):
    # The third run drops the list numbering the other two kept. Nothing here
    # is a misreading, so nothing should reach the user.
    await _stub_runs(
        monkeypatch,
        [
            "1. Граф\n2. Вершина\nСтепень равна 5",
            "1. Граф\n2. Вершина\nСтепень равна 5",
            "Граф\nВершина\nСтепень равна 5",
        ],
    )

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert result.numeric_divergences == []


async def test_consensus_still_reports_a_real_misreading(monkeypatch):
    # Same page, but the runs disagree about a value: that has to survive.
    await _stub_runs(
        monkeypatch,
        [
            "Степень вершины равна 5",
            "Степень вершины равна 5",
            "Степень вершины равна 1",
        ],
    )

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert len(result.numeric_divergences) == 1
    assert set(result.numeric_divergences[0].variants) == {"5", "1"}


async def _stub_uncertain(monkeypatch, entries: list) -> None:
    async def fake_transcribe(image_bytes):
        page = _transcription("Степень вершины равна 5")
        page.uncertain = list(entries)
        return page, []

    monkeypatch.setattr(vision, "transcribe", fake_transcribe)
    monkeypatch.setattr(vision.settings, "VISION_RUNS", 3)


async def test_consensus_drops_a_spot_that_names_no_other_reading(monkeypatch):
    # The filter being right is worth nothing if transcribe_consensus forgets
    # to call it, and that omission is invisible to every test above.
    await _stub_uncertain(
        monkeypatch, [_unc(why="слово обрезано краем страницы", alternatives=())]
    )

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert result.best.uncertain == []


async def test_consensus_keeps_a_spot_that_really_reads_two_ways(monkeypatch):
    await _stub_uncertain(monkeypatch, [_unc()])

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert [u.text for u in result.best.uncertain] == ["щ"]



# ── the ceilings are arithmetic now, not three hand-written numbers ──────────


def test_one_run_s_worst_case_counts_every_attempt_and_every_pause():
    # transcribe() makes one attempt more than it has pauses.
    assert vision.RUN_WORST_CASE_S == (
        (len(vision._RETRY_PAUSES_S) + 1) * vision._CALL_TIMEOUT_S
        + sum(vision._RETRY_PAUSES_S)
    )


def test_the_call_timeout_is_the_setting_itself():
    assert vision._CALL_TIMEOUT_S == vision.settings.VISION_CALL_TIMEOUT_S


def test_the_consensus_ceiling_exceeds_one_run_s_worst_case():
    # Below it a timeout cuts the retries short, and the run it abandons was
    # already paid for.
    assert vision._CONSENSUS_TIMEOUT_S > vision.RUN_WORST_CASE_S


def test_the_defaults_reproduce_the_numbers_they_replaced():
    assert (
        vision._CALL_TIMEOUT_S,
        vision.RUN_WORST_CASE_S,
        vision._CONSENSUS_TIMEOUT_S,
    ) == (30, 93, 120)


def test_the_semaphore_holds_the_slots_the_album_arithmetic_assumes():
    # albums.py derives its ceiling from vision.API_SLOTS. If the semaphore
    # were built from a different number, that ceiling would be derived from
    # a fiction and nothing else would notice.
    assert vision._API_SLOTS._value == vision.API_SLOTS


# ── a failed attempt has to be legible in the log ────────────────────────────


async def _always_raises(monkeypatch, exc: BaseException) -> None:
    async def raising(**kwargs):
        raise exc

    monkeypatch.setattr(vision._client.aio.models, "generate_content", raising)
    monkeypatch.setattr(vision, "_RETRY_PAUSES_S", (0, 0))


async def test_a_timeout_reaches_the_log_by_name(monkeypatch, caplog):
    """str(TimeoutError()) is "", so printing the exception produced a line
    ending in a bare colon. Three of those were the entire trace a failed
    album left behind — enough to know something broke, not what."""
    import logging

    await _always_raises(monkeypatch, TimeoutError())

    with caplog.at_level(logging.WARNING, logger="app.services.vision"):
        result, stats = await vision.transcribe(b"x")

    assert result is None and len(stats) == 3
    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 3
    assert all("TimeoutError" in message for message in messages)


async def test_the_log_says_which_attempt_and_whether_a_retry_is_coming(
    monkeypatch, caplog
):
    # "retryable" on the third attempt was true and useless: it was retryable
    # and got no retry. Only transcribe() knows both halves.
    import logging

    await _always_raises(monkeypatch, TimeoutError())

    with caplog.at_level(logging.WARNING, logger="app.services.vision"):
        await vision.transcribe(b"x")

    messages = [record.getMessage() for record in caplog.records]
    assert "attempt 1/3" in messages[0] and "retrying" in messages[0]
    assert "attempt 3/3" in messages[2] and "no retry left" in messages[2]


async def test_a_failure_that_is_not_retried_says_so_on_its_first_attempt(
    monkeypatch, caplog
):
    import logging

    await _always_raises(monkeypatch, ValueError("bad argument"))

    with caplog.at_level(logging.WARNING, logger="app.services.vision"):
        result, stats = await vision.transcribe(b"x")

    assert result is None and len(stats) == 1
    message = caplog.records[0].getMessage()
    assert "attempt 1/3" in message
    assert "no retry left" in message
    assert "ValueError: bad argument" in message
