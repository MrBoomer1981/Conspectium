"""What a #tag is, and where a record's topics come from.

Two kinds of tag, stored apart because they have different provenance. The
**subject** is the user's: the bot asks after saving a record and keeps the
answer on `Note.tag`. The **topics** are the bot's, read off the headings the
record already carries, and they live in their own table — the same rule this
project applies everywhere, that machine-written text never shares a field
with text a person wrote.

Nothing here calls the model. A heading was produced by the pipeline that read
the page, so a topic derived from it is a fact about the record rather than a
second opinion about it. That also means topics are only as good as the
headings: a stage that invents a section invents a topic with it, visibly, in
the reply the user gets straight away.
"""

from __future__ import annotations

import re
import unicodedata

# A topic long enough to be unrecognisable is not a handle to find anything
# by. The same 60 characters vision.py caps a title at.
TAG_LIMIT = 60

# Five topics a record, and they are the *main* five — see topics_of for what
# decides that. A page of notes can carry a dozen headings, and a record
# findable under a dozen words is a record whose words each find half the
# corpus.
TOPIC_LIMIT = 5

# Inline maths inside a heading — "Волновая ф-ция ($\Psi$)" — is stripped
# before anything else, or the tag comes back carrying "psi".
_MATH = re.compile(r"\$[^$]*\$")
_HEADING = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$")
# A caption carries its tag anywhere in it — "Лекция 5 #матан" — so the first
# "#word" is taken, and only the word. Not after a letter or another hash:
# "C#" and "##" are not tags.
_CAPTION_TAG = re.compile(r"(?<![\w#])#(\w+)")
# One "#word" and nothing else around it.
_BARE_TAG = re.compile(r"#\w+")
_GAPS = re.compile(r"[\s_]+")


def _in_hashtag(char: str) -> bool:
    """What Telegram counts in a hashtag: a letter, a decimal digit, the
    underscore. It ends one at anything else — «#ε-окрестность» was
    highlighted as «#ε» (task 106) — and «²», a number but no decimal digit,
    ends it too."""
    return char.isalpha() or char.isdecimal() or char == "_"


def normalize(text: str) -> str:
    """A heading, or whatever the user typed after the #, as a tag.

    Lower case, and only what Telegram highlights in a hashtag: everything
    else — a space, a hyphen, a dash, Markdown's own markers — is a gap, and
    gaps are one underscore. «Квантовая механика» has to survive as something
    typeable, and the bot's «#ф_ция» is a hashtag whole where «#ф-ция» was
    «#ф» (task 106, the CEO's). A mark NFC cannot join to its letter — a
    stress over «о» — is dropped rather than made a gap, which would cut the
    word in two.
    """
    lowered = unicodedata.normalize("NFC", _MATH.sub(" ", text).lower())
    kept = "".join(
        char if _in_hashtag(char) else " "
        for char in lowered
        if not unicodedata.category(char).startswith("M")
    )
    return _GAPS.sub("_", kept)[:TAG_LIMIT].strip("_")


def highlighted(tag: str) -> bool:
    """Whether Telegram makes "#tag" a hashtag: it needs a letter. «#1», a
    heading's number, is plain text, and finds every record numbered so."""
    return any(char.isalpha() for char in tag)


def parse(text: str | None) -> str | None:
    """The tag in a message that is one, `None` for a message that is not.

    The whole message has to start with "#": a sentence that happens to
    mention one is a sentence, and the bot has exactly one question it asks
    with a hash in it.
    """
    if not text:
        return None
    stripped = text.strip()
    if not stripped.startswith("#"):
        return None
    return normalize(stripped[1:]) or None


def from_caption(caption: str | None) -> str | None:
    """The subject a photo or a file was sent with: the first "#word" of its
    caption, `None` when it has none.

    A caption is not a message that has to be the tag and nothing else — it is
    where people write "Лекция 5 #матан" — so the word is looked for anywhere
    in it. In a group chat this is also what makes the bot take the photo at
    all.
    """
    if not caption:
        return None
    found = _CAPTION_TAG.search(caption)
    return (normalize(found.group(1)) or None) if found else None


def is_bare(text: str | None) -> bool:
    """Whether a message is one "#word" and nothing else.

    In a private chat every message is for the bot, so "#квантовая механика"
    is a search with a space in it. In a course chat people put hashtags into
    sentences — "#дз на завтра: §5" — and those are for each other: only a
    message that is a tag and nothing else is taken as a search there.
    """
    return bool(text) and _BARE_TAG.fullmatch(text.strip()) is not None


def _named(bot_username: str) -> re.Pattern[str]:
    # Telegram compares usernames without regard to case.
    return re.compile(rf"@{re.escape(bot_username)}\b", re.IGNORECASE)


def mentions(text: str | None, bot_username: str | None) -> bool:
    """Whether a message names the bot — "@konspekt_bot" — anywhere in it."""
    if not text or not bot_username:
        return False
    return _named(bot_username).search(text) is not None


def from_reply(text: str | None, bot_username: str | None = None) -> str | None:
    """The subject a reply in a group calls the bot with, `None` when it does
    not call it.

    One "#word" and nothing else, as for a search in a group — the bot's own
    name may stand beside it, since naming the bot is what calling it looks
    like. "#дз на завтра" under a photo is for the classmates, and so is "@вася
    #матан": another member's name makes it a message to that member.
    """
    if not text:
        return None
    if bot_username:
        text = _named(bot_username).sub(" ", text)
    return parse(text) if is_bare(text) else None


def topics_of(title: str, markdown: str) -> list[str]:
    """A record's five main topics: its title, then its headings.

    The title comes first because it is the one thing a record always has — a
    transcription made without the composing stage carries almost no headings,
    and a record with no topic at all could never be found again.

    The headings that follow are ordered by **level**, not by position on the
    page, and that is what makes the five "main" rather than "first". A page of
    notes has sections and subsections, and the subsections are where words
    like «Определение» and «Пример» live — rule 6 of the composing prompt asks
    for them by name, so nearly every record has one. Left in reading order,
    the five slots on a subsection-heavy page go to words every record carries,
    which match everything and therefore find nothing.
    """
    ranked: list[tuple[int, int, str]] = [(0, 0, title)]
    for position, found in enumerate(_HEADING.finditer(markdown), start=1):
        ranked.append((len(found.group(1)), position, found.group(2)))
    # Position breaks the tie, so headings of one level keep the order they
    # were written in. The title is level 0 and therefore always first.
    ranked.sort(key=lambda row: (row[0], row[1]))

    topics: list[str] = []
    for _, _, raw in ranked:
        topic = normalize(raw)
        # A topic is shown as a hashtag to tap and type, and one with no
        # letter is neither (task 106).
        if highlighted(topic) and topic not in topics:
            topics.append(topic)
        if len(topics) == TOPIC_LIMIT:
            break
    return topics
