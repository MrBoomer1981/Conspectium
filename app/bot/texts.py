"""Все строки, которые видит пользователь."""

from datetime import date, datetime

START = (
    "Привет! Пришли фотографию конспекта — верну структурированную запись "
    "и спрошу, под каким тегом её сохранить.\n\n"
    "Записи накапливаются: со временем из них соберётся твой личный корпус, "
    "и найти в нём нужное можно будет по тегу — #физика или #производная.\n\n"
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
CALLOUT_MISSING = "Не хватает страниц"


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


ALBUM_INCOMPLETE = (
    "Ни одна страница не разобралась, поэтому сохранять нечего."
)

ALBUM_RESEND = "Переснимите эти страницы и пришлите альбом заново."

ALBUM_PARTIAL = (
    "Конспект сохранён без этих страниц — в документе на их месте стоит "
    "пометка, чтобы пропуск нельзя было прочитать как целую запись."
)

ALBUM_SEND_MISSING = "Пришлите их отдельно, и они станут отдельной записью."


def album_incomplete(skips: list[tuple[int, str]]) -> str:
    """Why nothing was saved, and which pages to take again."""
    lines = [ALBUM_INCOMPLETE, ""]
    lines += [page_skipped(page, reason) for page, reason in skips]
    lines += ["", ALBUM_RESEND]
    return "\n".join(lines)


def album_partial(skips: list[tuple[int, str]]) -> str:
    """The record is saved; these pages are not in it."""
    lines = [ALBUM_PARTIAL, ""]
    lines += [page_skipped(page, reason) for page, reason in skips]
    lines += ["", ALBUM_SEND_MISSING]
    return "\n".join(lines)


def page_missing_marker(page: int) -> str:
    """The hole, at the position the page would have had.

    Bold rather than a heading: a heading here would become a topic, and this
    is the one line in a record that is about the record instead of about the
    lecture.
    """
    return f"**[Страница {page} не прочитана]**"


def missing_pages_line(page: int, reason: str) -> str:
    """One line of the box that names the hole inside the document."""
    return f"Страница {page}: {reason}."


def page_prefix(page: int, body: str) -> str:
    """Attach an album page number to a multi-line block — e.g. a mathcheck
    report that applies to that page alone."""
    return f"Страница {page}.\n{body}"


def uncertain_line(text: str, why: str, page: int | None = None) -> str:
    """One line per uncertain spot: what was read and why it is ambiguous.
    `page` prefixes the line for an album record."""
    prefix = f"с. {page} — " if page is not None else ""
    return f'{prefix}"{text}" — {why}'


# ── Tags — app/bot/corpus.py ─────────────────────────────────────────────────

NEEDS_REVIEW_SHORT = "нужна проверка"

TAG_UNREADABLE = "Не разобрал тег. Напиши его одним сообщением, например: #физика"


def ask_tag(topics: list[str], known: list[str]) -> str:
    """Asked straight after a record is delivered.

    The topics are shown rather than kept: they are what the record will be
    found by later, the bot wrote them, and something the bot wrote should be
    read by the person it belongs to on the day it was made — not discovered
    months later in a search that missed.
    """
    lines = ["Под каким тегом сохранить? Ответь одним словом с решёткой: #физика"]
    if known:
        lines += ["", "Уже в ходу: " + " ".join("#" + t for t in known)]
    if topics:
        lines += ["", "Темы этой записи: " + " ".join("#" + t for t in topics)]
    return "\n".join(lines)


def tagged(tag: str) -> str:
    return f"Сохранил под #{tag}. Чтобы найти — пришли #{tag} или название темы."


def nothing_tagged(tag: str, known: list[str]) -> str:
    text = f"По #{tag} ничего не нашлось."
    if known:
        text += "\n\nЕсть записи под: " + " ".join("#" + t for t in known)
    return text


def several_tagged(tag: str, rows: list[tuple[str, list[str]]]) -> str:
    """Several records under one tag. Each line carries the record's own
    topics, because the next message is expected to be one of them — a list
    you cannot act on is a list that made the user type the tag again."""
    lines = [f"По #{tag} нашлось несколько. Уточни темой:", ""]
    for title, topics in rows:
        hint = " ".join("#" + t for t in topics)
        lines.append(f"{title}\n{hint}" if hint else title)
        lines.append("")
    return "\n".join(lines).strip()


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
    ("stats", "сколько накопилось", None),
    ("help", "что я умею", None),
)


def _help_line(name: str, description: str, usage: str | None) -> str:
    """The usage example stands in for the bare command where there is one, so
    the syntax is visible without a second line per command."""
    return f"{usage or '/' + name} — {description}"


# The two gestures that carry the product are not commands, so /help has to
# say them outright: a hash is not on the menu Telegram shows.
HELP = "\n".join(
    [
        "Пришли фотографию страницы конспекта — верну структурированную "
        "запись и спрошу, под каким тегом её сохранить.",
        "",
        "Чтобы найти запись позже — пришли тег: #физика, или название "
        "темы, например #производная.",
        "",
        ".docx тоже приму — его распознавать не нужно.",
        "",
    ]
    + [_help_line(*command) for command in COMMANDS]
)


# ── The record as a file — app/bot/corpus.py send_record_pdf ─────────────────

PDF_FAILED = "Не смог собрать PDF — вот текст записи."


def record_caption(note_id: int, page_count: int) -> str:
    """The line under the file.

    It used to end with "открыть текстом: /note 42". That command is gone, and
    a caption pointing at a command the bot no longer answers is worse than a
    caption that points nowhere — so what is left is what identifies the
    record.
    """
    pages = f"{page_count} {_plural(page_count, 'страница', 'страницы', 'страниц')}"
    return f"#{note_id} · {pages}"


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
