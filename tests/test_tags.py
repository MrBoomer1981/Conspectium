"""The tag vocabulary — app/bot/tags.py.

Pure functions, no database. What they decide is what a record can be found by
later, which makes them worth a test each: a topic that comes out unreadable
is a record that is in the corpus and out of reach.
"""

from app.bot import tags


# ── normalize ────────────────────────────────────────────────────────────────


def test_a_phrase_becomes_one_typeable_word():
    # The one thing a hashtag cannot contain is a space, and «Квантовая
    # механика» still has to survive as something a person can type.
    assert tags.normalize("Квантовая механика") == "квантовая_механика"


def test_case_is_flattened_so_one_subject_is_one_tag():
    # Otherwise a corpus grows «Физика» and «физика» as two subjects and can
    # never be searched again.
    assert tags.normalize("ФИЗИКА") == tags.normalize("Физика") == "физика"


def test_punctuation_is_dropped_rather_than_transliterated():
    assert tags.normalize("Модель атома Бора.") == "модель_атома_бора"
    assert tags.normalize("**Определение**") == "определение"


def test_maths_inside_a_heading_does_not_become_part_of_the_tag():
    # "Волновая ф-ция ($\\Psi$)" would otherwise come back carrying "psi".
    assert tags.normalize("Волновая ф-ция ($\\Psi$)") == "волновая_ф-ция"


def test_a_hyphen_survives_because_it_is_part_of_the_word():
    assert tags.normalize("ф-ция") == "ф-ция"


def test_a_tag_is_capped_at_a_length_that_can_still_be_typed():
    assert len(tags.normalize("слово " * 40)) <= tags.TAG_LIMIT


def test_a_cap_never_leaves_a_trailing_underscore():
    # The cut lands mid-gap on some inputs, and "#тема_" is a different tag
    # from "#тема" for every purpose this file has.
    assert not tags.normalize("слово " * 40).endswith("_")


def test_nothing_usable_comes_back_empty_rather_than_as_punctuation():
    assert tags.normalize("!!!") == ""
    assert tags.normalize("   ") == ""


# ── parse ────────────────────────────────────────────────────────────────────


def test_a_message_that_is_a_tag():
    assert tags.parse("#физика") == "физика"
    assert tags.parse("  #физика  ") == "физика"


def test_a_message_that_is_not_a_tag():
    # A sentence is a sentence. The bot asks exactly one question with a hash
    # in it, and everything else falls through to the handler that says so.
    assert tags.parse("физика") is None
    assert tags.parse("что ты умеешь") is None
    assert tags.parse("") is None
    assert tags.parse(None) is None


def test_a_hash_with_nothing_behind_it_is_not_a_tag():
    assert tags.parse("#") is None
    assert tags.parse("#!!!") is None


def test_a_tag_typed_with_a_space_still_works():
    """Telegram would not make one hashtag of it, but a person types it.

    Refusing here would mean answering the bot's own question with an error,
    so the phrase is normalized the same way a heading is.
    """
    assert tags.parse("#Квантовая механика") == "квантовая_механика"


# ── topics_of ────────────────────────────────────────────────────────────────


_RECORD = """# Квантовая механика

теория из древней Греции

## Модель атома Бора

### Определение

Волновая функция описывает состояние.

## Модель атома Бора
"""


def test_the_title_comes_first_and_every_heading_follows_in_order():
    assert tags.topics_of("Олимпиадные задачи", _RECORD) == [
        "олимпиадные_задачи",
        "квантовая_механика",
        "модель_атома_бора",
        "определение",
    ]


def test_a_heading_that_repeats_is_one_topic():
    # "## Модель атома Бора" appears twice in _RECORD above.
    assert tags.topics_of("x" * 3, _RECORD).count("модель_атома_бора") == 1


def test_a_record_with_no_headings_still_has_a_topic():
    """A transcription made without the composing stage is flat — that is what
    prompts-v5.md is for. A record with no topic at all could never be found
    again, so the title is always one."""
    assert tags.topics_of("Теорема Кантора", "просто текст без заголовков") == [
        "теорема_кантора"
    ]


def test_a_hash_that_is_not_a_heading_is_not_a_topic():
    # A heading needs its space: "#физика" written in the body is a tag the
    # user typed, not a section of the document.
    assert tags.topics_of("Заголовок", "см. #физика и #матан") == ["заголовок"]


def test_every_heading_level_counts():
    markdown = "# Раз\n## Два\n### Три\n###### Шесть\n"
    assert tags.topics_of("Ноль", markdown) == ["ноль", "раз", "два", "три", "шесть"]


def test_a_title_that_normalizes_to_nothing_is_skipped_not_stored_empty():
    assert tags.topics_of("!!!", "## Раздел") == ["раздел"]
