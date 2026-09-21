"""A record rendered as a PDF — app/services/pdf.py.

The parser is pinned down exactly, because how a page is read is a decision
worth stating. The renderer is checked for producing a real document and, above
all, for never raising on the content of a record: a note is not worth losing
over a formula the drawing engine cannot read.
"""

from app.services import pdf


def _kinds(markdown: str) -> list[str]:
    return [b.kind for b in pdf.blocks(markdown)]


# ── blocks: the structure of a page ──────────────────────────────────────────


def test_a_plain_line_is_text():
    assert _kinds("Граф — пара множеств") == ["text"]


def test_headings_keep_their_level():
    result = pdf.blocks("# Графы\n### Представление")
    assert [(b.kind, b.level, b.text) for b in result] == [
        ("heading", 1, "Графы"),
        ("heading", 3, "Представление"),
    ]


def test_six_hashes_is_the_deepest_heading():
    assert pdf.blocks("###### Глубоко")[0] == pdf.Block("heading", "Глубоко", 6)


def test_seven_hashes_is_not_a_heading():
    # CommonMark stops at six, and so does this: a run of hashes past that is
    # ordinary text, not a heading nobody can see.
    assert pdf.blocks("####### Глубоко")[0].kind == "text"


def test_bullets_are_recognised_in_three_notations():
    assert _kinds("- раз\n* два\n• три") == ["bullet", "bullet", "bullet"]


def test_a_bullet_keeps_only_its_content():
    assert pdf.blocks("-   Если $V = \\emptyset$")[0].text == "Если $V = \\emptyset$"


def test_a_line_that_is_only_a_formula_becomes_display_math():
    result = pdf.blocks(r"$\sum_{i=1}^{p} \rho(v_i) = 2 q$")
    assert result[0].kind == "math"
    assert result[0].text == r"\sum_{i=1}^{p} \rho(v_i) = 2 q"


def test_double_dollar_display_math():
    assert pdf.blocks("$$x^2$$")[0] == pdf.Block("math", "x^2")


def test_a_formula_inside_a_sentence_is_not_display_math():
    # It has to stay in the line, or the sentence falls apart around it.
    assert _kinds("Граф $G$ — пара множеств") == ["text"]


def test_a_drawing_note_is_kept_as_a_remark():
    # Photos are never stored, so the model's note about a diagram is all
    # that is left of it.
    result = pdf.blocks("[схема: изображен граф с петлей]")
    assert result[0] == pdf.Block("note", "схема: изображен граф с петлей")


def test_every_line_is_its_own_block():
    # A lecture note is written line by line. Joining consecutive lines into
    # flowing paragraphs produces sentences the author never wrote.
    markdown = "Основные понятия:\nГраф — пара множеств\nРебра соединяют вершины"
    assert _kinds(markdown) == ["text", "text", "text"]


def test_a_blank_line_becomes_one_gap():
    assert _kinds("первая\n\nвторая") == ["text", "gap", "text"]


def test_runs_of_blank_lines_collapse():
    assert _kinds("первая\n\n\n\n\nвторая") == ["text", "gap", "text"]


def test_leading_and_trailing_blank_lines_are_dropped():
    assert _kinds("\n\nтекст\n\n\n") == ["text"]


def test_an_empty_record_has_no_blocks():
    assert pdf.blocks("") == []
    assert pdf.blocks("   \n\n  ") == []


# ── split_inline: text and formulas in one line ──────────────────────────────


def test_a_line_without_formulas_is_one_run():
    assert pdf.split_inline("просто текст") == [("text", "просто текст")]


def test_a_formula_is_separated_from_its_text():
    assert pdf.split_inline("Граф $G$ — пара") == [
        ("text", "Граф "),
        ("math", "G"),
        ("text", " — пара"),
    ]


def test_several_formulas_in_one_line():
    parts = pdf.split_inline("$a$ и $b$ смежные")
    assert [kind for kind, _ in parts] == ["math", "text", "math", "text"]


def test_a_line_that_is_entirely_one_formula():
    assert pdf.split_inline("$x^2$") == [("math", "x^2")]


def test_an_escaped_dollar_is_not_a_formula():
    # A literal dollar sign must not open a formula and eat the rest.
    assert pdf.split_inline(r"стоит \$5 за штуку") == [
        ("text", r"стоит \$5 за штуку")
    ]


def test_an_unclosed_dollar_stays_text():
    assert pdf.split_inline("цена $5 рублей") == [("text", "цена $5 рублей")]


# ── markup: the text has to survive reportlab's mini-HTML ────────────────────


def test_angle_brackets_are_escaped():
    # "A < B" on a page would otherwise be read as a tag and swallow the line.
    assert pdf._markup("если a < b") == "если a &lt; b"


def test_ampersand_is_escaped():
    assert pdf._markup("b & c") == "b &amp; c"


def test_bold_survives_escaping():
    assert pdf._markup("**важно** и <тег>") == "<b>важно</b> и &lt;тег&gt;"


class _FakeFormulas:
    """Stands in for the real renderer so line assembly can be checked without
    drawing anything."""

    def __init__(self, renderable: bool = True):
        self.renderable = renderable
        self.asked: list[str] = []

    def inline(self, latex: str, size_pt: float) -> str | None:
        self.asked.append(latex)
        return f"<img:{latex}>" if self.renderable else None


def test_a_line_mixes_drawn_formulas_with_escaped_text():
    formulas = _FakeFormulas()
    result = pdf._line_markup("Если $a < b$, то c & d", formulas, 10.0)
    assert result == "Если <img:a < b>, то c &amp; d"
    assert formulas.asked == ["a < b"]


def test_an_unrenderable_formula_falls_back_to_its_source():
    # Worse to look at than a drawn formula, far better than a missing one.
    formulas = _FakeFormulas(renderable=False)
    result = pdf._line_markup(r"дано $\begin{matrix}1\end{matrix}$", formulas, 10.0)
    assert r"$\begin{matrix}1\end{matrix}$" in result


# ── render: a real document, and never a crash ───────────────────────────────


def test_render_produces_a_pdf():
    data = pdf.render("Графы", "Граф $G$ — пара множеств.")
    assert data.startswith(b"%PDF-")
    assert len(data) > 1000


def test_render_handles_a_whole_page_of_notes():
    markdown = (
        "Дискретная математика\n"
        "- Графы\n\n"
        "Граф $G$ - пара множеств $G = \\{V, E\\}$\n"
        "[схема: граф с петлей]\n\n"
        "# Теорема Эйлера\n"
        "$\\sum_{i=1}^{p} \\rho(v_i) = 2 q$\n"
    )
    assert pdf.render("Дискретная математика", markdown).startswith(b"%PDF-")


def test_render_survives_latex_mathtext_cannot_read():
    data = pdf.render("Матрицы", r"Дано $\begin{matrix} 1 & 2 \end{matrix}$ и всё.")
    assert data.startswith(b"%PDF-")


def test_render_survives_a_display_formula_it_cannot_read():
    data = pdf.render("Матрицы", r"$\begin{matrix} 1 & 2 \end{matrix}$")
    assert data.startswith(b"%PDF-")


def test_render_survives_markup_characters_on_the_page():
    data = pdf.render("Сравнения", "Если a < b и b & c, то <всё> хорошо.")
    assert data.startswith(b"%PDF-")


def test_render_survives_an_empty_record():
    assert pdf.render("Пусто", "").startswith(b"%PDF-")


def test_render_accepts_a_subtitle():
    assert pdf.render("Графы", "текст", subtitle="3 страницы · 21.09").startswith(
        b"%PDF-"
    )


def test_a_repeated_formula_is_drawn_once():
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        first = formulas.inline("x^2", 10.0)
        second = formulas.inline("x^2", 10.0)
        assert first == second
        assert formulas._count == 1


def test_warm_up_never_raises(monkeypatch):
    monkeypatch.setattr(pdf, "_formula_png", lambda *a, **k: 1 / 0)
    pdf.warm_up()  # must not propagate
