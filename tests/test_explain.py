"""Stage three — app/services/explain.py.

Two steps, because one did not work on the live model: asked to explain and
search at once, it searched for nothing and wrote textbook-like quotes from
memory. So one call writes the explanations and the summary, and each
explanation is then searched for in a call of its own.

What the bot adds is held by two guards, both in code: an explanation is
printed only with the sources its own search returned, and the summary may
not state a number the record does not carry. Everything else is the
composing stage's contract again: off by default, never shown the photograph,
every call billed, and a failure costing the stage and not the record.
"""

import json
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


def _answer(summary="Введена тригонометрическая форма комплексного числа.", items=None):
    items = items if items is not None else [
        {"anchor": "(1)", "title": "Формула Эйлера", "text": EXPLANATION}
    ]
    return json.dumps({"explanations": items, "summary": summary}, ensure_ascii=False)


def _written(text: str, tokens=(100, 50)):
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(prompt_token_count=tokens[0], candidates_token_count=tokens[1]),
        candidates=[SimpleNamespace(grounding_metadata=None)],
    )


def _found(*uris: str, tokens=(40, 20)):
    meta = SimpleNamespace(
        grounding_chunks=[
            SimpleNamespace(web=SimpleNamespace(uri=uri, title=uri.split("/")[2]))
            for uri in uris
        ],
        grounding_supports=[],
        web_search_queries=["запрос"] if uris else [],
    )
    return SimpleNamespace(
        text="Подтверждается учебником.",
        usage_metadata=SimpleNamespace(prompt_token_count=tokens[0], candidates_token_count=tokens[1]),
        candidates=[SimpleNamespace(grounding_metadata=meta)],
    )


def _client(written, found=None, seen: list | None = None):
    """Answers the first call with `written` and every search with `found`."""
    async def generate_content(**kwargs):
        if seen is not None:
            seen.append(kwargs)
        if kwargs["config"].tools:
            return found if found is not None else _found("https://ru.wikipedia.org/x")
        return written

    return SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))


async def _run(monkeypatch, written, found=None, seen=None):
    monkeypatch.setattr(explain.settings, "EXPLAIN_ENABLED", True)
    monkeypatch.setattr(explain.settings, "EXPLAIN_MODEL", "gemini-3.8-flash")
    monkeypatch.setattr(vision, "_client", _client(written, found, seen))
    return await explain.explain(RECORD)


# ── off means off, and the photograph never comes near ───────────────────────


def test_the_stage_is_off_by_default():
    assert explain.settings.EXPLAIN_ENABLED is False


async def test_off_makes_no_call_and_adds_nothing(monkeypatch):
    async def never(**kwargs):
        raise AssertionError("called while off")

    monkeypatch.setattr(vision, "_client", SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=never))))
    result = await explain.explain(RECORD)
    assert result.explanations == [] and result.summary is None and result.stats == []


async def test_only_text_is_ever_sent(monkeypatch):
    seen: list[dict] = []
    await _run(monkeypatch, _written(_answer()), seen=seen)
    for call in seen:
        assert all(isinstance(part, str) for part in call["contents"])  # no image, ever


async def test_the_writing_call_is_strict_json_and_does_not_search(monkeypatch):
    # A model asked to write and search at once searched for nothing; the
    # writing call asks for JSON only, which also keeps LaTeX from breaking it.
    seen: list[dict] = []
    await _run(monkeypatch, _written(_answer()), seen=seen)
    first = seen[0]
    assert first["contents"][0] == explain.EXPLAIN_PROMPT
    assert first["config"].response_mime_type == "application/json"
    assert not first["config"].tools


async def test_each_explanation_is_searched_for_in_a_call_of_its_own(monkeypatch):
    items = [{"anchor": "(1)", "title": f"П{i}", "text": EXPLANATION} for i in range(3)]
    seen: list[dict] = []
    await _run(monkeypatch, _written(_answer(items=items)), seen=seen)
    searches = [call for call in seen if call["config"].tools]
    assert len(searches) == 3
    assert all(call["config"].tools[0].google_search is not None for call in searches)
    assert all(explain.SOURCE_PROMPT in call["contents"][0] for call in searches)


async def test_the_record_is_sent_with_its_formulas_numbered(monkeypatch):
    # "(1)" in the answer has to be the "(1)" on the page.
    seen: list[dict] = []
    await _run(monkeypatch, _written(_answer()), seen=seen)
    assert "(1)" in seen[0]["contents"][1]


# ── an explanation needs a source ────────────────────────────────────────────


async def test_an_explanation_keeps_the_sources_its_search_returned(monkeypatch):
    found = _found("https://ru.wikipedia.org/x", "https://math.msu.ru/y")
    result = await _run(monkeypatch, _written(_answer()), found)

    assert len(result.explanations) == 1
    item = result.explanations[0]
    assert item.anchor == "(1)" and item.title == "Формула Эйлера"
    # Ranked, not in the search's order: the university before the encyclopedia.
    assert [s.uri for s in item.sources] == ["https://math.msu.ru/y", "https://ru.wikipedia.org/x"]
    assert [s.title for s in item.sources] == ["math.msu.ru", "ru.wikipedia.org"]


async def test_an_explanation_whose_search_found_nothing_is_not_printed(monkeypatch):
    # The reader cannot check a claim; the page has to say where it is from.
    result = await _run(monkeypatch, _written(_answer()), _found())
    assert result.explanations == []
    assert result.unsourced == 1


async def test_no_more_than_three_sources_and_none_twice(monkeypatch):
    found = _found(*(f"https://s{i}.ru/p" for i in (1, 1, 2, 3, 4)))
    result = await _run(monkeypatch, _written(_answer()), found)
    assert [s.uri for s in result.explanations[0].sources] == [
        "https://s1.ru/p", "https://s2.ru/p", "https://s3.ru/p",
    ]


async def test_no_more_than_eight_explanations_are_even_searched(monkeypatch):
    items = [{"anchor": "(1)", "title": f"П{i}", "text": EXPLANATION} for i in range(12)]
    seen: list[dict] = []
    result = await _run(monkeypatch, _written(_answer(items=items)), seen=seen)
    assert len(result.explanations) == 8
    assert len([c for c in seen if c["config"].tools]) == 8


# ── the summary restates the record ──────────────────────────────────────────


async def test_a_summary_that_restates_the_record_is_kept(monkeypatch):
    result = await _run(monkeypatch, _written(_answer()))
    assert result.summary == "Введена тригонометрическая форма комплексного числа."


async def test_a_summary_with_a_number_the_record_does_not_carry_is_refused(monkeypatch):
    # A new number in the one box that claims to say what the lecture said is
    # the model inventing.
    result = await _run(monkeypatch, _written(_answer(summary="Доказано 7 свойств модуля.")))
    assert result.summary is None and result.summary_refused is True


async def test_a_summary_may_repeat_the_records_own_numbers(monkeypatch):
    answer = _answer(summary="Аргументы складываются: индексы 1 и 2.")
    result = await _run(monkeypatch, _written(answer))
    assert result.summary is not None


# ── parsing: never raises, and LaTeX survives it ─────────────────────────────


def test_a_fenced_answer_is_read():
    parsed = explain.parse("```json\n" + _answer() + "\n```")
    assert parsed is not None and len(parsed[0]) == 1


@pytest.mark.parametrize("garbage", ["", "не JSON", "[1, 2]", '{"explanations": "нет"}'])
def test_garbage_is_none(garbage):
    assert explain.parse(garbage) is None


def test_an_explanation_without_text_is_dropped_and_a_blank_summary_is_none():
    parsed = explain.parse('{"explanations": [{"anchor": "a", "text": ""}], "summary": " "}')
    assert parsed == ([], None)


def test_latex_with_single_backslashes_survives_the_json():
    # "\varphi" made the whole answer unparseable on the live model, and
    # "\frac", "\rho", "\text", "\nu" are escapes JSON knows — a form feed, a
    # carriage return, a tab, a newline — that parsed into garbage silently.
    raw = (
        '{"explanations": [{"anchor": "(1)", "title": "t", '
        '"text": "$\\frac{a}{b}$, $\\rho$, $\\varphi$, $\\text{где}$, $\\nu$"}], '
        '"summary": "итог\\nвторая строка"}'
    )
    items, summary = explain.parse(raw)
    assert items[0]["text"] == r"$\frac{a}{b}$, $\rho$, $\varphi$, $\text{где}$, $\nu$"
    assert summary == "итог\nвторая строка"


def test_properly_escaped_latex_is_left_as_it_is():
    raw = '{"explanations": [{"anchor": "(1)", "title": "t", "text": "$\\\\frac{a}{b}$"}], "summary": "s"}'
    assert explain.parse(raw)[0][0]["text"] == r"$\frac{a}{b}$"


async def test_an_unparseable_answer_costs_the_stage_not_the_record(monkeypatch):
    result = await _run(monkeypatch, _written("не JSON"))
    assert result.refused == "unparseable"
    assert result.explanations == [] and len(result.stats) == 1


# ── the bill, and the attempt after the first ────────────────────────────────


async def test_every_call_is_billed_and_a_search_is_billed_for_its_search(monkeypatch):
    result = await _run(monkeypatch, _written(_answer(), tokens=(1000, 1000)))
    writing, searching = result.stats
    assert writing.kind == "explain" and searching.kind == "source"
    assert writing.cost_usd == pytest.approx(vision._cost_usd("gemini-3.8-flash", 1000, 1000, None))
    assert searching.cost_usd == pytest.approx(
        vision._cost_usd("gemini-3.8-flash", 40, 20, None) + GROUNDING_USD_PER_CALL
    )


async def test_a_failed_call_is_billed_and_gives_nothing(monkeypatch):
    async def failing(**kwargs):
        raise ValueError("bad request")

    monkeypatch.setattr(explain.settings, "EXPLAIN_ENABLED", True)
    monkeypatch.setattr(vision, "_client", SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=failing))))
    result = await explain.explain(RECORD)

    assert result.refused == "call failed"
    assert [s.success for s in result.stats] == [False]


async def test_a_timeout_is_not_waited_out_twice(monkeypatch):
    calls: list[int] = []

    async def hanging(**kwargs):
        calls.append(1)
        raise TimeoutError()

    monkeypatch.setattr(explain.settings, "EXPLAIN_ENABLED", True)
    monkeypatch.setattr(vision, "_client", SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=hanging))))
    result = await explain.explain(RECORD)

    assert len(calls) == 1 and result.refused == "call failed"


async def test_a_search_that_fails_costs_that_explanation_only(monkeypatch):
    written = _written(_answer(items=[
        {"anchor": "(1)", "title": "Раз", "text": EXPLANATION},
        {"anchor": "(1)", "title": "Два", "text": EXPLANATION + " Ещё."},
    ]))

    async def generate_content(**kwargs):
        if not kwargs["config"].tools:
            return written
        if "Два" in kwargs["contents"][0]:
            raise ValueError("search broke")
        return _found("https://ru.wikipedia.org/x")

    monkeypatch.setattr(explain.settings, "EXPLAIN_ENABLED", True)
    monkeypatch.setattr(vision, "_client", SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))))
    result = await explain.explain(RECORD)

    assert [item.title for item in result.explanations] == ["Раз"]
    assert result.unsourced == 1
    assert [s.success for s in result.stats] == [True, True, False]


def test_both_prompts_ship_and_are_loaded():
    assert explain.EXPLAIN_PROMPT_WORDS > 50
    assert "JSON" in explain.EXPLAIN_PROMPT
    assert "поиском" in explain.SOURCE_PROMPT


# ── sources: science first, then encyclopedias, study sites, the rest ───────


@pytest.mark.parametrize(
    ("site", "tier"),
    [
        ("msu.ru", 0), ("www.msu.ru", 0), ("math.nsu.ru", 0), ("stanford.edu", 0),
        ("ox.ac.uk", 0), ("arxiv.org", 0), ("mccme.ru", 0),
        ("kazan-university.ru", 0), ("univ-lyon1.fr", 0),
        ("wikipedia.org", 1), ("ru.wikipedia.org", 1), ("academic.ru", 1), ("bigenc.ru", 1),
        ("studfile.net", 2), ("libelli.ru", 2), ("stepik.org", 2),
        # Seen beside university pages in the first live run, and a name that
        # only looks like a university's.
        ("my-shop.ru", 3), ("githubusercontent.com", 3), ("narod.ru", 3),
        ("codechick.io", 3), ("universetoday.com", 3),
    ],
)
def test_a_source_is_ranked_by_its_site(site, tier):
    assert explain._tier(site) == tier


async def test_the_three_shown_are_the_most_trusted(monkeypatch):
    # A shop first in the search does not make it the first link, and it is
    # not dropped for being everyday: it is pushed out only because three
    # better ones came back.
    found = _found(
        "https://my-shop.ru/a", "https://studfile.net/b",
        "https://ru.wikipedia.org/c", "https://nsu.ru/d",
    )
    result = await _run(monkeypatch, _written(_answer()), found)
    assert [s.uri for s in result.explanations[0].sources] == [
        "https://nsu.ru/d", "https://ru.wikipedia.org/c", "https://studfile.net/b",
    ]


async def test_within_a_tier_the_search_keeps_its_order(monkeypatch):
    found = _found(
        "https://my-shop.ru/a", "https://nsu.ru/b", "https://codechick.io/c", "https://msu.ru/d",
    )
    result = await _run(monkeypatch, _written(_answer()), found)
    assert [s.uri for s in result.explanations[0].sources] == [
        "https://nsu.ru/b", "https://msu.ru/d", "https://my-shop.ru/a",
    ]


async def test_everyday_sources_alone_still_carry_an_explanation(monkeypatch):
    result = await _run(monkeypatch, _written(_answer()), _found("https://my-shop.ru/a"))
    assert [s.uri for s in result.explanations[0].sources] == ["https://my-shop.ru/a"]


def test_the_site_is_read_from_the_chunk_not_from_the_link():
    # The link is Google's redirect; on the Gemini API the chunk's title
    # names the site, and a domain, where one is given, outranks it.
    chunk = lambda uri, title, domain=None: SimpleNamespace(
        web=SimpleNamespace(uri=uri, title=title, domain=domain)
    )
    response = SimpleNamespace(candidates=[SimpleNamespace(grounding_metadata=SimpleNamespace(
        grounding_chunks=[
            chunk("https://vertexaisearch.cloud.google.com/1", "my-shop.ru"),
            chunk("https://vertexaisearch.cloud.google.com/2", "Комплексные числа", "msu.ru"),
        ]
    ))])
    assert [s.title for s in explain._sources(response)] == ["Комплексные числа", "my-shop.ru"]
