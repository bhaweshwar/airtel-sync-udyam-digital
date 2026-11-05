#!/usr/bin/env bash
# Start the API (uvicorn --reload) and the web dev server together. Ctrl+C stops both.
# Ports come from API_PORT / WEB_PORT (defaults 8000 / 5173), so each worktree can run its own pair.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
export API_PORT WEB_PORT

"$ROOT/backend/.venv/bin/uvicorn" app.main:app --app-dir "$ROOT/backend" --reload --port "$API_PORT" &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT INT TERM

echo "API  http://127.0.0.1:$API_PORT/docs"
echo "Web  http://127.0.0.1:$WEB_PORT"
npm --prefix "$ROOT/frontend" run dev
