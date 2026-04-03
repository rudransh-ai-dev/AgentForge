#!/bin/bash

# ── Backend Start Script ──
PORT=8888
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Cleanup on exit ──
cleanup() {
    echo -e "\n${YELLOW}🛑 Backend stopped${NC}"
    [ -n "$PID" ] && kill "$PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Check python3 ──
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ python3 not found${NC}"
    exit 1
fi

# ── Install deps if needed ──
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Installing backend dependencies...${NC}"
    pip3 install -r "$BACKEND_DIR/requirements.txt" || {
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

# ── Start Backend ──
echo -e "${CYAN}🌐 Starting Backend on http://127.0.0.1:$PORT${NC}"
cd "$BACKEND_DIR"
python3 -m uvicorn main:app --reload --port $PORT --host 0.0.0.0 &
PID=$!

# ── Wait for ready ──
echo -e "${YELLOW}⏳ Waiting for backend...${NC}"
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:$PORT/" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend ready — http://127.0.0.1:$PORT${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Backend failed to start${NC}"
        kill $PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

echo -e "${CYAN}Press Ctrl+C to stop${NC}"
wait
