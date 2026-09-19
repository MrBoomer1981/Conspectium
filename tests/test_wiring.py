"""How the application is assembled — app/main.py.

One invariant, and it is easy to break by moving two adjacent lines:
handlers.router ends with a filterless catch-all that matches every message,
so any router included after it receives nothing at all. Every corpus command
would silently start answering "send me a photo of a page".
"""

import app.main
from app.bot import corpus, handlers


def test_the_catch_all_matches_everything():
    # The premise of the ordering rule: no filters means no message gets past.
    last = handlers.router.message.handlers[-1]
    assert last.callback.__name__ == "handle_unsupported"
    assert not last.filters


def test_the_catch_all_is_the_last_handler_of_its_router():
    names = [h.callback.__name__ for h in handlers.router.message.handlers]
    assert names[-1] == "handle_unsupported"


def test_corpus_commands_are_registered_before_the_catch_all():
    routers = list(app.main.dp.sub_routers)
    assert corpus.router in routers and handlers.router in routers
    assert routers.index(corpus.router) < routers.index(handlers.router)


def test_every_corpus_command_is_reachable():
    registered = {h.callback.__name__ for h in corpus.router.message.handlers}
    assert registered == {
        "cmd_notes",
        "cmd_note",
        "cmd_search",
        "cmd_retitle",
        "cmd_delete",
        "cmd_stats",
        "cmd_help",
    }


# ── the command menu ─────────────────────────────────────────────────────────
# Week 2 shipped six commands that nothing told the user about. texts.COMMANDS
# is the single source for Telegram's menu and for /help, and these tests keep
# it from drifting away from what is actually registered.

import re  # noqa: E402

from aiogram.filters import Command  # noqa: E402

from app.bot import texts  # noqa: E402


def _registered_commands() -> set[str]:
    """Every command name the bot answers, across both routers. CommandStart
    is a Command subclass, so /start comes out of the same extraction."""
    found: set[str] = set()
    for router in (corpus.router, handlers.router):
        for handler in router.message.handlers:
            for f in handler.filters or []:
                if isinstance(f.callback, Command):
                    found.update(str(c) for c in f.callback.commands)
    return found


def _described_commands() -> set[str]:
    return {name for name, _, _ in texts.COMMANDS}


def test_every_command_the_bot_answers_has_a_description():
    # A command shipped without a description is invisible: no menu entry, no
    # autocompletion, no line in /help.
    assert _registered_commands() - _described_commands() == set()


def test_no_description_promises_a_command_that_does_not_exist():
    assert _described_commands() - _registered_commands() == set()


def test_help_lists_every_command():
    for name, _, _ in texts.COMMANDS:
        assert f"/{name}" in texts.HELP, name


def test_menu_entries_are_acceptable_to_telegram():
    for name, description, _ in texts.COMMANDS:
        assert re.fullmatch(r"[a-z0-9_]{1,32}", name), name
        assert 1 <= len(description) <= 256, name


def test_usage_examples_start_with_their_own_command():
    for name, _, usage in texts.COMMANDS:
        if usage is not None:
            assert usage.startswith(f"/{name} "), name


def test_start_points_at_help():
    # The greeting used to end at photographs, with six commands unmentioned.
    assert "/help" in texts.START
