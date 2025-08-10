import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
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

class LinkFSM(StatesGroup):
    waiting_restaurant_id = State()

def buyer_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🍽 Открыть предложения рядом",
            web_app=WebAppInfo(url=f"{BUYER_WEBAPP_URL}/index.html?api={BACKEND_URL}")
        )
    ]])

def restaurant_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👨‍🍳 Открыть ЛК ресторана",
                web_app=WebAppInfo(url=f"{REG_WEBAPP_URL}/index.html?api={BACKEND_URL}")
            )
        ],
        [InlineKeyboardButton(text="🧾 Зарегистрировать ресторан (1 шаг)", callback_data="reg_start")],
        [InlineKeyboardButton(text="✏️ Заполнить профиль", web_app=WebAppInfo(url=f"{REG_WEBAPP_URL}/onboarding.html?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="🔗 Привязать этот Telegram к ЛК", callback_data="link_tg")],
        [
            InlineKeyboardButton(
                text="🍽 Перейти к экрану покупателя",
                web_app=WebAppInfo(url=f"{BUYER_WEBAPP_URL}/index.html?api={BACKEND_URL}")
            )
        ],
    ])

@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    kb = buyer_menu()
    intro = "Добро пожаловать в <b>Foody</b>!\nЗдесь вы можете смотреть горячие предложения рядом."
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{BACKEND_URL}/whoami", params={"telegram_id": m.from_user.id})
        if r.status_code == 200:
            data = r.json()
            kb = restaurant_menu()
            intro = f"Здравствуйте, <b>{data.get('restaurant_name','ресторан')}</b>!\nОткройте ЛК, управляйте предложениями, привязка активна."
    except Exception:
        pass
    await m.answer(intro, reply_markup=kb)

@dp.message(Command("merchant"))
async def merchant(m: Message):
    await m.answer("Раздел для ресторанов:", reply_markup=restaurant_menu())

@dp.callback_query(F.data == "reg_start")
async def reg_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите <b>название ресторана</b> (до 120 символов):")
    await state.set_state(Reg.waiting_name)
    await cb.answer()

@dp.message(Reg.waiting_name)
async def reg_name(m: Message, state: FSMContext):
    name = (m.text or "").strip()
    if not name:
        return await m.answer("Название не распознано. Попробуйте ещё раз.")
    await m.answer("Создаём аккаунт…")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{BACKEND_URL}/register_telegram",
                                  json={"name": name[:120], "telegram_id": str(m.from_user.id)})
            r.raise_for_status()
            data = r.json()
        await m.answer(
            f"✅ Готово! Ресторан «{data['restaurant_name']}» (id {data['restaurant_id']}) создан и привязан.\n"
            f"Откройте ЛК и заполните профиль: /merchant → «✏️ Заполнить профиль»."
        )
    except Exception as e:
        await m.answer(f"Ошибка регистрации: {e}")
    await state.clear()

@dp.callback_query(F.data == "link_tg")
async def link_tg(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите <b>ID ресторана</b>:")
    await state.set_state(LinkFSM.waiting_restaurant_id)
    await cb.answer()

@dp.message(LinkFSM.waiting_restaurant_id)
async def do_link(m: Message, state: FSMContext):
    rid_raw = (m.text or "").strip()
    if not rid_raw.isdigit():
        return await m.answer("Нужен числовой ID.")
    rid = int(rid_raw)
    tg_id = str(m.from_user.id)
    await m.answer("Привязываем…")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{BACKEND_URL}/link_telegram", json={"telegram_id": tg_id, "restaurant_id": rid})
            resp = r.json()
        if r.status_code == 200:
            await m.answer(f"✅ Готово. Привязано к «{resp.get('restaurant_name','')}» (id {resp.get('restaurant_id')}).\nОткройте /merchant для ЛК.")
        else:
            await m.answer(f"Не удалось привязать: {resp}")
    except Exception as e:
        await m.answer(f"Ошибка: {e}")
    await state.clear()

@dp.message(Command("menu"))
async def menu(m: Message):
    await m.answer("Меню:", reply_markup=buyer_menu())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
