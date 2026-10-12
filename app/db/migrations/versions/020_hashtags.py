"""tags written as Telegram highlights them

Revision ID: 020_hashtags
Revises: 019_note_study
Create Date: 2026-10-12

Task 106, the CEO's of 2026-10-12: «пиши темы конспекта в сообщении в ТГ без
тире, а только с нижними подчеркиваниями, иначе тг не выделяет их как #».
Telegram ends a hashtag at the first character that is not a letter, a
decimal digit or an underscore, and makes none of a word without a letter:
the bot wrote «#ε-окрестность», and Telegram highlighted «#ε». From now on
tags.normalize keeps only what a hashtag holds, every other character a gap
and gaps one underscore. This writes what is stored the same way, so that a
"#word" typed either way finds what it found before, and the chat is shown
the word it can tap.

note_topics.topic: the bot's, read off a record's headings — rewritten; a
    topic left with no letter goes, as tags.topics_of leaves one out now,
    and so does a record's topic that two of its rows have become.
subjects.word, notes.tag: the chat's "#word" — rewritten. Two subjects of
    one chat that become one word become one subject: the one already
    written so keeps its row, else the oldest, and the other's lectures and
    records move to it. A word with nothing left of it keeps itself.

The rule is copied here rather than imported from app.bot.tags: a migration
has to do tomorrow what it does today. What it changes is decided by
`plan`, apart from the writing, so that it can be read against a database
without writing to it.

Nothing to undo: a gap does not say whether it was a hyphen.
"""

import re
import unicodedata
from dataclasses import dataclass, field

import sqlalchemy as sa
from alembic import op

revision = "020_hashtags"
down_revision = "019_note_study"
branch_labels = None
depends_on = None

_GAPS = re.compile(r"[\s_]+")
_TAG_LIMIT = 60


def tag(word: str) -> str:
    """A stored tag as tags.normalize writes one from 2026-10-12. What is
    stored carries no formula, so the formulas' stripping is not copied."""
    lowered = unicodedata.normalize("NFC", word.lower())
    kept = "".join(
        char if char.isalpha() or char.isdecimal() or char == "_" else " "
        for char in lowered
        if not unicodedata.category(char).startswith("M")
    )
    return _GAPS.sub("_", kept)[:_TAG_LIMIT].strip("_")


def _highlighted(word: str) -> bool:
    return any(char.isalpha() for char in word)


@dataclass
class Plan:
    topic_words: dict[int, str] = field(default_factory=dict)
    topics_gone: list[int] = field(default_factory=list)
    subject_words: dict[int, str] = field(default_factory=dict)
    # A subject merged into another: its id, the keeper's.
    subjects_merged: dict[int, int] = field(default_factory=dict)
    tag_words: dict[str, str] = field(default_factory=dict)


def plan(topics, subjects, tags) -> Plan:
    """What upgrade() writes, from what it reads: `topics` as (id, note_id,
    topic) in id order, `subjects` as (id, group_id, user_id, word), `tags`
    the distinct notes.tag."""
    changes = Plan()

    kept: set[tuple[int, str]] = set()
    for topic_id, note_id, topic in topics:
        word = tag(topic)
        if not _highlighted(word) or (note_id, word) in kept:
            changes.topics_gone.append(topic_id)
            continue
        kept.add((note_id, word))
        if word != topic:
            changes.topic_words[topic_id] = word

    # One word is one subject in a chat: a group's, else its user's private
    # chat's, as the two unique indexes say.
    becoming: dict[tuple, list[tuple[int, str]]] = {}
    for subject_id, group_id, user_id, word in subjects:
        owner = ("group", group_id) if group_id is not None else ("user", user_id)
        becoming.setdefault((owner, tag(word) or word), []).append((subject_id, word))
    for (_, word), members in becoming.items():
        keeper = next(
            (subject_id for subject_id, old in members if old == word),
            min(subject_id for subject_id, _ in members),
        )
        for subject_id, old in members:
            if subject_id != keeper:
                changes.subjects_merged[subject_id] = keeper
            elif old != word:
                changes.subject_words[subject_id] = word

    for old in tags:
        word = tag(old) or old
        if word != old:
            changes.tag_words[old] = word
    return changes


def _each(bind, statement: str, rows: list[dict]) -> None:
    if rows:
        bind.execute(sa.text(statement), rows)


def upgrade() -> None:
    bind = op.get_bind()
    changes = plan(
        bind.execute(sa.text("SELECT id, note_id, topic FROM note_topics ORDER BY id")).all(),
        bind.execute(
            sa.text("SELECT id, group_id, user_id, word FROM subjects ORDER BY id")
        ).all(),
        bind.execute(
            sa.text("SELECT DISTINCT tag FROM notes WHERE tag IS NOT NULL")
        ).scalars().all(),
    )

    _each(
        bind,
        "DELETE FROM note_topics WHERE id = :id",
        [{"id": topic_id} for topic_id in changes.topics_gone],
    )
    _each(
        bind,
        "UPDATE note_topics SET topic = :word WHERE id = :id",
        [{"id": topic_id, "word": word} for topic_id, word in changes.topic_words.items()],
    )
    # The merged go before a keeper is renamed: a keeper's new word is no
    # other subject's then, and the unique index never sees two.
    merged = [
        {"merged": subject_id, "keeper": keeper}
        for subject_id, keeper in changes.subjects_merged.items()
    ]
    _each(bind, "UPDATE lectures SET subject_id = :keeper WHERE subject_id = :merged", merged)
    _each(bind, "UPDATE notes SET subject_id = :keeper WHERE subject_id = :merged", merged)
    _each(
        bind,
        "DELETE FROM subjects WHERE id = :merged",
        [{"merged": row["merged"]} for row in merged],
    )
    _each(
        bind,
        "UPDATE subjects SET word = :word WHERE id = :id",
        [{"id": subject_id, "word": word} for subject_id, word in changes.subject_words.items()],
    )
    _each(
        bind,
        "UPDATE notes SET tag = :word WHERE tag = :old",
        [{"old": old, "word": word} for old, word in changes.tag_words.items()],
    )


def downgrade() -> None:
    pass
