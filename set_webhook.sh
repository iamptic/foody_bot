#!/usr/bin/env bash
set -euo pipefail
: "${BOT_TOKEN:?BOT_TOKEN is required}"
: "${BACKEND_PUBLIC:?BACKEND_PUBLIC is required}"
URL="https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${BACKEND_PUBLIC}/tg/webhook"
echo "$URL"
curl -sS "$URL" | jq . || curl -sS "$URL"
