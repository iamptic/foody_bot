
import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

WEBAPP_MERCHANT = os.getenv("WEBAPP_MERCHANT_URL", "https://foody-reg.vercel.app")
WEBAPP_BUYER = os.getenv("WEBAPP_BUYER_URL", "https://foody-buyer.vercel.app")
BACKEND_URL = os.getenv("BACKEND_URL", "https://foodyback-production.up.railway.app")

@router.message(Command("offer"))
async def offer(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        [InlineKeyboardButton(text="📄 Коммерческое предложение (PDF)", url=f"{WEBAPP_MERCHANT}/docs/docs/Foody_Offer_Brand_ru.pdf")],
        [InlineKeyboardButton(text="🏬 Для сетей (PDF)", url=f"{WEBAPP_MERCHANT}/docs/docs/Foody_Offer_Chain_ru.pdf")],
        [InlineKeyboardButton(text="📊 ROI-калькулятор (XLSX)", url=f"{WEBAPP_MERCHANT}/docs/docs/ROI_%D0%A1%D0%BF%D0%B0%D1%81%D0%B5%D0%BD%D0%B8%D0%B5%D0%95%D0%B4%D1%8B_%D0%BA%D0%B0%D0%BB%D1%8C%D0%BA%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80.xlsx")]
    ]])
    await m.answer("Материалы Foody:", reply_markup=kb)

@router.message(Command("rules"))
async def rules(m: Message):
    await m.answer("Правила для ресторанов:", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="📘 Открыть правила", web_app=WebAppInfo(url=f"{WEBAPP_MERCHANT}/docs/rules.html"))
        ]]
    ))
