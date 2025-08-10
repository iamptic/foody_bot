import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo,
)
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
    waiting_address = State()

class LinkFSM(StatesGroup):
    waiting_restaurant_id = State()

class SubFSM(StatesGroup):
    choosing_type = State()
    waiting_category = State()
    waiting_restaurant = State()

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Открыть предложения рядом", web_app=WebAppInfo(url=f"{BUYER_WEBAPP_URL}/index.html?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="👨‍🍳 Открыть ЛК ресторана", web_app=WebAppInfo(url=f"{REG_WEBAPP_URL}/index.html?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="🧾 Регистрация ресторана", callback_data="reg_start")],
        [InlineKeyboardButton(text="🔗 Привязать этот Telegram к ЛК", callback_data="link_tg")],
        [InlineKeyboardButton(text="🔔 Подписаться на уведомления", callback_data="sub_menu")],
        [InlineKeyboardButton(text="🔕 Отписаться", callback_data="unsub_all")],
    ])

@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Добро пожаловать в <b>Foody</b>!\n"
        "— Покупателю: смотрите горячие предложения рядом (Mini App).\n"
        "— Ресторану: зарегистрируйтесь/войдите (Mini App).\n"
        "— Уведомления: подпишитесь по категории или ресторану.\n\n"
        "Выберите действие:",
        reply_markup=main_menu()
    )

# Registration (name -> address)
@dp.callback_query(F.data == "reg_start")
async def reg_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите <b>название ресторана</b>:")
    await state.set_state(Reg.waiting_name)
    await cb.answer()

@dp.message(Reg.waiting_name)
async def reg_name(m: Message, state: FSMContext):
    name = (m.text or "").strip()
    if not name:
        return await m.answer("Название не распознано. Попробуйте ещё раз.")
    await state.update_data(name=name)
    await state.set_state(Reg.waiting_address)
    await m.answer("Теперь укажите <b>адрес ресторана</b> (улица, дом; можно с ориентиром):")

@dp.message(Reg.waiting_address)
async def reg_address(m: Message, state: FSMContext):
    address = (m.text or "").strip()
    if not address:
        return await m.answer("Адрес пустой. Введите адрес ещё раз.")
    data = await state.get_data()
    name = data["name"]
    await m.answer("Регистрируем…")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{BACKEND_URL}/register_restaurant", params={"name": name, "address": address})
            r.raise_for_status()
            resp = r.json()
        link = resp.get("verification_link")
        rid = resp.get("restaurant_id")
        if link:
            await m.answer(f"✅ Готово!\nАктивируйте аккаунт по ссылке:\n{link}\n\nID: <code>{rid}</code>\n{name}\n{address}")
        else:
            await m.answer(f"Что-то пошло не так: {resp}")
    except Exception as e:
        await m.answer(f"Ошибка регистрации: {e}")
    await state.clear()

# Link Telegram
@dp.callback_query(F.data == "link_tg")
async def link_tg(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите <b>ID ресторана</b> (после активации):")
    await state.set_state(LinkFSM.waiting_restaurant_id)
    await cb.answer()

@dp.message(LinkFSM.waiting_restaurant_id)
async def do_link(m: Message, state: FSMContext):
    rid_raw = (m.text or "").strip()
    if not rid_raw.isdigit():
        return await m.answer("Нужен числовой ID. Введите только цифры.")
    rid = int(rid_raw)
    tg_id = str(m.from_user.id)
    await m.answer("Привязываем…")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{BACKEND_URL}/link_telegram", json={"telegram_id": tg_id, "restaurant_id": rid})
            resp = r.json()
        if r.status_code == 200:
            await m.answer(f"✅ Привязано к «{resp.get('restaurant_name','')}» (id {resp.get('restaurant_id')}).")
        else:
            await m.answer(f"Не удалось привязать: {resp}")
    except Exception as e:
        await m.answer(f"Ошибка: {e}")
    await state.clear()

# Subscribe menu
@dp.callback_query(F.data == "sub_menu")
async def sub_menu(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Категория", callback_data="sub_cat")],
        [InlineKeyboardButton(text="Ресторан", callback_data="sub_rest")],
        [InlineKeyboardButton(text="Все предложения", callback_data="sub_all")]
    ])
    await cb.message.answer("На что подписаться?", reply_markup=kb)
    await state.set_state(SubFSM.choosing_type)
    await cb.answer()

@dp.callback_query(SubFSM.choosing_type, F.data == "sub_cat")
async def sub_cat(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите название категории (например: Выпечка, Супы, Десерты):")
    await state.set_state(SubFSM.waiting_category)
    await cb.answer()

@dp.message(SubFSM.waiting_category)
async def do_sub_cat(m: Message, state: FSMContext):
    category = (m.text or "").strip()
    if not category:
        return await m.answer("Категория пустая. Введите снова:")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{BACKEND_URL}/subscribe", json={"chat_id": str(m.chat.id), "category": category})
            r.raise_for_status()
        await m.answer(f"✅ Подписка по категории «{category}» оформлена.
Будем присылать новые предложения.")
    except Exception as e:
        await m.answer(f"Ошибка: {e}")
    await state.clear()

@dp.callback_query(SubFSM.choosing_type, F.data == "sub_rest")
async def sub_rest(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите точное название ресторана (как в ЛК):")
    await state.set_state(SubFSM.waiting_restaurant)
    await cb.answer()

@dp.message(SubFSM.waiting_restaurant)
async def do_sub_rest(m: Message, state: FSMContext):
    rest = (m.text or "").strip()
    if not rest:
        return await m.answer("Название пустое. Введите снова:")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{BACKEND_URL}/subscribe", json={"chat_id": str(m.chat.id), "restaurant_name": rest})
            r.raise_for_status()
        await m.answer(f"✅ Подписка на ресторан «{rest}» оформлена.")
    except Exception as e:
        await m.answer(f"Ошибка: {e}")
    await state.clear()

@dp.callback_query(F.data == "sub_all")
async def sub_all(cb: CallbackQuery, state: FSMContext):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{BACKEND_URL}/subscribe", json={"chat_id": str(cb.message.chat.id)})
            r.raise_for_status()
        await cb.message.answer("✅ Подписка на все новые предложения оформлена.")
    except Exception as e:
        await cb.message.answer(f"Ошибка: {e}")
    await state.clear()
    await cb.answer()

@dp.callback_query(F.data == "unsub_all")
async def unsub_all(cb: CallbackQuery):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{BACKEND_URL}/unsubscribe", params={"chat_id": str(cb.message.chat.id)})
            r.raise_for_status()
        await cb.message.answer("🔕 Вы отписаны от всех уведомлений.")
    except Exception as e:
        await cb.message.answer(f"Ошибка: {e}")
    await cb.answer()

@dp.message(Command("menu"))
async def menu(m: Message):
    await m.answer("Главное меню:", reply_markup=main_menu())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
