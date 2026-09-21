"""Все строки, которые видит пользователь."""

from datetime import date, datetime

START = (
    "Привет! Пришли фотографию конспекта — верну структурированную запись.\n\n"
    "Записи накапливаются: со временем из них соберётся твой личный корпус.\n\n"
    "Что ещё умею — /help"
)

PROCESSING = "Обрабатываю..."

NO_TEXT_FOUND = "Не нашёл на странице текста. Попробуй снять крупнее и ровнее."

ERROR_GENERIC = "Не смог обработать фото. Попробуй ещё раз чуть позже."

# Anything the bot has no handler for — app/bot/handlers.py handle_unsupported.
UNSUPPORTED = (
    "Пока умею только одно: фотографию страницы конспекта. "
    "Пришли снимок — верну структурированную запись."
)

# Spend limits — app/services/limits.py, step 4.
AI_DISABLED = "Распознавание сейчас выключено. Загляни позже."

LIMIT_COST = (
    "На сегодня обработка недоступна: дневной бюджет распознавания исчерпан. "
    "Вернись завтра."
)

LIMIT_PAGES = "На сегодня лимит страниц исчерпан. Вернись завтра — счётчик обнулится."

REJECTED_QUALITY = (
    "Прогоны распознавания сильно разошлись — фото нечёткое или снято "
    "издалека. Переснимите одну страницу крупным планом."
)

NEEDS_REVIEW = "Прогоны распознавания местами разошлись — перепроверьте текст."

DIVERGENCES_HEADER = "Числа, прочитанные по-разному в разных прогонах:"

UNCERTAIN_HEADER = "Спорные места — символ читается двояко:"

# The same four flags as headings of a box inside the PDF. Short, because a
# box has its own title line, where the message needs a whole sentence.
CALLOUT_REVIEW = "Нужна проверка"
CALLOUT_MATH = "Проверка вычислений"
CALLOUT_DIVERGENCES = "Числа прочитаны по-разному"
CALLOUT_UNCERTAIN = "Спорные места"


def remark_label(page: int | None = None) -> str:
    """The heading of a remark set beside a line of the record."""
    return "В рукописи" if page is None else f"В рукописи, с. {page}"


def uncertain_remark(text: str, why: str, alternatives: list[str]) -> list[str]:
    """One spot that reads two ways, as the lines of a remark beside it.

    As a list at the top of the document this said what was doubtful but not
    where, and by the time a reader reached the text they had forgotten it.
    """
    lines = [f"«{text}» — {why}" if why else f"«{text}»"]
    other = [str(a).strip() for a in alternatives if str(a).strip()]
    if other:
        lines.append("другое прочтение: " + ", ".join(other))
    return lines


def issue_line(message: str, detail: str | None, suggestion: str | None) -> str:
    """One arithmetic issue on one line, for the PDF.

    mathcheck puts ❌ or ⚠️ in front of its own lines, which is right in
    Telegram and wrong on the page. DejaVu has a glyph for ⚠ but none for ❌,
    so on paper a critical issue would come out as an empty box while a mere
    warning drew fine — the worse of the two made to look like nothing at all.
    Inside the document the colour of the callout carries the severity.
    """
    parts = [message]
    if detail:
        parts.append(detail)
    if suggestion:
        parts.append(f"→ {suggestion}")
    return " · ".join(parts)


def divergence_line(
    context: str, variants: dict[str, int], page: int | None = None
) -> str:
    """One divergent number, phrased for a person.

    What stood here before was the comparison's own shape —
    `с. 4 — 0: 0 — 2, 2 — 1` — six lines of which went into a record and told
    nobody anything. The question a reader has is which reading won and by how
    much, so that is what the line says.
    """
    total = sum(variants.values()) or 1
    options = " или ".join(
        # consensus writes a gap as "— (пропущено)". Left as it is, the dash
        # reads as a stray minus mid-sentence and the brackets collide with
        # the count that follows: "(пропущено) (1 из 3)".
        f"{value.strip('—() ') or 'пропущено'} ({count} из {total})"
        for value, count in variants.items()
    )
    where = f"с. {page}" if page is not None else ""
    around = context.strip()
    if around and around not in variants:
        around = around if len(around) <= 30 else around[:29] + "…"
        where = f"{where}, «{around}»" if where else f"«{around}»"
    return f"{where}: {options}" if where else options


# Documents — app/bot/handlers.py handle_document.
DOCX_ONLY = "Понимаю только файлы .docx. Другие форматы пока не умею."

FILE_TOO_BIG = "Файл больше 5 МБ. Пришли документ поменьше."

# Albums — app/bot/handlers.py _process_album and app/bot/albums.py.
TOO_MANY_PAGES = (
    "В одном альбоме слишком много страниц. Пришли их несколькими альбомами "
    "поменьше."
)

# Why a single album page was dropped while the rest of the batch went on.
SKIP_UNRECOGNIZED = "не удалось распознать"
SKIP_DIVERGED = "прогоны распознавания разошлись"
SKIP_NO_TEXT = "на странице не найдено текста"
SKIP_ERROR = "ошибка обработки"


def page_skipped(page: int, reason: str) -> str:
    """One line naming a skipped album page and the reason."""
    return f"Страница {page} пропущена: {reason}."


def page_prefix(page: int, body: str) -> str:
    """Attach an album page number to a multi-line block — e.g. a mathcheck
    report that applies to that page alone."""
    return f"Страница {page}.\n{body}"


def uncertain_line(text: str, why: str, page: int | None = None) -> str:
    """One line per uncertain spot: what was read and why it is ambiguous.
    `page` prefixes the line for an album record."""
    prefix = f"с. {page} — " if page is not None else ""
    return f'{prefix}"{text}" — {why}'


# ── The corpus — app/bot/corpus.py ───────────────────────────────────────────

CORPUS_EMPTY = (
    "Корпус пока пуст. Пришли фотографию страницы конспекта — появится "
    "первая запись."
)

NOTE_NOT_FOUND = "Записи с таким номером нет."

NOTE_USAGE = "Укажи номер записи: /note 42"

NOTES_PAGE_EMPTY = "На этой странице записей нет."

NEEDS_REVIEW_SHORT = "нужна проверка"


def note_line(
    note_id: int,
    created_at: datetime,
    title: str,
    subject: str | None,
    page_count: int,
    needs_review: bool,
) -> str:
    """One record in a listing. Subject is omitted when the model didn't name
    one, so a record without it doesn't show an empty gap."""
    parts = [f"#{note_id}", created_at.strftime("%d.%m"), title]
    if subject:
        parts.append(subject)
    parts.append(f"{page_count} с.")
    if needs_review:
        parts.append(NEEDS_REVIEW_SHORT)
    return " · ".join(parts)


def notes_footer(total: int, page: int, per_page: int) -> str | None:
    """The line under a listing, or None when everything already fits."""
    shown = min(page * per_page, total)
    if shown >= total:
        return None
    return f"Показано {shown} из {total}. Дальше — /notes {page + 1}"


# Telegram rejects messages over 4096 characters. Split on blank lines; hard-cut
# only a single paragraph that is itself longer than the limit.
MESSAGE_LIMIT = 4000


def split_message(text: str, limit: int = MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(para) > limit:
            chunks.append(para[:limit])
            para = para[limit:]
        current = para
    if current:
        chunks.append(current)
    return chunks


SEARCH_USAGE = "Что искать? Например: /search производная"


def search_empty(query: str) -> str:
    return f'По запросу «{query}» ничего не нашлось.'


RETITLE_USAGE = "Укажи номер и новый заголовок: /retitle 42 Производная функции"

DELETE_USAGE = "Укажи номер записи: /delete 42"


def retitled(title: str) -> str:
    return f'Заголовок изменён: «{title}»'


def deleted(title: str) -> str:
    return f'Запись удалена: «{title}»'


STATS_EMPTY = (
    "Пока нечего считать. Пришли первую страницу — и здесь появится, "
    "сколько всего накопилось."
)

_MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)


def _plural(n: int, one: str, few: str, many: str) -> str:
    """Russian number agreement: 1 запись, 2 записи, 5 записей."""
    tail = abs(n) % 100
    if 11 <= tail <= 14:
        return many
    tail %= 10
    if tail == 1:
        return one
    if 2 <= tail <= 4:
        return few
    return many


def _day(value: date, today: date) -> str:
    if value == today:
        return "сегодня"
    if (today - value).days == 1:
        return "вчера"
    return f"{value.day} {_MONTHS[value.month - 1]}"


def stats(
    notes: int, pages: int, first: date, last: date, streak: int, today: date
) -> str:
    """The corpus at a glance. Accumulation is the thing that is supposed to
    make leaving costly, and it is invisible until someone counts it."""
    lines = [
        f"{notes} {_plural(notes, 'запись', 'записи', 'записей')}, "
        f"{pages} {_plural(pages, 'страница', 'страницы', 'страниц')}",
        f"Первая — {_day(first, today)}, последняя — {_day(last, today)}",
    ]
    if streak:
        lines.append(
            f"Подряд: {streak} {_plural(streak, 'день', 'дня', 'дней')}"
        )
    else:
        lines.append("Серия прервана — пришли страницу сегодня, чтобы начать заново.")
    return "\n".join(lines)


# ── The command list ─────────────────────────────────────────────────────────
# One source for three consumers: Telegram's command menu (main.py), /help,
# and the test that refuses to let a command ship without a description.
# (name, menu description, usage example or None)

COMMANDS: tuple[tuple[str, str, str | None], ...] = (
    ("start", "начать", None),
    ("notes", "последние записи", "/notes 2"),
    ("note", "открыть запись", "/note 42"),
    ("search", "поиск по корпусу", "/search производная"),
    ("retitle", "переименовать запись", "/retitle 42 Новый заголовок"),
    ("delete", "удалить запись", "/delete 42"),
    ("pdf", "запись файлом", "/pdf 42"),
    ("stats", "сколько накопилось", None),
    ("help", "что я умею", None),
)


def _help_line(name: str, description: str, usage: str | None) -> str:
    """The usage example stands in for the bare command where there is one, so
    the syntax is visible without a second line per command."""
    return f"{usage or '/' + name} — {description}"


HELP = "\n".join(
    ["Пришли фотографию страницы конспекта — верну структурированную запись.", ""]
    + [_help_line(*command) for command in COMMANDS]
)


# ── The record as a file — app/bot/corpus.py send_record_pdf ─────────────────

PDF_USAGE = "Укажи номер записи: /pdf 42"

PDF_FAILED = "Не смог собрать PDF. Текст записи цел — открой её через /note."


def record_caption(note_id: int, page_count: int) -> str:
    """The line under the file. It carries the record number on purpose: the
    document should lead back into the corpus, not away from it."""
    pages = f"{page_count} {_plural(page_count, 'страница', 'страницы', 'страниц')}"
    return f"#{note_id} · {pages}\nОткрыть текстом: /note {note_id}"


def byline(margin_notes: list[str]) -> str | None:
    """What stood in the margin, as one line under the title. None when the
    margin was empty — an empty line under a title is worse than none."""
    parts = [str(n).strip() for n in margin_notes if str(n).strip()]
    return " · ".join(parts) if parts else None


def pdf_subtitle(created_at: datetime, page_count: int, needs_review: bool) -> str:
    """The grey line under the title inside the document itself."""
    parts = [
        created_at.strftime("%d.%m.%Y"),
        f"{page_count} {_plural(page_count, 'страница', 'страницы', 'страниц')}",
    ]
    if needs_review:
        parts.append(NEEDS_REVIEW_SHORT)
    return " · ".join(parts)
