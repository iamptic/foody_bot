FROM python:3.11-slim
WORKDIR /app

# кэш-бамп — ДО установки зависимостей
ARG CACHE_BUST=2025-08-11-3

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# точка входа бота
CMD ["python", "bot_webhook_fixed.py"]
