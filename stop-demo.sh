#!/bin/bash

# ClauseFlow Demo Stopper

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.demo-pids"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if [ -f "$PID_FILE" ]; then
    source "$PID_FILE"

    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null && echo -e "${GREEN}Stopped backend (PID: $BACKEND_PID)${NC}"
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null && echo -e "${GREEN}Stopped frontend (PID: $FRONTEND_PID)${NC}"
    fi

    rm -f "$PID_FILE"
    echo -e "${GREEN}ClauseFlow demo stopped.${NC}"
else
    echo -e "${RED}No running demo found (PID file missing).${NC}"
    echo "You can manually kill processes on ports 9847 and 9848:"
    echo "  lsof -ti:9847 | xargs kill 2>/dev/null"
    echo "  lsof -ti:9848 | xargs kill 2>/dev/null"
fi
