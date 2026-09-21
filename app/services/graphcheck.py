"""Does the matrix on the page agree with the graph drawn beside it?

Deterministic: no model call, no lookup. The uncertainty a record carries is
concentrated on matrix pages — of six numeric divergences in one album, five
sat on the page with two hand-drawn matrices, every one of them a single
digit. Whether a cell is 0 or 1 is not a matter of opinion and not something
the internet knows: it is decided by the edges of the graph the author drew
next to it.

The parsing comes from `pdf.blocks` and `pdf.parse_graph` — the same two
functions the drawing goes through. The check and the picture then see one
structure by construction rather than by coincidence.

Findings come back as `mathcheck.Issue`, so they join the record's existing
`issues` column, its callout and its critical -> needs_review downgrade
instead of opening a second channel for the same kind of finding.
"""

from __future__ import annotations

from app.services import pdf
from app.services.mathcheck import Issue

# Past this, a wall of cell-by-cell findings says less than one count of them.
_MAX_CELL_ISSUES = 6


def check(markdown: str) -> list[Issue]:
    """Every matrix in the record compared against the graph it belongs to."""
    issues: list[Issue] = []
    parsed = pdf.blocks(markdown)
    for position, block in enumerate(parsed):
        if block.kind != "graph":
            continue
        graph = pdf.parse_graph(block.text)
        table = _table_after(parsed, position)
        if graph is None or table is None:
            continue
        issues.extend(_compare(graph, table))
    return issues


def _table_after(parsed: list[pdf.Block], start: int) -> pdf.Block | None:
    """The table this graph is about: the next one, unless another graph comes
    first and claims it."""
    for block in parsed[start + 1 :]:
        if block.kind == "graph":
            return None
        if block.kind == "table":
            return block
    return None


def _plain(cell: str) -> str:
    return cell.replace("*", "").strip()


def _value(cell: str) -> int | None:
    """A cell as a number, or None when it was not readable on the page.

    Anything that is not a number counts as unreadable, which covers every
    mark the model uses for a cell it could not make out — "-", "—", "?", or
    nothing at all.
    """
    try:
        return int(_plain(cell))
    except ValueError:
        return None


def _grid(table: pdf.Block) -> tuple[list[str], list[list[str]]] | None:
    """(row labels, cells), with the header row and the label column removed.

    A matrix copied off a page comes with its vertex numbers around it. An
    empty top-left corner is what says the first column holds labels and not
    data — a matrix of noughts and ones gives no other way to tell.
    """
    rows = [list(row) for row in table.rows]
    if not rows:
        return None

    labels: list[str] = []
    body = rows[1:] if table.header else rows
    if table.header and not _plain(rows[0][0]) and body:
        labels = [_plain(row[0]) for row in body]
        body = [row[1:] for row in body]

    if not body or not body[0] or any(len(row) != len(body[0]) for row in body):
        return None
    return labels, body


def _order(labels: list[str], vertices: list[str], size: int) -> list[str] | None:
    """Which vertex each row and column stands for, or None when that cannot
    be known. Guessing it wrong would report every cell as a contradiction."""
    if labels and set(labels) == set(vertices) and len(labels) == size:
        return labels
    # No labels: the only defensible reading is numeric order, and only when
    # every vertex is a number and there are exactly as many as there are rows.
    if not labels and len(vertices) == size and all(v.isdigit() for v in vertices):
        return sorted(vertices, key=int)
    return None


def _compare(
    graph: tuple[list[str], list[tuple[str, str]], bool], table: pdf.Block
) -> list[Issue]:
    vertices, edges, directed = graph
    grid = _grid(table)
    if grid is None:
        return []
    labels, body = grid
    rows, columns = len(body), len(body[0])

    # A cycle has as many edges as vertices, and then a square table reads as
    # either matrix with equal force. Nothing on the page settles it, so say
    # nothing: a confident wrong "does not agree with the graph" is worse than
    # a check that stayed quiet.
    if rows == columns == len(vertices) == len(edges):
        return []

    order = _order(labels, vertices, rows)
    if order is None:
        return []
    if rows == columns:
        return _adjacency(vertices, edges, directed, order, body)
    if rows == len(vertices) and columns == len(edges):
        return _incidence(vertices, edges, order, body)
    return []


def _adjacency(
    vertices: list[str],
    edges: list[tuple[str, str]],
    directed: bool,
    order: list[str],
    body: list[list[str]],
) -> list[Issue]:
    """Cell by cell, on presence rather than value.

    Whether a loop puts 1 or 2 on the diagonal is a matter of convention and
    both are written in practice; whether an edge is there at all is not.
    """
    linked = {(tail, head) for tail, head in edges}
    if not directed:
        linked |= {(head, tail) for tail, head in edges}

    contradictions: list[str] = []
    fillable: list[str] = []
    for i, row_vertex in enumerate(order):
        for j, column_vertex in enumerate(order):
            expected = (row_vertex, column_vertex) in linked
            read = _value(body[i][j])
            if read is None:
                if expected:
                    fillable.append(f"({row_vertex}, {column_vertex}) — 1")
                continue
            if bool(read) != expected:
                seen = "есть на рисунке" if expected else "на рисунке нет"
                contradictions.append(
                    f"({row_vertex}, {column_vertex}): ребро {seen}, "
                    f"в матрице {read}"
                )

    issues: list[Issue] = []
    if contradictions:
        issues.append(_disagreement(contradictions))
    if fillable:
        issues.append(
            Issue(
                kind="matrix",
                severity="warning",
                message="Матрица смежности местами не прочиталась",
                detail=f"нечитаемых ячеек: {len(fillable)}",
                suggestion="по графу там стоит: " + ", ".join(fillable[:_MAX_CELL_ISSUES]),
            )
        )
    return issues


def _disagreement(contradictions: list[str]) -> Issue:
    if len(contradictions) > _MAX_CELL_ISSUES:
        return Issue(
            kind="matrix",
            severity="critical",
            message="Матрица смежности не сходится с графом",
            detail=f"расхождений: {len(contradictions)}",
            suggestion="проверьте и матрицу, и рисунок — прочитано неверно одно из них",
        )
    return Issue(
        kind="matrix",
        severity="critical",
        message="Матрица смежности не сходится с графом",
        detail="; ".join(contradictions),
        suggestion="проверьте и матрицу, и рисунок",
    )


def _incidence(
    vertices: list[str],
    edges: list[tuple[str, str]],
    order: list[str],
    body: list[list[str]],
) -> list[Issue]:
    """Aggregates only. Nothing says which edge a column stands for, so a cell
    cannot be checked — but a column has to hold the two ends of one edge, and
    a row has to hold the degree of its vertex."""
    issues: list[Issue] = []

    wrong: list[str] = []
    for j in range(len(body[0])):
        column = [_value(row[j]) for row in body]
        if any(v is None for v in column):
            continue
        total = sum(column)
        if total != 2:
            wrong.append(f"столбец {j + 1}: {total}")
    if wrong:
        issues.append(
            Issue(
                kind="incidence",
                severity="critical",
                message="В матрице инцидентности столбец не описывает ребро",
                detail="; ".join(wrong[:_MAX_CELL_ISSUES]),
                suggestion="у ребра два конца, поэтому в каждом столбце сумма 2",
            )
        )

    degrees = sorted(
        sum((tail == v) + (head == v) for tail, head in edges) for v in order
    )
    sums = []
    for row in body:
        read = [_value(cell) for cell in row]
        if any(v is None for v in read):
            return issues
        sums.append(sum(read))
    if sorted(sums) != degrees:
        issues.append(
            Issue(
                kind="incidence",
                severity="warning",
                message="Суммы по строкам не совпадают со степенями вершин",
                detail=f"в матрице {sorted(sums)}, по графу {degrees}",
                suggestion="строка вершины содержит столько единиц, какова её степень",
            )
        )
    return issues
