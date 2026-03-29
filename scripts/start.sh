#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Starting Operator Dashboard ==="
echo ""

# Start backend
echo "Starting backend on port 8000..."
cd backend
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "Waiting for backend..."
for i in {1..15}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend ready."
    break
  fi
  sleep 1
done

# Start frontend
echo "Starting frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=== Running ==="
echo "Dashboard: http://localhost:3000"
echo "API docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both."

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
