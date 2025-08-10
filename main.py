# Foody Bot (aiogram 3)
import os, asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN=os.getenv('BOT_TOKEN')
BACKEND_URL=os.getenv('BACKEND_URL','http://localhost:8000')
REG_WEBAPP_URL=os.getenv('REG_WEBAPP_URL','http://localhost:5173')
BUYER_WEBAPP_URL=os.getenv('BUYER_WEBAPP_URL','http://localhost:5174')
if not BOT_TOKEN: raise RuntimeError('❌ BOT_TOKEN is not set')

dp=Dispatcher()
bot=Bot(BOT_TOKEN, parse_mode='HTML')

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='👨‍🍳 ЛК ресторана', web_app=WebAppInfo(url=f"{REG_WEBAPP_URL}/index.html?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text='🍽 Экран покупателя', web_app=WebAppInfo(url=f"{BUYER_WEBAPP_URL}/index.html?api={BACKEND_URL}"))],
    ])

@dp.message(CommandStart())
async def start(m: Message):
    await m.answer("Добро пожаловать в <b>Foody</b>! Выберите раздел:", reply_markup=menu())

@dp.message(Command("merchant"))
async def merchant(m: Message):
    await m.answer("Раздел для ресторанов:", reply_markup=menu())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
