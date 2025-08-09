import os, asyncio, json, requests
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN is not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(m: Message):
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть ЛК ресторана", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="Регистрация (demo)", callback_data="reg_demo")]
    ])
    await m.answer("Добро пожаловать! Нажмите, чтобы открыть ЛК или зарегистрироваться.", reply_markup=ikb)

@dp.callback_query(F.data == "reg_demo")
async def cb_reg(call: CallbackQuery):
    name = f"Ресторан {call.from_user.first_name or call.from_user.id}"
    email = f"rest_{call.from_user.id}@example.com"
    try:
        r = requests.post(f"{BACKEND_URL}/register_restaurant", params={"name": name, "email": email}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            await call.message.answer(f"Ресторан зарегистрирован ✅\nСсылка для активации: {data['verification_link']}\nID: {data['restaurant_id']}")
        else:
            await call.message.answer(f"Ошибка регистрации: {r.text}")
    except Exception as e:
        await call.message.answer(f"Сервис недоступен: {e}")
    await call.answer()

@dp.message(F.web_app_data)
async def on_webapp_data(m: Message):
    payload = json.loads(m.web_app_data.data)
    await m.answer(f"Из ЛК получено: {payload}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
