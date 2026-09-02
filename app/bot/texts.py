"""Все строки, которые видит пользователь."""

START = (
    "Привет! Пришли фотографию конспекта — верну структурированную запись.\n\n"
    "Записи накапливаются: со временем из них соберётся твой личный корпус."
)

PROCESSING = "Обрабатываю..."

NO_TEXT_FOUND = "Не нашёл на странице текста. Попробуй снять крупнее и ровнее."

ERROR_GENERIC = "Не смог обработать фото. Попробуй ещё раз чуть позже."

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
