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


def test_a_graph_note_is_drawn_instead_of_described():
    # The same square brackets, with the edges in them rather than a sentence
    # about them.
    assert pdf.blocks("[граф: 1-2, 2-3]")[0] == pdf.Block("graph", "1-2, 2-3")


def test_a_drawing_can_carry_a_caption():
    block = pdf.blocks("[граф Ориентированный: 1->2, 2->3]")[0]
    assert block.kind == "graph"
    assert block.caption == "Ориентированный"
    assert block.text == "1->2, 2->3"


def test_a_drawing_without_a_caption_has_an_empty_one():
    assert pdf.blocks("[граф: 1-2]")[0] == pdf.Block("graph", "1-2")


def test_a_graph_note_is_recognised_in_english_too():
    assert pdf.blocks("[graph: a-b]")[0].kind == "graph"


def test_the_seam_between_album_pages_becomes_a_rule():
    # _assemble joins the pages of an album with "---". Printed literally, it
    # was three hyphens sitting in the middle of the record.
    assert _kinds("страница\n\n---\n\nследующая") == [
        "text", "gap", "rule", "gap", "text",
    ]


def test_a_rule_is_recognised_in_three_notations():
    assert _kinds("---\n***\n___") == ["rule", "rule", "rule"]


def test_a_bullet_is_not_a_rule():
    assert _kinds("- пункт") == ["bullet"]


def test_a_markdown_table_becomes_one_block():
    result = pdf.blocks("| 1 | 2 |\n|---|---|\n| 0 | 1 |")
    assert len(result) == 1
    assert result[0].kind == "table"
    assert result[0].rows == [["1", "2"], ["0", "1"]]
    assert result[0].header is True


def test_a_table_without_a_separator_row_has_no_header():
    # A hand-copied matrix rarely comes with one, and its first row is data.
    result = pdf.blocks("| 0 | 1 |\n| 1 | 0 |")
    assert result[0].rows == [["0", "1"], ["1", "0"]]
    assert result[0].header is False


def test_a_single_piped_line_is_not_a_table():
    # "|V| \times |E|" is maths, and it opens and closes with a pipe.
    assert _kinds(r"|V| \times |E|") == ["text"]


def test_ragged_table_rows_are_padded():
    # reportlab raises on a ragged table, and a matrix with one cell missing
    # is still worth showing.
    result = pdf.blocks("| a | b | c |\n| 1 |")
    assert result[0].rows == [["a", "b", "c"], ["1", "", ""]]


def test_a_table_ends_where_the_pipes_stop():
    result = pdf.blocks("| a | b |\n| 1 | 2 |\nпосле таблицы")
    assert [b.kind for b in result] == ["table", "text"]
    assert result[-1].text == "после таблицы"


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


# ── parse_graph: a drawing read back as data ─────────────────────────────────


def test_an_undirected_graph_is_read():
    assert pdf.parse_graph("1-2, 2-3") == (
        ["1", "2", "3"], [("1", "2"), ("2", "3")], False,
    )


def test_one_arrow_makes_the_whole_graph_directed():
    assert pdf.parse_graph("1->2, 2-3")[2] is True


def test_a_loop_is_an_edge_from_a_vertex_to_itself():
    assert pdf.parse_graph("3-3") == (["3"], [("3", "3")], False)


def test_a_lone_vertex_is_not_a_loop():
    # "4" is a vertex drawn with nothing attached to it; a loop is "4-4".
    assert pdf.parse_graph("1-2, 4") == (["1", "2", "4"], [("1", "2")], False)


def test_vertices_keep_the_order_they_were_read_in():
    assert pdf.parse_graph("5-1, 3-5")[0] == ["5", "1", "3"]


def test_a_repeated_edge_is_kept_once():
    assert pdf.parse_graph("1-2, 1-2")[1] == [("1", "2")]


def test_an_empty_spec_is_not_a_graph():
    assert pdf.parse_graph("") is None
    assert pdf.parse_graph("  ,  ") is None


def test_prose_the_model_mislabelled_is_not_a_graph():
    # A vertex is called "1" or "v_1", never a sentence. Rather than draw
    # nonsense, refuse and let the line be printed.
    assert pdf.parse_graph("изображён граф с вершинами и петлёй") is None


def test_a_crowd_of_vertices_is_not_a_graph():
    # Past two dozen a circle of vertices is unreadable, and the text is more
    # likely to be something else entirely.
    assert pdf.parse_graph(", ".join(f"{i}-{i + 1}" for i in range(30))) is None


def test_numbered_vertices_go_round_the_circle_in_numeric_order():
    # Read off the page as 5,1,3,2,4 a cycle becomes a star of crossing
    # chords; in numeric order the same cycle is the rim of the circle.
    assert pdf._placement(["5", "1", "3", "2", "4"]) == ["1", "2", "3", "4", "5"]


def test_named_vertices_keep_the_order_they_were_read_in():
    assert pdf._placement(["b", "a", "c"]) == ["b", "a", "c"]


def test_names_mixed_with_numbers_are_left_alone():
    assert pdf._placement(["2", "a", "1"]) == ["2", "a", "1"]


def test_a_graph_is_drawn():
    assert pdf._graph("1-2, 2-3, 3-1, 3-3") is not None


def test_a_graph_of_a_single_vertex_is_drawn():
    assert pdf._graph("1") is not None


def test_a_spec_that_is_not_a_graph_is_not_drawn():
    assert pdf._graph("здесь была нарисована схема") is None


# ── for_mathtext: LaTeX the drawing engine will accept ───────────────────────


def test_limits_is_dropped():
    # The real failure: \sum\limits_{i=1}^p printed as its own source on a
    # deployed record, while \sum_{i=1}^p drew perfectly two pages later.
    assert pdf.for_mathtext(r"\sum\limits_{i=1}^p") == r"\sum_{i=1}^p"


def test_lim_and_limsup_survive():
    # The boundary has to be the end of the command name, not \b: "_" counts
    # as a word character, so \b would miss \limits_{i=1} entirely.
    assert pdf.for_mathtext(r"\lim_{x \to 0}") == r"\lim_{x \to 0}"
    assert pdf.for_mathtext(r"\limsup_n a_n") == r"\limsup_n a_n"


def test_displaystyle_is_dropped():
    assert pdf.for_mathtext(r"\displaystyle\sum_i x") == r"\sum_i x"


def test_mbox_becomes_the_synonym_mathtext_knows():
    assert pdf.for_mathtext(r"\mbox{дерево}") == r"\text{дерево}"


def test_thin_spaces_become_ordinary_ones():
    assert pdf.for_mathtext(r"a\,b\!c") == "a b c"


def test_latex_mathtext_already_understands_is_left_alone():
    assert pdf.for_mathtext(r"\rho(v_i) = 2q") == r"\rho(v_i) = 2q"


def test_the_spellings_mathtext_does_not_know_are_translated():
    # \le and \ge are what ruined a real record: every inequality on the page
    # printed as its own source while the formulas around them drew fine.
    assert pdf.for_mathtext(r"a_n \le b_n") == r"a_n \leq b_n"
    assert pdf.for_mathtext(r"b_1 \ge a_n") == r"b_1 \geq a_n"
    assert pdf.for_mathtext(r"p \implies q") == r"p \Rightarrow q"


def test_a_synonym_is_not_matched_inside_a_longer_command():
    # "\le" opens "\leq", "\left" and "\leftarrow"; the boundary is the end
    # of the command name, which is the same trap \limits fell into.
    for untouched in (r"\leq", r"\geq", r"\left[ x \right]", r"\leftarrow"):
        assert pdf.for_mathtext(untouched) == untouched


def test_every_translation_in_the_table_is_one_mathtext_draws():
    # A wrong replacement would be invisible: the formula would still fall back
    # to its source, exactly as it did before the table existed.
    import tempfile

    # Most are binary operators between two terms; the rest take arguments,
    # and a-\textrm-b is not LaTeX in the first place.
    samples = {
        "mbox": r"\mbox{тут}",
        "textrm": r"\textrm{тут}",
        "tfrac": r"\tfrac{a}{b}",
        "stackrel": r"\stackrel{t}{\to}",
        "overbrace": r"\overbrace{abc}",
        "underbrace": r"\underbrace{abc}",
    }

    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        for spelling in pdf._SYNONYMS:
            latex = samples.get(spelling, f"a \\{spelling} b")
            assert formulas.display(latex, 10.0) is not None, spelling


def test_a_formula_with_limits_is_drawn_rather_than_dumped_as_source():
    # Proves the shim is wired into the drawing path, not merely correct on
    # its own: without it this returns None and the source goes on the page.
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        assert formulas.display(r"\sum\limits_{i=1}^p \rho(v)_i = 2q", 10.0)


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


def test_render_draws_a_byline_under_the_title(monkeypatch):
    drawn: list[str] = []
    original = pdf.Paragraph
    monkeypatch.setattr(
        pdf,
        "Paragraph",
        lambda text, style, **kw: drawn.append((style.name, text))
        or original(text, style, **kw),
    )
    pdf.render("Дискретная математика", "текст", byline="Шиманская Г. С.")
    assert ("byline", "Шиманская Г. С.") in drawn


def test_a_record_with_no_byline_draws_none(monkeypatch):
    drawn: list[str] = []
    original = pdf.Paragraph
    monkeypatch.setattr(
        pdf,
        "Paragraph",
        lambda text, style, **kw: drawn.append(style.name) or original(text, style, **kw),
    )
    pdf.render("Дискретная математика", "текст")
    assert "byline" not in drawn


def test_a_byline_is_escaped():
    assert pdf.render("Т", "текст", byline="a < b").startswith(b"%PDF-")


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


def _sizes(monkeypatch) -> list[float]:
    """Records the point size every line of the record is set at."""
    seen: list[float] = []
    original = pdf._line_markup
    monkeypatch.setattr(
        pdf,
        "_line_markup",
        lambda text, formulas, size: seen.append(size) or original(text, formulas, size),
    )
    return seen


def test_a_heading_is_set_at_the_size_of_its_level(monkeypatch):
    # blocks() has always read the level; render() threw it away and set every
    # heading at one size, which made "#" and "###" the same thing on a page.
    sizes = _sizes(monkeypatch)
    pdf.render("Заголовок", "# Раз\n## Два\n### Три")
    assert sizes == [14.0, 12.5, 11.0]


def test_a_heading_deeper_than_three_is_set_like_the_third(monkeypatch):
    sizes = _sizes(monkeypatch)
    pdf.render("Заголовок", "###### Глубоко")
    assert sizes == [11.0]


def test_render_draws_a_callout():
    data = pdf.render(
        "Графы",
        "текст записи",
        callouts=[pdf.Callout("Нужна проверка", ["прогоны разошлись"], "warning")],
    )
    assert data.startswith(b"%PDF-")


def test_render_draws_every_callout_it_is_given(monkeypatch):
    # A PDF comes out either way; only the call proves the boxes were built.
    seen: list[str] = []
    original = pdf._callout
    monkeypatch.setattr(
        pdf,
        "_callout",
        lambda box, formulas, styles: seen.append(box.title)
        or original(box, formulas, styles),
    )
    pdf.render(
        "Графы",
        "текст",
        callouts=[pdf.Callout("Раз", ["a"]), pdf.Callout("Два", ["b"])],
    )
    assert seen == ["Раз", "Два"]


def _panel(box: pdf.Callout) -> list[str]:
    """The reportlab markup that actually ends up inside a callout panel.

    _cellvalues is reportlab's own record of what a table was built from.
    Reaching into it is the only way to see that the title and the lines got
    as far as the page: a test that checks a PDF came out passes just as
    happily with the panel empty.
    """
    import tempfile

    pdf._register_fonts()
    with tempfile.TemporaryDirectory() as directory:
        table = pdf._callout(box, pdf._Formulas(directory), pdf._styles())
    return [flowable.text for flowable in table._cellvalues[0][0]]


def test_a_panel_holds_its_title_and_every_line():
    panel = _panel(pdf.Callout("Спорные места", ["раз", "два"]))
    assert len(panel) == 3
    assert "Спорные места" in panel[0]
    assert panel[1:] == ["раз", "два"]


def test_a_warning_panel_is_titled_in_the_warning_colour():
    assert pdf._CALLOUT_TONES["warning"][1] in _panel(
        pdf.Callout("Нужна проверка", [], "warning")
    )[0]
    assert pdf._CALLOUT_TONES["info"][1] in _panel(pdf.Callout("Спорные", []))[0]


def test_an_unknown_tone_is_titled_like_an_ordinary_one():
    assert pdf._CALLOUT_TONES["info"][1] in _panel(
        pdf.Callout("Раз", [], "лиловый")
    )[0]


def test_a_panel_escapes_its_title_and_its_lines():
    panel = _panel(pdf.Callout("a < b", ["c & d"]))
    assert "a &lt; b" in panel[0]
    assert panel[1] == "c &amp; d"


def test_a_formula_in_a_panel_line_is_drawn():
    assert "<img" in _panel(pdf.Callout("Раз", ["дано $x^2$"]))[1]


def test_a_callout_with_an_unknown_tone_still_draws():
    # The tone comes from the caller; a typo there must not sink a record.
    data = pdf.render("Графы", "текст", callouts=[pdf.Callout("Раз", ["a"], "лиловый")])
    assert data.startswith(b"%PDF-")


def test_a_callout_draws_the_formulas_in_its_lines():
    data = pdf.render("Графы", "текст", callouts=[pdf.Callout("Раз", ["дано $x^2$"])])
    assert data.startswith(b"%PDF-")


def test_a_callout_survives_markup_characters():
    data = pdf.render("Графы", "текст", callouts=[pdf.Callout("a < b", ["c & d"])])
    assert data.startswith(b"%PDF-")


def test_a_callout_with_no_lines_still_draws():
    assert pdf.render("Графы", "текст", callouts=[pdf.Callout("Раз", [])]).startswith(
        b"%PDF-"
    )


def test_render_asks_for_a_drawing_when_the_record_has_a_graph(monkeypatch):
    # Checking only that a PDF comes out would pass with the drawing dropped
    # on the floor: an unhandled block kind prints as an empty line.
    asked: list[str] = []
    monkeypatch.setattr(
        pdf, "_graph", lambda spec, width=None: asked.append(spec) or None
    )
    pdf.render("Графы", "[граф: 1-2, 2-3]")
    assert asked == ["1-2, 2-3"]


def test_render_builds_a_table_for_a_matrix(monkeypatch):
    seen: list[list[list[str]]] = []
    original = pdf._table
    monkeypatch.setattr(
        pdf,
        "_table",
        lambda rows, header, formulas, styles: seen.append(rows)
        or original(rows, header, formulas, styles),
    )
    pdf.render("Матрица", "| 1 | 2 |\n|---|---|\n| 0 | 1 |")
    assert seen == [[["1", "2"], ["0", "1"]]]


def test_render_draws_a_line_at_the_seam_between_pages(monkeypatch):
    drawn: list[dict] = []
    original = pdf.HRFlowable
    monkeypatch.setattr(
        pdf, "HRFlowable", lambda **kw: drawn.append(kw) or original(**kw)
    )
    pdf.render("Альбом", "первая\n\n---\n\nвторая")
    # Two rules: the full-width one under the title, then the short one at the
    # seam. Their widths are how they are told apart on the page.
    assert [rule["width"] for rule in drawn] == ["100%", "35%"]


def test_render_survives_a_graph_it_cannot_read():
    data = pdf.render("Графы", "[граф: здесь нарисована какая то схема]")
    assert data.startswith(b"%PDF-")


def test_render_draws_a_record_with_a_graph_and_a_matrix():
    markdown = (
        "# Представление графов\n"
        "[граф: 1-2, 2-3, 3-4, 4-5, 5-1]\n\n"
        "| $a_{ij}$ | 1 | 2 |\n|---|---|---|\n| 1 | 0 | 1 |\n| 2 | 1 | 0 |\n"
    )
    assert pdf.render("Графы", markdown).startswith(b"%PDF-")


def test_render_survives_a_table_too_wide_for_the_page():
    row = "|" + "|".join(str(i) for i in range(12)) + "|"
    assert pdf.render("Матрица", f"{row}\n{row}").startswith(b"%PDF-")


# ── _column_widths: a table has to fit the page ──────────────────────────────


def test_a_column_is_measured_from_its_content():
    narrow = pdf._column_widths([["0", "1"], ["1", "0"]])
    wide = pdf._column_widths([["0", "довольно длинный заголовок"], ["1", "0"]])
    assert wide[1] > narrow[1]


def test_a_matrix_of_digits_gets_narrow_columns():
    # The whole point: reportlab left alone would spread five columns of "0"
    # and "1" across the entire page.
    widths = pdf._column_widths([["0", "1", "0", "1", "0"]] * 5)
    assert sum(widths) < pdf._TEXT_WIDTH_PT / 2


def test_a_table_too_wide_for_the_page_is_squeezed_to_fit():
    # reportlab does not complain about a table wider than its frame — it
    # simply runs off the edge of the paper, so nothing downstream catches
    # this but the arithmetic here.
    rows = [[f"заголовок {i}" for i in range(12)]] * 2
    assert sum(pdf._column_widths(rows)) <= pdf._TEXT_WIDTH_PT + 0.01


def test_an_empty_cell_still_gets_a_usable_column():
    assert min(pdf._column_widths([["", "1"], ["", "0"]])) >= pdf._MIN_COLUMN_PT


def test_a_table_is_built_with_the_measured_columns(monkeypatch):
    # The arithmetic being right proves nothing if the table is built without
    # it: reportlab would spread the columns evenly and nothing would fail.
    asked: list[list[list[str]]] = []
    monkeypatch.setattr(
        pdf, "_column_widths", lambda rows: asked.append(rows) or [30.0, 30.0]
    )
    pdf.render("Матрица", "| 0 | 1 |\n| 1 | 0 |")
    assert asked == [[["0", "1"], ["1", "0"]]]


def test_a_graph_is_drawn_in_the_placement_order(monkeypatch):
    # Same trap: _placement can be perfectly correct and never called.
    seen: list[list[str]] = []
    original = pdf._placement
    monkeypatch.setattr(
        pdf, "_placement", lambda vertices: seen.append(vertices) or original(vertices)
    )
    pdf._graph("5-1, 3-5")
    assert seen == [["5", "1", "3"]]


# ── the story: where a flowable actually lands ───────────────────────────────


def _story(monkeypatch, *args, **kwargs) -> list:
    """The flowables render() hands to reportlab, caught on the way in.

    Position is the whole point of a remark — that it sits beside the line it
    belongs to — and a finished PDF says nothing about where a flowable went.
    """
    captured: list = []

    class _Doc:
        def __init__(self, *a, **k):
            pass

        def build(self, story):
            captured.extend(story)

    monkeypatch.setattr(pdf, "SimpleDocTemplate", _Doc)
    pdf.render(*args, **kwargs)
    return captured


def _where(story: list, needle: str) -> int:
    for position, flowable in enumerate(story):
        if needle in getattr(flowable, "text", ""):
            return position
    return -1


def test_a_remark_is_set_directly_under_the_line_it_belongs_to(monkeypatch):
    story = _story(
        monkeypatch,
        "Графы",
        "первая строка\nвторая строка про щуку\nтретья строка",
        remarks=[pdf.Remark("щуку", "В рукописи", ["двоится"])],
    )
    anchor = _where(story, "щуку")

    assert anchor > 0
    assert type(story[anchor + 1]).__name__ == "Table"
    assert _where(story, "третья") > anchor + 1


def test_a_remark_that_anchors_nowhere_goes_to_the_end(monkeypatch):
    # Not dropped: it still says something about the record, and the end of
    # the document is where it is least in the way.
    story = _story(
        monkeypatch,
        "Графы",
        "первая строка\nвторая строка",
        remarks=[pdf.Remark("чего тут нет", "В рукописи", ["двоится"])],
    )
    assert type(story[-1]).__name__ == "Table"
    assert _where(story, "вторая") < len(story) - 1


def test_a_remark_with_an_empty_anchor_is_not_pinned_to_the_first_line(monkeypatch):
    # "" is a substring of everything; an empty anchor must not swallow the
    # first block it meets.
    story = _story(
        monkeypatch,
        "Графы",
        "первая строка\nвторая строка",
        remarks=[pdf.Remark("", "В рукописи", ["двоится"])],
    )
    assert type(story[-1]).__name__ == "Table"


def test_a_heading_repeating_the_title_is_dropped(monkeypatch):
    # The commonest shape a page takes: the record is called "Графы" and the
    # page is headed "Графы". Printing both says nothing twice.
    story = _story(monkeypatch, "Графы", "# Графы\nтекст записи")
    assert sum(1 for f in story if getattr(f, "text", "") == "Графы") == 1


def test_a_repeated_heading_is_matched_past_case_and_spaces(monkeypatch):
    story = _story(monkeypatch, "Графы", "#   графы  \nтекст записи")
    assert _where(story, "рафы") == 0


def test_a_heading_that_is_not_the_title_survives(monkeypatch):
    story = _story(monkeypatch, "Графы", "# Основные понятия\nтекст записи")
    assert _where(story, "Основные понятия") > 0


def test_adjacent_drawings_are_set_in_one_row(monkeypatch):
    rows: list[list[tuple[str, str]]] = []
    monkeypatch.setattr(
        pdf, "_figure_row", lambda figures, styles: rows.append(figures) or []
    )
    pdf.render("Графы", "[граф A: 1-2]\n[граф B: 1->2]\n[граф C: 1-2, 2-3]")
    assert rows == [[("A", "1-2"), ("B", "1->2"), ("C", "1-2, 2-3")]]


def test_a_fourth_drawing_starts_a_new_row(monkeypatch):
    rows: list[list] = []
    monkeypatch.setattr(
        pdf, "_figure_row", lambda figures, styles: rows.append(figures) or []
    )
    pdf.render("Графы", "\n".join(f"[граф: {i}-{i + 1}]" for i in range(4)))
    assert [len(row) for row in rows] == [3, 1]


def test_a_drawing_with_text_around_it_stays_on_its_own(monkeypatch):
    rows: list[list] = []
    monkeypatch.setattr(
        pdf, "_figure_row", lambda figures, styles: rows.append(figures) or []
    )
    pdf.render("Графы", "[граф: 1-2]\nтекст между ними\n[граф: 2-3]")
    assert [len(row) for row in rows] == [1, 1]


def test_one_drawing_in_a_row_is_drawn_at_its_natural_size():
    assert pdf._figure_width(1) == pdf._GRAPH_WIDTH_PT


def test_a_crowded_row_gives_way_to_the_page():
    # Three fit at full size; the arithmetic has to hold past that too, or a
    # row runs off the edge of the paper without reportlab complaining.
    assert pdf._figure_width(pdf._FIGURES_PER_ROW) == pdf._GRAPH_WIDTH_PT
    for count in (4, 6, 8):
        row = count * (pdf._figure_width(count) + pdf._FIGURE_GAP_PT)
        assert row <= pdf._TEXT_WIDTH_PT


def test_a_caption_is_set_under_its_drawing():
    row = pdf._figure_row([("Ориентированный", "1->2")], pdf._styles())
    cell = row[1]._cellvalues[0][0]
    assert cell[-1].text == "Ориентированный"


def test_a_drawing_that_cannot_be_read_still_leaves_a_row():
    row = pdf._figure_row([("", "тут была какая то схема")], pdf._styles())
    assert "граф:" in row[1]._cellvalues[0][0][0].text


def test_render_draws_a_hairline_under_the_title(monkeypatch):
    story = _story(monkeypatch, "Графы", "текст записи")
    assert type(story[1]).__name__ == "HRFlowable"


def test_a_top_level_heading_gets_a_hairline_and_a_deeper_one_does_not(monkeypatch):
    with_rule = _story(monkeypatch, "Т", "# Раздел\nтекст")
    without = _story(monkeypatch, "Т", "## Подраздел\nтекст")
    assert sum(1 for f in with_rule if type(f).__name__ == "HRFlowable") == 2
    assert sum(1 for f in without if type(f).__name__ == "HRFlowable") == 1


# ── the sweep: what a page of chemistry writes that mathtext will not take ───


def test_the_swept_synonyms_are_rewritten():
    # Found by putting ~120 constructs through the parser at once, rather than
    # one broken record at a time, which is how the first six were found.
    assert pdf.for_mathtext(r"\textrm{АТФ}") == r"\text{АТФ}"
    assert pdf.for_mathtext(r"\tfrac{a}{b}") == r"\frac{a}{b}"
    assert pdf.for_mathtext(r"\stackrel{t}{\to}") == r"\overset{t}{\to}"
    assert pdf.for_mathtext(r"\overbrace{abc}") == r"\overline{abc}"
    assert pdf.for_mathtext(r"\underbrace{abc}") == r"\underline{abc}"


def test_a_sized_delimiter_loses_its_size_and_keeps_its_bracket():
    # mathtext sizes its own delimiters; the modifier means nothing to it and
    # takes the whole formula down. Dropping it leaves the bracket standing.
    assert pdf.for_mathtext(r"\big( a \big)") == "( a )"
    assert pdf.for_mathtext(r"\Bigg[ a \Bigg]") == "[ a ]"
    assert pdf.for_mathtext(r"\bigl\{ a \bigr\}") == r"\{ a \}"


def test_the_big_family_does_not_eat_the_operators_that_start_the_same_way():
    # \bigcup, \bigcap, \bigoplus are real symbols mathtext knows. The command
    # boundary is what keeps \big off them — the same rule that keeps \le off
    # \leq, and the reason \bigl and \bigr have to be listed in their own
    # right rather than left to \big.
    for untouched in (
        r"\bigcup_{i} A_i",
        r"\bigcap_{i} A_i",
        r"\bigoplus V_i",
        r"\bigwedge p",
    ):
        assert pdf.for_mathtext(untouched) == untouched


def test_an_arrow_with_a_condition_over_it_keeps_the_condition():
    # Most of the reactions on a page of biology. mathtext has no
    # \xrightarrow and does have \overset, so the label survives instead of
    # the whole formula going out as its own source.
    assert pdf.for_mathtext(r"A \xrightarrow{t} B") == r"A \overset{t}{\to} B"
    assert (
        pdf.for_mathtext(r"A \xleftarrow{t} B") == r"A \overset{t}{\leftarrow} B"
    )


def test_the_condition_may_itself_be_a_command_with_an_argument():
    # \xrightarrow{\text{фермент}} is the ordinary way to write it.
    assert pdf.for_mathtext(r"A \xrightarrow{\text{фермент}} B") == (
        r"A \overset{\text{фермент}}{\to} B"
    )


def test_a_label_nested_deeper_than_one_level_is_left_alone():
    # It then goes out as its own source, which is what happens today. Better
    # than a half-rewritten formula that reads as something it is not.
    deep = r"A \xrightarrow{\text{при \frac{a}{b}}} B"
    assert pdf.for_mathtext(deep) == deep


def test_every_swept_rewrite_is_one_mathtext_actually_draws():
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        for latex in (
            r"\textrm{АТФ}",
            r"\tfrac{a}{b}",
            r"\stackrel{t}{\to}",
            r"\overbrace{a+b}",
            r"\underbrace{a+b}",
            r"\big( a + b \big)",
            r"6CO_2 \xrightarrow{\text{свет}} C_6H_{12}O_6",
        ):
            assert formulas.display(latex, 10.0) is not None, latex


# ── a formula that still cannot be drawn says so out loud ────────────────────


def test_a_refused_formula_is_logged_with_what_mathtext_said(caplog):
    """It was a debug line and LOG_LEVEL is INFO, so it never appeared: three
    rounds of "the PDF has broken symbols" were found by eye instead."""
    import logging
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        with caplog.at_level(logging.WARNING, logger="app.services.pdf"):
            assert formulas.display(r"\ce{H2O}", 10.0) is None

    line = next(r.getMessage() for r in caplog.records if "refused" in r.getMessage())
    assert r"\ce{H2O}" in line
    assert "Unknown symbol" in line  # mathtext names the command itself


def test_the_diagnosis_survives_the_blank_first_line(caplog):
    # mathtext's message opens with an empty line and a caret under the
    # source — the same shape of trap as str(TimeoutError()) being "".
    import logging
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        with caplog.at_level(logging.WARNING, logger="app.services.pdf"):
            formulas.display(r"\begin{cases} a \\ b \end{cases}", 10.0)

    line = next(r.getMessage() for r in caplog.records if "refused" in r.getMessage())
    assert not line.rstrip().endswith(":")  # a diagnosis follows the colon


def test_the_same_broken_formula_is_reported_once_per_document(caplog):
    # A macro the model cannot spell is usually on every page of a record.
    import logging
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        with caplog.at_level(logging.WARNING, logger="app.services.pdf"):
            for _ in range(5):
                formulas.display(r"\ce{H2O}", 10.0)
                formulas.inline(r"\ce{H2O}", 10.0)

    refusals = [r for r in caplog.records if "refused" in r.getMessage()]
    assert len(refusals) == 1


def test_two_different_broken_formulas_are_both_reported(caplog):
    import logging
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        with caplog.at_level(logging.WARNING, logger="app.services.pdf"):
            formulas.display(r"\ce{H2O}", 10.0)
            formulas.display(r"\ce{CO2}", 10.0)

    refusals = [r for r in caplog.records if "refused" in r.getMessage()]
    assert len(refusals) == 2
