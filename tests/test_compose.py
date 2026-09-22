"""Stage two — app/services/compose.py.

The stage is off by default and refuses itself on any doubt, so most of this
file is about what it must *not* do: not run when disabled, not change a
number, not lose a mark, not shrink a document, and never sink a record by
failing. The one thing it is allowed to do that looks like a violation — add
the word "Определение" over a definition — is the reason word drift is
reported rather than refused on.
"""

from types import SimpleNamespace

import pytest

from app.services import compose, vision

SOURCE = (
    "Теорема Кантора о вложенных отрезках\n"
    "Пусть $I_n = [a_n; b_n]$, где $a_n \\le b_n$ для всех $n \\in \\mathbb{N}$.\n"
    "Тогда пересечение непусто.\n"
    "Длина отрезка равна 0,75 при n = 12.\n"
)


def _fake_client(generate_content):
    return SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )
    )


def _answering(text: str, tokens=(10, 20)):
    async def generate_content(**kwargs):
        return SimpleNamespace(
            text=text,
            usage_metadata=SimpleNamespace(
                prompt_token_count=tokens[0], candidates_token_count=tokens[1]
            ),
        )

    return generate_content


async def _run(monkeypatch, answer: str, **settings_overrides):
    monkeypatch.setattr(compose.settings, "COMPOSE_ENABLED", True)
    for name, value in settings_overrides.items():
        monkeypatch.setattr(compose.settings, name, value)
    monkeypatch.setattr(vision, "_client", _fake_client(_answering(answer)))
    return await compose.compose(SOURCE)


# ── off means off ────────────────────────────────────────────────────────────


async def test_the_stage_is_off_by_default(monkeypatch):
    assert compose.settings.COMPOSE_ENABLED is False


async def test_disabled_makes_no_call_and_changes_nothing(monkeypatch):
    called = False

    async def must_not_run(**kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(compose.settings, "COMPOSE_ENABLED", False)
    monkeypatch.setattr(vision, "_client", _fake_client(must_not_run))

    result = await compose.compose(SOURCE)

    assert called is False
    assert result.markdown == SOURCE
    assert result.stats == []
    assert result.refused is None


# ── what the call is given ───────────────────────────────────────────────────


async def test_the_photograph_never_reaches_this_call(monkeypatch):
    """The whole reason the stage exists. A model that cannot see the page
    cannot produce the fluent retelling of one."""
    sent: list[dict] = []

    async def capture(**kwargs):
        sent.append(kwargs)
        return SimpleNamespace(text="# Теорема", usage_metadata=None)

    monkeypatch.setattr(compose.settings, "COMPOSE_ENABLED", True)
    monkeypatch.setattr(vision, "_client", _fake_client(capture))

    await compose.compose(SOURCE)

    contents = sent[0]["contents"]
    assert all(isinstance(part, str) for part in contents)
    assert contents == [compose.COMPOSE_PROMPT, SOURCE]


async def test_the_answer_is_markdown_and_not_json(monkeypatch):
    # response_mime_type=application/json would make the model wrap a document
    # in a string field, and there would be a parse to fail where there is
    # nothing to parse.
    sent: list[dict] = []

    async def capture(**kwargs):
        sent.append(kwargs)
        return SimpleNamespace(text="# Теорема", usage_metadata=None)

    monkeypatch.setattr(compose.settings, "COMPOSE_ENABLED", True)
    monkeypatch.setattr(vision, "_client", _fake_client(capture))

    await compose.compose(SOURCE)

    assert sent[0]["config"].response_mime_type is None


async def test_the_call_goes_to_the_compose_model_and_is_billed_as_one(
    monkeypatch,
):
    monkeypatch.setattr(compose.settings, "COMPOSE_MODEL", "gemini-2.5-flash-lite")
    result = await _run(monkeypatch, SOURCE + "\n\n**жирным**")

    assert result.stats[0].kind == "compose"
    assert result.stats[0].model == "gemini-2.5-flash-lite"
    assert result.stats[0].cost_usd is not None


# ── the guards ───────────────────────────────────────────────────────────────


async def test_a_composition_that_touches_nothing_forbidden_is_accepted(
    monkeypatch,
):
    composed = (
        "# Теорема Кантора о вложенных отрезках\n\n"
        "Пусть $I_n = [a_n; b_n]$, где $a_n \\le b_n$ для всех "
        "$n \\in \\mathbb{N}$. Тогда пересечение непусто.\n\n"
        "Длина отрезка равна 0,75 при n = 12.\n"
    )

    result = await _run(monkeypatch, composed)

    assert result.refused is None
    assert result.markdown == composed.strip()  # the answer is stripped


async def test_a_changed_number_is_refused(monkeypatch):
    result = await _run(monkeypatch, SOURCE.replace("n = 12", "n = 13"))

    assert result.refused == "numbers"
    assert result.markdown == SOURCE


async def test_a_number_quietly_normalised_is_refused(monkeypatch):
    # 0,75 -> 0.75 looks like tidying and is exactly what rule 3 of the
    # transcription prompt forbids: the page said what it said.
    result = await _run(monkeypatch, SOURCE.replace("0,75", "0.75"))

    assert result.refused == "numbers"


async def test_a_lost_unreadable_mark_is_refused(monkeypatch):
    source_with_mark = SOURCE + "Далее [неразборчиво] и ещё строка.\n"

    async def run(answer):
        monkeypatch.setattr(compose.settings, "COMPOSE_ENABLED", True)
        monkeypatch.setattr(vision, "_client", _fake_client(_answering(answer)))
        return await compose.compose(source_with_mark)

    filled = await run(source_with_mark.replace("[неразборчиво]", "формула"))

    assert filled.refused == "unreadable marks"
    assert filled.markdown == source_with_mark


async def test_a_document_that_came_back_shorter_is_refused(monkeypatch):
    # Half the text gone, and the half that went had no numbers in it, so the
    # numbers guard would have waved it through.
    short = "Теорема Кантора\nДлина отрезка равна 0,75 при n = 12.\n"
    result = await _run(monkeypatch, short)

    assert result.refused == "too short"
    assert result.markdown == SOURCE


async def test_an_empty_answer_is_refused_as_empty_not_as_a_failure(monkeypatch):
    # The call happened and was billed. "call failed" would send whoever reads
    # the log looking for a network problem that is not there.
    result = await _run(monkeypatch, "   \n  ")

    assert result.refused == "empty"
    assert result.markdown == SOURCE
    assert result.stats[0].error == "empty model response"


async def test_renumbering_a_list_is_not_a_changed_number(monkeypatch):
    """Rule 8 lets the composer turn a run of lines into a list, and a list
    markdown renumbers. Counting "1." as a value on the page would refuse
    every composition that did what it was asked."""
    source = "Свойства:\nпервое свойство\nвторое свойство\nтретье свойство\n"
    composed = (
        "## Свойства\n\n"
        "1. первое свойство\n2. второе свойство\n3. третье свойство\n"
    )
    monkeypatch.setattr(compose.settings, "COMPOSE_ENABLED", True)
    monkeypatch.setattr(vision, "_client", _fake_client(_answering(composed)))

    result = await compose.compose(source)

    assert result.refused is None


async def test_a_subscript_is_a_number_that_has_to_survive(monkeypatch):
    # $a_n$ carries no digit, but $I_1$ does, and a composer that renamed it
    # would be changing the mathematics.
    source = "Возьмём $I_1$ и $I_2$, длина равна 0,5.\n" * 4
    monkeypatch.setattr(compose.settings, "COMPOSE_ENABLED", True)
    monkeypatch.setattr(
        vision, "_client", _fake_client(_answering(source.replace("$I_2$", "$I_3$")))
    )

    result = await compose.compose(source)

    assert result.refused == "numbers"


# ── drift is measured, not punished ──────────────────────────────────────────


async def test_a_sub_heading_the_page_did_not_carry_is_allowed_and_counted(
    monkeypatch,
):
    """Rule 6 asks for "### Определение" over a definition, so the stage is
    *required* to write a word the page does not have. Refusing on word drift
    would refuse the prompt's own instruction; the number is kept so the size
    of the liberty can be seen before anyone decides what to do about it."""
    composed = "### Теорема\n\n" + SOURCE

    result = await _run(monkeypatch, composed)

    assert result.refused is None
    assert result.drift == 1


async def test_drift_counts_both_directions(monkeypatch):
    assert compose._drift("одно слово", "одно слово") == 0
    assert compose._drift("одно слово", "одно слово третье") == 1
    assert compose._drift("одно слово третье", "одно слово") == 1
    assert compose._drift("одно слово", "одно другое") == 2


async def test_drift_ignores_the_markup_that_was_added(monkeypatch):
    # **жирным** and жирным are the same word wearing markdown.
    assert compose._drift("термин определяется", "**термин** определяется") == 0


# ── a failure is not a lost record ───────────────────────────────────────────


async def test_a_failed_call_gives_back_the_text_it_was_given(monkeypatch):
    async def failing(**kwargs):
        raise TimeoutError()

    monkeypatch.setattr(compose.settings, "COMPOSE_ENABLED", True)
    monkeypatch.setattr(vision, "_client", _fake_client(failing))

    result = await compose.compose(SOURCE)

    assert result.markdown == SOURCE
    assert result.refused == "call failed"
    assert len(result.stats) == 1
    assert result.stats[0].success is False
    assert "TimeoutError" in result.stats[0].error


async def test_a_failed_call_is_still_written_to_the_spend_log(monkeypatch):
    # Rule 4 has no exception for a call that did not come back.
    async def failing(**kwargs):
        raise TimeoutError()

    monkeypatch.setattr(compose.settings, "COMPOSE_ENABLED", True)
    monkeypatch.setattr(vision, "_client", _fake_client(failing))

    result = await compose.compose(SOURCE)

    assert [s.kind for s in result.stats] == ["compose"]


# ── the prompt that ships ────────────────────────────────────────────────────


def test_the_compose_prompt_ships_and_is_loaded():
    assert compose.COMPOSE_PROMPT_WORDS > 100
    assert compose.COMPOSE_PROMPT != vision.TRANSCRIBE_PROMPT


def test_a_compose_prompt_that_is_not_there_stops_the_process():
    with pytest.raises(FileNotFoundError):
        vision.load_prompt("prompts-compose-v99.md")
