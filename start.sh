#!/bin/bash

# ══════════════════════════════════════════════════════════════
# AI Agent IDE — Unified Start Script
# ══════════════════════════════════════════════════════════════
# Usage:
#   ./start.sh              — Start everything (backend + frontend)
#   ./start.sh backend      — Start backend only
#   ./start.sh frontend     — Start frontend only
#   ./start.sh all          — Start everything
#   ./start.sh stop         — Stop all services
# ══════════════════════════════════════════════════════════════

BACKEND_PORT=8888
FRONTEND_PORT=5173
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Cleanup on exit ──
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down...${NC}"
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && echo -e "${GREEN}✓ Backend stopped${NC}"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && echo -e "${GREEN}✓ Frontend stopped${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

kill_port() {
    local pid=$(lsof -ti:$1 2>/dev/null)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}⚠ Port $1 in use, killing existing process...${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

stop_all() {
    echo -e "${YELLOW}🛑 Stopping all services...${NC}"
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    echo -e "${GREEN}✓ All services stopped${NC}"
    exit 0
}

start_backend() {
    echo -e "${CYAN}🌐 Starting Backend on port $BACKEND_PORT...${NC}"

    if [ -d "$PROJECT_DIR/.venv" ]; then
        source "$PROJECT_DIR/.venv/bin/activate"
    elif [ -d "$BACKEND_DIR/.venv" ]; then
        source "$BACKEND_DIR/.venv/bin/activate"
    fi

    if ! python3 -c "import fastapi, mcp" 2>/dev/null; then
        echo -e "${YELLOW}⚠ Installing backend dependencies...${NC}"
        pip3 install -r "$BACKEND_DIR/requirements.txt" || {
            echo -e "${RED}✗ Failed to install backend dependencies${NC}"
            exit 1
        }
    fi

    kill_port $BACKEND_PORT

    cd "$BACKEND_DIR"
    python3 -m uvicorn main:app --reload --port $BACKEND_PORT --host 0.0.0.0 &
    BACKEND_PID=$!
    cd "$PROJECT_DIR"

    echo -e "${YELLOW}⏳ Waiting for backend...${NC}"
    for i in $(seq 1 30); do
        if curl -s "http://127.0.0.1:$BACKEND_PORT/" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend ready — http://127.0.0.1:$BACKEND_PORT${NC}"
            return 0
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}✗ Backend failed to start${NC}"
            kill $BACKEND_PID 2>/dev/null
            exit 1
        fi
        sleep 1
    done
}

start_frontend() {
    echo -e "${CYAN}💻 Starting Frontend on port $FRONTEND_PORT...${NC}"

    if ! command -v npm &> /dev/null; then
        echo -e "${RED}✗ npm not found${NC}"
        exit 1
    fi

    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo -e "${YELLOW}⚠ Installing frontend dependencies...${NC}"
        npm install --prefix "$FRONTEND_DIR" || {
            echo -e "${RED}✗ Failed to install frontend dependencies${NC}"
            exit 1
        }
    fi

    kill_port $FRONTEND_PORT

    cd "$FRONTEND_DIR"
    npm run dev -- --port $FRONTEND_PORT --host 0.0.0.0 &
    FRONTEND_PID=$!
    cd "$PROJECT_DIR"

    echo -e "${GREEN}✓ Frontend ready — http://127.0.0.1:$FRONTEND_PORT${NC}"
}

# ── Main ──
case "${1:-all}" in
    stop)
        stop_all
        ;;
    backend)
        start_backend
        echo -e "\n${GREEN}✅ Backend running!${NC}"
        echo -e "  📡 Backend: ${CYAN}http://127.0.0.1:$BACKEND_PORT${NC}"
        echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop"
        wait
        ;;
    frontend)
        start_frontend
        echo -e "\n${GREEN}✅ Frontend running!${NC}"
        echo -e "  🎨 Frontend: ${CYAN}http://127.0.0.1:$FRONTEND_PORT${NC}"
        echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop"
        wait
        ;;
    all|"")
        echo -e "${CYAN}🔍 Checking prerequisites...${NC}"

        if ! command -v python3 &> /dev/null; then
            echo -e "${RED}✗ python3 not found${NC}"
            exit 1
        fi

        if ! command -v npm &> /dev/null; then
            echo -e "${RED}✗ npm not found${NC}"
            exit 1
        fi

        echo -e "${GREEN}✓ All prerequisites met${NC}"

        start_backend
        start_frontend

        echo -e "\n${GREEN}✅ Both services running!${NC}"
        echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "  📡 Backend:  ${CYAN}http://127.0.0.1:$BACKEND_PORT${NC}"
        echo -e "  🎨 Frontend: ${CYAN}http://127.0.0.1:$FRONTEND_PORT${NC}"
        echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop everything"
        echo ""
        wait
        ;;
    *)
        echo -e "${RED}Usage:${NC} $0 [all|backend|frontend|stop]"
        exit 1
        ;;
esac
