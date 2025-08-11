# -*- coding: utf-8 -*-
"""
bot_webhook_final_url.py — aiogram v3 + aiohttp (вебхук)
• Кнопки = обычные URL, без web_app (не требует /setdomain в BotFather)
• Всегда 200 OK на вебхук, health/debug
Запуск: python bot_webhook_final_url.py
"""
import os, asyncio, json, logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update, BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("foody_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN env is required")

BACKEND_PUBLIC = os.getenv("BACKEND_PUBLIC", "").rstrip("/")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/tg/webhook")
WEBHOOK_URL = f"{BACKEND_PUBLIC}{WEBHOOK_PATH}" if BACKEND_PUBLIC else ""

WEBAPP_MERCHANT_URL = os.getenv("WEBAPP_MERCHANT_URL", "https://foody-reg.vercel.app")
WEBAPP_BUYER_URL = os.getenv("WEBAPP_BUYER_URL", "https://foody-buyer.vercel.app")
API_URL = os.getenv("API_URL", "https://foodyback-production.up.railway.app")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(F.text.in_({"/start","start"}))
async def start(m: Message):
    log.info("start-handler fired for chat %s", m.chat.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="👨‍🍳 ЛК партнёра", url=f"{WEBAPP_MERCHANT_URL}/?api={API_URL}")
    kb.button(text="🍽 Для покупателя", url=f"{WEBAPP_BUYER_URL}/?api={API_URL}")
    kb.button(text="📄 Материалы", url=f"{WEBAPP_MERCHANT_URL}/docs/index.html")
    kb.adjust(1)
    await m.answer("Foody: спасаем еду вместе.\nКоманды: /offer /rules", reply_markup=kb.as_markup())

@dp.message(F.text == "/offer")
async def offer(m: Message):
    log.info("/offer handler for chat %s", m.chat.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 Оффер (SMB)", url=f"{WEBAPP_MERCHANT_URL}/docs/docs/Foody_Offer_Brand_ru.pdf")
    kb.button(text="🏬 Оффер для сетей", url=f"{WEBAPP_MERCHANT_URL}/docs/docs/Foody_Offer_Chain_ru.pdf")
    kb.button(text="📊 ROI-калькулятор", url=f"{WEBAPP_MERCHANT_URL}/docs/docs/ROI_%D0%A1%D0%BF%D0%B0%D1%81%D0%B5%D0%BD%D0%98%D0%B5%D0%95%D0%B4%D1%8B_%D0%BA%D0%B0%D0%BB%D1%8C%D0%BA%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80.xlsx")
    kb.adjust(1)
    await m.answer("Материалы:", reply_markup=kb.as_markup())

@dp.message(F.text == "/rules")
async def rules(m: Message):
    log.info("/rules handler for chat %s", m.chat.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="📘 Открыть правила", url=f"{WEBAPP_MERCHANT_URL}/docs/rules.html")
    await m.answer("Правила для ресторанов:", reply_markup=kb.as_markup())

async def _process_update(data: dict):
    try:
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        log.exception("update processing failed: %s", e)

async def webhook_post(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    try:
        log.info("update: %s", json.dumps(data)[:800])
    except Exception:
        pass
    asyncio.create_task(_process_update(data))
    return web.Response(text="OK")

async def webhook_get(request: web.Request):
    return web.Response(text="OK")

async def health(request: web.Request):
    return web.json_response({"ok": True, "webhook": WEBHOOK_URL or None})

async def dbg(request: web.Request):
    info = await bot.get_webhook_info()
    return web.json_response(info.model_dump())

async def on_startup(app: web.Application):
    if WEBHOOK_URL:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(url=WEBHOOK_URL)
        log.info("Webhook set to %s", WEBHOOK_URL)
    else:
        log.warning("BACKEND_PUBLIC not set — webhook not configured")
    await bot.set_my_commands([
        BotCommand(command="start", description="Старт"),
        BotCommand(command="offer", description="Материалы (PDF/XLSX)"),
        BotCommand(command="rules", description="Правила для ресторанов"),
    ])

def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="OK"))
    app.router.add_get("/health", health)
    app.router.add_get("/debug/webhookinfo", dbg)
    app.router.add_post(WEBHOOK_PATH, webhook_post)
    app.router.add_get(WEBHOOK_PATH, webhook_get)
    app.on_startup.append(on_startup)
    return app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    web.run_app(make_app(), host="0.0.0.0", port=port)
