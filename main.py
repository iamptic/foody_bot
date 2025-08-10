import os, asyncio, httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
REG_WEBAPP_URL = os.getenv("REG_WEBAPP_URL", "http://localhost:5173")
BUYER_WEBAPP_URL = os.getenv("BUYER_WEBAPP_URL", "http://localhost:5174")
if not BOT_TOKEN: raise RuntimeError("❌ BOT_TOKEN is not set")

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(BOT_TOKEN, parse_mode="HTML")

class Reg(StatesGroup):
    waiting_name_new = State()

def buyer_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🍽 Открыть предложения рядом", web_app=WebAppInfo(url=f"{BUYER_WEBAPP_URL}/index.html?api={BACKEND_URL}"))
    ]])

def merchant_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍🍳 ЛК ресторана", web_app=WebAppInfo(url=f"{REG_WEBAPP_URL}/index.html?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="🍽 Экран покупателя", web_app=WebAppInfo(url=f"{BUYER_WEBAPP_URL}/index.html?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="⚙️ Настройки ресторана", callback_data="settings_open")],
    ])

def settings_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать новый ресторан", callback_data="create_new_rest")],
        [InlineKeyboardButton(text="🔀 Сменить активный ресторан", callback_data="switch_rest")],
        [InlineKeyboardButton(text="✏️ Заполнить профиль (Mini App)", web_app=WebAppInfo(url=f"{REG_WEBAPP_URL}/onboarding.html?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    kb = buyer_menu()
    intro = "Добро пожаловать в <b>Foody</b>!\nСмотрите горячие предложения рядом."
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{BACKEND_URL}/whoami", params={"telegram_id": m.from_user.id})
        if r.status_code == 200:
            data = r.json()
            kb = merchant_menu()
            intro = f"Здравствуйте, <b>{data.get('restaurant_name','ресторан')}</b>!\nУправляйте меню и бронями."
    except Exception:
        pass
    await m.answer(intro, reply_markup=kb)

@dp.message(Command("merchant"))
async def merchant(m: Message):
    await m.answer("Раздел для ресторанов:", reply_markup=merchant_menu())

@dp.callback_query(F.data == "settings_open")
async def settings_open(cb: CallbackQuery):
    await cb.message.edit_text("⚙️ Настройки ресторана:", reply_markup=settings_menu())
    await cb.answer()

@dp.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery):
    await cb.message.edit_text("Меню ресторана:", reply_markup=merchant_menu())
    await cb.answer()

@dp.callback_query(F.data == "create_new_rest")
async def create_new_rest(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите <b>название нового ресторана</b>:")
    await state.set_state(Reg.waiting_name_new)
    await cb.answer()

@dp.message(Reg.waiting_name_new)
async def reg_name_new(m: Message, state: FSMContext):
    name = (m.text or "").strip()[:120] or "Мой ресторан"
    await m.answer("Создаём новый ресторан…")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{BACKEND_URL}/register_telegram",
                                  params={"force_new": "true"},
                                  json={"name": name, "telegram_id": str(m.from_user.id)})
            r.raise_for_status()
            data = r.json()
        await m.answer(f"✅ Создан «{data['restaurant_name']}» (id {data['restaurant_id']}). Он выбран активным. Откройте «👨‍🍳 ЛК ресторана».")
    except Exception as e:
        await m.answer(f"Ошибка: {e}")
    await state.clear()

@dp.callback_query(F.data == "switch_rest")
async def switch_rest(cb: CallbackQuery):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{BACKEND_URL}/my_restaurants", params={"telegram_id": cb.from_user.id})
        lst = r.json()
    except Exception as e:
        await cb.message.answer(f"Ошибка: {e}"); return await cb.answer()

    if not lst:
        await cb.message.answer("У вас пока нет ресторанов. Создайте новый в настройках.")
        return await cb.answer()

    rows = [[InlineKeyboardButton(text=f"🍽 {x['restaurant_name']} (id {x['id']})", callback_data=f"pick_rest:{x['id']}")] for x in lst]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_open")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await cb.message.answer("Выберите активный ресторан:", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data.startswith("pick_rest:"))
async def pick_rest(cb: CallbackQuery):
    rid = int(cb.data.split(":")[1])
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{BACKEND_URL}/set_active_restaurant",
                                  params={"telegram_id": cb.from_user.id, "restaurant_id": rid})
        if r.status_code == 200:
            await cb.message.answer(f"✅ Активный ресторан установлен (id {rid}). Откройте «👨‍🍳 ЛК ресторана».")
        else:
            await cb.message.answer("Не удалось переключить ресторан.")
    except Exception as e:
        await cb.message.answer(f"Ошибка: {e}")
    await cb.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
