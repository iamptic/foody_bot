import os
import asyncio
import aiosqlite
from dataclasses import dataclass
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, Location
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import ClientSession

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_PUBLIC = os.getenv("BACKEND_PUBLIC", "http://localhost:8000").rstrip("/")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:5173").rstrip("/")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is not set. Add it to env.")

DB_PATH = "bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS restaurants (
            tg_id INTEGER PRIMARY KEY,
            name TEXT,
            lat REAL,
            lon REAL,
            restaurant_id INTEGER,
            verification_token TEXT
        )""")
        await db.commit()

@dataclass
class RestRec:
    tg_id: int
    name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    restaurant_id: Optional[int] = None
    verification_token: Optional[str] = None

async def get_rest(tg_id: int) -> Optional[RestRec]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM restaurants WHERE tg_id=?", (tg_id,))
        row = await cur.fetchone()
        if not row: return None
        return RestRec(**row)

async def upsert_rest(rec: RestRec):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO restaurants (tg_id, name, lat, lon, restaurant_id, verification_token)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(tg_id) DO UPDATE SET
                              name=excluded.name,
                              lat=excluded.lat,
                              lon=excluded.lon,
                              restaurant_id=excluded.restaurant_id,
                              verification_token=excluded.verification_token
                         """,
                         (rec.tg_id, rec.name, rec.lat, rec.lon, rec.restaurant_id, rec.verification_token))
        await db.commit()

def placeholder_email(tg_id: int) -> str:
    return f"tg_{tg_id}@example.com"

class AddRest(StatesGroup):
    waiting_name = State()
    waiting_location = State()

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

def choose_role_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏪 Ресторан / кафе", callback_data="role|rest")
    kb.button(text="👤 Покупатель", callback_data="role|buyer")
    kb.adjust(1, 1)
    return kb.as_markup()

def lk_button(verification_link: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔐 Открыть ЛК ресторана", url=verification_link)
    kb.adjust(1)
    return kb.as_markup()

def open_catalog_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    buyer_url = WEBAPP_URL.replace("foody-reg", "foody-buyer")
    kb.button(text="🍔 Открыть каталог", url=f"{buyer_url}?api={BACKEND_PUBLIC}")
    kb.adjust(1)
    return kb.as_markup()

@dp.message(CommandStart())
async def start_cmd(m: Message, state: FSMContext):
    await state.clear()
    txt = ("🍽 <b>Foody — вкусно, выгодно, без отходов.</b>\n"
           "Выберите, кто вы:")
    await m.answer(txt, reply_markup=choose_role_kb())

@dp.callback_query(F.data.startswith("role|"))
async def role_pick(c: CallbackQuery, state: FSMContext):
    role = c.data.split("|",1)[1]
    if role == "rest":
        rec = await get_rest(c.from_user.id)
        if rec and rec.verification_token:
            link = f"{WEBAPP_URL}/verify.html?token={rec.verification_token}&api={BACKEND_PUBLIC}"
            await c.message.edit_text("🏪 Аккаунт найден. Можно открыть ЛК:", reply_markup=lk_button(link))
            await c.answer()
            return
        await state.set_state(AddRest.waiting_name)
        await c.message.edit_text("🏪 Введите <b>название заведения</b> (например: «Кофейня №1»):")
        await c.answer()
    else:
        await c.message.edit_text("👤 Режим покупателя: откройте каталог — он покажет предложения рядом.", reply_markup=open_catalog_kb())
        await c.answer()

@dp.message(AddRest.waiting_name)
async def enter_name(m: Message, state: FSMContext):
    name = (m.text or "").strip()
    if len(name) < 2:
        await m.reply("Название слишком короткое. Введите корректно:")
        return
    await state.update_data(name=name)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Отправить геопозицию", request_location=True)]],
                             resize_keyboard=True, one_time_keyboard=True)
    await state.set_state(AddRest.waiting_location)
    await m.answer("Теперь отправьте локацию заведения (кнопкой ниже).", reply_markup=kb)

@dp.message(AddRest.waiting_location, F.location)
async def got_location(m: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name")
    loc: Location = m.location
    lat, lon = loc.latitude, loc.longitude

    email = placeholder_email(m.from_user.id)
    async with ClientSession() as sess:
        try:
            async with sess.post(f"{BACKEND_PUBLIC}/register_restaurant", params={"name": name, "email": email}) as resp:
                js = await resp.json()
        except Exception:
            await m.answer("Ошибка связи с сервером. Попробуйте ещё раз позже.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            return

    verification_link = js.get("verification_link")
    restaurant_id = js.get("restaurant_id")

    if not verification_link or not restaurant_id:
        await m.answer("Не удалось зарегистрировать. Напишите нам, мы поможем.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    import urllib.parse as up
    q = up.urlparse(verification_link).query
    token = up.parse_qs(q).get("token", [None])[0] or verification_link.split("token=")[-1].split("&")[0]

    rec = RestRec(tg_id=m.from_user.id, name=name, lat=lat, lon=lon, restaurant_id=restaurant_id, verification_token=token)
    await upsert_rest(rec)

    await m.answer("✅ Регистрация завершена! Откройте ЛК ресторана для управления предложениями.",
                   reply_markup=ReplyKeyboardRemove())
    await m.answer("Открыть ЛК:", reply_markup=lk_button(verification_link))
    await state.clear()

@dp.message(AddRest.waiting_location)
async def location_required(m: Message, state: FSMContext):
    await m.reply("Пожалуйста, отправьте локацию кнопкой «📍 Отправить геопозицию».")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
