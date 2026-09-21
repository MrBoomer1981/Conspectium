"""The matrix against the graph beside it — app/services/graphcheck.py.

The point of the module is that it is deterministic, so the tests are written
as a table of shapes: which ones it must catch, and — the half that matters
more — which ones it must stay quiet about. A confident wrong "does not agree
with the graph" costs more than a check that said nothing.
"""

from app.services import graphcheck, mathcheck


def _record(spec: str, *rows: str, header: bool = True) -> str:
    body = "\n".join(rows)
    separator = "|" + "|".join("---" for _ in rows[0].split("|")[1:-1]) + "|\n"
    head, rest = (rows[0] + "\n", "\n".join(rows[1:]))
    return f"[граф: {spec}]\n\n" + (head + separator + rest if header else body)


def _severities(markdown: str) -> list[str]:
    return [issue.severity for issue in graphcheck.check(markdown)]


# ── adjacency: what it must catch ────────────────────────────────────────────


def test_an_edge_the_matrix_is_missing():
    found = graphcheck.check(
        _record(
            "1-2, 2-3, 3-4",
            "|   | 1 | 2 | 3 | 4 |",
            "| **1** | 0 | 1 | 0 | 0 |",
            "| **2** | 1 | 0 | 0 | 0 |",
            "| **3** | 0 | 0 | 0 | 1 |",
            "| **4** | 0 | 0 | 1 | 0 |",
        )
    )
    assert [i.severity for i in found] == ["critical"]
    assert "(2, 3)" in found[0].detail and "(3, 2)" in found[0].detail


def test_an_edge_the_matrix_invented():
    found = graphcheck.check(
        _record(
            "1-2, 2-3, 3-4",
            "|   | 1 | 2 | 3 | 4 |",
            "| **1** | 0 | 1 | 1 | 0 |",
            "| **2** | 1 | 0 | 1 | 0 |",
            "| **3** | 1 | 1 | 0 | 1 |",
            "| **4** | 0 | 0 | 1 | 0 |",
        )
    )
    assert [i.severity for i in found] == ["critical"]
    assert "на рисунке нет" in found[0].detail


def test_a_cell_that_could_not_be_read_is_filled_in_from_the_graph():
    # The whole reason the check exists: "в рукописи матрица плохо читается,
    # поэтому она восстановлена по рисунку графа".
    found = graphcheck.check(
        _record(
            "1-2, 2-3, 3-4",
            "|   | 1 | 2 | 3 | 4 |",
            "| **1** | 0 | - | 0 | 0 |",
            "| **2** | - | 0 | 1 | 0 |",
            "| **3** | 0 | 1 | 0 | 1 |",
            "| **4** | 0 | 0 | 1 | 0 |",
        )
    )
    assert [i.severity for i in found] == ["warning"]
    assert "(1, 2) — 1" in found[0].suggestion


def test_a_wall_of_disagreements_collapses_into_a_count():
    found = graphcheck.check(
        _record(
            "1-2, 2-3, 3-4",
            "|   | 1 | 2 | 3 | 4 |",
            "| **1** | 1 | 1 | 1 | 1 |",
            "| **2** | 1 | 1 | 1 | 1 |",
            "| **3** | 1 | 1 | 1 | 1 |",
            "| **4** | 1 | 1 | 1 | 1 |",
        )
    )
    assert [i.severity for i in found] == ["critical"]
    assert "расхождений:" in found[0].detail


# ── adjacency: what it must stay quiet about ─────────────────────────────────


def test_a_matrix_that_agrees_says_nothing():
    assert not graphcheck.check(
        _record(
            "1-2, 2-3, 3-1, 1-4",
            "|   | 1 | 2 | 3 | 4 |",
            "| **1** | 0 | 1 | 1 | 1 |",
            "| **2** | 1 | 0 | 1 | 0 |",
            "| **3** | 1 | 1 | 0 | 0 |",
            "| **4** | 1 | 0 | 0 | 0 |",
        )
    )


def test_a_loop_is_accepted_whichever_convention_the_page_used():
    # 1 and 2 on the diagonal are both written in practice. The check is on
    # whether the edge is there, never on the number in the cell.
    # Five edges on four vertices, so the table cannot be mistaken for an
    # incidence matrix and the check actually runs.
    for diagonal in ("1", "2"):
        assert not graphcheck.check(
            _record(
                "1-2, 2-3, 3-4, 1-1, 2-4",
                "|   | 1 | 2 | 3 | 4 |",
                f"| **1** | {diagonal} | 1 | 0 | 0 |",
                "| **2** | 1 | 0 | 1 | 1 |",
                "| **3** | 0 | 1 | 0 | 1 |",
                "| **4** | 0 | 1 | 1 | 0 |",
            )
        ), diagonal


def test_a_directed_graph_is_not_expected_to_be_symmetric():
    assert not graphcheck.check(
        _record(
            "1->2, 2->3",
            "|   | 1 | 2 | 3 |",
            "| **1** | 0 | 1 | 0 |",
            "| **2** | 0 | 0 | 1 |",
            "| **3** | 0 | 0 | 0 |",
        )
    )


def test_a_square_table_that_could_be_either_matrix_is_left_alone():
    # A cycle has as many edges as vertices; nothing on the page says whether
    # the table is adjacency or incidence.
    assert not graphcheck.check(
        _record(
            "1-2, 2-3, 3-1",
            "|   | 1 | 2 | 3 |",
            "| **1** | 1 | 0 | 1 |",
            "| **2** | 1 | 1 | 0 |",
            "| **3** | 0 | 1 | 1 |",
        )
    )


def test_labels_that_do_not_match_the_vertices_stop_the_check():
    assert not graphcheck.check(
        _record(
            "1-2, 2-3, 3-4",
            "|   | a | b | c | d |",
            "| **a** | 1 | 1 | 1 | 1 |",
            "| **b** | 1 | 1 | 1 | 1 |",
            "| **c** | 1 | 1 | 1 | 1 |",
            "| **d** | 1 | 1 | 1 | 1 |",
        )
    )


def test_a_bare_matrix_of_numbered_vertices_is_still_checked():
    # No labels, but numbered vertices have one defensible order.
    assert _severities(
        "[граф: 1-2, 2-3, 3-4]\n\n| 0 | 0 | 0 | 0 |\n| 0 | 0 | 0 | 0 |\n"
        "| 0 | 0 | 0 | 0 |\n| 0 | 0 | 0 | 0 |\n"
    ) == ["critical"]


def test_a_bare_matrix_of_named_vertices_is_not_guessed_at():
    assert not graphcheck.check(
        "[граф: a-b, b-c, c-d]\n\n| 0 | 0 | 0 | 0 |\n| 0 | 0 | 0 | 0 |\n"
        "| 0 | 0 | 0 | 0 |\n| 0 | 0 | 0 | 0 |\n"
    )


def test_a_table_is_claimed_by_the_graph_nearest_above_it():
    # Both graphs have the same vertices here, so the first would have plenty
    # to say about this table if it were allowed to reach past the second.
    # The table agrees with the second graph and nothing is reported.
    assert not graphcheck.check(
        "[граф: 1-2, 2-3, 3-4]\n\n"
        + _record(
            "1-2, 2-3, 3-4, 4-1, 1-3",
            "|   | 1 | 2 | 3 | 4 |",
            "| **1** | 0 | 1 | 1 | 1 |",
            "| **2** | 1 | 0 | 1 | 0 |",
            "| **3** | 1 | 1 | 0 | 1 |",
            "| **4** | 1 | 0 | 1 | 0 |",
        )
    )


def test_an_unreadable_cell_is_anything_that_is_not_a_number():
    for mark in ("-", "—", "?", " "):
        found = graphcheck.check(
            _record(
                "1-2, 2-3, 3-4",
                "|   | 1 | 2 | 3 | 4 |",
                f"| **1** | 0 | {mark} | 0 | 0 |",
                "| **2** | 1 | 0 | 1 | 0 |",
                "| **3** | 0 | 1 | 0 | 1 |",
                "| **4** | 0 | 0 | 1 | 0 |",
            )
        )
        assert [i.severity for i in found] == ["warning"], mark


def test_a_graph_with_no_table_says_nothing():
    assert not graphcheck.check("[граф: 1-2, 2-3]\n\nпросто текст")


def test_a_table_with_no_graph_says_nothing():
    assert not graphcheck.check("| 0 | 1 |\n| 1 | 0 |")


def test_an_empty_record_says_nothing():
    assert not graphcheck.check("")


def test_a_spec_that_does_not_read_as_a_graph_says_nothing():
    assert not graphcheck.check(
        "[граф: тут была нарисована схема]\n\n| 0 | 1 |\n| 1 | 0 |"
    )


# ── incidence: aggregates, because the column order is unknown ───────────────


def test_a_column_that_does_not_hold_two_ends_of_an_edge():
    found = graphcheck.check(
        _record(
            "1-2, 2-3, 3-4, 4-1, 1-3",
            "|   | 1 | 2 | 3 | 4 | 5 |",
            "| **1** | 1 | 0 | 0 | 1 | 1 |",
            "| **2** | 1 | 1 | 0 | 0 | 0 |",
            "| **3** | 1 | 1 | 1 | 0 | 1 |",
            "| **4** | 0 | 0 | 1 | 1 | 0 |",
        )
    )
    assert "critical" in [i.severity for i in found]
    assert "столбец 1" in found[0].detail


def test_row_sums_that_do_not_match_the_degrees():
    found = graphcheck.check(
        _record(
            "1-2, 2-3, 3-4, 4-1, 1-3",
            "|   | 1 | 2 | 3 | 4 | 5 |",
            "| **1** | 1 | 1 | 0 | 0 | 0 |",
            "| **2** | 1 | 0 | 1 | 0 | 0 |",
            "| **3** | 0 | 1 | 0 | 1 | 0 |",
            "| **4** | 0 | 0 | 1 | 1 | 0 |",
        )
    )
    assert "warning" in [i.severity for i in found]


def test_an_incidence_matrix_that_agrees_says_nothing():
    assert not graphcheck.check(
        _record(
            "1-2, 2-3, 3-4, 4-1, 1-3",
            "|   | 1 | 2 | 3 | 4 | 5 |",
            "| **1** | 1 | 0 | 0 | 1 | 1 |",
            "| **2** | 1 | 1 | 0 | 0 | 0 |",
            "| **3** | 0 | 1 | 1 | 0 | 1 |",
            "| **4** | 0 | 0 | 1 | 1 | 0 |",
        )
    )


def test_an_unreadable_cell_does_not_make_a_column_look_wrong():
    # A column with a hole in it cannot be summed, so it is passed over rather
    # than reported as holding one end of an edge.
    assert "critical" not in _severities(
        _record(
            "1-2, 2-3, 3-4, 4-1, 1-3",
            "|   | 1 | 2 | 3 | 4 | 5 |",
            "| **1** | - | 0 | 0 | 1 | 1 |",
            "| **2** | 1 | 1 | 0 | 0 | 0 |",
            "| **3** | 0 | 1 | 1 | 0 | 1 |",
            "| **4** | 0 | 0 | 1 | 1 | 0 |",
        )
    )


# ── the shape of a finding ───────────────────────────────────────────────────


def test_findings_are_mathcheck_issues():
    # They travel in the record's existing `issues` column, through the same
    # callout and the same critical -> needs_review downgrade. A type of their
    # own would have meant a second channel for the same kind of finding.
    found = graphcheck.check(
        _record(
            "1-2, 2-3, 3-4",
            "|   | 1 | 2 | 3 | 4 |",
            "| **1** | 0 | 0 | 0 | 0 |",
            "| **2** | 0 | 0 | 0 | 0 |",
            "| **3** | 0 | 0 | 0 | 0 |",
            "| **4** | 0 | 0 | 0 | 0 |",
        )
    )
    assert found and all(isinstance(i, mathcheck.Issue) for i in found)
    assert all(i.kind in ("matrix", "incidence") for i in found)
