"""Все строки, которые видит пользователь."""

import re
from datetime import date, datetime

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
# The teacher's boxes (task 56), each under a label that says what it is and
# whose: reasoning of the bot's, printed without a source.
ELEMENT_LABELS = {
    "idea": "Идея · от бота",
    "condition": "Зачем условие · от бота",
    "example": "Пример · от бота",
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
        + ["", "Отзыв — «Хорошо» или «Плохо» под конспектом."]
    )


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


# ── What a reader says of a record — app/bot/feedback.py ─────────────────────
# Two buttons under every document, and after «Плохо» a question whose reply
# is the reader's account of the error (task 70). Words, no emoji: the chat
# stays plain text. The question is asked of one person, by name in a group.

RATE_GOOD = "Хорошо"
RATE_BAD = "Плохо"
RATED_GOOD = "Спасибо!"
RATED_BAD = "Спасибо! Напиши, что не так, — ответом на моё сообщение."
# What the reply field shows before anything is typed; Telegram allows 64.
FEEDBACK_PLACEHOLDER = "Где ошибка и как должно быть"
FEEDBACK_THANKS = "Спасибо, записал."


def feedback_question(title: str) -> str:
    """After «Плохо»: where the error is."""
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


def feedback_answer_report(note_id: int, title: str, where: str, who: str) -> str:
    """To FEEDBACK_CHAT_ID, over the reader's message copied after it."""
    return f"Что не так — конспект #{note_id} «{title}», {where}, {who}:"


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
    page, as one line under the title. None when nothing did — an empty line
    under a title is worse than none."""
    parts = [
        part
        for note in margin_notes
        for part in _MARGIN_SEPARATOR_RE.split(str(note).strip())
        if part and _belongs_under_title(part)
    ]
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
