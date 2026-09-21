"""The webhook endpoint — app/main.py.

Telegram delivers the updates of one chat strictly in sequence: it will not
send the next until the current request ends. Processing a photo takes about
nine seconds, so handling an update inside the request meant the other pages
of an album could not arrive until the first had finished — the album closed
with a single page and the rest were dropped as stragglers. That is what these
tests exist to prevent from coming back.
"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.main as main
from app.core.config import settings

_UPDATE = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "date": 1700000000,
        "chat": {"id": 5, "type": "private"},
        "from": {"id": 5, "is_bot": False, "first_name": "Глеб"},
        "text": "привет",
    },
}


def _request(payload: dict | None = None):
    async def json():
        return payload or _UPDATE

    return SimpleNamespace(json=json)


async def _drain() -> None:
    """Let every background task settle, so one test cannot leak into another."""
    if main._in_flight:
        await asyncio.gather(*list(main._in_flight), return_exceptions=True)


@pytest.fixture(autouse=True)
async def clean():
    yield
    for task in list(main._in_flight):
        task.cancel()
    await _drain()
    main._in_flight.clear()


# ── the point of the whole endpoint ──────────────────────────────────────────


async def test_the_response_does_not_wait_for_processing(monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_feed(bot, update):
        started.set()
        await release.wait()

    monkeypatch.setattr(main.dp, "feed_update", slow_feed)

    result = await main.telegram_webhook(
        settings.WEBHOOK_SECRET, _request(), settings.WEBHOOK_SECRET
    )

    assert result == {"ok": True}
    # Processing has begun and is still running: Telegram is already free to
    # deliver the next page of the album.
    await asyncio.wait_for(started.wait(), timeout=2)
    assert any(not task.done() for task in main._in_flight)
    release.set()


async def test_the_update_really_does_get_processed(monkeypatch):
    seen: list[int] = []

    async def feed(bot, update):
        seen.append(update.update_id)

    monkeypatch.setattr(main.dp, "feed_update", feed)

    await main.telegram_webhook(
        settings.WEBHOOK_SECRET, _request(), settings.WEBHOOK_SECRET
    )
    await _drain()

    assert seen == [1]


async def test_a_running_task_is_held_onto(monkeypatch):
    # asyncio keeps only a weak reference to a task; one that nothing else
    # holds can be collected while it is still running.
    release = asyncio.Event()

    async def slow_feed(bot, update):
        await release.wait()

    monkeypatch.setattr(main.dp, "feed_update", slow_feed)

    await main.telegram_webhook(
        settings.WEBHOOK_SECRET, _request(), settings.WEBHOOK_SECRET
    )

    assert len(main._in_flight) == 1
    release.set()
    await _drain()
    # And released again once finished, so the set cannot grow for ever.
    assert main._in_flight == set()


async def test_a_failure_after_the_response_is_logged_not_lost(monkeypatch, caplog):
    # Nothing above _process catches anything any more.
    async def exploding_feed(bot, update):
        raise RuntimeError("что-то сломалось")

    monkeypatch.setattr(main.dp, "feed_update", exploding_feed)

    await main.telegram_webhook(
        settings.WEBHOOK_SECRET, _request(), settings.WEBHOOK_SECRET
    )
    await _drain()

    assert "failed outside the error handler" in caplog.text


async def test_several_updates_of_one_chat_run_at_the_same_time(monkeypatch):
    """The behaviour an album depends on: page two is not made to wait for
    page one."""
    release = asyncio.Event()
    running = 0

    async def slow_feed(bot, update):
        nonlocal running
        running += 1
        await release.wait()

    monkeypatch.setattr(main.dp, "feed_update", slow_feed)

    for update_id in (1, 2, 3, 4):
        payload = {**_UPDATE, "update_id": update_id}
        await main.telegram_webhook(
            settings.WEBHOOK_SECRET, _request(payload), settings.WEBHOOK_SECRET
        )
    await asyncio.sleep(0)  # let the tasks start

    assert running == 4
    release.set()
    await _drain()


# ── the secret is still checked, before anything is scheduled ────────────────


async def test_a_wrong_path_secret_is_refused(monkeypatch):
    monkeypatch.setattr(main.dp, "feed_update", lambda *a: 1 / 0)
    with pytest.raises(HTTPException):
        await main.telegram_webhook("не тот", _request(), settings.WEBHOOK_SECRET)
    assert main._in_flight == set()


async def test_a_wrong_header_secret_is_refused(monkeypatch):
    monkeypatch.setattr(main.dp, "feed_update", lambda *a: 1 / 0)
    with pytest.raises(HTTPException):
        await main.telegram_webhook(settings.WEBHOOK_SECRET, _request(), "не тот")
    assert main._in_flight == set()


async def test_a_missing_header_is_refused(monkeypatch):
    monkeypatch.setattr(main.dp, "feed_update", lambda *a: 1 / 0)
    with pytest.raises(HTTPException):
        await main.telegram_webhook(settings.WEBHOOK_SECRET, _request(), None)
    assert main._in_flight == set()
