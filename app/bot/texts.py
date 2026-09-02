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


def divergence_line(context: str, variants: dict[str, int]) -> str:
    """One line per divergent number: its context and each competing value with
    how many runs produced it."""
    options = ", ".join(f"{value} — {count}" for value, count in variants.items())
    return f"{context}: {options}"
