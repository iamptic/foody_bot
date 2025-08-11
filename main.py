# -*- coding: utf-8 -*-
# main.py — Foody bot (aiogram v3), safe include of extras router
import os, asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN is not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Base commands
@dp.message(F.text.in_({"/start","start"}))
async def start(m: Message):
    await m.answer("Foody: спасаем еду вместе.\nКоманды: /offer /rules")

# Optional extras (offer/rules)
try:
    from extras_commands import router as extras_router
    dp.include_router(extras_router)
except Exception as e:
    print("extras_commands not loaded:", e)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
