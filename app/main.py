"""FastAPI application: Telegram webhook and health check."""

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, ErrorEvent, Message, Update
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import corpus, texts
from app.bot.handlers import router
from app.bot.middlewares import DbSessionMiddleware
from app.core.config import settings
from app.core.events import log_event_standalone
from app.services import pdf
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
    await dp.feed_update(bot, update)
    return {"ok": True}
