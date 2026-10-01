"""Все строки, которые видит пользователь."""

import re
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

# The one box above a record: the pages it is missing. How the page was read —
# which spot reads two ways, which numbers the runs read differently, which
# page no second reading confirmed — is not printed at all: the author's
# decision, 2026-09-25, since the group studies from the document and talk
# about the recognition is noise to it.
CALLOUT_MISSING = "Не хватает страниц"

# The label of a finding set under the line it is about. A matrix checked
# against its graph is not a calculation, and says so.
FINDING_LABEL = "Проверка вычислений"
GRAPH_FINDING_LABEL = "Сверка с графом"

# What the bot adds of its own to a record, in the document. The labels say
# whose words these are: a reader who missed the lecture cannot tell an added
# sentence from a remembered one unless the page tells them.
EXPLANATION_LABEL = "Пояснение бота"
# The record summed up, first in the document as the guide's "Суть": its name,
# then whose words these are.
SUMMARY_LABEL = "Суть · составлено ботом по тексту записи"
SOURCES_LABEL = "Источники"


def explanation_line(title: str, text: str) -> str:
    """One explanation as the text of its box: what it is about, in bold,
    then what it says."""
    title = title.strip().rstrip(".:")
    return f"**{title}.** {text}" if title else text


# mathcheck names a chain by its line — "строка 29: звенья цепочки не
# сходятся" — a line of the page as it was recognised, which is nothing a
# reader can count, and beside the line itself says nothing at all.
_LINE_NUMBER_RE = re.compile(r"^строка \d+:\s*")


def finding_lines(message: str, detail: str, suggestion: str) -> list[str]:
    """One finding of a check, as the lines of the box under what it is about:
    what is wrong, in bold, and the numbers that show it.

    mathcheck puts ❌ or ⚠️ in front of its own lines, and none of that comes
    here: DejaVu has a glyph for ⚠ and none for ❌, so on paper a critical
    finding would come out as an empty box while a mere warning drew fine.
    The accent of the box carries the severity.
    """
    what = _LINE_NUMBER_RE.sub("", message.strip()).rstrip(".")
    what = what[:1].upper() + what[1:]
    first = f"**{what}.** {detail}" if detail else f"**{what}.**"
    return [first, f"→ {suggestion}"] if suggestion else [first]


# Documents — app/bot/handlers.py handle_document.
DOCX_ONLY = "Понимаю только файлы .docx. Другие форматы пока не умею."

FILE_TOO_BIG = "Файл больше 5 МБ. Пришли документ поменьше."

# An image sent as a file — app/bot/handlers.py handle_photo. Telegram lets a
# bot download 20 MB at most.
IMAGE_TOO_BIG = (
    "Картинка больше 20 МБ — такую мне не скачать. Пришлите её обычным фото."
)

# Calling the bot on pages somebody else sent to a group —
# app/bot/handlers.py handle_summon.
SUMMON_NEEDS_TAG = (
    "Ответьте на фото или альбом тегом предмета, например #матан, — "
    "и я сделаю из него запись."
)
SUMMON_ALBUM_UNKNOWN = (
    "Этот альбом я целиком не видел: он старше недели или пришёл, когда меня "
    "не было в чате. Пришлите его заново с тегом предмета в подписи, "
    "например #матан."
)

# Albums — app/bot/handlers.py _process_album and app/bot/albums.py.
TOO_MANY_PAGES = (
    "В одном альбоме слишком много страниц. Пришли их несколькими альбомами "
    "поменьше."
)

# Why a single album page was dropped while the rest of the batch went on.
SKIP_UNRECOGNIZED = "не удалось распознать"
SKIP_DIVERGED = "прогоны распознавания разошлись"
# Not a skip: the page is in the record, and notes.unverified_pages keeps why
# nothing confirmed its reading. Kept for the measurements; since 2026-09-25
# the document does not print it.
UNVERIFIED_DIVERGED = "прогоны распознавания сильно разошлись"
UNVERIFIED_ONE_RUN = "прочитана одним прогоном, сверить было не с чем"
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


# A page the frame check turned away, asked for again before anything is read.
ALBUM_RETAKE = "Альбом пока не читаю — эти страницы нужно переснять:"

ALBUM_RETAKE_HOW = (
    "Пришлите альбом заново, все страницы вместе, — соберу одну полную "
    "запись. Если переснять нельзя, пришлите альбом без них."
)


def album_retake(skips: list[tuple[int, str]]) -> str:
    """Which pages to retake and why, before any of the album was read."""
    lines = [ALBUM_RETAKE, ""]
    lines += [
        f"Страница {page}: {reason[:1].lower()}{reason[1:]}." for page, reason in skips
    ]
    lines += ["", ALBUM_RETAKE_HOW]
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


# ── Tags — app/bot/corpus.py ─────────────────────────────────────────────────

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


def filed(tag: str, topics: list[str]) -> str:
    """Said instead of the question when the photo came with its subject. The
    topics are still shown, and for the same reason as under the question:
    they are what the record will be found by, and in a group they are how
    the others learn what to type."""
    lines = [f"Сохранил под #{tag}. Найти: #{tag} или тема записи."]
    if topics:
        lines += ["", "Темы этой записи: " + " ".join("#" + t for t in topics)]
    return "\n".join(lines)


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
        "запись и спрошу, под каким тегом её сохранить. Тег можно сразу "
        "написать в подписи к фото.",
        "",
        "Чтобы найти запись позже — пришли тег: #физика, или название "
        "темы, например #производная.",
        "",
        ".docx тоже приму — его распознавать не нужно.",
        "",
        "Добавь меня в чат своей группы: там я беру фото с тегом предмета "
        "в подписи и присылаю PDF всем.",
        "",
    ]
    + [_help_line(*command) for command in COMMANDS]
)


# ── The bot in a group chat — app/bot/handlers.py on_joined ─────────────────
# A course chat is mostly people talking to each other, so the bot answers
# only what is addressed to it. That makes the rule worth saying up front: a
# photo sent without a tag gets no answer at all.

GROUP_HELP = "\n".join(
    [
        "Я делаю из фотографий конспекта PDF для всей группы.",
        "",
        "Пришлите фото или альбом страниц с тегом предмета в подписи, "
        "например #матан, — верну PDF сюда. Фото без тега не трогаю.",
        "",
        "Если страницы уже прислали без тега, ответьте на них тегом — "
        "#матан — и я сделаю запись из них.",
        "",
        "Найти запись может любой: напишите #матан или тему записи, "
        "например #производная.",
        "",
    ]
    + [_help_line(*command) for command in COMMANDS]
)

GROUP_CANNOT_SEE = (
    "Пока я не вижу фотографий в этом чате. Сделайте меня администратором — "
    "никаких прав давать не нужно."
)

GROUP_SEES_PHOTOS = (
    "Теперь я вижу фотографии в этом чате. Присылайте страницы с тегом "
    "предмета в подписи, например #матан."
)


def group_welcome(sees_photos: bool) -> str:
    text = f"Привет! {GROUP_HELP}"
    return text if sees_photos else f"{text}\n\n{GROUP_CANNOT_SEE}"


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


# The head of every page of the document, and the signature at its foot —
# app/services/pdf.py, BRAND.md. The invitation is the guide's and may change
# with who it is for; the bot's name under it and the QR code never do.
PDF_PAGE_WORD = "стр."
PDF_INVITE = "Сделай такой конспект своей группе"


def pdf_date(created_at: datetime) -> str:
    """The record's day, in the head of every page. Facts only: the grey line
    under the title that carried the date used to end in "нужна проверка" on
    a record the runs had disagreed about — a doubt about the reading that
    told nobody what to check."""
    return created_at.strftime("%d.%m.%Y")


def pdf_subject(tag: str | None) -> str:
    """The subject in the head of every page, written as the "#word" that
    finds the record again. Empty until the record is filed under one."""
    return f"#{tag}" if tag else ""
