import os
import asyncio
from dataclasses import dataclass
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                           InlineKeyboardButton, InputMediaPhoto)
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp

# ========= Настройки через ENV =========
BOT_TOKEN = os.getenv("BOT_TOKEN")  # обязательно
BACKEND_API = os.getenv("BACKEND_API", "https://foodyback-production.up.railway.app")
WEBAPP_BUYER = os.getenv("WEBAPP_BUYER", "https://foody-buyer.vercel.app")
WEBAPP_REG = os.getenv("WEBAPP_REG", "https://foody-reg.vercel.app")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задан")

# ========= Маркировка callback'ов =========
@dataclass
class Actions:
    BUYER = "buyer"
    RESTO = "resto"
    OFFERS = "offers"
    RESERVE = "reserve"
    HELP = "help"

router = Router()

# ========= Клавиатуры =========
def start_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Я покупатель", callback_data=Actions.BUYER)
    kb.button(text="🏪 Я ресторан", callback_data=Actions.RESTO)
    kb.adjust(1)
    return kb.as_markup()

def buyer_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🍽 Открыть каталог (WebApp)", url=WEBAPP_BUYER)
    kb.button(text="🔄 Показать предложения", callback_data=Actions.OFFERS)
    kb.button(text="ℹ️ Помощь", callback_data=Actions.HELP)
    kb.adjust(1, 1, 1)
    return kb.as_markup()

def resto_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🧑‍🍳 Открыть ЛК ресторана (WebApp)", url=WEBAPP_REG)
    kb.button(text="ℹ️ Помощь", callback_data=Actions.HELP)
    kb.adjust(1, 1)
    return kb.as_markup()

def offer_kb(offer_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Забронировать", callback_data=f"{Actions.RESERVE}:{offer_id}")
    kb.adjust(1)
    return kb.as_markup()

# ========= API-вспомогалки =========
async def get_offers(session: aiohttp.ClientSession):
    url = f"{BACKEND_API}/offers"
    async with session.get(url, timeout=20) as r:
        r.raise_for_status()
        return await r.json()

async def reserve_offer(session: aiohttp.ClientSession, offer_id: int, buyer_name: Optional[str]):
    url = f"{BACKEND_API}/reserve"
    payload = {"offer_id": offer_id, "buyer_name": buyer_name}
    async with session.post(url, json=payload, timeout=20) as r:
        r.raise_for_status()
        return await r.json()

# ========= Хендлеры =========
@router.message(CommandStart())
async def on_start(m: Message):
    text = (
        "🍽 Привет! Это Foody — вкусно, выгодно, без отходов.\n\n"
        "Кем вы являетесь?"
    )
    await m.answer(text, reply_markup=start_kb())

@router.callback_query(F.data == Actions.BUYER)
async def on_buyer(c: CallbackQuery):
    await c.message.edit_text(
        "👤 Режим покупателя.\n"
        "— смотрите еду со скидкой рядом\n"
        "— бронируйте за пару кликов\n\n"
        "Выберите действие:",
        reply_markup=buyer_kb()
    )
    await c.answer()

@router.callback_query(F.data == Actions.RESTO)
async def on_resto(c: CallbackQuery):
    await c.message.edit_text(
        "🏪 Режим ресторана.\n"
        "Откройте ЛК, чтобы добавить или отредактировать предложения.",
        reply_markup=resto_kb()
    )
    await c.answer()

@router.callback_query(F.data == Actions.HELP)
async def on_help(c: CallbackQuery):
    await c.message.answer(
        "ℹ️ Как это работает:\n"
        "• Ресторан публикует излишки в ЛК (WebApp)\n"
        "• Покупатель находит и бронирует\n"
        "• На выдаче показывает код/бронь\n\n"
        "Открыть каталог: " + WEBAPP_BUYER + "\n"
        "ЛК ресторана: " + WEBAPP_REG
    )
    await c.answer()

@router.callback_query(F.data == Actions.OFFERS)
async def on_offers(c: CallbackQuery, bot: Bot):
    await c.answer("Загружаю предложения…")
    async with aiohttp.ClientSession() as session:
        try:
            items = await get_offers(session)
        except Exception as e:
            await c.message.answer("⚠️ Не удалось получить предложения. Попробуйте позже.")
            return

    if not items:
        await c.message.answer("Пока предложений нет. Загляните позже или откройте WebApp: " + WEBAPP_BUYER)
        return

    # Первые 5 карточек
    for o in items[:5]:
        title = o.get("title", "Без названия")
        restaurant = o.get("restaurant", "Ресторан")
        price = o.get("price", 0)
        qty = o.get("quantity", 0)
        photo = o.get("photo_url")
        expires = o.get("expires_at", "")

        caption = (
            f"🍔 <b>{title}</b>\n"
            f"🏷 {restaurant}\n"
            f"💰 {price} ₽   •   🧾 Остаток: {qty}\n"
        )
        kb = offer_kb(o["id"])
        try:
            if photo:
                await bot.send_photo(
                    chat_id=c.message.chat.id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb
                )
            else:
                await bot.send_message(
                    chat_id=c.message.chat.id,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=kb
                )
        except Exception:
            # если URL фото недоступен — просто текст
            await bot.send_message(
                chat_id=c.message.chat.id,
                text=caption,
                parse_mode="HTML",
                reply_markup=kb
            )

@router.callback_query(F.data.startswith(f"{Actions.RESERVE}:"))
async def on_reserve(c: CallbackQuery):
    _, offer_id_str = c.data.split(":")
    offer_id = int(offer_id_str)
    buyer_name = c.from_user.full_name

    async with aiohttp.ClientSession() as session:
        try:
            data = await reserve_offer(session, offer_id, buyer_name)
        except Exception:
            await c.answer("Не удалось забронировать", show_alert=True)
            return

    code = data.get("code")
    until = data.get("expires_at", "")
    title = data.get("title", "")
    price = data.get("price", 0)
    restaurant = data.get("restaurant", "")

    text = (
        "✅ Бронь оформлена!\n\n"
        f"🍽 <b>{title}</b>\n"
        f"🏪 {restaurant}\n"
        f"💰 {price} ₽\n"
        f"🔐 Код брони: <code>{code}</code>\n"
        f"⏳ Действует до: {until}\n\n"
        "Покажите этот код на выдаче."
    )
    await c.message.answer(text, parse_mode="HTML")
    await c.answer()

# ========= Запуск =========
async def main():
    bot = Bot(BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
