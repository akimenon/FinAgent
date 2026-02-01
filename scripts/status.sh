#!/bin/bash
# FinAgent - Check status of all services
# Usage: ./scripts/status.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_DIR/.pids"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📊 FinAgent Status${NC}"
echo ""

# Function to check service status
check_service() {
    local name=$1
    local port=$2
    local pid_file="$PID_DIR/$name.pid"

    printf "  %-12s" "$name:"

    # Check PID file
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${GREEN}Running${NC} (PID: $pid, Port: $port)"
            return 0
        fi
    fi

    # Check if port is in use (might be running without PID file)
    if lsof -ti:$port > /dev/null 2>&1; then
        pid=$(lsof -ti:$port)
        echo -e "${YELLOW}Running${NC} (PID: $pid, Port: $port) [no PID file]"
        return 0
    fi

    echo -e "${RED}Stopped${NC}"
    return 1
}

# Check Ollama
printf "  %-12s" "Ollama:"
if pgrep -x "ollama" > /dev/null; then
    echo -e "${GREEN}Running${NC}"
else
    echo -e "${RED}Stopped${NC}"
fi

# Check Backend
check_service "Backend" 8000

# Check Frontend
check_service "Frontend" 5173

echo ""
echo "  URLs:"
echo "    Frontend:  http://localhost:5173"
echo "    Backend:   http://localhost:8000"
echo "    API Docs:  http://localhost:8000/docs"
echo ""
