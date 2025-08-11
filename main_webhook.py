# -*- coding: utf-8 -*-
"""
main_webhook.py — надёжный вход для aiogram v3 + FastAPI webhook.
Положи файл в КОРЕНЬ репозитория бота и запусти командой:
    python main_webhook.py
ENV:
  BOT_TOKEN           — токен бота (обязательно)
  BACKEND_PUBLIC      — публичный URL Railway (например, https://foodybot-production.up.railway.app)
  WEBAPP_MERCHANT_URL — https://foody-reg.vercel.app (опц. для /start)
  WEBAPP_BUYER_URL    — https://foody-buyer.vercel.app (опц. для /start)
  API_URL             — https://foodyback-production.up.railway.app (опц., подставляется в web-app кнопки)
"""
import os, sys, asyncio, json
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# --- ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN env is required")

BACKEND_PUBLIC = os.getenv("BACKEND_PUBLIC", "").rstrip("/")
WEBAPP_MERCHANT_URL = os.getenv("WEBAPP_MERCHANT_URL", "https://foody-reg.vercel.app")
WEBAPP_BUYER_URL = os.getenv("WEBAPP_BUYER_URL", "https://foody-buyer.vercel.app")
API_URL = os.getenv("API_URL", "https://foodyback-production.up.railway.app")

# --- Aiogram core ---
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(F.text.in_({"/start", "start"}))
async def cmd_start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        [InlineKeyboardButton(text="👨‍🍳 ЛК партнёра", web_app=WebAppInfo(url=f"{WEBAPP_MERCHANT_URL}/?api={API_URL}"))],
        [InlineKeyboardButton(text="🍽 Для покупателя", web_app=WebAppInfo(url=f"{WEBAPP_BUYER_URL}/?api={API_URL}"))],
        [InlineKeyboardButton(text="📄 Материалы", web_app=WebAppInfo(url=f"{WEBAPP_MERCHANT_URL}/docs/index.html"))],
    ]])
    await m.answer("Foody: спасаем еду вместе.\nКоманды: /offer /rules", reply_markup=kb)

# Встроенные обработчики /offer и /rules (на случай, если extras_commands отсутствует)
@dp.message(F.text == "/offer")
async def cmd_offer(m: Message):
    await m.answer("Материалы:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        [InlineKeyboardButton(text="📄 Оффер (SMB)", url=f"{WEBAPP_MERCHANT_URL}/docs/docs/Foody_Offer_Brand_ru.pdf")],
        [InlineKeyboardButton(text="🏬 Оффер для сетей", url=f"{WEBAPP_MERCHANT_URL}/docs/docs/Foody_Offer_Chain_ru.pdf")],
        [InlineKeyboardButton(text="📊 ROI-калькулятор", url=f"{WEBAPP_MERCHANT_URL}/docs/docs/ROI_%D0%A1%D0%BF%D0%B0%D1%81%D0%B5%D0%BD%D0%B8%D0%B5%D0%95%D0%B4%D1%8B_%D0%BA%D0%B0%D0%BB%D1%8C%D0%BA%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80.xlsx")]
    ]]))

@dp.message(F.text == "/rules")
async def cmd_rules(m: Message):
    await m.answer("Правила для ресторанов:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        [InlineKeyboardButton(text="📘 Открыть", web_app=WebAppInfo(url=f"{WEBAPP_MERCHANT_URL}/docs/rules.html"))]
    ]]))

# Пытаемся подключить внешние расширения, если они есть — это НЕ обязательно
try:
    from extras_commands import router as extras_router
    dp.include_router(extras_router)
except Exception as e:
    print("[main_webhook] extras_commands not loaded:", e)

# --- FastAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> Bot webhook app starting")
    yield
    print(">>> Bot webhook app stopped")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
    return {"ok": True, "file": __file__}

@app.post("/tg/webhook")
async def tg_webhook(request: Request):
    data = await request.json()
    try:
        update = Update.model_validate(data)
    except Exception as e:
        # Логи на случай несовпадения версии Telegram Update
        return JSONResponse({"ok": False, "error": f"bad update: {e}", "data": data}, status_code=400)
    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main_webhook:app", host="0.0.0.0", port=port)
