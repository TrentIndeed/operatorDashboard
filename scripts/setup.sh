#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Operator Dashboard Setup ==="
echo ""

# --- .env ---
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[1/3] Created .env from .env.example"
  echo "      → Add your ANTHROPIC_API_KEY and GITHUB_TOKEN to .env before starting"
else
  echo "[1/3] .env already exists — skipping"
fi

# --- Backend ---
echo "[2/3] Installing backend dependencies..."
cd backend
if [ ! -d .venv ]; then
  python -m venv .venv
fi
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
pip install -q -r requirements.txt
echo "      Backend ready."
cd ..

# --- Frontend ---
echo "[3/3] Installing frontend dependencies..."
cd frontend
npm install --silent
echo "      Frontend ready."
cd ..

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To start the backend:"
echo "  cd backend && source .venv/Scripts/activate && uvicorn main:app --reload --port 8000"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm run dev"
echo ""
echo "Dashboard: http://localhost:3000"
echo "API docs:  http://localhost:8000/docs"
