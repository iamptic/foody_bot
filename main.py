import os, asyncio, json, requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN is not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

def demo_identity(user: types.User):
    name = f"Ресторан {user.first_name or user.id}"
    email = f"rest_{user.id}@example.com"
    return name, email

def fetch_verification_link(name: str, email: str) -> str | None:
    try:
        r = requests.post(
            f"{BACKEND_URL}/register_restaurant",
            params={"name": name, "email": email},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            return data.get("verification_link")
        return None
    except Exception:
        return None

@dp.message(Command("start"))
async def start_cmd(m: Message):
    name, email = demo_identity(m.from_user)
    lk_url = fetch_verification_link(name, email)

    if not lk_url:
        await m.answer(
            "Не удалось получить ссылку для входа в ЛК 🤖\n"
            "Проверьте, что BACKEND_URL у бота указывает на рабочий API и backend возвращает verification_link."
        )
        return

    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть ЛК ресторана", web_app=WebAppInfo(url=lk_url))],
        [InlineKeyboardButton(text="Регистрация (demo)", callback_data="reg_demo")]
    ])
    await m.answer("Добро пожаловать! Нажмите, чтобы открыть ЛК или зарегистрироваться.", reply_markup=ikb)

@dp.callback_query(F.data == "reg_demo")
async def cb_reg(call: types.CallbackQuery):
    name, email = demo_identity(call.from_user)
    lk_url = fetch_verification_link(name, email)

    if not lk_url:
        await call.message.answer("Ошибка: backend не вернул verification_link. Проверьте BACKEND_URL и переменные бэкенда.")
        await call.answer()
        return

    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть ЛК ресторана", web_app=WebAppInfo(url=lk_url))]
    ])
    await call.message.answer("Ресторан зарегистрирован ✅\nОткройте ЛК:", reply_markup=ikb)
    await call.answer()

@dp.message(F.web_app_data)
async def on_webapp_data(m: Message):
    payload = json.loads(m.web_app_data.data)
    await m.answer(f"Из ЛК получено: {payload}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
