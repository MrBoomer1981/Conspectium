"""Stage three — app/services/explain.py.

What the bot adds of its own is held by two guards, both in code: an
explanation is printed only with the sources the search gave for it, and the
summary may not state a number the record does not carry. Everything else
here is the composing stage's contract again: off by default, never shown the
photograph, every attempt billed, and a failure costing the stage and not the
record.
"""

from types import SimpleNamespace

import pytest

from app.core.config import GROUNDING_USD_PER_CALL
from app.services import explain, vision

RECORD = (
    "## Тригонометрическая форма\n"
    "$$\\boxed{z = |z|(\\cos\\varphi + i\\sin\\varphi)}$$\n"
    "Модуль произведения равен произведению модулей, аргументы складываются.\n"
    "$$z_1 z_2 = |z_1||z_2| e^{i(\\varphi_1 + \\varphi_2)}$$\n"
)

EXPLANATION = (
    "Формула Эйлера связывает показательную функцию с тригонометрическими: "
    "поворот на угол задаётся умножением на единичное комплексное число."
)


def _meta(segment: str | None = EXPLANATION, grounded: bool = True):
    if not grounded:
        return None
    return SimpleNamespace(
        grounding_chunks=[
            SimpleNamespace(web=SimpleNamespace(uri="https://ru.wikipedia.org/x", title="wikipedia.org")),
            SimpleNamespace(web=SimpleNamespace(uri="https://math.msu.ru/y", title="math.msu.ru")),
        ],
        grounding_supports=(
            [SimpleNamespace(segment=SimpleNamespace(text=segment), grounding_chunk_indices=[0, 1])]
            if segment
            else []
        ),
        web_search_queries=["формула Эйлера"],
    )


def _answer(summary: str = "Введена тригонометрическая форма комплексного числа.", items=None):
    import json

    items = items if items is not None else [
        {"anchor": "(1)", "title": "Формула Эйлера", "text": EXPLANATION}
    ]
    return json.dumps({"explanations": items, "summary": summary}, ensure_ascii=False)


def _response(text: str, meta=None, tokens=(100, 50)):
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=tokens[0], candidates_token_count=tokens[1]
        ),
        candidates=[SimpleNamespace(grounding_metadata=meta)],
    )


def _client(generate_content):
    return SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    )


def _answering(response, seen: list | None = None):
    async def generate_content(**kwargs):
        if seen is not None:
            seen.append(kwargs)
        return response

    return generate_content


async def _run(monkeypatch, response, seen=None, **overrides):
    monkeypatch.setattr(explain.settings, "EXPLAIN_ENABLED", True)
    monkeypatch.setattr(explain.settings, "EXPLAIN_MODEL", "gemini-3.8-flash")
    for name, value in overrides.items():
        monkeypatch.setattr(explain.settings, name, value)
    monkeypatch.setattr(vision, "_client", _client(_answering(response, seen)))
    return await explain.explain(RECORD)


# ── off means off, and the photograph never comes near ───────────────────────


def test_the_stage_is_off_by_default():
    assert explain.settings.EXPLAIN_ENABLED is False


async def test_off_makes_no_call_and_adds_nothing(monkeypatch):
    async def never(**kwargs):
        raise AssertionError("called while off")

    monkeypatch.setattr(vision, "_client", _client(never))
    result = await explain.explain(RECORD)
    assert result.explanations == [] and result.summary is None and result.stats == []


async def test_only_text_is_sent_and_the_search_is_switched_on(monkeypatch):
    seen: list[dict] = []
    await _run(monkeypatch, _response(_answer(), _meta()), seen)

    contents = seen[0]["contents"]
    assert all(isinstance(part, str) for part in contents)  # no image, ever
    assert contents[0] == explain.EXPLAIN_PROMPT
    tools = seen[0]["config"].tools
    assert tools and tools[0].google_search is not None


async def test_the_record_is_sent_with_its_formulas_numbered(monkeypatch):
    # "(1)" in the answer has to be the "(1)" on the page.
    seen: list[dict] = []
    await _run(monkeypatch, _response(_answer(), _meta()), seen)
    assert "(1)" in seen[0]["contents"][1]


# ── an explanation needs a source ────────────────────────────────────────────


async def test_an_explanation_keeps_the_sources_the_search_gave_it(monkeypatch):
    result = await _run(monkeypatch, _response(_answer(), _meta()))

    assert len(result.explanations) == 1
    item = result.explanations[0]
    assert item.anchor == "(1)" and item.title == "Формула Эйлера"
    assert [s.uri for s in item.sources] == [
        "https://ru.wikipedia.org/x",
        "https://math.msu.ru/y",
    ]


async def test_an_explanation_with_no_source_behind_it_is_not_printed(monkeypatch):
    # The reader cannot check a claim; the page has to say where it is from.
    result = await _run(monkeypatch, _response(_answer(), _meta(segment=None)))
    assert result.explanations == []
    assert result.unsourced == 1


async def test_an_ungrounded_answer_prints_no_explanation(monkeypatch):
    result = await _run(monkeypatch, _response(_answer(), _meta(grounded=False)))
    assert result.explanations == []


async def test_a_segment_is_found_through_json_escaping_and_latex(monkeypatch):
    # The segment is a slice of the raw answer, where a backslash is doubled
    # and a quote escaped; the parsed text has neither.
    text = r"Здесь $e^{i\varphi}$ — «поворот» на угол $\varphi$ вокруг нуля."
    items = [{"anchor": "(1)", "title": "Поворот", "text": text}]
    raw_segment = r"Здесь $e^{i\\varphi}$ — «поворот» на угол $\\varphi$ вокруг нуля."
    result = await _run(monkeypatch, _response(_answer(items=items), _meta(raw_segment)))
    assert len(result.explanations) == 1


async def test_no_more_than_eight_explanations(monkeypatch):
    items = [{"anchor": "(1)", "title": f"П{i}", "text": EXPLANATION} for i in range(12)]
    result = await _run(monkeypatch, _response(_answer(items=items), _meta()))
    assert len(result.explanations) == 8


# ── the summary restates the record ──────────────────────────────────────────


async def test_a_summary_that_restates_the_record_is_kept(monkeypatch):
    result = await _run(monkeypatch, _response(_answer(), _meta()))
    assert result.summary == "Введена тригонометрическая форма комплексного числа."


async def test_a_summary_with_a_number_the_record_does_not_carry_is_refused(monkeypatch):
    # A new number in the one box that claims to say what the lecture said is
    # the model inventing.
    answer = _answer(summary="Доказано 7 свойств модуля.")
    result = await _run(monkeypatch, _response(answer, _meta()))
    assert result.summary is None and result.summary_refused is True


async def test_a_summary_may_repeat_the_records_own_numbers(monkeypatch):
    answer = _answer(summary="Аргументы складываются: φ₁ + φ₂, индекс 1 и 2.")
    result = await _run(monkeypatch, _response(answer, _meta()))
    assert result.summary is not None


# ── parsing: never raises ────────────────────────────────────────────────────


def test_a_fenced_answer_is_read():
    parsed = explain.parse("```json\n" + _answer() + "\n```")
    assert parsed is not None and len(parsed[0]) == 1


@pytest.mark.parametrize("garbage", ["", "не JSON", "[1, 2]", '{"explanations": "нет"}'])
def test_garbage_is_none(garbage):
    assert explain.parse(garbage) is None


def test_an_explanation_without_text_is_dropped_and_a_blank_summary_is_none():
    parsed = explain.parse('{"explanations": [{"anchor": "a", "text": ""}], "summary": " "}')
    assert parsed == ([], None)


async def test_an_unparseable_answer_costs_the_stage_not_the_record(monkeypatch):
    result = await _run(monkeypatch, _response("не JSON", _meta()))
    assert result.refused == "unparseable"
    assert result.explanations == [] and len(result.stats) == 1


# ── the bill, and the attempt after the first ────────────────────────────────


async def test_a_grounded_call_is_billed_for_its_search_too(monkeypatch):
    result = await _run(monkeypatch, _response(_answer(), _meta(), tokens=(1000, 1000)))
    tokens_only = vision._cost_usd("gemini-3.8-flash", 1000, 1000, None)
    stat = result.stats[0]
    assert stat.kind == "explain" and stat.model == "gemini-3.8-flash"
    assert stat.cost_usd == pytest.approx(tokens_only + GROUNDING_USD_PER_CALL)


async def test_a_failed_call_is_billed_and_gives_nothing(monkeypatch):
    async def failing(**kwargs):
        raise ValueError("bad request")

    monkeypatch.setattr(explain.settings, "EXPLAIN_ENABLED", True)
    monkeypatch.setattr(vision, "_client", _client(failing))
    result = await explain.explain(RECORD)

    assert result.refused == "call failed"
    assert [s.success for s in result.stats] == [False]


async def test_a_timeout_is_not_waited_out_twice(monkeypatch):
    calls: list[int] = []

    async def hanging(**kwargs):
        calls.append(1)
        raise TimeoutError()

    monkeypatch.setattr(explain.settings, "EXPLAIN_ENABLED", True)
    monkeypatch.setattr(vision, "_client", _client(hanging))
    result = await explain.explain(RECORD)

    assert len(calls) == 1 and result.refused == "call failed"


def test_the_explain_prompt_ships_and_is_loaded():
    assert explain.EXPLAIN_PROMPT_WORDS > 50
    assert "JSON" in explain.EXPLAIN_PROMPT
