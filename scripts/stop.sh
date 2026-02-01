#!/bin/bash
# FinAgent - Stop all services
# Usage: ./scripts/stop.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_DIR/.pids"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping FinAgent...${NC}"

# Function to stop a service
stop_service() {
    local name=$1
    local pid_file="$PID_DIR/$name.pid"

    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "  Stopping $name (PID: $pid)..."
            kill "$pid" 2>/dev/null

            # Wait for graceful shutdown
            for i in {1..10}; do
                if ! ps -p "$pid" > /dev/null 2>&1; then
                    break
                fi
                sleep 0.5
            done

            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null
            fi

            echo -e "  ✅ $name stopped"
        else
            echo -e "  ⚠️  $name not running (stale PID file)"
        fi
        rm -f "$pid_file"
    else
        echo -e "  ⚠️  $name not running (no PID file)"
    fi
}

# Stop Frontend
stop_service "frontend"

# Stop Backend
stop_service "backend"

# Optionally stop Ollama (commented out by default - you may want to keep it running)
# stop_service "ollama"

# Also kill any orphaned processes on the ports
echo -e "${YELLOW}Cleaning up ports...${NC}"

# Kill process on port 8000 (backend)
pid_8000=$(lsof -ti:8000 2>/dev/null)
if [ -n "$pid_8000" ]; then
    kill $pid_8000 2>/dev/null
    echo -e "  ✅ Cleaned port 8000"
fi

# Kill process on port 5173 (frontend)
pid_5173=$(lsof -ti:5173 2>/dev/null)
if [ -n "$pid_5173" ]; then
    kill $pid_5173 2>/dev/null
    echo -e "  ✅ Cleaned port 5173"
fi

echo ""
echo -e "${GREEN}✅ All services stopped!${NC}"
