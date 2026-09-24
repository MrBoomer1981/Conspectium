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


# ── a formula between lines of dollars ───────────────────────────────────────


def test_a_formula_between_lines_of_dollars_is_display_math():
    # How the composing stage writes one. Read line by line it went out as
    # "$$", the LaTeX, "$$" — seven times on one record.
    result = pdf.blocks("$$\n\\sum_{i=1}^p \\rho(v_i) = 2q\n$$")
    assert result == [pdf.Block("math", r"\sum_{i=1}^p \rho(v_i) = 2q")]


def test_each_line_between_the_dollars_is_a_formula_of_its_own():
    assert pdf.blocks("$$\na = b\nc = d\n$$") == [
        pdf.Block("math", "a = b"),
        pdf.Block("math", "c = d"),
    ]


def test_an_environment_between_the_dollars_stays_one_formula():
    result = pdf.blocks("$$\n\\begin{cases} a \\\\\nb \\end{cases}\n$$")
    assert [b.kind for b in result] == ["math"]
    assert r"\begin{cases}" in result[0].text and r"\end{cases}" in result[0].text


def test_a_formula_may_open_on_the_line_of_its_dollars():
    assert pdf.blocks("$$ a = b\n$$") == [pdf.Block("math", "a = b")]


def test_dollars_that_never_close_stay_text():
    # A blank line before the closing "$$" means it was never a block, and the
    # dollars must not swallow the rest of the record.
    assert _kinds("$$\nтекст\n\nдальше") == ["text", "text", "gap", "text"]


def test_the_text_around_a_display_block_is_untouched():
    assert _kinds("до\n$$\nx\n$$\nпосле") == ["text", "math", "text"]


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


# ── the environments mathtext refuses outright ───────────────────────────────


def test_no_file_carries_an_invalid_escape_sequence():
    """A docstring about LaTeX is where this bites: "\\begin" in a plain string
    is a backspace and a SyntaxWarning, and the deployed process printed one on
    every start. Python 3.12 warns; a later one will refuse to compile."""
    import pathlib
    import warnings

    found = []
    for path in sorted(pathlib.Path("app").rglob("*.py")):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", SyntaxWarning)
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            found += [f"{path}:{w.lineno}" for w in caught]

    assert found == []


def test_a_piecewise_definition_becomes_a_braced_stack():
    """`cases` is the one CLAUDE.md said would be missed: a piecewise
    definition is ordinary mathematics and it printed as its own source. It has
    no \begin at all, but \substack stacks rows at full size and
    \left...\right puts the brace around them."""
    out = pdf.for_mathtext(r"\begin{cases} x, & x > 0 \\ -x, & x \le 0 \end{cases}")

    assert out.startswith(r"\left\{\substack{")
    assert out.endswith(r"}\right.")
    assert r"\\" in out  # the rows are still rows


def test_every_matrix_environment_keeps_its_own_delimiters():
    for name, opening in (
        ("pmatrix", "("),
        ("bmatrix", "["),
        ("vmatrix", "|"),
    ):
        out = pdf.for_mathtext(
            rf"\begin{{{name}}} 1 & 2 \\ 3 & 4 \end{{{name}}}"
        )
        assert out.startswith(rf"\left{opening}\substack{{")


def test_a_column_separator_becomes_a_wide_space():
    out = pdf.for_mathtext(r"\begin{pmatrix} 1 & 2 \end{pmatrix}")

    assert r"1 \quad" in out


def test_an_alignment_marker_is_removed_rather_than_widened():
    # "&" in aligned marks where two lines line up, inside one expression. A
    # \quad there opens a gap the page does not have.
    out = pdf.for_mathtext(r"\begin{aligned} a &= 1 \\ b &= 2 \end{aligned}")

    assert out == r"\substack{a = 1 \\ b = 2}"


def test_the_column_spec_of_an_array_is_dropped():
    out = pdf.for_mathtext(r"\begin{array}{cc} 1 & 2 \end{array}")

    assert "cc" not in out
    assert out.startswith(r"\substack{")


def test_a_starred_environment_is_recognised():
    out = pdf.for_mathtext(r"\begin{align*} a &= 1 \end{align*}")

    assert out == r"\substack{a = 1}"


def test_an_environment_nobody_taught_it_is_left_alone():
    # Unchanged behaviour: the formula falls back to its own source, which is
    # what the log now says out loud.
    source = r"\begin{equation} a = 1 \end{equation}"

    assert pdf.for_mathtext(source) == source


def test_every_environment_in_the_table_is_one_mathtext_draws():
    """The same rule as the synonym table: a wrong rewrite would be invisible,
    because the formula would fall back to its source exactly as it does now."""
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        for name in pdf._ENVIRONMENT_DELIMITERS:
            latex = rf"\begin{{{name}}} 1 & 2 \\ 3 & 4 \end{{{name}}}"
            assert formulas.display(latex, 10.0) is not None, name


def test_the_formula_that_went_out_as_source_now_draws():
    """From the record of 2026-09-23, logged by the warning that says which
    command mathtext refused."""
    import tempfile

    latex = (
        r"\begin{cases} a_1 b_1 - a_2 b_2 = 1 \\ a_1 b_2 + a_2 b_1 = 0 "
        r"\end{cases} \quad z = (z_1, z_2) \text{ тогда } z^{-1} = "
        r"\left(\frac{z_1}{z_1^2 + z_2^2}, -\frac{z_2}{z_1^2 + z_2^2}\right)"
    )

    with tempfile.TemporaryDirectory() as directory:
        assert pdf._Formulas(directory).display(latex, 10.0) is not None


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


def test_a_double_dollar_formula_inside_a_line_leaves_no_dollar_behind():
    # "$$v = cR$$ — формула Ридберга": read as the single form, a stray dollar
    # was left at either end, on three records.
    assert pdf.split_inline("$$v = cR$$ — формула Ридберга") == [
        ("math", "v = cR"),
        ("text", " — формула Ридберга"),
    ]


def test_a_line_that_is_one_double_dollar_formula_is_still_display_math():
    assert pdf.blocks("$$ \\varphi(ab) = \\varphi(a) $$")[0].kind == "math"


def test_two_inline_formulas_side_by_side_are_both_read():
    assert [kind for kind, _ in pdf.split_inline("$a$$b$")] == ["math", "math"]


# ── markup: the text has to survive reportlab's mini-HTML ────────────────────


def test_angle_brackets_are_escaped():
    # "A < B" on a page would otherwise be read as a tag and swallow the line.
    assert pdf._markup("если a < b") == "если a &lt; b"


def test_ampersand_is_escaped():
    assert pdf._markup("b & c") == "b &amp; c"


def test_bold_survives_escaping():
    assert pdf._markup("**важно** и <тег>") == "<b>важно</b> и &lt;тег&gt;"


def test_struck_through_text_is_drawn_struck_through():
    # A word the author crossed out stays crossed out. Printed with its tildes
    # it read as noise, on six records of twelve.
    assert pdf._markup("с какой V ~~она~~ туда") == "с какой V <strike>она</strike> туда"


def test_an_unpaired_marker_is_printed_as_it_stands():
    assert pdf._markup("a ** b") == "a ** b"
    assert pdf._markup("**a** **b") == "<b>a</b> **b"


def test_crossed_spans_still_make_well_formed_markup():
    # Malformed markup is an exception inside reportlab, and a record is never
    # worth losing over its emphasis.
    markup = pdf._markup("**a ~~b** c~~")
    assert markup == "<b>a <strike>b</strike></b><strike> c</strike>"
    assert pdf.render("Т", "**a ~~b** c~~").startswith(b"%PDF-")


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


def test_bold_may_run_across_a_formula():
    # "**Регулярный граф степени $n$**" is one bold span with a formula in it;
    # paired run by run, it went out with its asterisks showing.
    result = pdf._line_markup("**степени $n$** - граф", _FakeFormulas(), 10.0)
    assert result == "<b>степени <img:n></b> - граф"


def test_a_space_after_a_formula_is_a_place_to_break():
    # reportlab will not break at a space that follows an image, and the word
    # after a long formula ran off the paper.
    result = pdf._line_markup("$x$ Ассоциативность", _FakeFormulas(), 10.0)
    assert result == "<img:x>​ Ассоциативность"


def test_a_formula_and_its_comma_are_never_parted():
    result = pdf._line_markup("$x$, то", _FakeFormulas(), 10.0)
    assert "​" not in result


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
    assert sizes == [pdf._HEADING_PT[1], pdf._HEADING_PT[2], pdf._HEADING_PT[3]]
    assert sizes[0] > sizes[1] > sizes[2] >= pdf._BODY_PT


def test_a_heading_deeper_than_three_is_set_like_the_third(monkeypatch):
    sizes = _sizes(monkeypatch)
    pdf.render("Заголовок", "# Раз\n###### Глубоко")
    assert sizes == [pdf._HEADING_PT[1], pdf._HEADING_PT[3]]


def test_levels_are_counted_from_the_top_one_the_record_uses(monkeypatch):
    # Records composed with "##" sections and "###" subsections looked a step
    # smaller than the ones written with "#": the reference has one scale.
    sizes = _sizes(monkeypatch)
    pdf.render("Заголовок", "## Раздел\n### Подраздел")
    assert sizes == [pdf._HEADING_PT[1], pdf._HEADING_PT[2]]


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


def _panel(box: pdf.Callout) -> list:
    """The flowables that actually end up inside a callout panel.

    _cellvalues is reportlab's own record of what a table was built from.
    Reaching into it is the only way to see that the title and the lines got
    as far as the page: a test that checks a PDF came out passes just as
    happily with the panel empty.
    """
    import tempfile

    pdf._register_fonts()
    with tempfile.TemporaryDirectory() as directory:
        table = pdf._callout(box, pdf._Formulas(directory), pdf._styles())
    return list(table._cellvalues[0][0])


def test_a_panel_holds_its_title_and_every_line():
    panel = _panel(pdf.Callout("Спорные места", ["раз", "два"]))
    assert len(panel) == 3
    # The label is set in capitals, the way the reference sets "ЗАМЕЧАНИЕ".
    assert panel[0].text == "СПОРНЫЕ МЕСТА"
    assert [line.text for line in panel[1:]] == ["раз", "два"]


def test_a_warning_panel_is_titled_in_the_warning_colour():
    assert _panel(pdf.Callout("Нужна проверка", [], "warning"))[0].color == (
        pdf._CALLOUT_TONES["warning"]
    )
    assert _panel(pdf.Callout("Спорные", []))[0].color == pdf._CALLOUT_TONES["info"]


def test_an_unknown_tone_is_titled_like_an_ordinary_one():
    assert _panel(pdf.Callout("Раз", [], "лиловый"))[0].color == (
        pdf._CALLOUT_TONES["info"]
    )


def test_a_panel_escapes_its_lines_and_draws_its_title_as_written():
    # The label is drawn on the canvas, not parsed as markup, so it needs no
    # escaping; the lines are paragraphs and do.
    panel = _panel(pdf.Callout("a < b", ["c & d"]))
    assert panel[0].text == "A < B"
    assert panel[1].text == "c &amp; d"


def test_a_label_is_drawn_with_its_letters_spaced(monkeypatch):
    # The reference's "ЗАМЕЧАНИЕ" is tracked; a paragraph cannot do that.
    spaced: list[float] = []
    from reportlab.pdfgen.textobject import PDFTextObject

    original = PDFTextObject.setCharSpace
    monkeypatch.setattr(
        PDFTextObject,
        "setCharSpace",
        lambda self, value: spaced.append(value) or original(self, value),
    )
    pdf.render("Т", "текст", callouts=[pdf.Callout("Нужна проверка", ["a"])])
    assert spaced == [pdf._LABEL_TRACKING]


def test_a_callout_and_a_remark_are_one_anatomy():
    # Two systems, a tinted panel and a grey note, became one: a rule down the
    # left, a label, the lines. Nothing behind either of them.
    import tempfile

    pdf._register_fonts()
    styles = pdf._styles()
    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        boxes = [
            pdf._callout(pdf.Callout("Нужна проверка", ["a"], "warning"), formulas, styles),
            pdf._remark(pdf.Remark("x", "В рукописи", ["b"]), formulas, styles),
        ]
    for box in boxes:
        assert [cmd[0] for cmd in box._linecmds] == ["LINEBEFORE"]
        assert box._bkgrndcmds == []


def test_a_formula_in_a_panel_line_is_drawn():
    assert "<img" in _panel(pdf.Callout("Раз", ["дано $x^2$"]))[1].text


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

        def build(self, story, **kwargs):
            captured.extend(story)

    monkeypatch.setattr(pdf, "SimpleDocTemplate", _Doc)
    pdf.render(*args, **kwargs)
    return captured


def _flat(story: list) -> list:
    """The story with every group opened: what is kept together is still in
    the order it will be set in."""
    out: list = []
    for flowable in story:
        if type(flowable).__name__ == "KeepTogether":
            out.extend(_flat(flowable._content))
        else:
            out.append(flowable)
    return out


def _where(story: list, needle: str) -> int:
    for position, flowable in enumerate(story):
        if needle in getattr(flowable, "text", ""):
            return position
    return -1


def _group_of(story: list, needle: str):
    """The KeepTogether that holds the paragraph containing `needle`."""
    for flowable in story:
        if type(flowable).__name__ == "KeepTogether" and _where(
            _flat(flowable._content), needle
        ) >= 0:
            return flowable
    return None


def test_a_remark_is_set_directly_under_the_line_it_belongs_to(monkeypatch):
    story = _story(
        monkeypatch,
        "Графы",
        "первая строка\nвторая строка про щуку\nтретья строка",
        remarks=[pdf.Remark("щуку", "В рукописи", ["двоится"])],
    )
    flat = [f for f in _flat(story) if type(f).__name__ != "Spacer"]
    anchor = _where(flat, "щуку")

    assert anchor > 0
    assert type(flat[anchor + 1]).__name__ == "Table"
    assert _where(flat, "третья") > anchor + 1


def test_a_remark_is_kept_on_the_page_of_its_line(monkeypatch):
    story = _story(
        monkeypatch,
        "Графы",
        "первая строка\nвторая строка про щуку",
        remarks=[pdf.Remark("щуку", "В рукописи", ["двоится"])],
    )
    group = _group_of(story, "щуку")

    assert group is not None
    assert type(group._content[-1]).__name__ == "Table"


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
    assert sum(1 for f in _flat(story) if getattr(f, "text", "") == "Графы") == 1


def test_a_repeated_heading_is_matched_past_case_and_spaces(monkeypatch):
    story = _story(monkeypatch, "Графы", "#   графы  \nтекст записи")
    assert _where(_flat(story), "рафы") == 0


def test_a_heading_that_is_not_the_title_survives(monkeypatch):
    story = _story(monkeypatch, "Графы", "# Основные понятия\nтекст записи")
    assert _where(_flat(story), "Основные понятия") > 0


def test_a_heading_is_set_in_one_group_with_what_it_heads(monkeypatch):
    # "Пример" at the foot of page three, its graph on page four, read as a
    # heading over nothing.
    story = _story(monkeypatch, "Т", "### Пример\nтекст примера\nдальше")
    group = _group_of(story, "Пример")

    assert group is not None
    assert _where(_flat(group._content), "текст примера") >= 0
    assert _where(_flat(group._content), "дальше") < 0


def test_headings_in_a_row_wait_together_for_the_text(monkeypatch):
    story = _story(monkeypatch, "Т", "# Раздел\n## Подраздел\nтекст")
    group = _group_of(story, "Раздел")

    assert group is not None
    assert _where(_flat(group._content), "Подраздел") >= 0
    assert _where(_flat(group._content), "текст") >= 0


def test_no_group_is_ever_nested_in_another(monkeypatch):
    """The failure this rule was written after: reportlab's keepWithNext put a
    heading and the next group in a KeepTogether, the inner one reported an
    effectively infinite height, and the heading stayed behind anyway."""
    story = _story(
        monkeypatch,
        "Т",
        "### Пример\nстрока про щуку\n\n## Таблица\n| 1 | 2 |\n| 3 | 4 |",
        remarks=[pdf.Remark("щуку", "В рукописи", ["двоится"])],
    )
    for flowable in story:
        if type(flowable).__name__ == "KeepTogether":
            assert all(
                type(inner).__name__ != "KeepTogether" for inner in flowable._content
            )


def test_a_table_is_kept_whole(monkeypatch):
    story = _story(monkeypatch, "Т", "текст\n\n| 1 | 2 |\n| 3 | 4 |")
    groups = [f for f in story if type(f).__name__ == "KeepTogether"]

    assert any(type(f).__name__ == "Table" for g in groups for f in g._content)


def test_a_graph_does_not_catch_a_remark_with_its_edge_list(monkeypatch):
    # An anchor "2" is in "1-2, 2-3", and a remark about a word was pinned to
    # a drawing. The spec is not text anyone reads.
    story = _story(
        monkeypatch,
        "Т",
        "[граф: 1-2, 2-3]\nтекст\nстрока 2 про вершины",
        remarks=[pdf.Remark("2", "В рукописи", ["двоится"])],
    )
    assert _group_of(story, "строка 2") is not None


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
    cell = row[0]._cellvalues[0][0]
    assert cell[-1].text == "Ориентированный"


def test_a_drawing_that_cannot_be_read_still_leaves_a_row():
    row = pdf._figure_row([("", "тут была какая то схема")], pdf._styles())
    assert "граф:" in row[0]._cellvalues[0][0][0].text


def test_render_draws_a_hairline_under_the_title(monkeypatch):
    story = _story(monkeypatch, "Графы", "текст записи")
    assert type(story[1]).__name__ == "HRFlowable"


def test_a_top_level_heading_gets_a_hairline_and_a_deeper_one_does_not(monkeypatch):
    story = _flat(_story(monkeypatch, "Т", "# Раздел\nтекст\n## Подраздел\nтекст"))
    rules = [f for f in story if type(f).__name__ == "HRFlowable"]
    # The title's and the section's; the subsection has none.
    assert len(rules) == 2
    assert type(story[_where(story, "Подраздел") + 1]).__name__ == "Paragraph"


def test_a_second_section_is_set_off_by_the_broader_rule(monkeypatch):
    # The reference puts a paler, thicker rule between two of its sections.
    story = _flat(_story(monkeypatch, "Т", "# Раз\nтекст\n# Два\nтекст"))
    rules = [f for f in story if type(f).__name__ == "HRFlowable"]
    broad = [rule for rule in rules if rule.lineWidth == 1.5]
    assert len(broad) == 1
    assert story.index(broad[0]) < _where(story, "Два")


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
            # mhchem is a language of its own, not a command, and it is what
            # is left of the set nothing can rescue now that the environments
            # go through \substack.
            formulas.display(r"\ce{H2O + NaCl}", 10.0)

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


# ── as_formula: the LaTeX a remark quotes ────────────────────────────────────


def test_a_fragment_that_is_all_latex_becomes_one_formula():
    # «\rho^-(v)» went out on a remark as its own source.
    assert pdf.as_formula(r"\rho^-(v)") == r"$\rho^-(v)$"
    assert pdf.as_formula("V_i, V_j") == "$V_i, V_j$"


def test_prose_keeps_every_word_and_marks_only_its_commands():
    assert pdf.as_formula(r"похожа на греческую \chi, либо \varphi") == (
        r"похожа на греческую $\chi$, либо $\varphi$"
    )


def test_a_fragment_with_nothing_latex_in_it_is_left_alone():
    for untouched in ("верш", "A =", "∂cv", "[неразборчиво], b_1 c_2", "$x$", ""):
        assert pdf.as_formula(untouched) == untouched


# ── the rhythm: space between two kinds of block ─────────────────────────────


def test_lines_of_one_paragraph_are_set_at_the_leading_alone():
    # A lecture note is written line by line; 4 pt under every one of them
    # made a page of them read as double-spaced.
    assert pdf._space_before("text", "text", False) == 0.0


def test_a_blank_line_opens_a_paragraph():
    assert pdf._space_before("text", "text", True) == pdf._PARAGRAPH_GAP


def test_a_run_of_display_formulas_is_set_close():
    # A chain of equalities is one thing on paper.
    assert pdf._space_before("math", "math", False) < pdf._space_before(
        "text", "math", False
    )


def test_a_heading_brings_its_own_space():
    assert pdf._space_before("text", "heading", True) == 0.0
    assert pdf._space_before("heading", "text", False) == 0.0


def test_the_first_thing_on_the_page_needs_no_space():
    assert pdf._space_before(None, "math", True) == 0.0


# ── drawings: cut to size, and set beside their matrix ───────────────────────


def test_a_graph_is_cut_to_what_is_drawn():
    # A square as wide as the layout circle left a third of a triangle's
    # picture empty under it.
    _, width, height = pdf._graph_png(
        ["1", "2", "3"], [("1", "2"), ("2", "3"), ("3", "1")], False
    )
    assert height < width * 0.95


def test_every_graph_is_drawn_at_one_scale():
    # Two vertices stand one above the other; cut to what is drawn, the
    # picture is narrow rather than stretched to the width of a hexagon.
    _, width, height = pdf._graph_png(["1", "2"], [("1", "2")], False)
    assert width < height
    assert width < pdf._GRAPH_WIDTH_PT / 3


def test_a_graph_is_shrunk_only_to_fit():
    _, width, _ = pdf._graph_png(
        [str(i) for i in range(1, 7)],
        [(str(i), str(i % 6 + 1)) for i in range(1, 7)],
        False,
        width_pt=60.0,
    )
    assert width <= 60.0


def _matrix(size: int = 3) -> str:
    head = "| |" + "|".join(f" {i} " for i in range(1, size + 1)) + "|"
    rule = "|---|" + "|".join("---" for _ in range(size)) + "|"
    rows = [
        f"| {r} |" + "|".join(" 0 " for _ in range(size)) + "|"
        for r in range(1, size + 1)
    ]
    return "\n".join([head, rule, *rows])


def _besides(monkeypatch) -> list:
    seen: list = []
    monkeypatch.setattr(
        pdf,
        "_beside",
        lambda graph, name, table, formulas, styles: seen.append(
            (graph.text if graph else None, name.text if name else None)
        )
        or [],
    )
    return seen


def test_a_graph_and_its_matrix_are_set_side_by_side(monkeypatch):
    seen = _besides(monkeypatch)
    pdf.render("Т", f"[граф: 1-2, 2-3]\n\n$A =$\n\n{_matrix()}")
    assert seen == [("1-2, 2-3", "A =")]


def test_a_matrix_name_is_set_beside_its_matrix(monkeypatch):
    seen = _besides(monkeypatch)
    pdf.render("Т", f"$B =$\n{_matrix()}")
    assert seen == [(None, "B =")]


def test_a_line_of_text_keeps_a_graph_and_a_table_apart(monkeypatch):
    # The layout never moves a word of the record to put two pictures together.
    seen = _besides(monkeypatch)
    pdf.render("Т", f"[граф: 1-2, 2-3]\nтекст между ними\n{_matrix()}")
    assert seen == []


def test_a_graph_and_a_matrix_too_wide_to_share_the_column_are_stacked():
    import tempfile

    wide = pdf.blocks("| " + " | ".join(f"столбец {i}" for i in range(9)) + " |\n"
                      "| " + " | ".join("0" for _ in range(9)) + " |")[0]
    graph = pdf.Block("graph", "1-2, 2-3")
    pdf._register_fonts()
    with tempfile.TemporaryDirectory() as directory:
        assert pdf._beside(graph, None, wide, pdf._Formulas(directory), pdf._styles()) is None


def test_a_record_with_a_graph_beside_its_matrix_renders():
    assert pdf.render("Т", f"[граф: 1-2, 2-3]\n$A =$\n{_matrix()}").startswith(b"%PDF-")


def _rules(rows: list[list[str]], header: bool) -> list[str]:
    import tempfile

    pdf._register_fonts()
    with tempfile.TemporaryDirectory() as directory:
        table = pdf._table(rows, header, pdf._Formulas(directory), pdf._styles())
    return [cmd[0] for cmd in table._linecmds]


def test_a_matrix_is_ruled_not_caged():
    # A grid round every cell made noughts and ones a wall of boxes; a matrix
    # is ruled under its column names and after its row names.
    rules = _rules([["", "1", "2"], ["1", "0", "1"], ["2", "1", "0"]], header=True)
    assert "GRID" not in rules
    assert "LINEBELOW" in rules and "LINEAFTER" in rules


def test_a_table_of_records_is_ruled_between_its_rows():
    rules = _rules(
        [["Вершина", "Степень"], ["первая вершина", "1"], ["вторая вершина", "2"]],
        header=True,
    )
    assert "GRID" not in rules
    assert "LINEAFTER" not in rules


# ── formulas: the serif, the baseline, the column ────────────────────────────


def test_formulas_are_set_in_computer_modern(monkeypatch):
    import matplotlib.figure

    seen: list = []
    original = matplotlib.figure.Figure.text

    def spy(self, *args, **kwargs):
        seen.append(kwargs.get("math_fontfamily"))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(matplotlib.figure.Figure, "text", spy)
    pdf._formula_png("x^2", 10.0)
    # KaTeX in the reference draws Computer Modern.
    assert seen == ["cm"]


def test_a_deep_formula_sits_lower_on_the_line():
    # A fixed fraction of the height lifted a subscript off the line and sank
    # a fraction through it; the depth is measured instead.
    assert pdf._formula_png(r"\frac{a}{b}", 10.0)[3] > pdf._formula_png("x", 10.0)[3]


def test_an_inline_formula_is_lowered_by_its_own_depth():
    import tempfile

    depth = pdf._formula_png("x_i", 10.0)[3]
    with tempfile.TemporaryDirectory() as directory:
        tag = pdf._Formulas(directory).inline("x_i", 10.0)
    assert f'valign="-{depth:.2f}"' in tag


def test_a_formula_wider_than_the_column_is_shrunk_to_fit():
    # At its own size a long chain of equalities ran off the paper.
    import re
    import tempfile

    long = " + ".join(f"a_{{{i}}} b_{{{i}}} c_{{{i}}}" for i in range(40))
    with tempfile.TemporaryDirectory() as directory:
        formulas = pdf._Formulas(directory)
        shown = formulas.display(long, pdf._DISPLAY_PT)
        tag = formulas.inline(long, pdf._BODY_PT)
    assert shown.drawWidth <= pdf._TEXT_WIDTH_PT + 0.01
    assert float(re.search(r'width="([\d.]+)"', tag).group(1)) <= pdf._INLINE_MAX_PT + 0.01


# ── the page's furniture ─────────────────────────────────────────────────────


class _Canvas:
    """Records what the furniture writes and ignores how it writes it."""

    def __init__(self):
        self.written: list[str] = []

    def drawString(self, x, y, text):  # noqa: N802 — reportlab's name
        self.written.append(text)

    def drawCentredString(self, x, y, text):  # noqa: N802 — reportlab's name
        self.written.append(text)

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def test_every_page_of_a_long_record_is_numbered_out_of_the_whole(monkeypatch):
    seen: list[tuple[int, int]] = []
    monkeypatch.setattr(
        pdf,
        "_draw_furniture",
        lambda canvas, number, total, title: seen.append((number, total)),
    )
    pdf.render("Графы", "\n".join(f"строка {i}" for i in range(200)))

    total = len(seen)
    assert total >= 2
    assert seen == [(number, total) for number in range(1, total + 1)]


def test_a_one_page_record_carries_no_furniture():
    canvas = _Canvas()
    pdf._draw_furniture(canvas, 1, 1, "Графы")
    assert canvas.written == []


def test_the_running_title_starts_on_the_second_page():
    first, later = _Canvas(), _Canvas()
    pdf._draw_furniture(first, 1, 3, "Графы")
    pdf._draw_furniture(later, 2, 3, "Графы")

    # "2 / 3", not "с. 2": inside a record "с. 2" is a photographed page.
    assert first.written == ["1 / 3"]
    assert later.written == ["Графы", "2 / 3"]


def test_a_long_running_title_is_cut_to_the_column():
    cut = pdf._fit("очень длинное название " * 20, 100.0, pdf._FURNITURE_PT)

    assert cut.endswith("…")
    assert pdf.pdfmetrics.stringWidth(cut, pdf._TEXT_FONT, pdf._FURNITURE_PT) <= 100.0


# ── the reference's style: Lato, and what Lato cannot draw ───────────────────


def test_the_text_is_set_in_the_bundled_lato():
    # Lato 2, with Cyrillic, from the repo: the Lato Google serves has none.
    import os

    styles = pdf._styles()
    assert styles["body"].fontName == "Lato"
    assert styles["title"].fontName == "Lato-Black"
    assert os.path.exists(os.path.join(pdf._FONT_DIR, "Lato-Regular.ttf"))
    assert os.path.exists(os.path.join(pdf._FONT_DIR, "OFL.txt"))


def test_a_glyph_lato_lacks_is_set_in_dejavu():
    # reportlab has no fallback of its own and draws an empty box instead.
    assert pdf._markup("► Так как") == '<font face="DejaVu">►</font> Так как'
    assert pdf._markup("∀ε ∈ ℝ") == (
        '<font face="DejaVu">∀</font>ε <font face="DejaVu">∈</font> '
        '<font face="DejaVu">ℝ</font>'
    )


def test_text_lato_can_draw_is_left_as_it_is():
    assert pdf._markup("Граф — пара «множеств»…") == "Граф — пара «множеств»…"


def test_a_line_break_the_composer_wrote_is_a_line_break():
    # <br> in a table cell went out as the tag itself, three times a cell.
    assert pdf._markup("a<br>b<br/>c<BR />d") == "a<br/>b<br/>c<br/>d"


def test_a_header_with_nothing_in_it_is_not_a_header():
    result = pdf.blocks("| | |\n|---|---|\n| a | b |\n| c | d |")[0]
    assert result.rows == [["a", "b"], ["c", "d"]]
    assert result.header is False


def test_a_table_made_for_layout_is_set_without_rules():
    # Record 42's two columns of algebra, ruled as a table, came out as a
    # grid of small type.
    rows = [
        ["$a, b, c \\in \\mathbb{C}$<br>$a = (a_1, a_2)$", "$a(b + c) = ab + ac$"],
    ]
    assert pdf._for_layout(rows)
    assert _rules(rows, header=False) == []


def test_a_matrix_is_not_mistaken_for_layout():
    assert not pdf._for_layout([["", "1", "2"], ["1", "0", "1"]])


def test_a_numbered_line_is_a_list_item_with_its_own_number():
    result = pdf.blocks("1) абелева группа\n2. законы дистрибутивности")
    assert [(b.kind, b.marker, b.text) for b in result] == [
        ("bullet", "1)", "абелева группа"),
        ("bullet", "2.", "законы дистрибутивности"),
    ]


def test_a_number_inside_a_sentence_does_not_open_a_list():
    assert pdf.blocks("12 рёбер и 5 вершин")[0].kind == "text"


def test_a_remark_is_set_in_the_grey_of_the_reference():
    styles = pdf._styles()
    assert styles["remark_body"].textColor == pdf._MUTED == "#6b7480"
    assert styles["remark_body"].fontSize == styles["body"].fontSize


def test_a_record_in_the_new_style_renders_whole():
    markdown = (
        "## Раздел\n\n"
        "**Лемма.** Для любых $a, b \\in \\mathbb{R}$ ► существует $c$.\n\n"
        "1) $\\langle \\mathbb{C}, + \\rangle \\text{ абелева группа}$\n"
        "| | |\n|---|---|\n| $a$<br>$b$ | $a(b+c) = ab + ac$ |\n\n"
        "## Второй раздел\n~~зачёркнуто~~ и дальше"
    )
    data = pdf.render(
        "Т",
        markdown,
        subtitle="24.09.2026 · 1 страница",
        callouts=[pdf.Callout("Нужна проверка", ["строка"], "warning")],
        remarks=[pdf.Remark("Лемма", "В рукописи, с. 1", ["«$x$» — двоится"])],
    )
    assert data.startswith(b"%PDF-")


# ── main formulas: framed, larger, numbered ──────────────────────────────────


def test_what_a_box_frames_is_found_with_its_braces_matched():
    assert pdf.boxed_contents(r"\boxed{\frac{a}{b}} + \boxed{c}") == [r"\frac{a}{b}", "c"]
    assert pdf.boxed_contents(r"\boxed{a") == []  # unclosed: not a box


def test_a_box_is_taken_off_for_mathtext_and_remembered():
    assert pdf.unbox(r"z = \boxed{|z|(\cos\varphi)}") == (r"z = |z|(\cos\varphi)", True)
    assert pdf.unbox("x^2") == ("x^2", False)
    assert "boxed" not in pdf.for_mathtext(r"\boxed{x^2}")


def test_a_framed_formula_is_a_main_one():
    # Recognition writes the author's frame as \boxed; the composer marks a
    # section's result the same way.
    block = pdf.blocks(r"$$\boxed{e^{i\varphi} = \cos\varphi + i\sin\varphi}$$")[0]
    assert block == pdf.Block("math", r"e^{i\varphi} = \cos\varphi + i\sin\varphi", main=True)
    assert pdf.blocks(r"$\boxed{i^2 = -1}$")[0].main is True


def test_a_ruled_array_is_the_authors_frame_too():
    # Record 43 drew the frame as an array with \hline, and went out as source.
    latex = r"z = x \quad \begin{array}{|l|} \hline (0, 1) = i \\ (0, -1) = -i \\ \hline \end{array}"
    block = pdf.blocks(f"$${latex}$$")[0]
    assert block.main is True
    assert r"\hline" not in pdf.for_mathtext(block.text)


def test_the_formula_record_43_printed_as_source_now_draws():
    import tempfile

    latex = (
        r"z = (z_1, z_2) = z_1 + i z_2 \text{ , где } i^2 = -1 \quad "
        r"\begin{array}{|l|} \hline (0, 1) = i \\ (0, -1) = -i \\ \hline \end{array}"
    )
    with tempfile.TemporaryDirectory() as directory:
        assert pdf._Formulas(directory).display(latex, 12.0) is not None


def test_an_ordinary_formula_is_not_a_main_one():
    assert pdf.blocks("$$a = b$$")[0].main is False


def test_framed_text_is_its_own_block():
    assert pdf.blocks("[рамка: Алгебраическая форма]")[0] == pdf.Block(
        "framed", "Алгебраическая форма"
    )
    assert pdf.blocks("[в рамке: $(0, 1) = i$]")[0].kind == "framed"


def test_a_frame_round_several_lines_is_one_block():
    # Read line by line it printed "[в рамке:", the formulas, and a lone "]".
    result = pdf.blocks("[в рамке:\n$(0, 1) = i$\n$(0, -1) = -i$\n]\nпосле")
    assert [b.kind for b in result] == ["framed", "text"]
    assert result[0].text == "$(0, 1) = i$\n$(0, -1) = -i$"


def test_a_frame_never_closed_stays_text():
    assert _kinds("[в рамке:\nстрока\n\nдальше")[0] == "text"


def _numbers_in(story: list) -> list:
    return [f.main_number for f in _flat(story) if hasattr(f, "main_number")]


def test_main_formulas_are_numbered_in_order_through_the_record(monkeypatch):
    story = _story(
        monkeypatch,
        "Т",
        "## Раз\n$$\\boxed{a = 1}$$\nтекст\n## Два\n$$\\boxed{b = 2}$$\n$$c = 3$$",
    )
    assert _numbers_in(story) == [1, 2]


def test_a_frame_round_a_formula_is_numbered_and_one_round_words_is_not(monkeypatch):
    story = _story(
        monkeypatch, "Т", "[рамка: Алгебраическая форма]\n[рамка: $(0, 1) = i$]"
    )
    assert _numbers_in(story) == [None, 1]


def test_a_main_formula_is_set_apart_more_than_a_step():
    assert pdf._space_before("math", "main", False) > pdf._space_before(
        "math", "math", False
    )


def test_a_main_formula_is_drawn_larger_than_an_ordinary_one(monkeypatch):
    sizes: list[float] = []
    original = pdf._formula_png
    monkeypatch.setattr(
        pdf, "_formula_png", lambda latex, size: sizes.append(size) or original(latex, size)
    )
    pdf.render("Т", "$$a = 1$$\n\n$$\\boxed{b = 2}$$")
    assert sizes[-1] > sizes[0]


def test_a_record_with_frames_of_every_kind_renders():
    markdown = (
        "## Раздел\n$$\\boxed{\\frac{a + ib}{c + id}}$$\n"
        "[рамка: Алгебраическая форма]\n"
        "[в рамке:\n$(0, 1) = i$\n$(0, -1) = -i$\n]\n"
        "$$z = x \\quad \\begin{array}{|l|} \\hline a \\\\ b \\\\ \\hline \\end{array}$$\n"
    )
    assert pdf.render("Т", markdown).startswith(b"%PDF-")
