#!/usr/bin/env bash
set -euo pipefail
if [ -z "${BOT_TOKEN:-}" ]; then echo "BOT_TOKEN is required in env"; exit 1; fi
if [ -z "${BACKEND_PUBLIC:-}" ]; then echo "BACKEND_PUBLIC is required in env"; exit 1; fi
URL="https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${BACKEND_PUBLIC}/tg/webhook"
echo "Setting webhook to: $URL"
curl -sS "$URL" | jq . || curl -sS "$URL"
