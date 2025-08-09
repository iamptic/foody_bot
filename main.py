import os, asyncio, json, urllib.parse as up
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, WebAppInfo,
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, Location
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import ClientSession

BOT_TOKEN   = os.getenv("BOT_TOKEN")
WEBAPP_URL  = os.getenv("WEBAPP_URL",  "https://foody-reg.vercel.app").rstrip("/")     # домен мини-аппа (один!)
BACKEND_URL = os.getenv("BACKEND_URL", "https://foodyback-production.up.railway.app").rstrip("/")

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN is not set")

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp  = Dispatcher()

DB_PATH = "bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            tg_id INTEGER PRIMARY KEY,
            name  TEXT,
            token TEXT  -- verification_token
        )
        """)
        await db.commit()

async def get_token(tg_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT token FROM restaurants WHERE tg_id=?", (tg_id,))
        row = await cur.fetchone()
        return row["token"] if row and row["token"] else None

async def save_rest(tg_id: int, name: str, token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO restaurants (tg_id, name, token) VALUES (?, ?, ?) "
            "ON CONFLICT(tg_id) DO UPDATE SET name=excluded.name, token=excluded.token",
            (tg_id, name, token)
        )
        await db.commit()

def kb_role() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏪 Ресторан / кафе", callback_data="role|rest")
    kb.button(text="👤 Покупатель",    callback_data="role|buyer")
    kb.adjust(1, 1)
    return kb.as_markup()

def kb_webapp_lk(token: str) -> InlineKeyboardMarkup:
    # ЛК открываем как мини-апп; обязательно один домен у бота в /setdomain!
    url = f"{WEBAPP_URL}/verify.html?token={token}&api={BACKEND_URL}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🔐 Открыть ЛК ресторана", web_app=WebAppInfo(url=url))
    kb.adjust(1)
    return kb.as_markup()

def kb_webapp_buyer() -> InlineKeyboardMarkup:
    # Для покупателя — предполагаем, что каталог доступен по /buyer/index.html на том же домене
    url = f"{WEBAPP_URL}/buyer/index.html?api={BACKEND_URL}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🍔 Открыть каталог", web_app=WebAppInfo(url=url))
    kb.adjust(1)
    return kb.as_markup()

class Onboard(StatesGroup):
    waiting_name = State()

@dp.message(CommandStart())
async def start_cmd(m: Message, state: FSMContext):
    await state.clear()
    # Если у ресторана уже есть токен — сразу даём ЛК
    token = await get_token(m.from_user.id)
    if token:
        await m.answer(
            "🍽 <b>Foody</b> — выберите действие:",
            reply_markup=kb_webapp_lk(token)
        )
        await m.answer("Или переключитесь на режим покупателя:", reply_markup=kb_role())
        return
    # Иначе обычный старт с выбором роли
    await m.answer("🍽 <b>Foody — вкусно, выгодно, без отходов.</b>\nВыберите, кто вы:",
                   reply_markup=kb_role())

@dp.callback_query(F.data == "role|buyer")
async def role_buyer(call: CallbackQuery):
    await call.message.edit_text("👤 Режим покупателя: откройте каталог (мини-приложение).",
                                 reply_markup=kb_webapp_buyer())
    await call.answer()

@dp.callback_query(F.data == "role|rest")
async def role_rest(call: CallbackQuery, state: FSMContext):
    # Проверяем, есть ли уже токен — если да, показываем ЛК
    token = await get_token(call.from_user.id)
    if token:
        await call.message.edit_text("🏪 Аккаунт найден. Откройте ЛК:",
                                     reply_markup=kb_webapp_lk(token))
        await call.answer()
        return
    # Иначе быстрый онбординг: спросим только имя ресторана
    await state.set_state(Onboard.waiting_name)
    await call.message.edit_text("🏪 Введите название заведения (например: «Кофейня №1»):")
    await call.answer()

@dp.message(Onboard.waiting_name)
async def rest_name_entered(m: Message, state: FSMContext):
    name = (m.text or "").strip()
    if len(name) < 2:
        await m.reply("Название слишком короткое. Введите корректно:")
        return
    email = f"rest_{m.from_user.id}@example.com"  # стабильный «email»
    # Регистрируем в бекенде (асинхронно)
    try:
        async with ClientSession() as sess:
            async with sess.post(f"{BACKEND_URL}/register_restaurant",
                                 params={"name": name, "email": email}) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    await m.answer(f"Ошибка регистрации: {txt}", reply_markup=ReplyKeyboardRemove())
                    await state.clear()
                    return
                data = await resp.json()
    except Exception as e:
        await m.answer(f"Сервис недоступен: {e}", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    link = data.get("verification_link", "")
    # Извлекаем token из verification_link
    q = up.urlparse(link).query
    token = up.parse_qs(q).get("token", [None])[0] or (link.split("token=")[-1].split("&")[0] if "token=" in link else None)
    if not token:
        await m.answer("Не удалось получить токен активации. Свяжитесь с поддержкой.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    await save_rest(m.from_user.id, name, token)

    await m.answer("✅ Регистрация почти готова. ЛК откроется как мини-приложение Telegram.",
                   reply_markup=ReplyKeyboardRemove())
    await m.answer("Открыть ЛК:", reply_markup=kb_webapp_lk(token))
    await state.clear()

@dp.message(F.web_app_data)
async def on_webapp_data(m: Message):
    # если мини-апп присылает данные назад
    try:
        payload = json.loads(m.web_app_data.data)
    except Exception:
        payload = m.web_app_data.data
    await m.answer(f"Из мини-приложения получено:\n<code>{payload}</code>")

@dp.message(Command("lk"))
async def cmd_lk(m: Message):
    token = await get_token(m.from_user.id)
    if not token:
        await m.answer("Пока нет аккаунта ресторана. Нажмите «🏪 Ресторан / кафе» и пройдите быструю регистрацию.")
        return
    await m.answer("Открыть ЛК:", reply_markup=kb_webapp_lk(token))

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
