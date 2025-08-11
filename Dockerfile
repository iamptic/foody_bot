FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# важно:
CMD ["python", "bot_webhook_fixed.py"]
ARG CACHE_BUST=2025-08-11-2
