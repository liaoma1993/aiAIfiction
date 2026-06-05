#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

cd "$ROOT_DIR/backend"
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001 &
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
if [[ ! -d "node_modules" ]]; then
  npm install
fi
npm run dev -- --host 127.0.0.1 &
FRONTEND_PID=$!

echo "AI Fiction Studio is starting..."
echo "Frontend: http://127.0.0.1:5173"
echo "Backend:  http://127.0.0.1:8001"
wait
