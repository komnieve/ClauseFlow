#!/bin/bash

# ClauseFlow Demo Launcher
# Ports chosen to avoid conflicts with common services
BACKEND_PORT=9847
FRONTEND_PORT=9848

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.demo-pids"

echo -e "${GREEN}=== ClauseFlow Demo Launcher ===${NC}"
echo ""

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "Stopped backend (PID: $BACKEND_PID)"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "Stopped frontend (PID: $FRONTEND_PID)"
    fi
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if ports are available
check_port() {
    if command -v lsof &> /dev/null; then
        if lsof -i:$1 >/dev/null 2>&1; then
            echo -e "${RED}Error: Port $1 is already in use${NC}"
            exit 1
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln | grep -q ":$1 "; then
            echo -e "${RED}Error: Port $1 is already in use${NC}"
            exit 1
        fi
    fi
}

check_port $BACKEND_PORT
check_port $FRONTEND_PORT

# Get server IP for network access
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$SERVER_IP" ] || [[ "$SERVER_IP" == *"<"* ]]; then
    # Try ipconfig getifaddr for macOS
    SERVER_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
fi
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="localhost"
fi

# Start backend
echo -e "${YELLOW}Starting backend...${NC}"
cd "$SCRIPT_DIR/backend"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null

# Start backend in background
uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!
echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"

# Give backend a moment to start
sleep 2

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Backend failed to start. Check logs above.${NC}"
    exit 1
fi

# Start frontend
echo -e "${YELLOW}Starting frontend...${NC}"
cd "$SCRIPT_DIR/frontend"

# Install npm dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Start frontend with custom port - connects to backend
VITE_API_URL="http://${SERVER_IP}:${BACKEND_PORT}" npm run dev -- --port $FRONTEND_PORT --host 0.0.0.0 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"

# Save PIDs for stop script
echo "BACKEND_PID=$BACKEND_PID" > "$PID_FILE"
echo "FRONTEND_PID=$FRONTEND_PID" >> "$PID_FILE"

sleep 2

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ClauseFlow is running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Local access:${NC}"
echo -e "  Frontend: http://localhost:${FRONTEND_PORT}"
echo -e "  Backend:  http://localhost:${BACKEND_PORT}"
echo -e "  API Docs: http://localhost:${BACKEND_PORT}/docs"
echo ""
echo -e "${CYAN}Network access (for demo):${NC}"
echo -e "  Frontend: http://${SERVER_IP}:${FRONTEND_PORT}"
echo -e "  Backend:  http://${SERVER_IP}:${BACKEND_PORT}"
echo ""
echo -e "${YELLOW}Firewall note:${NC} Ports ${BACKEND_PORT} and ${FRONTEND_PORT} must be open"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Wait for either process to exit
wait
