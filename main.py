import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import httpx

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
REG_WEBAPP_URL = os.getenv("REG_WEBAPP_URL", "http://localhost:5173")
BUYER_WEBAPP_URL = os.getenv("BUYER_WEBAPP_URL", "http://localhost:5174")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is not set")

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(BOT_TOKEN, parse_mode="HTML")

class Reg(StatesGroup):
    waiting_name = State()
    waiting_email = State()

def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🍽 Открыть предложения рядом", url=f"{BUYER_WEBAPP_URL}/index.html?api={BACKEND_URL}"),
    ],[
        InlineKeyboardButton(text="👨‍🍳 Открыть ЛК ресторана (есть аккаунт)", url=f"{REG_WEBAPP_URL}/index.html?api={BACKEND_URL}")
    ],[
        InlineKeyboardButton(text="🧾 Регистрация ресторана", callback_data="reg_start")
    ]])
    return kb

@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Добро пожаловать в <b>Foody</b>!\n"
        "— Покупателю: смотрите горячие предложения рядом.\n"
        "— Ресторану: зарегистрируйтесь и управляйте остатками.\n\n"
        "Выберите действие:",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "reg_start")
async def reg_start(cb, state: FSMContext):
    await cb.message.answer("Введите <b>название ресторана</b>:")
    await state.set_state(Reg.waiting_name)
    await cb.answer()

@dp.message(Reg.waiting_name)
async def reg_name(m: Message, state: FSMContext):
    name = (m.text or "").strip()
    if not name:
        return await m.answer("Название не распознано. Попробуйте ещё раз.")
    await state.update_data(name=name)
    await state.set_state(Reg.waiting_email)
    await m.answer("Отлично. Теперь укажите <b>email</b> для активации:")

@dp.message(Reg.waiting_email)
async def reg_email(m: Message, state: FSMContext):
    email = (m.text or "").strip()
    if "@" not in email or "." not in email:
        return await m.answer("Похоже не email. Введите корректный адрес.")
    data = await state.get_data()
    name = data["name"]
    await m.answer("Регистрируем…")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{BACKEND_URL}/register_restaurant", params={"name": name, "email": email})
            r.raise_for_status()
            resp = r.json()
        link = resp.get("verification_link")
        rid = resp.get("restaurant_id")
        if link:
            await m.answer(
                f"✅ Готово!\nАктивируйте аккаунт по ссылке ниже, затем попадёте в ЛК:\n{link}\n\n"
                f"ID ресторана: <code>{rid}</code>"
            )
        else:
            await m.answer(f"Что-то пошло не так: {resp}")
    except Exception as e:
        await m.answer(f"Ошибка регистрации: {e}")
    await state.clear()

@dp.message(Command("menu"))
async def menu(m: Message):
    await m.answer("Главное меню:", reply_markup=main_menu())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
