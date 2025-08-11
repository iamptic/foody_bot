# -*- coding: utf-8 -*-
# bot/main_webhook.py — запуск aiogram через FastAPI webhook + встроенный uvicorn
import os, asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "https://foodyback-production.up.railway.app")
WEBAPP_MERCHANT_URL = os.getenv("WEBAPP_MERCHANT_URL", "https://foody-reg.vercel.app")
WEBAPP_BUYER_URL = os.getenv("WEBAPP_BUYER_URL", "https://foody-buyer.vercel.app")

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN is not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Base commands
@dp.message(F.text.in_({"/start","start"}))
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        [InlineKeyboardButton(text="👨‍🍳 ЛК партнёра", web_app=WebAppInfo(url=f"{WEBAPP_MERCHANT_URL}/?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="🍽 Для покупателя", web_app=WebAppInfo(url=f"{WEBAPP_BUYER_URL}/?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="📄 Материалы", web_app=WebAppInfo(url=f"{WEBAPP_MERCHANT_URL}/docs/index.html"))],
    ]])
    await m.answer("Foody: спасаем еду вместе. Выберите действие:", reply_markup=kb)

try:
    # опционально подключим доп. команды, если файл есть
    from extras_commands import router as extras_router
    dp.include_router(extras_router)
except Exception:
    pass

@asynccontextmanager
async def lifespan(_: FastAPI):
    # тут можно поставить вебхук, если нужно при старте
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/tg/webhook")
async def tg_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn, os
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main_webhook:app", host="0.0.0.0", port=port)
