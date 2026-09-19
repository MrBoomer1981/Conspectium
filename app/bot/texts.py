"""Все строки, которые видит пользователь."""

from datetime import datetime

START = (
    "Привет! Пришли фотографию конспекта — верну структурированную запись.\n\n"
    "Записи накапливаются: со временем из них соберётся твой личный корпус."
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


def divergence_line(
    context: str, variants: dict[str, int], page: int | None = None
) -> str:
    """One line per divergent number: its context and each competing value with
    how many runs produced it. `page` prefixes the line for an album record."""
    options = ", ".join(f"{value} — {count}" for value, count in variants.items())
    prefix = f"с. {page} — " if page is not None else ""
    return f"{prefix}{context}: {options}"


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
