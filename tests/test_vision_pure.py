"""The pure decision functions of app/services/vision.py.

parse_response has its own file; this one covers the four helpers that decide
whether money is spent again, how much was spent, and how the result is
judged. All of them are pure, so they are cheap to pin down exactly.
"""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors as genai_errors
from google.genai import types

from app.services import consensus, vision
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
    return CallStats(
        kind="transcribe",
        model="gemini-3.5-flash-lite",
        tokens_in=None,
        tokens_out=None,
        tokens_thought=None,
        cost_usd=cost,
        latency_ms=0,
        success=cost is not None,
        error=None,
    )


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


def test_thinking_is_billed_at_the_output_rate():
    """The shape that was actually observed: 498 visible tokens against some
    7700 of thinking. Counted only by the visible half, that call goes into
    ai_calls at a fifteenth of its price, and DAILY_COST_LIMIT_USD stops being
    a limit with nothing failing to show it."""
    visible = vision._cost_usd("gemini-2.5-flash-lite", 1000, 500)
    thinking = vision._cost_usd("gemini-2.5-flash-lite", 1000, 500, 7700)

    assert thinking > visible
    # 0.40 per Mtok on 8200 output tokens, 0.10 on 1000 in.
    assert thinking == pytest.approx((1000 * 0.10 + 8200 * 0.40) / 1_000_000)


def test_a_model_that_does_not_think_costs_what_it_always_did():
    # Absent, not unknown: the field is missing exactly when there was no
    # thinking, so None reads as zero rather than voiding the price.
    assert vision._cost_usd("gemini-2.5-flash-lite", 1_000_000, 1_000_000, None) == 0.50


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
    assert vision._verdict(1.0, False) == "clean"
    assert vision._verdict(0.90, False) == "clean"
    assert vision._verdict(0.8999, False) == "needs_review"
    assert vision._verdict(0.70, False) == "needs_review"
    assert vision._verdict(0.6999, False) == "rejected"
    assert vision._verdict(0.0, False) == "rejected"


def test_vouching_numbers_move_only_the_bottom_band():
    """A page whose runs read the same numbers is saved and flagged, never
    thrown away — and never called clean either, because they did disagree
    about something."""
    assert vision._verdict(0.6999, True) == "needs_review"
    assert vision._verdict(0.0, True) == "needs_review"
    # Above the bottom band the vouch changes nothing at all.
    assert vision._verdict(0.70, True) == "needs_review"
    assert vision._verdict(0.95, True) == "clean"


def test_numbers_vouch_only_for_a_page_that_has_enough_of_them():
    five = ["Рёбра 1, 0 и степени 2, 3, 4"] * 3
    four = ["Рёбра 1, 0 и степени 2, 3"] * 3

    assert vision.numbers_vouch(five, []) is True
    assert vision.numbers_vouch(four, []) is False
    assert vision.numbers_vouch(["Текста без чисел"] * 3, []) is False


def test_one_reported_divergence_is_enough_to_refuse_the_vouch():
    """The unfiltered list, deliberately. meaningful_divergences drops a number
    against a gap as an alignment artefact, which is right when the question is
    "tell the reader"; here the question is whether the runs read the same
    page, and a gap means one of them read something the others did not."""
    runs = [
        "Рёбра 1, 0 и степени 2, 3, 4",
        "Рёбра 1, 0 и степени 2, 3, 4",
        "Рёбра 1, 0 и степени 2, 3, 9",
    ]
    reported = consensus.compare(runs).divergences

    assert reported
    assert vision.numbers_vouch(runs, reported) is False


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

    async def fake_transcribe(image_bytes, model):
        return _transcription(remaining.pop(0)), []

    monkeypatch.setattr(vision, "transcribe", fake_transcribe)
    monkeypatch.setattr(vision.settings, "VISION_RUNS", len(markdowns))


async def _stub_partial_runs(monkeypatch, outcomes: list[str | None]) -> None:
    """Some runs come back readable, some do not."""
    remaining = list(outcomes)

    async def fake_transcribe(image_bytes, model):
        markdown = remaining.pop(0)
        return (_transcription(markdown) if markdown else None), []

    monkeypatch.setattr(vision, "transcribe", fake_transcribe)
    monkeypatch.setattr(vision.settings, "VISION_RUNS", len(outcomes))


async def test_one_readable_run_is_kept_and_says_it_was_not_checked(monkeypatch):
    """One run is not a consensus and is not nothing either. Dropping it cost
    the page, and a page used to cost the album — while the text on it was
    perfectly legible."""
    await _stub_partial_runs(monkeypatch, ["Степень вершины равна 5", None, None])

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert result.best.markdown == "Степень вершины равна 5"
    assert result.text_agreement is None  # a comparison needs two of something
    assert result.numeric_agreement is None
    assert result.numeric_divergences == []
    assert result.verdict == "needs_review"


async def test_no_readable_run_is_still_nothing(monkeypatch):
    await _stub_partial_runs(monkeypatch, [None, None, None])

    result, stats = await vision.transcribe_consensus(b"x")

    assert result is None


async def test_two_readable_runs_are_compared_as_before(monkeypatch):
    await _stub_partial_runs(
        monkeypatch, ["Степень вершины равна 5", "Степень вершины равна 5", None]
    )

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert result.text_agreement == 1.0


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
    async def fake_transcribe(image_bytes, model):
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

    monkeypatch.setattr(vision, "_client", _fake_client(raising))
    monkeypatch.setattr(vision, "_RETRY_PAUSES_S", (0, 0))


async def test_a_timeout_reaches_the_log_by_name(monkeypatch, caplog):
    """str(TimeoutError()) is "", so printing the exception produced a line
    ending in a bare colon. Three of those were the entire trace a failed
    album left behind — enough to know something broke, not what."""
    import logging

    await _always_raises(monkeypatch, TimeoutError())

    with caplog.at_level(logging.WARNING, logger="app.services.vision"):
        result, stats = await vision.transcribe(b"x", "test-model")

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
        await vision.transcribe(b"x", "test-model")

    messages = [record.getMessage() for record in caplog.records]
    assert "attempt 1/3" in messages[0] and "retrying" in messages[0]
    assert "attempt 3/3" in messages[2] and "no retry left" in messages[2]


async def test_a_failure_that_is_not_retried_says_so_on_its_first_attempt(
    monkeypatch, caplog
):
    import logging

    await _always_raises(monkeypatch, ValueError("bad argument"))

    with caplog.at_level(logging.WARNING, logger="app.services.vision"):
        result, stats = await vision.transcribe(b"x", "test-model")

    assert result is None and len(stats) == 1
    message = caplog.records[0].getMessage()
    assert "attempt 1/3" in message
    assert "no retry left" in message
    assert "ValueError: bad argument" in message


# ── how the model is asked, as opposed to what it is asked ───────────────────


def _fake_client(generate_content):
    """The whole client, not a method on it — test_reliability.py records the
    reason: patching _client.aio.models breaks the day the SDK gives that
    object __slots__."""
    return SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )
    )


def test_by_default_neither_new_knob_is_sent():
    # "unset" has to mean absent rather than a value we picked: Gemini's own
    # default is the baseline every measurement will be compared against.
    config = vision._generation_config()
    assert config.media_resolution is None
    assert config.thinking_config is None


def test_what_was_always_sent_is_still_sent():
    config = vision._generation_config()
    assert config.response_mime_type == "application/json"
    assert config.max_output_tokens == vision.MAX_OUTPUT_TOKENS


def test_the_temperature_is_not_lowered_and_no_seed_goes_out():
    # Runs made identical would drive text_agreement up without touching
    # accuracy: the instrument inverted rather than merely broken.
    config = vision._generation_config()
    assert config.temperature == 1.0
    assert config.seed is None


@pytest.mark.parametrize(
    "setting,expected",
    [
        ("low", types.MediaResolution.MEDIA_RESOLUTION_LOW),
        ("medium", types.MediaResolution.MEDIA_RESOLUTION_MEDIUM),
        ("high", types.MediaResolution.MEDIA_RESOLUTION_HIGH),
    ],
)
def test_each_media_resolution_reaches_the_call(monkeypatch, setting, expected):
    monkeypatch.setattr(vision.settings, "VISION_MEDIA_RESOLUTION", setting)
    assert vision._generation_config().media_resolution == expected


@pytest.mark.parametrize(
    "setting,expected",
    [
        ("minimal", types.ThinkingLevel.MINIMAL),
        ("low", types.ThinkingLevel.LOW),
        ("medium", types.ThinkingLevel.MEDIUM),
        ("high", types.ThinkingLevel.HIGH),
    ],
)
def test_each_thinking_level_reaches_the_call(monkeypatch, setting, expected):
    monkeypatch.setattr(vision.settings, "VISION_THINKING_LEVEL", setting)
    config = vision._generation_config()
    assert config.thinking_config is not None
    assert config.thinking_config.thinking_level == expected


async def test_the_configured_knobs_reach_the_actual_call(monkeypatch):
    # _generation_config being right is worth nothing if _one_attempt builds
    # its own config inline, which is exactly what it used to do.
    monkeypatch.setattr(vision.settings, "VISION_MEDIA_RESOLUTION", "high")
    sent: list[dict] = []

    async def capture(**kwargs):
        sent.append(kwargs)
        raise TimeoutError()

    monkeypatch.setattr(vision, "_client", _fake_client(capture))
    monkeypatch.setattr(vision, "_RETRY_PAUSES_S", ())

    await vision.transcribe(b"x", "test-model")

    assert sent[0]["config"].media_resolution == (
        types.MediaResolution.MEDIA_RESOLUTION_HIGH
    )


# ── the model a row names is the model that was called ───────────────────────


async def test_the_model_reaches_the_call_and_every_row_of_the_run(monkeypatch):
    sent: list[dict] = []

    async def capture(**kwargs):
        sent.append(kwargs)
        raise TimeoutError()

    monkeypatch.setattr(vision, "_client", _fake_client(capture))
    monkeypatch.setattr(vision, "_RETRY_PAUSES_S", (0, 0))

    _, stats = await vision.transcribe(b"x", "some-other-model")

    assert [call["model"] for call in sent] == ["some-other-model"] * 3
    assert {s.model for s in stats} == {"some-other-model"}
    assert {s.kind for s in stats} == {"transcribe"}


async def test_the_cost_is_priced_by_the_model_that_was_called(monkeypatch):
    """_cost_usd used to be handed settings.VISION_MODEL. A second stage on
    another model would have been costed at the first stage's price — a
    number that looks perfectly reasonable and is simply wrong."""
    answer = SimpleNamespace(
        text='{"markdown": "Enough body text here to pass the length gate."}',
        usage_metadata=SimpleNamespace(
            prompt_token_count=1_000_000, candidates_token_count=1_000_000
        ),
    )

    async def answering(**kwargs):
        return answer

    monkeypatch.setattr(vision, "_client", _fake_client(answering))

    _, priced = await vision.transcribe(b"x", "gemini-2.5-flash-lite")
    _, unpriced = await vision.transcribe(b"x", "gemini-9.9-imaginary")

    assert priced[0].cost_usd == pytest.approx(0.10 + 0.40)
    assert unpriced[0].cost_usd is None


# ── numeric_agreement: the instrument that survives a change of prompt ───────


def test_identical_number_sequences_agree_completely():
    assert vision.numeric_agreement([["1", "2", "3"]] * 3) == 1.0


def test_one_changed_digit_shows_up():
    agreement = vision.numeric_agreement(
        [["1", "2", "3"], ["1", "2", "3"], ["1", "7", "3"]]
    )
    assert 0.0 < agreement < 1.0


def test_a_page_with_no_numbers_agrees_rather_than_dividing_by_zero():
    assert vision.numeric_agreement([[], [], []]) == 1.0


def test_the_measure_is_the_mean_over_every_pair():
    # Two runs agree and the third differs from both, so one pair of three is
    # perfect. Reading the best pair, or the first, would report far higher.
    assert vision.numeric_agreement([["1"], ["1"], ["9"]]) == pytest.approx(1 / 3)


async def test_numbers_agree_where_layout_does_not(monkeypatch, caplog):
    """The whole reason for a second measure, and it is worth nothing if
    transcribe_consensus never computes it. Two runs read the same numbers and
    set them out differently: text agreement falls, numeric agreement does
    not."""
    import logging

    pages = [
        ("# Теорема\n\n**Дано:** $n = 5$, $k = 12$", ["5", "12"]),
        ("Теорема\nДано: n = 5, k = 12", ["5", "12"]),
    ]
    remaining = list(pages)

    async def fake_transcribe(image_bytes, model):
        markdown, tokens = remaining.pop(0)
        page = _transcription(markdown)
        page.numeric_tokens = tokens
        return page, []

    monkeypatch.setattr(vision, "transcribe", fake_transcribe)
    monkeypatch.setattr(vision.settings, "VISION_RUNS", 2)

    with caplog.at_level(logging.INFO, logger="app.services.vision"):
        result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    line = next(m for m in (r.getMessage() for r in caplog.records) if "consensus:" in m)
    assert "numeric_agreement=1.000" in line
    assert "text_agreement=1.000" not in line


async def test_the_number_in_the_log_is_the_number_in_the_record(
    monkeypatch, caplog
):
    """One value read twice, never two computations.

    The column is what the experiment queries; the log line is what anyone
    would check the column against. Computed separately they can drift, and a
    disagreeing pair is worse than either alone — there would be no way to
    tell which of the two is the measurement.
    """
    import logging

    pages = [
        ("Дано: $n = 5$, $k = 12$, $m = 7$", ["5", "12", "7"]),
        ("Дано: $n = 5$, $k = 13$, $m = 7$", ["5", "13", "7"]),
    ]
    remaining = list(pages)

    async def fake_transcribe(image_bytes, model):
        markdown, tokens = remaining.pop(0)
        page = _transcription(markdown)
        page.numeric_tokens = tokens
        return page, []

    monkeypatch.setattr(vision, "transcribe", fake_transcribe)
    monkeypatch.setattr(vision.settings, "VISION_RUNS", 2)

    with caplog.at_level(logging.INFO, logger="app.services.vision"):
        result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    # Strictly inside the range, so a field frozen at either end fails here.
    assert 0.0 < result.numeric_agreement < 1.0
    assert result.numeric_agreement == pytest.approx(
        vision.numeric_agreement([tokens for _, tokens in pages])
    )

    line = next(m for m in (r.getMessage() for r in caplog.records) if "consensus:" in m)
    assert f"numeric_agreement={result.numeric_agreement:.3f}" in line


def test_a_page_dense_with_repeated_digits_is_not_written_off_as_noise():
    """difflib's autojunk heuristic calls anything common in a sequence over
    200 long "noise" and stops matching on it. A page of matrices is exactly
    that: four hundred numbers out of a handful of digits. With the heuristic
    left on, four changes out of four hundred come back as total disagreement.
    """
    a = [str(i % 5) for i in range(400)]
    b = list(a)
    for position in (17, 123, 256, 301):
        b[position] = "9"

    assert vision.numeric_agreement([a, b]) > 0.5


# ── a divergent number lowers the verdict ────────────────────────────────────

# A page's worth of text, because that is where the rule has to work. On a
# short line one changed digit moves compare_text to 0.83 and the band already
# says needs_review; on a real page it moves it to 0.97 and the band says
# clean. That second case is the one the deployed bot produced twice in an
# evening — text_agreement=0.969 with a divergence kept, verdict clean.
_PAGE = (
    "Теорема. Пусть дан связный граф без кратных рёбер и петель. Тогда "
    "сумма степеней всех его вершин равна удвоенному числу рёбер, и степень "
    "выделенной вершины равна 5."
)
_PAGE_MISREAD = _PAGE.replace("равна 5.", "равна 1.")

# A page whose runs disagree only about markdown: the third drops the list
# numbering, so the raw comparison aligns numbers against gaps and reports
# divergences that are not misreadings. Long enough that the band still says
# clean, which is what makes it a test of the filter rather than of the band.
_LIST_PAGE = (
    "Теорема о вложенных отрезках. Пусть дана последовательность отрезков, "
    "каждый следующий содержится в предыдущем. Тогда их пересечение непусто.\n"
    "1. Первое свойство последовательности\n"
    "2. Второе свойство последовательности\n"
    "3. Третье свойство последовательности\n"
    "Отсюда следует утверждение о полноте прямой."
)
_LIST_PAGE_UNNUMBERED = (
    _LIST_PAGE.replace("1. ", "").replace("2. ", "").replace("3. ", "")
)


async def test_a_divergent_number_lowers_a_clean_verdict(monkeypatch):
    """The runs agree on the prose and disagree on a value.

    One character apart, so text_agreement barely moves and the band says
    clean — which is exactly the case this exists for. A sentence that makes
    no sense gets caught on re-reading; a wrong digit in a matrix looks as
    authoritative as a right one and stays.
    """
    await _stub_runs(monkeypatch, [_PAGE, _PAGE, _PAGE_MISREAD])

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert vision._verdict(result.text_agreement, False) == "clean"  # the band
    assert result.numeric_divergences  # but the numbers did not agree
    assert result.verdict == "needs_review"


async def test_agreement_with_no_divergence_stays_clean(monkeypatch):
    await _stub_runs(monkeypatch, [_PAGE] * 3)

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert result.numeric_divergences == []
    assert result.verdict == "clean"


async def test_an_alignment_artefact_does_not_lower_the_verdict(monkeypatch):
    """The filter is the whole reason the rule is safe to act on.

    One page of real notes produced eight raw divergences of which one was
    genuine; reading the unfiltered list would put the flag on every record
    and the flag would stop meaning anything. This page is the shape that
    produces them — one run drops the list numbering, so numbers align against
    gaps — and it has to come back clean.
    """
    runs = [_LIST_PAGE, _LIST_PAGE, _LIST_PAGE_UNNUMBERED]
    # The premise, stated so this cannot quietly become a test of nothing:
    # the raw comparison does report divergences here.
    assert consensus.compare(runs).divergences

    await _stub_runs(monkeypatch, runs)
    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert vision._verdict(result.text_agreement, False) == "clean"
    assert result.numeric_divergences == []
    assert result.verdict == "clean"


async def test_a_divergence_never_lifts_a_rejected_page(monkeypatch):
    """rejected exits the pipeline at step 10 and never reaches the database.
    A finding that means "look at this" must not be able to turn that into a
    record that gets saved."""
    await _stub_runs(
        monkeypatch,
        [
            "Степень вершины равна 5",
            "Совершенно другой текст про кольца и поля, 7 штук",
            "Третий вариант ни на что не похожий, всего 1",
        ],
    )

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert vision._verdict(result.text_agreement, False) == "rejected"
    assert result.verdict == "rejected"  # and the numbers did not vouch either


async def test_layout_alone_no_longer_throws_a_page_away(monkeypatch):
    """The loss of 2026-09-23, as a test. Five pages were photographed, two
    came back at text_agreement 0.428 and 0.419 with their numbers agreeing
    exactly, and "a record is all its pages or none" took the other three with
    them. The bands measure markdown; prompts-v5.md gave the markdown away to
    the composing stage and the bands stayed where they were."""
    runs = [
        "# Матрица смежности $|V| \\times |V|$\n\n"
        "**Если существует ребро**, то $a_{ij} = 1$, иначе 0.\n\n"
        "- степени вершин: 2, 3, 4\n",
        "Матрица смежности размера V на V\n"
        "если существует ребро то a = 1 иначе 0\n"
        "степени вершин 2 3 4\n",
        "## Представление графов\n\n"
        "Матрица смежности. Ребро даёт 1, отсутствие даёт 0.\n"
        "Степени вершин равны 2, 3 и 4 соответственно.\n",
    ]
    await _stub_runs(monkeypatch, runs)

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert result.text_agreement < 0.70  # the band on its own says rejected
    assert result.verdict == "needs_review"  # the numbers say otherwise
    assert result.numeric_divergences == []


async def test_the_downgrade_is_the_one_the_record_is_built_from(monkeypatch):
    # The rule lives in transcribe_consensus rather than in the two capture
    # paths, so it has to come out on the result rather than be applied later.
    await _stub_runs(
        monkeypatch,
        [_PAGE, _PAGE, _PAGE.replace("равна 5.", "равна 15.")],
    )

    result, _ = await vision.transcribe_consensus(b"x")

    assert result is not None
    assert result.verdict == "needs_review"
    assert len(result.numeric_divergences) == 1


# ── a 200 that would not parse should say why the model stopped ──────────────


def _response(text, finish_reason=None, candidates=True):
    """A response shaped like the SDK's, with only what vision reads."""
    candidate = SimpleNamespace(finish_reason=finish_reason)
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=100, candidates_token_count=8192
        ),
        candidates=[candidate] if candidates else [],
    )


async def _attempt(monkeypatch, response):
    async def answering(**kwargs):
        return response

    monkeypatch.setattr(vision, "_client", _fake_client(answering))
    return await vision._one_attempt(b"x", "test-model")


async def test_an_answer_cut_off_at_our_ceiling_says_so(monkeypatch):
    """MAX_TOKENS is the difference between "the model came back wrong" and
    "we truncated it ourselves". The JSON ends mid-string, parse_response
    returns None as it must, and the row used to say only that much."""
    _, stats, retryable = await _attempt(
        monkeypatch, _response("{'markdown': 'половина ответа", "MAX_TOKENS")
    )

    assert stats.success is False
    assert "unparseable model response" in stats.error
    assert "MAX_TOKENS" in stats.error
    # The one parse failure not worth asking again: the ceiling is ours, and
    # the second call walks into the same wall having paid the same way there.
    assert retryable is False


async def test_an_enum_finish_reason_is_recorded_by_name(monkeypatch):
    # str() on the SDK enum prints "FinishReason.MAX_TOKENS" into a column
    # that gets read by eye and grepped in logs.
    from google.genai import types

    _, stats, _ = await _attempt(
        monkeypatch, _response("не json", types.FinishReason.MAX_TOKENS)
    )

    assert "finish_reason=MAX_TOKENS" in stats.error
    assert "FinishReason." not in stats.error


async def test_a_model_that_simply_answered_in_prose_is_distinguishable(
    monkeypatch,
):
    # STOP means the answer finished on its own and still was not JSON, which
    # is a different problem with a different fix from a truncation.
    _, stats, _ = await _attempt(monkeypatch, _response("Конечно! Вот текст:", "STOP"))

    assert "finish_reason=STOP" in stats.error


async def test_a_response_with_no_candidates_still_records_the_failure(
    monkeypatch,
):
    _, stats, _ = await _attempt(
        monkeypatch, _response("не json", candidates=False)
    )

    assert stats.error == "unparseable model response (not json)"


async def test_an_absent_finish_reason_adds_nothing(monkeypatch):
    _, stats, _ = await _attempt(monkeypatch, _response("не json", None))

    assert stats.error == "unparseable model response (not json)"


# ── what came back instead of a record, and whether to ask again ─────────────


def test_the_shape_names_the_keys_and_not_the_page():
    """Diagnosis without content: "json without markdown" and "not json at
    all" have different fixes, and a student's notes do not belong in a log."""
    shape = vision._answer_shape(
        '{"title": "Графы", "text": "Степень вершины равна 5"}'
    )

    assert shape == "json keys: text,title"
    assert "Графы" not in shape
    assert "Степень" not in shape


def test_the_shape_of_everything_that_is_not_an_object():
    assert vision._answer_shape("Конечно! Вот текст:") == "not json"
    assert vision._answer_shape("   ") == "empty answer"
    assert vision._answer_shape("[1, 2, 3]") == "json list"
    assert vision._answer_shape("{}") == "json object with no keys"
    assert vision._answer_shape('"просто строка"') == "json str"


def test_the_shape_reads_a_fenced_answer_like_the_parser_does():
    assert vision._answer_shape(
        '```json\n{"markdown": "текст"}\n```'
    ) == "json keys: markdown"


def test_the_shape_names_at_most_eight_keys():
    many = "{" + ",".join(f'"k{i}": 1' for i in range(20)) + "}"

    assert vision._answer_shape(many).count(",") == vision._SHAPE_KEYS - 1


async def test_an_answer_that_stopped_of_its_own_accord_is_asked_again(
    monkeypatch,
):
    """The loss of 2026-09-23: four of one album's fifteen runs came back
    unparseable with finish_reason=STOP, one page lost all three, and the
    five-page record was never made — while eleven calls in the same minute
    parsed. At temperature 1.0 the next call is an independent draw."""
    _, _, retryable = await _attempt(
        monkeypatch, _response('{"title": "Графы"}', "STOP")
    )

    assert retryable is True


async def test_a_refusal_is_not_asked_again(monkeypatch):
    # SAFETY is the model declining. It declines the second time too.
    _, _, retryable = await _attempt(monkeypatch, _response("", "SAFETY"))

    assert retryable is False


async def test_an_unknown_finish_reason_is_asked_again(monkeypatch):
    _, _, retryable = await _attempt(monkeypatch, _response("не json", None))

    assert retryable is True


async def test_an_answer_that_parsed_is_never_retryable(monkeypatch):
    good = _response(
        '{"markdown": "Степень вершины равна 5", "title": "Графы"}', "STOP"
    )

    result, stats, retryable = await _attempt(monkeypatch, good)

    assert result is not None
    assert stats.success is True
    assert retryable is False


async def test_a_response_that_parsed_carries_no_error_whatever_it_finished_on(
    monkeypatch,
):
    good = '{"markdown": "Достаточно текста, чтобы пройти проверку длины."}'
    result, stats, _ = await _attempt(monkeypatch, _response(good, "MAX_TOKENS"))

    assert result is not None
    assert stats.success is True
    assert stats.error is None


def test_the_error_fits_the_column(monkeypatch):
    # ai_calls.error is 500 characters; _short_error already respects that and
    # this path builds its own string.
    long_reason = "X" * 900
    assert len(vision._unparseable(_response("x", long_reason))) <= 500


async def test_a_response_without_candidates_at_all_does_not_crash(monkeypatch):
    """The SDK's response shape is not a contract this project controls, and
    _usage guards the same way for the same reason.

    The cost of getting it wrong is not the missing reason. An exception here
    escapes _one_attempt, and the CallStats of a call that was already billed
    goes with it — transcribe_consensus can only log "run crashed" and record
    a row with no tokens on it.
    """
    no_candidates = SimpleNamespace(
        text="не json",
        usage_metadata=SimpleNamespace(
            prompt_token_count=7, candidates_token_count=11
        ),
    )

    _, stats, _ = await _attempt(monkeypatch, no_candidates)

    assert stats.error == "unparseable model response (not json)"
    assert (stats.tokens_in, stats.tokens_out) == (7, 11)  # the spend survives


async def test_a_candidate_without_a_finish_reason_does_not_crash(monkeypatch):
    bare = SimpleNamespace(
        text="не json",
        usage_metadata=SimpleNamespace(
            prompt_token_count=7, candidates_token_count=11
        ),
        candidates=[SimpleNamespace()],
    )

    _, stats, _ = await _attempt(monkeypatch, bare)

    assert stats.error == "unparseable model response (not json)"
    assert stats.tokens_out == 11


# ── the half of the budget that was invisible ────────────────────────────────


async def test_the_thinking_a_call_did_is_recorded(monkeypatch):
    """The shape that was actually observed on 2026-09-23, numbers and all.

    The call stopped at max_output_tokens having produced 498 visible tokens,
    because the rest of the allowance went on thinking. Stored as the visible
    half alone, a truncated call is indistinguishable in ai_calls from one
    that simply answered briefly — and a query over three days read as proof
    that the ceiling was not the problem.
    """
    thinking = SimpleNamespace(
        text="не json",
        usage_metadata=SimpleNamespace(
            prompt_token_count=1609,
            candidates_token_count=498,
            thoughts_token_count=7700,
        ),
        candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")],
    )

    _, stats, _ = await _attempt(monkeypatch, thinking)

    assert stats.tokens_thought == 7700
    assert stats.tokens_out == 498
    assert stats.error == (
        "unparseable model response (finish_reason=MAX_TOKENS, not json)"
    )


async def test_a_model_that_does_not_think_reports_none_not_zero(monkeypatch):
    # The field is absent, which is not the same claim as "it thought nothing".
    _, stats, _ = await _attempt(monkeypatch, _response("не json"))

    assert stats.tokens_thought is None
