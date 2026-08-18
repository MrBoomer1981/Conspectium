"""FastAPI application: Telegram webhook and health check."""

import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request

from app.bot.handlers import router
from app.core.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Created once per process, never inside a request handler.
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

WEBHOOK_PATH = f"/webhook/{settings.WEBHOOK_SECRET}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    url = f"{settings.WEBHOOK_URL}{WEBHOOK_PATH}"
    # A bot without a webhook is useless, so a failure here must stop startup.
    await bot.set_webhook(url, secret_token=settings.WEBHOOK_SECRET)
    logger.info("Webhook set")
    yield
    await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
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
