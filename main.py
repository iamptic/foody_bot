import os, asyncio, json, requests
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram import types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")  # твой backend (Railway)
# WEBAPP_URL не обязателен: будем открывать verification_link, который вернет бэкенд

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN is not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

def get_demo_identity(user: types.User):
    # Детеминированные данные — для повторных /start у того же пользователя получим тот же email
    name = f"Ресторан {user.first_name or user.id}"
    email = f"rest_{user.id}@example.com"
    return name, email

def get_verification_link(name: str, email: str) -> str | None:
    """
    Просим у бэкенда ссылку верификации (уже содержит token и api).
    Бэкенд сам не дублирует пользователя: вернет 'Already registered' с той же ссылкой.
    """
    try:
        r = requests.post(
            f"{BACKEND_URL}/register_restaurant",
            params={"name": name, "email": email},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("verification_link")
        return None
    except Exception:
        return None

@dp.message(Command("start"))
async def start_cmd(m: Message):
    name, email = get_demo_identity(m.from_user)
    lk_url = get_verification_link(name, email)  # <-- тут тянем verification_link (с token + api)
    webapp_link = lk_url or "https://example.com"  # fallback, если бэк временно недоступен

    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть ЛК ресторана", web_app=WebAppInfo(url=webapp_link))],
        [InlineKeyboardButton(text="Регистрация (demo)", callback_data="reg_demo")]
    ])
    await m.answer(
        "🍽 Добро пожаловать в Foody!\nНажмите, чтобы открыть ЛК или зарегистрироваться.",
        reply_markup=ikb
    )

@dp.callback_query(F.data == "reg_demo")
async def cb_reg(call: types.CallbackQuery):
    name, email = get_demo_identity(call.from_user)
    try:
        r = requests.post(
            f"{BACKEND_URL}/register_restaurant",
            params={"name": name, "email": email},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            lk_url = data.get("verification_link")
            if lk_url:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Открыть ЛК ресторана", web_app=WebAppInfo(url=lk_url))]
                ])
                await call.message.answer(f"Ресторан зарегистрирован ✅\nID: {data['restaurant_id']}", reply_markup=kb)
            else:
                await call.message.answer("Ошибка: не получили verification_link")
        else:
            await call.message.answer(f"Ошибка регистрации: {r.text}")
    except Exception as e:
        await call.message.answer(f"Сервис недоступен: {e}")
    await call.answer()

@dp.message(F.web_app_data)
async def on_webapp_data(m: Message):
    # если позже будет отправка данных из WebApp через tg.WebApp.sendData
    payload = json.loads(m.web_app_data.data)
    await m.answer(f"Из ЛК получено: {payload}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
