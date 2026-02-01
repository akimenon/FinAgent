#!/bin/bash
# FinAgent - Start all services
# Usage: ./scripts/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_DIR/.pids"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting FinAgent...${NC}"

# Create PID directory
mkdir -p "$PID_DIR"

# Function to check if a process is running
is_running() {
    if [ -f "$PID_DIR/$1.pid" ]; then
        pid=$(cat "$PID_DIR/$1.pid")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# 1. Check/Start Ollama
echo -e "${YELLOW}Checking Ollama...${NC}"
if pgrep -x "ollama" > /dev/null; then
    echo -e "  ✅ Ollama already running"
else
    echo -e "  Starting Ollama..."
    ollama serve > "$PROJECT_DIR/logs/ollama.log" 2>&1 &
    echo $! > "$PID_DIR/ollama.pid"
    sleep 2
    echo -e "  ✅ Ollama started"
fi

# 2. Start Backend
echo -e "${YELLOW}Starting Backend...${NC}"
if is_running "backend"; then
    echo -e "  ✅ Backend already running (PID: $(cat $PID_DIR/backend.pid))"
else
    cd "$PROJECT_DIR/backend"

    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "  ${RED}❌ Virtual environment not found. Run: cd backend && python3 -m venv venv${NC}"
        exit 1
    fi

    # Create logs directory
    mkdir -p "$PROJECT_DIR/logs"

    # Start uvicorn
    uvicorn main:app --reload --port 8000 > "$PROJECT_DIR/logs/backend.log" 2>&1 &
    echo $! > "$PID_DIR/backend.pid"
    sleep 2
    echo -e "  ✅ Backend started on http://localhost:8000"
fi

# 3. Start Frontend
echo -e "${YELLOW}Starting Frontend...${NC}"
if is_running "frontend"; then
    echo -e "  ✅ Frontend already running (PID: $(cat $PID_DIR/frontend.pid))"
else
    cd "$PROJECT_DIR/frontend"

    # Create logs directory
    mkdir -p "$PROJECT_DIR/logs"

    # Start Vite dev server
    npm run dev > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    sleep 3
    echo -e "  ✅ Frontend started on http://localhost:5173"
fi

echo ""
echo -e "${GREEN}✅ All services started!${NC}"
echo ""
echo "  📊 Frontend:  http://localhost:5173"
echo "  🔧 Backend:   http://localhost:8000"
echo "  📝 Logs:      $PROJECT_DIR/logs/"
echo ""
echo -e "To stop all services: ${YELLOW}./scripts/stop.sh${NC}"
