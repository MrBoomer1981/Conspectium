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
