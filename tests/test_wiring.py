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
    }
