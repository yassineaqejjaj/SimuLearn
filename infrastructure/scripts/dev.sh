#!/usr/bin/env sh
# Développement local SANS clés ni Keycloak : fournisseurs mock, connexion simulée. Ports configurables.
set -e
API_PORT="${API_PORT:-8000}"
cd "$(dirname "$0")/../../apps/api"
export AUTH_DEV_MODE=true VOICE_PROVIDER=mock EVALUATION_PROVIDER=mock APP_ENV=development
uv sync --group dev >/dev/null
.venv/bin/python scripts_seed.py
.venv/bin/uvicorn app.main:app --port "$API_PORT" --reload &
cd ../web
NEXT_PUBLIC_AUTH_MODE=dev NEXT_PUBLIC_API_URL="http://localhost:$API_PORT" npm run dev
