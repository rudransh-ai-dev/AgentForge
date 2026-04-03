#!/bin/bash

# ── Frontend Start Script ──
PORT=5173
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Cleanup on exit ──
cleanup() {
    echo -e "\n${YELLOW}🛑 Frontend stopped${NC}"
    [ -n "$PID" ] && kill "$PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Check npm ──
if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm not found${NC}"
    exit 1
fi

# ── Install deps if needed ──
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}⚠ Installing frontend dependencies...${NC}"
    npm install --prefix "$FRONTEND_DIR" || {
        echo -e "${RED}✗ Failed to install dependencies${NC}"
        exit 1
    }
fi

# ── Kill existing process on port ──
EXISTING_PID=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
    echo -e "${YELLOW}⚠ Port $PORT in use, killing existing process...${NC}"
    kill -9 $EXISTING_PID 2>/dev/null
    sleep 1
fi

# ── Start Frontend ──
echo -e "${CYAN}💻 Starting Frontend on http://127.0.0.1:$PORT${NC}"
cd "$FRONTEND_DIR"
npm run dev -- --port $PORT --host 0.0.0.0 &
PID=$!

echo -e "${GREEN}✓ Frontend ready — http://127.0.0.1:$PORT${NC}"
echo -e "${CYAN}Press Ctrl+C to stop${NC}"
wait
