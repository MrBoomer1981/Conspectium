"""Все строки, которые видит пользователь."""

import re
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.bot import rating

START = (
    "Привет! Я делаю из фотографий конспекта PDF для всей группы.\n\n"
    "Добавь меня в чат своей группы — кнопка ниже. Там я беру фото с тегом "
    "предмета в подписи, например #матан, и присылаю PDF всем.\n\n"
    "Можно и здесь: пришли фото конспекта — верну запись и спрошу, под каким "
    "тегом её сохранить. Найти её потом можно по тегу — #физика или #производная.\n\n"
    "Что ещё умею — /help"
)

# The one button the bot shows, under /start and /help in a private chat — it
# opens Telegram's own chat picker (task 47).
ADD_TO_GROUP = "Добавить в чат группы"

# What a chat sees while its record is made (task 105): one line, changed in
# place every few seconds round these, and deleted when the record arrives —
# the CEO's «работаем, еще минуту, считаю формулы, учусь, чтобы вам не
# пришлось» and two of the same kind, true of a photo and a .docx alike.
WAITING = (
    "Работаем…",
    "Читаю конспект…",
    "Считаю формулы…",
    "Учусь, чтобы вам не пришлось…",
    "Раскладываю по темам…",
    "Ещё минуту…",
)

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


# A group's day (task 41), the CEO's lines of 2026-10-07. The day turns at
# 00:00 UTC, 03:00 in Moscow, and the lines name the hour: "завтра" said at
# one in the morning would send a group away for a day it does not have to
# wait.
def group_day_over(left: int, pages: int, cap: int) -> str:
    """Why a group's pages are turned away: none left today, or fewer than
    the album holds — a single page is refused only when none are left."""
    if left <= 0:
        return (
            f"Страницы группы на сегодня закончились — {cap} в день. "
            "Новые можно после 3:00 по Москве."
        )
    return (
        f"Сегодня группа может прислать ещё {_pages_to_send(left)}, "
        f"а в альбоме {pages}. Пришли меньше или подожди до 3:00 по Москве."
    )


def group_day(left: int, cap: int) -> str:
    """What is left of the group's day, under its week in /stats."""
    if left <= 0:
        return group_day_over(0, 0, cap)
    return f"Сегодня группа может прислать ещё {_pages_to_send(left)} из {cap}."


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
# The teacher's boxes (task 56), each under a label that says what it is and
# whose: reasoning of the bot's, printed without a source.
ELEMENT_LABELS = {
    "idea": "Идея · от бота",
    "condition": "Зачем условие · от бота",
    "example": "Пример · от бота",
    # A formula or a drawing the record says nothing about, named (task 95).
    "caption": "Что это · от бота",
}
# The record summed up, first in the document as the guide's "Суть": its name,
# then whose words these are.
SUMMARY_LABEL = "Суть · составлено ботом по тексту записи"
# Over a passage another notebook of the same lecture adds to its document
# (task 63) — the CEO's words, 2026-10-04.
INSERT_LABEL = "Из другого конспекта"
SOURCES_LABEL = "Источники"


def explanation_line(title: str, text: str) -> str:
    """One explanation as the text of its box: what it is about, in bold,
    then what it says — opening with a capital letter, as every box of
    record 92's did not (task 86)."""
    title = _capitalised(title.strip().rstrip(".:"))
    return f"**{title}.** {text}" if title else _capitalised(text)


def _capitalised(text: str) -> str:
    return text[:1].upper() + text[1:]


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


def equality_lines(
    equality: str, point: list[tuple[str, str]], left: str, right: str
) -> list[str]:
    """An equality that does not hold (task 84), as the box under it says
    so: the equality, and numbers the reader can count it at."""
    at = ", ".join(f"${letter} = {value}$" for letter, value in point)
    return [
        f"**Равенство ${equality}$ не выполняется.** При {at} левая часть "
        f"равна ${left}$, правая — ${right}$."
    ]


# Documents — app/bot/handlers.py handle_document.
DOCX_ONLY = "Понимаю файлы .docx и PDF. Другие форматы пока не умею."

FILE_TOO_BIG = "Файл больше 5 МБ. Пришли документ поменьше."

# An image sent as a file — app/bot/handlers.py handle_photo. Telegram lets a
# bot download 20 MB at most.
IMAGE_TOO_BIG = (
    "Картинка больше 20 МБ — такую мне не скачать. Пришлите её обычным фото."
)

# A PDF of notes, read page by page as an album — app/bot/handlers.py
# _read_pdf (task 100). Telegram lets a bot download 20 MB at most.
PDF_TOO_BIG = (
    "PDF больше 20 МБ — такой мне не скачать. Пришлите страницы фотографиями."
)

PDF_UNREADABLE = "Не смог открыть PDF: файл повреждён или защищён паролем."

PDF_BLANK = "В этом PDF все страницы пустые — читать нечего."


def pdf_too_many_pages(limit: int) -> str:
    """A PDF longer than an album may be, refused before a page is read."""
    pages = _plural(limit, "страницы", "страниц", "страниц")
    return (
        f"В этом PDF больше {limit} {pages} — столько за раз не читаю. "
        "Пришлите его частями."
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
# The same pages being read for the chat at that moment (task 41): the record
# goes to the chat once, and this call starts nothing.
SUMMON_READING = "Уже читаю эти страницы — конспект придёт сюда."

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

PDF_RESEND = "Пришлите PDF заново, с этими страницами почётче."

ALBUM_PARTIAL = (
    "Конспект сохранён без этих страниц — в документе на их месте стоит "
    "пометка, чтобы пропуск нельзя было прочитать как целую запись."
)

ALBUM_SEND_MISSING = "Пришлите их отдельно, и они станут отдельной записью."


def album_incomplete(skips: list[tuple[int, str]], resend: str = ALBUM_RESEND) -> str:
    """Why nothing was saved, and which pages to take again — PDF_RESEND for
    a PDF's, which no camera takes again."""
    lines = [ALBUM_INCOMPLETE, ""]
    lines += [page_skipped(page, reason) for page, reason in skips]
    lines += ["", resend]
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


# A page of a PDF the frame check turned away (task 100): the whole PDF waits,
# as an album does since task 43 — the CEO's choice of 2026-10-10.
PDF_RETAKE = "Этот PDF пока не читаю — страницы не прошли проверку:"

PDF_RETAKE_HOW = (
    "Пришлите PDF заново — с этими страницами почётче или без них, — "
    "и соберу одну полную запись."
)


def pdf_retake(skips: list[tuple[int, str]]) -> str:
    """Which pages of a PDF the frame check refused, before any was read: the
    cause alone, since photoguard's advice after it — «добавьте света» — is
    a photographer's."""
    lines = [PDF_RETAKE, ""]
    lines += [f"Страница {page}: {_cause(reason)}." for page, reason in skips]
    lines += ["", PDF_RETAKE_HOW]
    return "\n".join(lines)


def _cause(reason: str) -> str:
    cause = reason.split(" — ")[0].strip()
    return cause[:1].lower() + cause[1:]


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


def _lecture_day(given_on: date) -> str:
    return given_on.strftime("%d.%m")


def _filed_under(tag: str, given_on: date | None) -> str:
    """"Сохранил под #матан — лекция от 03.10": the day the record stands at
    in its subject (task 63), so a lecture sent late without its date is seen
    standing at the wrong one."""
    if given_on is None:
        return f"Сохранил под #{tag}."
    return f"Сохранил под #{tag} — лекция от {_lecture_day(given_on)}."


def tagged(tag: str, given_on: date | None = None) -> str:
    return f"{_filed_under(tag, given_on)} Чтобы найти — пришли #{tag} или название темы."


def filed(tag: str, topics: list[str], given_on: date | None = None) -> str:
    """Said instead of the question when the photo came with its subject. The
    topics are still shown, and for the same reason as under the question:
    they are what the record will be found by, and in a group they are how
    the others learn what to type."""
    lines = [f"{_filed_under(tag, given_on)} Найти: #{tag} или тема записи."]
    if topics:
        lines += ["", "Темы этой записи: " + " ".join("#" + t for t in topics)]
    return "\n".join(lines)


def _passages(n: int) -> str:
    return f"{n} {_plural(n, 'вставка', 'вставки', 'вставок')}"


def lecture_added(tag: str, given_on: date, added: int) -> str:
    """Under the lecture's document when a notebook joined a lecture already
    there and is not its base (task 63)."""
    head = f"Это лекция от {_lecture_day(given_on)} — она уже есть в #{tag}."
    if added:
        return f"{head} Дополнил её этим конспектом: {_passages(added)} в документе."
    return f"{head} Нового в этом конспекте не нашлось — документ прежний."


def lecture_led(tag: str, given_on: date, from_others: int) -> str:
    """Under the lecture's document when the notebook that joined is fuller
    than the one it had, and is its base now."""
    head = f"Это лекция от {_lecture_day(given_on)} — она уже есть в #{tag}."
    tail = f", из прежнего — {_passages(from_others)}" if from_others else ""
    return f"{head} Этот конспект полнее — теперь документ собран по нему{tail}."


def listed(title: str, given_on: date | None) -> str:
    """A record in a list of several, with its lecture's day when it is
    filed into one."""
    return f"{_lecture_day(given_on)} · {title}" if given_on else title


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


# ── A whole notebook — app/bot/notebook.py, handlers._read_notebook ───────────

# A lecture's title when nothing in its text could be one.
NOTEBOOK_TITLE = "Конспект из тетради"
NOTEBOOK_ONE_A_DAY = (
    "Целая тетрадь — одна в день, сегодняшняя уже прочитана. Пришли эту завтра."
)


def notebook_too_long(limit: int) -> str:
    """A notebook of more pages than one may hold, refused before a page is
    read."""
    pages = _plural(limit, "страницы", "страниц", "страниц")
    return (
        f"В тетради больше {limit} {pages} — столько за раз не читаю. "
        "Пришли её двумя частями: сегодня первую, завтра вторую."
    )


def _page_span(pages: tuple[int, int]) -> str:
    return f"{pages[0]}–{pages[1]}" if pages[0] != pages[1] else f"{pages[0]}"


def _page_spans(runs: list[tuple[int, int]]) -> str:
    spans = [_page_span(run) for run in runs]
    return ", ".join(spans[:-1]) + f" и {spans[-1]}" if len(spans) > 1 else spans[0]


def _lectures(n: int) -> str:
    return f"{n} {_plural(n, 'лекция', 'лекции', 'лекций')}"


def notebook_reading(done: int, total: int) -> str:
    """The line a chat sees while a notebook's pages are read (task 63, the
    CEO's of 2026-10-13)."""
    return f"Читаю тетрадь: {done} из {total} {_plural(total, 'страницы', 'страниц', 'страниц')}"


def notebook_making(done: int, total: int) -> str:
    """The same line while its lectures are made and sent."""
    return f"Собираю лекции: {done} из {total}"


def notebook_done(
    lectures: list[tuple[str, date | None]],
    parts: list[tuple[int, int]],
    missing: list[tuple[int, str]],
    failed: list[tuple[int, int]],
    tag: str | None,
    known: list[str],
) -> str:
    """The last message of a notebook (task 63): the lectures it was cut
    into, by their days; the pages where no lecture's start was found, and
    the parts they were kept in (`parts`, each its first and last page);
    the pages it could not read, each with why, to be sent again as a reply
    to this message (the CEO's of 2026-10-13); the lectures that could not
    be made; then where they all are — or, sent without its "#word", the
    one question which subject they are, its answer filing every one."""
    lines = [f"Тетрадь разобрана: {_lectures(len(lectures))}.", ""]
    lines += [listed(title, day) for title, day in lectures]
    if parts:
        stretch = []
        for first, last in parts:
            if stretch and first == stretch[-1][1] + 1:
                stretch[-1] = (stretch[-1][0], last)
            else:
                stretch.append((first, last))
        lines += [
            "",
            f"Стр. {_page_spans(stretch)}: где там начинаются лекции, не нашлось — "
            f"сохранил частями: {_page_spans(parts)}.",
        ]
    if len(missing) == 1:
        page, reason = missing[0]
        lines += [
            "",
            f"Не прочитана страница {page}: {_cause(reason)}. В лекции на её месте "
            "пометка — пересними её и пришли ответом на это сообщение, она встанет "
            "в свою лекцию.",
        ]
    elif missing:
        lines += ["", "Не прочитаны страницы:"]
        lines += [f"{page} — {_cause(reason)}" for page, reason in missing]
        lines.append(
            "В лекциях на их месте пометки. Пересними их и пришли ответом на это "
            "сообщение, по одной, с номером страницы в подписи, — каждая встанет "
            "в свою лекцию."
        )
    if failed:
        lines += [
            "",
            f"Не вышли лекции со страниц {_page_spans(failed)} — пришли эти страницы ещё раз альбомом.",
        ]
    lines.append("")
    if tag is not None:
        lines.append(f"Все — под #{tag}. Найти: #{tag} или тема лекции.")
    else:
        lines.append(
            "Под каким тегом сохранить все лекции тетради? Ответь одним словом "
            "с решёткой: #физика"
        )
        if known:
            lines.append("Уже в ходу: " + " ".join("#" + t for t in known))
    return "\n".join(lines)


NOTEBOOK_WHOLE = "В этой тетради все страницы уже на месте."
NOTEBOOK_PAGE_NOT_PLACED = (
    "Не нашёл в лекции места этой страницы. Пришли её обычным фото — она станет "
    "отдельной записью."
)


def notebook_page_which(missing: list[int]) -> str:
    """A page sent again with no number, while more than one is missing."""
    return (
        "Какая это страница? Пришли её ещё раз ответом на сводку тетради, с "
        f"номером в подписи: не прочитаны {_page_spans(_runs_of(missing))}."
    )


def notebook_page_not_missing(page: int, missing: list[int]) -> str:
    return (
        f"Страница {page} уже на месте. Не прочитаны "
        f"{_page_spans(_runs_of(missing))}."
    )


def notebook_page_added(page: int, title: str) -> str:
    """Under a lecture's document sent again with a page it was missing."""
    return f"Страница {page} встала в лекцию «{_shortened(title, 80)}»."


def _runs_of(pages: list[int]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for page in sorted(set(pages)):
        if runs and page == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], page)
        else:
            runs.append((page, page))
    return runs


def notebook_tagged(tag: str, count: int) -> str:
    """The answer to a notebook's question: every lecture of it filed."""
    return f"Сохранил под #{tag} {_lectures(count)} тетради. Найти — пришли #{tag} или название темы."


# ── A subject's whole semester — app/bot/semester_version.py ─────────────────

SEMESTER_BUTTON = "Весь семестр одним PDF"
SEMESTER_BUILDING = "Собираю весь семестр по темам — пара минут."
SEMESTER_SENDING = "Отправляю семестр."
SEMESTER_BUSY = "Семестр уже собирается."
SEMESTER_FEW = "В этом предмете пока одна лекция — семестр собирать не из чего."
SEMESTER_FAILED = (
    "Не получилось собрать семестр. Лекции по отдельности — по #слову предмета."
)
SEMESTER_SUBTITLE = "Весь семестр · по темам, собран ботом из конспектов лекций"
SEMESTER_FILE_WORD = "semestr"


def semester_title(word: str) -> str:
    return f"{word[:1].upper()}{word[1:]} — весь семестр"


def semester_dates(first: date, last: date) -> str:
    """The semester's days at the head of every page."""
    return f"{first:%d.%m} – {last:%d.%m.%Y}"


def semester_caption(word: str, lectures: int, topics: int) -> str:
    return (
        f"#{word} · весь семестр: {_lectures(lectures)}, {topics} "
        f"{_plural(topics, 'тема', 'темы', 'тем')}. Текст лекций — слова авторов; "
        "всё, что добавил бот, — в рамках «от бота»."
    )


# ── A lecture moved into a group — app/bot/to_group.py ──────────────────────


def _shortened(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def move_button(group_title: str | None) -> str:
    """Under a private lecture's document (task 63), a button a group: named,
    since a person may be in several."""
    name = _shortened(group_title or "", 28)
    return f"В группу «{name}»" if name else "В группу"


def move_all_button(group_title: str | None) -> str:
    """Under a notebook's last message: all its lectures into a group."""
    name = _shortened(group_title or "", 24)
    return f"Все в группу «{name}»" if name else "Все в группу"


MOVE_ALREADY = "Эта лекция уже в группе."
MOVE_ALL_ALREADY = "Лекции этой тетради уже в группе."
MOVE_NOT_MEMBER = "Не вижу тебя в этой группе — перенести туда не могу."


def moved_notice(group_title: str | None, tag: str) -> str:
    """What the person who pressed is shown: where the lecture is now, and
    how it is found there — it is the group's, and the private chat's "#word"
    no longer finds it."""
    name = _shortened(group_title or "", 60)
    where = f"в группе «{name}»" if name else "в группе"
    return f"Лекция теперь {where} — там её найдёт #{tag}."


def moved_all_notice(group_title: str | None, tag: str, count: int) -> str:
    name = _shortened(group_title or "", 60)
    where = f"в группе «{name}»" if name else "в группе"
    return f"{_lectures(count).capitalize()} теперь {where} — там их найдёт #{tag}."


def moved_all_line(name: str, tag: str, count: int, first: date, last: date) -> str:
    """The one line a group is shown when a whole notebook's lectures are
    moved into it (task 63), its verb in the present as `moved_line`'s."""
    days = (
        f"от {_lecture_day(first)}"
        if first == last
        else f"с {_lecture_day(first)} по {_lecture_day(last)}"
    )
    return f"{name} добавляет в #{tag} {_lectures(count)} своей тетради — {days}."


def moved_line(
    name: str,
    tag: str,
    given_on: date,
    title: str,
    joined: bool,
    leads: bool,
    added: int,
) -> str:
    """The one line a group is shown when a lecture is moved into it from a
    private chat (task 63): who, under which "#word", which lecture — and,
    when the group had that lecture, what the notebook did to its document,
    as `lecture_added` and `lecture_led` say it to the person who sent it.
    The verb in the present: Russian's past would name whoever moved it a
    man or a woman."""
    day = _lecture_day(given_on)
    if not joined:
        return f"{name} добавляет в #{tag} лекцию от {day} — «{_shortened(title, 80)}»."
    if leads:
        return (
            f"{name} добавляет к лекции от {day} в #{tag} свой конспект — он полнее, "
            "документ теперь собран по нему."
        )
    if added:
        return f"{name} дополняет лекцию от {day} в #{tag} своим конспектом: {_passages(added)}."
    return (
        f"{name} добавляет к лекции от {day} в #{tag} свой конспект — "
        "нового в нём не нашлось."
    )


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


# ── A group's week (task 72) ─────────────────────────────────────────────────
# Who sent the group's records and who rated them: two numbers a person,
# ordered by records. A person is (name, records, отзывы).


def _records(n: int) -> str:
    return f"{n} {_plural(n, 'конспект', 'конспекта', 'конспектов')}"


def _ratings(n: int) -> str:
    return f"{n} {_plural(n, 'отзыв', 'отзыва', 'отзывов')}"


def _persons(n: int) -> str:
    return f"{n} {_plural(n, 'человек', 'человека', 'человек')}"


def _pages_to_send(n: int) -> str:
    # The accusative, after "прислать": 1 страницу, 2 страницы, 5 страниц.
    return f"{n} {_plural(n, 'страницу', 'страницы', 'страниц')}"


def _people(people: list[tuple[str, int, int]], more: int) -> list[str]:
    lines = [
        f"{place}. {name} — "
        + ", ".join(
            part
            for count, part in ((records, _records(records)), (ratings, _ratings(ratings)))
            if count
        )
        for place, (name, records, ratings) in enumerate(people, 1)
    ]
    if more:
        lines.append(f"и ещё {more} {_plural(more, 'человек', 'человека', 'человек')}")
    return lines


def group_week(
    title: str | None,
    since: date,
    records: int,
    ratings: int,
    people: list[tuple[str, int, int]],
    more: int,
    all_records: int,
    all_ratings: int,
) -> str:
    """/stats in a group: the week so far, and what the group has come to.
    The week runs from Saturday, as the summary does, and its head says so —
    a week that starts on a Saturday is not the one a student assumes."""
    lines = [f"{title or 'Группа'} · неделя с {since.day} {_MONTHS[since.month - 1]}"]
    if people:
        lines += [f"{_records(records)}, {_ratings(ratings)}", ""] + _people(people, more)
    else:
        lines.append("На этой неделе ещё ни конспектов, ни отзывов.")
    lines += ["", f"За всё время: {_records(all_records)}, {_ratings(all_ratings)}"]
    return "\n".join(lines)


def _span(first: date, last: date) -> str:
    """28 сентября — 4 октября; 5–11 октября within one month."""
    if first.month == last.month:
        return f"{first.day}–{last.day} {_MONTHS[last.month - 1]}"
    return (
        f"{first.day} {_MONTHS[first.month - 1]} — {last.day} {_MONTHS[last.month - 1]}"
    )


def week_summary(
    first: date,
    last: date,
    records: int,
    ratings: int,
    people: list[tuple[str, int, int]],
    more: int,
) -> str:
    """The week just ended, posted unasked on Saturday morning. Its last line
    says what an отзыв is: the chat sees the count before it has looked under
    a document."""
    return "\n".join(
        [f"Итоги недели, {_span(first, last)}", f"{_records(records)}, {_ratings(ratings)}", ""]
        + _people(people, more)
        + ["", "Отзыв — «Хорошо» или «Плохо» под конспектом и каждый комментарий к нему."]
    )


# ── The bot's week (task 74) ─────────────────────────────────────────────────
# /stats in the feedback chat, the CEO's own: every chat's week and all time.
# The operator's screen — spend is in dollars here, and nowhere a student
# reads (task 14).


def _usd(value: float) -> str:
    return f"${value:.2f}"


def _chat_week(chat: "rating.ChatWeek") -> str:
    name = "Личные чаты" if chat.private else (chat.title or "Группа без названия")
    parts = [
        part
        for count, part in (
            (chat.records, _records(chat.records)),
            (chat.pages, f"{chat.pages} стр."),
            (chat.people, _persons(chat.people)),
            (chat.ratings, _ratings(chat.ratings)),
        )
        if count
    ]
    return f"{name} — " + ", ".join(parts + [_usd(chat.spent)])


def _comments(n: int) -> str:
    return f"{n} {_plural(n, 'комментарий', 'комментария', 'комментариев')}"


def _everyone(people: list[tuple[str, int, int, int, int]], more: int) -> list[str]:
    """The bot's people with their week and all their time (task 103) —
    «byAVEN — 4 конспекта · всего 49 конспектов, 4 отзыва» — and one quiet
    this week with their all time alone: a new week's zeros are no loss."""
    lines = []
    for place, (name, records, ratings, all_records, all_ratings) in enumerate(people, 1):
        week = ", ".join(
            part
            for count, part in ((records, _records(records)), (ratings, _ratings(ratings)))
            if count
        )
        total = ", ".join(
            part
            for count, part in (
                (all_records, _records(all_records)),
                (all_ratings, _ratings(all_ratings)),
            )
            if count
        )
        said = f"{week} · всего {total}" if week else f"всего {total}"
        lines.append(f"{place}. {name} — {said}")
    if more:
        lines.append(f"и ещё {more} {_plural(more, 'человек', 'человека', 'человек')}")
    return lines


def bot_week(week: "rating.BotWeek") -> str:
    """The week so far and all time, every chat active in the week, and
    everyone with their week and their all time."""
    lines = [
        f"SUM · неделя с {week.since.day} {_MONTHS[week.since.month - 1]}",
        f"{_records(week.records)}, "
        f"{week.pages} {_plural(week.pages, 'страница', 'страницы', 'страниц')}"
        f" · всего {week.all_records}",
        # The verb first, so that it agrees with any number: "прислали 1".
        f"Люди: прислали {week.senders}, оценили {week.raters}"
        f" · всего {week.users}, новых {week.new_users}",
        # An отзыв is a rating and every comment (task 103): the week's of
        # each kind, then all the отзывы ever.
        f"Отзывы: {week.good} «Хорошо», {week.bad} «Плохо», {_comments(week.comments)}"
        f" · всего {week.all_ratings}",
        f"Расход: сегодня {_usd(week.spent_today)}, неделя {_usd(week.spent_week)}, "
        f"всего {_usd(week.spent_all)}",
    ]
    if week.groups or week.private:
        lines += ["", "Группы:"] + [_chat_week(chat) for chat in week.groups]
        if week.more_groups:
            lines.append(
                f"и ещё {week.more_groups} "
                f"{_plural(week.more_groups, 'группа', 'группы', 'групп')}"
            )
        lines += [_chat_week(chat) for chat in week.private]
    if week.people:
        lines += ["", "Люди:"] + _everyone(week.people, week.more_people)
    else:
        lines += ["", "Ещё ни конспектов, ни отзывов."]
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
        "PDF конспекта тоже приму — прочитаю каждую страницу, как фото. "
        "И .docx — его распознавать не нужно.",
        "",
        "Целую тетрадь можно прислать разом — фото или PDF, со словом "
        "«тетрадь» в подписи: разрежу её на лекции по датам и заголовкам. "
        "Одну в день.",
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
        "Пришлите фото, альбом страниц или PDF с тегом предмета в подписи, "
        "например #матан, — верну PDF сюда. Без тега не трогаю.",
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


# ── What a reader says of a record — app/bot/feedback.py ─────────────────────
# Two buttons under every document, and after either a question whose reply
# is the reader's comment — after «Плохо», their account of the error (task
# 70), after «Хорошо», what was good (task 103). Words, no emoji: the chat
# stays plain text. The question is asked of one person, by name in a group.

RATE_GOOD = "Хорошо"
RATE_BAD = "Плохо"
RATED_GOOD = "Спасибо! Если хочешь, напиши, что понравилось, — ответом на моё сообщение."
RATED_BAD = "Спасибо! Напиши, что не так, — ответом на моё сообщение."
# What the reply field shows before anything is typed; Telegram allows 64.
FEEDBACK_PLACEHOLDER = "Где ошибка и как должно быть"
PRAISE_PLACEHOLDER = "Что понравилось"
FEEDBACK_THANKS = "Спасибо, записал."


def feedback_question(title: str, rating: str) -> str:
    """After «Плохо», where the error is; after «Хорошо», what was good — a
    comment the reader may leave or not."""
    if rating == "good":
        return (
            f"Что понравилось в конспекте «{title}»? Ответь на это сообщение, "
            "если хочешь что-то добавить."
        )
    return (
        f"Что не так в конспекте «{title}»? Ответь на это сообщение: "
        "страница, строка или формула — и как должно быть. Можно скриншот."
    )


def feedback_where(group_title: str | None) -> str:
    return f"чат «{group_title}»" if group_title else "личный чат"


def feedback_report(
    note_id: int, title: str, rating: str, where: str, who: str
) -> str:
    """To FEEDBACK_CHAT_ID, over the document copied after it."""
    verdict = "плохо" if rating == "bad" else "хорошо"
    return f"Отзыв «{verdict}»: конспект #{note_id} «{title}», {where}, {who}."


def feedback_answer_report(
    note_id: int, title: str, rating: str, where: str, who: str
) -> str:
    """To FEEDBACK_CHAT_ID, over the reader's message copied after it: a
    comment, under the rating its reader holds now."""
    verdict = "плохо" if rating == "bad" else "хорошо"
    return f"Комментарий к «{verdict}»: конспект #{note_id} «{title}», {where}, {who}:"


# ── A lecture's study version — app/bot/corpus.py on_study (task 80) ────────
# A third button under every document. The study version is the record set
# out by topic: the author's text moved whole, the bot's boxes marked, three
# to five questions at the end and their answers on the last page.

STUDY_BUTTON = "Учебная версия"
STUDY_BUILDING = "Собираю учебную версию — около минуты."
STUDY_BUSY = "Учебная версия уже собирается."
STUDY_SENDING = "Отправляю учебную версию."
STUDY_FAILED = (
    "Не получилось собрать учебную версию этого конспекта. Сам конспект — выше."
)
STUDY_SUBTITLE = "Учебная версия · лекция по темам, собрана ботом из конспекта"
STUDY_LABELS = {
    "about": "О чём тема · от бота",
    "questions": "Проверь себя · от бота",
    "answers": "Ответы · от бота",
}
STUDY_NOTIONS = "Ключевые понятия"
STUDY_FILE_WORD = "uchebnaya"


def study_notions(notions: list[str]) -> str:
    """The key notions of a topic, the author's words, on one line."""
    return f"**{STUDY_NOTIONS}:** {', '.join(notions)}"


def study_caption(note_id: int, page_count: int, topics: int) -> str:
    """The line under the study version's file — what a chat gets for a
    record (task 80): the record's number and pages, as record_caption gives
    them, and what the file is."""
    return (
        f"{record_caption(note_id, page_count)} · учебная версия, {topics} "
        f"{_plural(topics, 'тема', 'темы', 'тем')}. Текст лекции — слова автора; "
        "всё, что добавил бот, — в рамках «от бота»."
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


def lecture_caption(caption: str, notebooks: int) -> str:
    """The line under a lecture's document: its base's, and how many
    notebooks it was drawn from (task 63)."""
    return f"{caption} · {notebooks} {_plural(notebooks, 'конспект', 'конспекта', 'конспектов')}"


# What may stand under a record's title: whose lecture, which day, which page —
# all that rule 8 of the prompt asks for. What the margin held on real pages
# was mostly not that: the notebook's own print ("DATE", "BRAUBERG®"), a
# doodle described, stray letters, once a whole "[схема: …]", and on record 59
# «фор · 21:27 (0, 1)». So the line is chosen here rather than trusted, and a
# record stored before the rule is drawn by it too.
_MARGIN_NAME_RE = re.compile(
    r"^(?:[А-ЯЁA-Z][а-яёa-z]+(?:-[А-ЯЁA-Z][а-яёa-z]+)?\s+[А-ЯЁA-Z]\.\s?(?:[А-ЯЁA-Z]\.)?"
    r"|[А-ЯЁA-Z]\.\s?(?:[А-ЯЁA-Z]\.\s?)?[А-ЯЁA-Z][а-яёa-z]+(?:-[А-ЯЁA-Z][а-яёa-z]+)?)$"
)
_MARGIN_DATE_RE = re.compile(
    rf"^(?:\d{{1,2}}[./]\d{{1,2}}(?:[./](?:\d{{4}}|\d{{2}}))?"
    rf"|\d{{1,2}}\s+(?:{'|'.join(_MONTHS)})(?:\s+\d{{4}})?)$",
    re.IGNORECASE,
)
_MARGIN_PAGE_RE = re.compile(r"^(?:(?:с|стр|л|лист)\.?\s*)?\d{1,3}$", re.IGNORECASE)
_MARGIN_SEPARATOR_RE = re.compile(r"\s*[·,;]\s*")


def _belongs_under_title(part: str) -> bool:
    return bool(
        _MARGIN_NAME_RE.match(part)
        or _MARGIN_DATE_RE.match(part)
        or _MARGIN_PAGE_RE.match(part)
    )


def byline(margin_notes: list[str]) -> str | None:
    """What stood in the margin that says whose lecture, which day or which
    page, as one line under the title, each once. None when nothing did —
    an empty line under a title is worse than none.

    A page's number only when one page gave one: record 90 printed «4 · 16
    · 17 · 8 · 2 · 19 · 2», a number from every page's margin, which says
    nothing of the record (task 86)."""
    parts: list[str] = []
    for note in margin_notes:
        for part in _MARGIN_SEPARATOR_RE.split(str(note).strip()):
            if part and part not in parts and _belongs_under_title(part):
                parts.append(part)
    pages = [part for part in parts if _MARGIN_PAGE_RE.match(part)]
    if len(pages) > 1:
        parts = [part for part in parts if part not in pages]
    return " · ".join(parts) if parts else None


# The head of every page of the document, and the signature at its foot —
# app/services/pdf.py, BRAND.md. The invitation is the guide's and may change
# with who it is for; the bot's name under it and the QR code never do.
PDF_PAGE_WORD = "стр."
PDF_INVITE = "Сделай такой конспект своей группе"


def pdf_date(day: date | datetime) -> str:
    """The record's day, in the head of every page: the day its lecture was
    given when it is filed into one (task 63), else the day it was made.
    Facts only: the grey line under the title that carried the date used to
    end in "нужна проверка" on a record the runs had disagreed about — a
    doubt about the reading that told nobody what to check."""
    return day.strftime("%d.%m.%Y")


def pdf_subject(tag: str | None) -> str:
    """The subject in the head of every page, written as the "#word" that
    finds the record again. Empty until the record is filed under one."""
    return f"#{tag}" if tag else ""
