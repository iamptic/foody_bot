import os
import asyncio
from aiohttp import ClientSession
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "").rstrip("/")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")
BUYER_URL = os.getenv("BUYER_URL", "").rstrip("/")

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN is not set. Add it to .env or environment variables.")

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(BOT_TOKEN, parse_mode="HTML")

def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏪 Я ресторан/кафе", callback_data="role_restaurant")],
        [InlineKeyboardButton(text="👤 Я покупатель", callback_data="role_buyer")]
    ])

def restaurant_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Зарегистрироваться / получить ссылку", callback_data="rest_register")],
        [InlineKeyboardButton(text="📋 Открыть ЛК (WebApp)", web_app=WebAppInfo(url=f"{WEBAPP_URL}/index.html?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="rest_help")]
    ])

def buyer_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍔 Открыть каталог (WebApp)", web_app=WebAppInfo(url=f"{BUYER_URL}?api={BACKEND_URL}"))],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="buyer_help")]
    ])

class RegForm(StatesGroup):
    waiting_name = State()
    waiting_email = State()

@dp.message(CommandStart())
async def on_start(message: Message):
    await message.answer(
        "🍽 <b>Foody</b> — вкусно, выгодно, без отходов.\n"
        "Выберите, кто вы:",
        reply_markup=start_kb()
    )

@dp.callback_query(F.data == "role_restaurant")
async def role_restaurant(c: CallbackQuery):
    await c.message.edit_text("🏪 <b>Foody для ресторанов</b>
— Размещайте предложения
— Смотрите брони
— Получайте уведомления", reply_markup=restaurant_menu_kb())
    await c.answer()

@dp.callback_query(F.data == "role_buyer")
async def role_buyer(c: CallbackQuery):
    await c.message.edit_text("👤 <b>Foody для покупателей</b>
— Ищите еду со скидкой рядом
— Резервируйте и забирайте вовремя", reply_markup=buyer_menu_kb())
    await c.answer()

@dp.callback_query(F.data == "rest_help")
async def rest_help(c: CallbackQuery):
    await c.answer()
    await c.message.answer("ℹ️ <b>Как это работает</b>
1) Нажмите «Зарегистрироваться» и укажите название и email.
2) Получите ссылку для активации ЛК.
3) В ЛК добавьте фото, цену, количество и срок действия.
4) Покупатели увидят оффер и смогут забронировать.")

@dp.callback_query(F.data == "buyer_help")
async def buyer_help(c: CallbackQuery):
    await c.answer()
    await c.message.answer("ℹ️ <b>Как это работает</b>
1) Откройте каталог и найдите предложение.
2) Нажмите «Забронировать» и покажите код на кассе.
3) Бронь действует ограниченное время.")

@dp.callback_query(F.data == "rest_register")
async def rest_register(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(RegForm.waiting_name)
    await c.message.answer("🧾 Введите <b>название ресторана</b>:")

@dp.message(RegForm.waiting_name)
async def reg_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2:
        return await message.reply("Название слишком короткое. Введите ещё раз:")
    await state.update_data(name=name)
    await state.set_state(RegForm.waiting_email)
    await message.answer("📧 Введите <b>email</b> для доступа в ЛК:")

@dp.message(RegForm.waiting_email)
async def reg_email(message: Message, state: FSMContext):
    email = (message.text or "").strip()
    if "@" not in email:
        return await message.reply("Некорректный email. Попробуйте ещё раз:")
    data = await state.get_data()
    name = data.get("name")
    await state.clear()
    await message.answer("⏳ Регистрируем…")
    try:
        async with ClientSession() as sess:
            url = f"{BACKEND_URL}/register_restaurant"
            params = {"name": name, "email": email}
            async with sess.post(url, params=params) as resp:
                js = await resp.json()
        link = js.get("verification_link")
        if not link:
            return await message.answer(f"❌ Ошибка регистрации: {js}")
        await message.answer(f"✅ <b>Готово!</b>
Ресторан: <b>{name}</b>
Email: <code>{email}</code>
Нажмите кнопку ниже, чтобы активировать личный кабинет.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔐 Активировать ЛК", url=link)]]))
    except Exception as e:
        await message.answer(f"❌ Не удалось зарегистрировать: {e}")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Команды:
/start — главное меню
/help — помощь")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
