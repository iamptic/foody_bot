import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from extras_commands import router as extras_router
dp.include_router(extras_router)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_MERCHANT = os.getenv("WEBAPP_MERCHANT_URL", "https://foody-reg.vercel.app")
WEBAPP_BUYER = os.getenv("WEBAPP_BUYER_URL", "https://foody-buyer.vercel.app")
API_URL = os.getenv("BACKEND_URL", "https://foodyback-production.up.railway.app")

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN is not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

def buttons():
    kb = InlineKeyboardBuilder()
    kb.button(text="👨‍🍳 ЛК ресторана", web_app=WebAppInfo(url=f"{WEBAPP_MERCHANT}/?api={API_URL}"))
    kb.button(text="🍽 Экран покупателя", web_app=WebAppInfo(url=f"{WEBAPP_BUYER}/?api={API_URL}"))
    kb.adjust(1, 1)
    return kb.as_markup()

@dp.message(CommandStart())
async def start(m: Message):
    await m.answer(
        "Foody — вкусно, выгодно, всем!\nВыберите, чем хотите заняться:",
        reply_markup=buttons()
    )

@dp.message(Command("merchant"))
async def merchant(m: Message):
    await m.answer("Откройте ЛК ресторана:", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="👨‍🍳 ЛК ресторана", web_app=WebAppInfo(url=f"{WEBAPP_MERCHANT}/?api={API_URL}"))]]
    ))

@dp.message(Command("buyer"))
async def buyer(m: Message):
    await m.answer("Посмотреть предложения рядом:", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🍽 Экран покупателя", web_app=WebAppInfo(url=f"{WEBAPP_BUYER}/?api={API_URL}"))]]
    ))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
