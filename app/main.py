"""FastAPI application: Telegram webhook and health check."""

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, ErrorEvent, Message, Update
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import albums, corpus, texts
from app.bot.handlers import router
from app.bot.middlewares import DbSessionMiddleware
from app.core.config import settings
from app.core.events import log_event_standalone
from app.services import compose, pdf, vision
from app.db.models import User
from app.db.session import async_session_maker, get_session

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Created once per process, never inside a request handler.
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
dp.message.outer_middleware(DbSessionMiddleware())
# Order matters: handlers.router ends with a filterless catch-all that
# matches every message, so a router included after it gets nothing.
dp.include_router(corpus.router)
dp.include_router(router)

WEBHOOK_PATH = f"/webhook/{settings.WEBHOOK_SECRET}"

# Updates are processed after the response, so the tasks need an owner:
# asyncio keeps only a weak reference to a running task, and one that nothing
# else holds can be collected mid-flight.
_in_flight: set[asyncio.Task] = set()

# Not a limit, just a line in the log. Every in-flight update holds a DB
# session and a photo in memory, and the pool is 5 + 15.
_BUSY_WARNING_AT = 15


@dp.errors()
async def on_error(event: ErrorEvent) -> None:
    """Last line of defence: not a single traceback reaches the user. The main
    session is already rolling back by now, so note_failed goes through a
    standalone session — a regular log_event would roll back with it
    (PLAN.md -> Transaction model)."""
    exc = event.exception
    update = event.update
    logger.exception("Unhandled error while processing an update", exc_info=exc)

    chat_id = _chat_id(update)
    if chat_id is not None:
        try:
            await bot.send_message(chat_id, texts.ERROR_GENERIC)
        except Exception:
            logger.exception("could not deliver the error message to the user")

    tg_id = _tg_id(update)
    user_id = await _resolve_user_id(tg_id) if tg_id is not None else None
    await log_event_standalone(
        user_id,
        "note_failed",
        {"reason": type(exc).__name__, "where": _where(update)},
    )


def _incoming(update: Update) -> Message | None:
    return getattr(update, "message", None)


def _chat_id(update: Update) -> int | None:
    message = _incoming(update)
    return message.chat.id if message is not None else None


def _tg_id(update: Update) -> int | None:
    message = _incoming(update)
    if message is None or message.from_user is None:
        return None
    return message.from_user.id


def _where(update: Update) -> str:
    """Best-effort name of the handler that was running — ErrorEvent doesn't
    carry it, so it's inferred from the update."""
    message = _incoming(update)
    if message is None:
        return "unknown"
    if message.photo:
        return "handle_photo"
    if message.document:
        return "handle_document"
    if message.text and message.text.startswith("/start"):
        return "cmd_start"
    return "unknown"


async def _resolve_user_id(tg_id: int) -> int | None:
    """Our users.id for a Telegram id, or None. The error handler runs without
    the middleware's injected user, and a user created inside the failed
    transaction has just been rolled back."""
    try:
        async with async_session_maker() as session:
            return (
                await session.execute(select(User.id).where(User.tg_id == tg_id))
            ).scalar_one_or_none()
    except Exception:
        logger.exception("could not resolve the user for note_failed")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    url = f"{settings.WEBHOOK_URL}{WEBHOOK_PATH}"
    # A bot without a webhook is useless, so a failure here must stop startup.
    await bot.set_webhook(url, secret_token=settings.WEBHOOK_SECRET)
    logger.info("Webhook set")

    # The model that reads the photograph, and how many times. Every quality
    # finding in CLAUDE.md is attributed to a model, and this one has already
    # changed twice under this project, retiring a page of them — while the
    # startup log named the compose model and not this one. The run count is
    # on the same line because a page scored on two runs agrees more easily
    # than one scored on three, so an agreement without it is unattributable.
    logger.info(
        "Recognition: %s, %d runs", settings.VISION_MODEL, settings.VISION_RUNS
    )
    # Which prompt produced a record is only answerable from the logs, and
    # only if the deploy says which file it read and how long it was.
    logger.info(
        "Prompt: %s, %d words", settings.PROMPT_FILE, vision.PROMPT_WORDS
    )
    logger.info(
        "Images: %d px long side, quality %d",
        settings.IMAGE_MAX_SIDE,
        settings.IMAGE_QUALITY,
    )
    # Two of these three are computed, so the only way to know what the
    # process is actually running on is for it to say so.
    # Both default to "unset", meaning the field is not sent. The deploy has
    # to say which, or a record cannot be attributed to the call that made it.
    logger.info(
        "Compose: %s, %s, %s, %d words",
        "on" if settings.COMPOSE_ENABLED else "off",
        settings.COMPOSE_MODEL,
        settings.COMPOSE_PROMPT_FILE,
        compose.COMPOSE_PROMPT_WORDS,
    )
    logger.info(
        "Model call: media_resolution=%s, thinking_level=%s",
        settings.VISION_MEDIA_RESOLUTION,
        settings.VISION_THINKING_LEVEL,
    )
    logger.info(
        "Timeouts: call %ds, consensus %ds, album %ds",
        settings.VISION_CALL_TIMEOUT_S,
        vision._CONSENSUS_TIMEOUT_S,
        albums._ALBUM_TIMEOUT_S,
    )
    # Allowed by ALLOW_UNPRICED_MODEL; said out loud on every deploy so it
    # cannot become the state nobody remembers choosing. Both models, from the
    # same list the validator refuses on — this used to name VISION_MODEL
    # alone, so swapping COMPOSE_MODEL for an unpriced one started in silence.
    for name, model in settings.unpriced_models():
        logger.warning(
            "%s=%s has no price: its ai_calls rows carry cost_usd NULL, SUM "
            "skips them, and DAILY_COST_LIMIT_USD undercounts the day's spend",
            name,
            model,
        )

    # Unlike the webhook, this one must not stop startup: a bot without a
    # command menu still works, it is just harder to use.
    try:
        await bot.set_my_commands(
            [
                BotCommand(command=name, description=description)
                for name, description, _ in texts.COMMANDS
            ]
        )
        logger.info("Command menu published")
    except Exception:
        logger.exception("could not publish the command menu")

    # matplotlib builds a font cache on first use and reportlab registers its
    # fonts once — several seconds nobody should pay inside their first photo.
    # Off the startup path too: a slow warm-up must not delay serving.
    warm_up = asyncio.create_task(asyncio.to_thread(pdf.warm_up))

    yield

    warm_up.cancel()
    if _in_flight:
        # Shutdown wins: an album can run for minutes, far past any grace
        # period, so waiting is futile. Log the loss rather than hide it.
        logger.warning("dropping %d updates still in flight", len(_in_flight))
        for task in list(_in_flight):
            task.cancel()
    await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    # The bot idles for hours between photos; a health check that never touches
    # the database would stay green through a dead connection pool.
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("health check: database unreachable")
        raise HTTPException(status_code=503, detail="database unreachable")
    return {"status": "ok"}


@app.post("/webhook/{secret}")
async def telegram_webhook(
    secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    # Path and header are checked separately on purpose: the path segment is
    # visible in proxy logs, the header is what Telegram actually signs with.
    if secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403)
    if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403)

    update = Update.model_validate(await request.json(), context={"bot": bot})

    # Answer first, work afterwards. Telegram delivers the updates of one chat
    # strictly in sequence: it will not send the next one until this request
    # ends. Processing a photo takes ~9 s, so handling it inline meant the
    # other pages of an album could not arrive until the first was finished —
    # the album closed with one page and the rest were dropped as stragglers.
    # Updates from *different* chats are already delivered concurrently, so
    # this costs other users nothing and gains them nothing either.
    task = asyncio.create_task(_process(update))
    _in_flight.add(task)
    task.add_done_callback(_in_flight.discard)
    if len(_in_flight) >= _BUSY_WARNING_AT:
        logger.warning("%d updates in flight", len(_in_flight))
    return {"ok": True}


async def _process(update: Update) -> None:
    """Run an update outside the request. Nothing above this catches errors any
    more, so the last resort has to be here: aiogram's @dp.errors() handles
    what happens inside a handler, this covers everything around it."""
    try:
        await dp.feed_update(bot, update)
    except Exception:
        logger.exception("update %s failed outside the error handler", update.update_id)
