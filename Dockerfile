FROM python:3.11-slim
WORKDIR /app

# кэш-бамп
ARG CACHE_BUST=2025-08-11-6

# корневые сертификаты для HTTPS к Telegram
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

CMD ["python", "bot_webhook_final.py"]
