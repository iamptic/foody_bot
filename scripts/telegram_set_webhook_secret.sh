#!/usr/bin/env bash
set -euo pipefail
: "${BOT_TOKEN:?BOT_TOKEN is required}"
: "${BACKEND_PUBLIC:?BACKEND_PUBLIC is required}"
: "${WEBHOOK_SECRET:?WEBHOOK_SECRET is required}"
URL="https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${BACKEND_PUBLIC}/tg/webhook&drop_pending_updates=true&secret_token=${WEBHOOK_SECRET}"
echo "$URL"
curl -sS "$URL" | jq . || curl -sS "$URL"
