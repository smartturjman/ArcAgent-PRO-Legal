#!/bin/bash
# A-PROL Quick Start Script
# Starts both API and UI servers

set -e

PROJECT_DIR="/Users/jonieculaste/Projects/ArcAgent PRO-Legal/venv_repo/ArcAgent-PRO-Legal"
VENV_DIR="/Users/jonieculaste/Projects/ArcAgent PRO-Legal/venv_repo/venv"

echo "================================"
echo "A-PROL Quick Start"
echo "================================"
echo ""

# Activate venv
echo "📦 Activating Python virtual environment..."
source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"

# Check dependencies
echo "✓ Virtual environment activated"
echo ""

# Start API in background
echo "🚀 Starting FastAPI server (port 8000)..."
python api.py &
API_PID=$!
sleep 2

# Check if API is running
if kill -0 $API_PID 2>/dev/null; then
    echo "✓ FastAPI started (PID: $API_PID)"
else
    echo "✗ FastAPI failed to start"
    exit 1
fi
echo ""

# Start UI
echo "🎨 Starting Streamlit UI (port 8501)..."
echo "   Dashboard will open automatically in your browser"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start Streamlit (this will block)
streamlit run ui.py

# Cleanup on exit
trap "kill $API_PID 2>/dev/null || true" EXIT
