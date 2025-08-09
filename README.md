# Foody Telegram Bot — роль + быстрая регистрация ресторана

Функции:
- Выбор роли (ресторан/покупатель)
- Ресторан: название + геолокация → регистрация через backend → кнопка «Открыть ЛК»
- Покупатель: кнопка «Открыть каталог»

## Запуск локально
1) Создайте `.env` по примеру `.env.example` и укажите:
   - `BOT_TOKEN`
   - `BACKEND_PUBLIC` (https://foodyback-production.up.railway.app)
   - `WEBAPP_URL` (https://foody-reg.vercel.app)
2) `pip install -r requirements.txt`
3) `python main.py`

## Запуск на Railway
- Залейте этот архив, в Variables задайте `BOT_TOKEN`, `BACKEND_PUBLIC`, `WEBAPP_URL`.
- Деплой.

Данные о ресторанах кэшируются в `bot_data.db` (SQLite) по Telegram ID, чтобы повторно показывать кнопку ЛК без повторной регистрации.
