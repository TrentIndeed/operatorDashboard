#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Operator Dashboard Setup ==="
echo ""

# --- .env ---
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[1/4] Created .env from .env.example"
  echo "      → Edit .env with your credentials before starting"
else
  echo "[1/4] .env already exists — skipping"
fi

# --- Backend ---
echo "[2/4] Installing backend..."
cd backend
if [ ! -d .venv ]; then
  python3 -m venv .venv 2>/dev/null || python -m venv .venv
fi
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
pip install -q -r requirements.txt
echo "      Backend ready."
cd ..

# --- Frontend ---
echo "[3/4] Installing frontend..."
cd frontend
npm install --silent
if [ ! -f .env.local ]; then
  cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DISPLAY_NAME=Operator
NEXT_PUBLIC_TAGLINE=solo founder mode
NEXT_PUBLIC_INITIALS=OP
EOF
  echo "      Created frontend/.env.local — edit with your display name"
fi
cd ..

# --- Claude CLI check ---
echo "[4/4] Checking Claude CLI..."
if command -v claude &>/dev/null; then
  echo "      Claude CLI found: $(claude --version)"
else
  echo "      Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
  echo "      Then run: claude (to authenticate)"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Start everything with:"
echo "  bash scripts/start.sh"
echo ""
echo "Or manually:"
echo "  Terminal 1: cd backend && source .venv/Scripts/activate && uvicorn main:app --reload --port 8000"
echo "  Terminal 2: cd frontend && npm run dev"
echo ""
echo "Dashboard: http://localhost:3000"
echo "API docs:  http://localhost:8000/docs"
