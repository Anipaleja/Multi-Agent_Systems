#!/bin/bash

# Token Efficiency Testing - Combined Startup Script

echo "🚀 Starting Token Efficiency Testing Environment"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install backend deps if needed
echo "[1/3] Checking dependencies..."
cd "$SCRIPT_DIR/default_testing/backend"

if ! python -c "import flask, flask_cors" 2>/dev/null; then
  echo "     Installing Flask..."
  pip install -r requirements.txt -q
fi

# Install frontend deps if needed
if [ ! -d "$SCRIPT_DIR/default_testing/node_modules" ]; then
  echo "     Installing npm packages..."
  cd "$SCRIPT_DIR/default_testing"
  npm install -q
  cd "$SCRIPT_DIR/default_testing/backend"
fi

echo "✓ Dependencies OK"
echo ""

# Start backend
echo "[2/3] Starting Python backend..."
cd "$SCRIPT_DIR/default_testing/backend"
python api.py &
BACKEND_PID=$!
echo "✓ Backend running on http://localhost:5000 (PID: $BACKEND_PID)"

sleep 2

# Start frontend
echo "[3/3] Starting React frontend..."
cd "$SCRIPT_DIR/default_testing"
npm run dev &
FRONTEND_PID=$!
echo "✓ Frontend running on http://localhost:5173"

echo ""
echo "Open http://localhost:5173 in your browser"
echo "Press Ctrl+C to stop"
echo ""

# Wait and cleanup on exit
wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
echo ""
echo "Services stopped"
