#!/bin/bash

# ── Chat Server Start Script ──
PORT=8889
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Cleanup on exit ──
cleanup() {
    echo -e "\n${YELLOW}🛑 Chat server stopped${NC}"
    [ -n "$PID" ] && kill "$PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Check python3 ──
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ python3 not found${NC}"
    exit 1
fi

# ── Kill existing process on port ──
EXISTING_PID=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
    echo -e "${YELLOW}⚠ Port $PORT in use, killing existing process...${NC}"
    kill -9 $EXISTING_PID 2>/dev/null
    sleep 1
fi

# ── Start Chat Server ──
echo -e "${CYAN}💬 Starting Chat Server on http://127.0.0.1:$PORT${NC}"
cd "$BACKEND_DIR"
python3 -m uvicorn chat_server:app --reload --port $PORT --host 0.0.0.0 &
PID=$!

# ── Wait for ready ──
echo -e "${YELLOW}⏳ Waiting for chat server...${NC}"
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:$PORT/" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Chat server ready — http://127.0.0.1:$PORT${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Chat server failed to start${NC}"
        kill $PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

echo -e "${CYAN}Press Ctrl+C to stop${NC}"
wait
