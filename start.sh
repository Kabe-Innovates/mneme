#!/usr/bin/env bash
# Mneme — start backend + frontend

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Starting Mneme Healthcare Operations Assistant ==="
echo ""

# Backend
echo "[1/2] Starting FastAPI backend on http://localhost:8000 ..."
cd "$ROOT/backend"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "      Backend PID: $BACKEND_PID"

# Frontend
echo "[2/2] Starting Vite dev server on http://localhost:5173 ..."
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
echo "      Frontend PID: $FRONTEND_PID"

echo ""
echo "=== Mneme is running ==="
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services."

wait
