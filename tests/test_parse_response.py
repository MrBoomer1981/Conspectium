"""parse_response: one case per row of the Contracts table, plus the wrapper
and garbage cases from PLAN.md task 5. Every case returns None or a correct
object — never raises.
"""

import json

from app.services.vision import Transcription, Uncertain, parse_response


def _raw(**payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False)


# ── Happy path and wrappers ──────────────────────────────────────────────────


def test_valid_full_object():
    raw = _raw(
        title="Механика",
        subject="Физика",
        markdown="# Механика\n\nТело движется равномерно.",
        margin_notes=["см. лекцию 3"],
        uncertain=[
            {
                "text": "v_0",
                "where": "формула 2",
                "why": "цифра или буква",
                "alternatives": ["v_o"],
            }
        ],
        numeric_tokens=["9,8", "10"],
        unreadable_count=1,
    )
    t = parse_response(raw)
    assert isinstance(t, Transcription)
    assert t.title == "Механика"
    assert t.subject == "Физика"
    assert t.markdown.startswith("# Механика")
    assert t.margin_notes == ["см. лекцию 3"]
    assert t.uncertain == [Uncertain("v_0", "формула 2", "цифра или буква", ["v_o"])]
    assert t.numeric_tokens == ["9,8", "10"]
    assert t.unreadable_count == 1


def test_json_fenced_block_is_tolerated():
    inner = _raw(markdown="Достаточно длинный текст записи для теста.")
    t = parse_response(f"```json\n{inner}\n```")
    assert isinstance(t, Transcription)
    assert t.markdown == "Достаточно длинный текст записи для теста."


def test_extra_confidence_field_is_ignored():
    t = parse_response(_raw(markdown="Текст записи.", confidence=0.95))
    assert isinstance(t, Transcription)
    assert not hasattr(t, "confidence")


# ── Inputs that must yield None ──────────────────────────────────────────────


def test_invalid_json_returns_none():
    assert parse_response("{not json at all") is None


def test_empty_string_returns_none():
    assert parse_response("") is None


def test_non_object_json_returns_none():
    assert parse_response("null") is None
    assert parse_response("[1, 2, 3]") is None
    assert parse_response('"just a string"') is None


def test_markdown_missing_returns_none():
    assert parse_response(_raw(title="Есть только заголовок")) is None


def test_markdown_wrong_type_returns_none():
    assert parse_response(_raw(markdown=123)) is None
    assert parse_response(_raw(markdown=None)) is None
    assert parse_response(_raw(markdown=["a", "b"])) is None


# ── Field fallbacks ─────────────────────────────────────────────────────────


def test_empty_markdown_still_parses():
    # "" is a string, so the record survives; the handler's MIN_MARKDOWN_LEN
    # check is what rejects short notes.
    t = parse_response(_raw(markdown=""))
    assert isinstance(t, Transcription)
    assert t.markdown == ""
    assert t.title == "Untitled"


def test_title_missing_is_derived_from_markdown():
    t = parse_response(_raw(markdown="Первая строка\nвторая строка"))
    assert t.title == "Первая строка"


def test_title_wrong_type_is_derived_from_markdown():
    t = parse_response(_raw(markdown="Заголовок из текста", title=42))
    assert t.title == "Заголовок из текста"


def test_title_truncated_to_60_chars():
    t = parse_response(_raw(markdown="текст", title="А" * 100))
    assert t.title == "А" * 60


def test_title_untitled_when_markdown_is_blank():
    t = parse_response(_raw(markdown="   \n\n  "))
    assert isinstance(t, Transcription)
    assert t.title == "Untitled"


def test_subject_defaults_to_none():
    assert parse_response(_raw(markdown="текст")).subject is None
    assert parse_response(_raw(markdown="текст", subject=123)).subject is None


def test_margin_notes_wrong_type_becomes_empty_list():
    assert parse_response(_raw(markdown="текст", margin_notes="не список")).margin_notes == []


def test_margin_notes_non_string_elements_dropped():
    t = parse_response(_raw(markdown="текст", margin_notes=["ок", 5, None, "тоже"]))
    assert t.margin_notes == ["ок", "тоже"]


def test_numeric_tokens_wrong_type_becomes_empty_list():
    assert parse_response(_raw(markdown="текст", numeric_tokens={})).numeric_tokens == []


def test_numeric_tokens_non_string_elements_dropped():
    t = parse_response(_raw(markdown="текст", numeric_tokens=["9,8", 10, "10"]))
    assert t.numeric_tokens == ["9,8", "10"]


def test_unreadable_count_wrong_type_becomes_zero():
    assert parse_response(_raw(markdown="текст")).unreadable_count == 0
    assert parse_response(_raw(markdown="текст", unreadable_count="х")).unreadable_count == 0
    assert parse_response(_raw(markdown="текст", unreadable_count=True)).unreadable_count == 0


def test_unreadable_count_numeric_string_is_coerced():
    assert parse_response(_raw(markdown="текст", unreadable_count="3")).unreadable_count == 3


def test_uncertain_wrong_type_becomes_empty_list():
    assert parse_response(_raw(markdown="текст", uncertain="нет")).uncertain == []


def test_uncertain_element_without_text_is_dropped():
    t = parse_response(_raw(markdown="текст", uncertain=[{"where": "тут"}, {"text": "ок"}]))
    assert [u.text for u in t.uncertain] == ["ок"]


def test_uncertain_element_non_string_text_is_dropped():
    t = parse_response(_raw(markdown="текст", uncertain=[{"text": 5}, {"text": "ок"}]))
    assert [u.text for u in t.uncertain] == ["ок"]


def test_uncertain_optional_fields_default():
    t = parse_response(_raw(markdown="текст", uncertain=[{"text": "x"}]))
    u = t.uncertain[0]
    assert u.where == ""
    assert u.why == ""
    assert u.alternatives == []


def test_uncertain_alternatives_wrong_type_becomes_empty_list():
    t = parse_response(
        _raw(markdown="текст", uncertain=[{"text": "x", "alternatives": "нет"}])
    )
    assert t.uncertain[0].alternatives == []


# ── Never raises ────────────────────────────────────────────────────────────


def test_never_raises_on_garbage():
    for bad in [
        "",
        "   ",
        "{",
        "}",
        "[}",
        "null",
        "true",
        "123",
        '{"markdown":',
        "```json\n```",
        "```\nnot json\n```",
    ]:
        parse_response(bad)  # must not raise


# ── LaTeX written with one backslash ─────────────────────────────────────────
# The model is asked for JSON and mostly doubles a LaTeX backslash. When it
# does not, a command whose letter is an escape JSON has — \t, \f, \b, \r —
# parsed into a control character without a word, and one whose letter is not
# — \pmod, \varphi — failed the whole answer, which cost the run.


def _markdown_of(body: str) -> str | None:
    t = parse_response('{"markdown": "' + body + '"}')
    return t.markdown if t is not None else None


def test_a_command_that_collides_with_an_escape_survives():
    assert _markdown_of(r"$\frac{a}{b}$, $\beta$, $\rho$, $\textbf{x}$") == (
        r"$\frac{a}{b}$, $\beta$, $\rho$, $\textbf{x}$"
    )


def test_a_command_json_has_no_escape_for_no_longer_fails_the_answer():
    assert _markdown_of(r"$23 \equiv 2 \pmod 7$ и $\varphi$") == (
        r"$23 \equiv 2 \pmod 7$ и $\varphi$"
    )


def test_a_line_break_before_latin_letters_stays_a_line_break():
    # Only a command no line of notes starts with is taken for one: "Re z"
    # and "sin x" begin lines of a page on complex numbers.
    assert _markdown_of(r"строка\nRe z = x\nsin x") == "строка\nRe z = x\nsin x"


def test_a_negation_is_read_as_the_command_it_is():
    assert _markdown_of(r"$a \neq b$") == r"$a \neq b$"


def test_a_unicode_escape_is_still_one():
    assert _markdown_of(r"\u0430 и $\underline{x}$") == r"а и $\underline{x}$"


def test_an_answer_escaped_properly_is_read_exactly_as_before():
    body = r"$\\frac{a}{b} \\\\ \\textbf{x}$\nдалее \"цитата\""
    assert _markdown_of(body) == '$\\frac{a}{b} \\\\ \\textbf{x}$\nдалее "цитата"'
