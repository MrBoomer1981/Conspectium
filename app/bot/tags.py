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
# Everything that is not a letter, a digit or a gap. Markdown's own markers go
# here too: "**Определение**" and "Определение" are one topic.
_PUNCTUATION = re.compile(r"[^\w\s-]", re.UNICODE)
_GAPS = re.compile(r"[\s_]+")


def normalize(text: str) -> str:
    """A heading, or whatever the user typed after the #, as a tag.

    Lower case, no punctuation, gaps joined by underscores — because a hashtag
    is the one thing that cannot contain a space, and «Квантовая механика» has
    to survive as something typeable.
    """
    cleaned = _PUNCTUATION.sub(" ", _MATH.sub(" ", text)).strip().lower()
    return _GAPS.sub("_", cleaned)[:TAG_LIMIT].strip("_")


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
        if topic and topic not in topics:
            topics.append(topic)
        if len(topics) == TOPIC_LIMIT:
            break
    return topics
