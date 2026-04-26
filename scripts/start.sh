#!/bin/bash

# ══════════════════════════════════════════════════════════════
# 🤖 AgentForge — Unified Control Center
# ══════════════════════════════════════════════════════════════
# Robust, beautiful, and intelligent startup manager.
# ══════════════════════════════════════════════════════════════

# ── Configuration ──
BACKEND_PORT=8888
FRONTEND_PORT=5173
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# ── Visuals ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

BANNER="
${CYAN}${BOLD}    ___                         __  ______                      
   /   | ____ ____  ____  / /_/ ____/___  _________ ____ 
  / /| |/ __ \/ __ \/ __ \/ __/ /_  / __ \/ ___/ __ \/ __ \\
 / ___ / /_/ / /_/ / / / / /_/ __/ / /_/ / /  / /_/ / /_/ /
/_/  |_\__, /\__,_/_/ /_/\__/_/    \____/_/   \__, /\____/ 
      /____/                                 /____/        ${NC}
"

log() { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $1"; }
info() { echo -e "${BLUE}${BOLD}ℹ${NC} $1"; }
success() { echo -e "${GREEN}${BOLD}✓${NC} $1"; }
warn() { echo -e "${YELLOW}${BOLD}⚠${NC} $1"; }
error() { echo -e "${RED}${BOLD}✗${NC} $1"; }

# ── Prerequisite Checks ──
check_requirements() {
    echo -e "$BANNER"
    info "Initializing AgentForge Environment..."

    # Check for Ollama
    if command -v ollama &> /dev/null; then
        if curl -s http://localhost:11434/api/tags > /dev/null; then
            success "Ollama is running"
        else
            warn "Ollama is installed but not running. Starting agents might fail."
            info "Suggestion: Run ${BOLD}ollama serve${NC} in a separate terminal."
        fi
    else
        warn "Ollama not found. Local inference will be unavailable."
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "python3 is required but not installed."
        exit 1
    fi

    # Check Node/NPM
    if ! command -v npm &> /dev/null; then
        error "npm is required but not installed."
        exit 1
    fi

    success "Basic prerequisites verified."
}

# ── Cleanup ──
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down AgentForge...${NC}"
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && success "Backend process terminated"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && success "Frontend process terminated"
    exit 0
}
trap cleanup SIGINT SIGTERM

kill_port() {
    local pid=$(lsof -ti:$1 2>/dev/null)
    if [ -n "$pid" ]; then
        warn "Port $1 is busy (PID: $pid). Clearing..."
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

# ── Service Launchers ──
start_backend() {
    info "Starting ${PURPLE}Backend Engine${NC} on port $BACKEND_PORT..."

    # Virtual Environment Detection
    if [ -d "$PROJECT_DIR/.venv" ]; then
        BACKEND_PYTHON="$PROJECT_DIR/.venv/bin/python"
    elif [ -d "$BACKEND_DIR/.venv" ]; then
        BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
    else
        BACKEND_PYTHON="$(command -v python3)"
    fi

    if [ ! -x "$BACKEND_PYTHON" ]; then
        error "Python executable not found at $BACKEND_PYTHON"
        exit 1
    fi

    # Install dependencies if missing (optimized check)
    if ! "$BACKEND_PYTHON" -c "import fastapi, uvicorn, mcp" 2>/dev/null; then
        info "Installing backend dependencies (this may take a moment)..."
        "$BACKEND_PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt" || {
            error "Dependency installation failed."
            exit 1
        }
    fi

    kill_port $BACKEND_PORT

    cd "$BACKEND_DIR"
    # Run uvicorn in background, redirecting logs to a file but showing errors
    "$BACKEND_PYTHON" -m uvicorn main:app --reload --port $BACKEND_PORT --host 0.0.0.0 > /tmp/agentforge_backend.log 2>&1 &
    BACKEND_PID=$!
    cd "$PROJECT_DIR"

    # Wait for readiness
    info "Waiting for backend heartbeat..."
    for i in $(seq 1 30); do
        if curl -s "http://127.0.0.1:$BACKEND_PORT/" > /dev/null 2>&1; then
            success "Backend is alive at ${CYAN}http://127.0.0.1:$BACKEND_PORT${NC}"
            return 0
        fi
        if ! kill -0 $BACKEND_PID 2>/dev/null; then
            error "Backend crashed on startup. See /tmp/agentforge_backend.log"
            exit 1
        fi
        sleep 1
    done
    error "Backend timed out. Check /tmp/agentforge_backend.log"
    exit 1
}

start_frontend() {
    info "Starting ${BLUE}Frontend Interface${NC} on port $FRONTEND_PORT..."

    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        info "Installing frontend dependencies..."
        npm install --prefix "$FRONTEND_DIR" || {
            error "Frontend installation failed."
            exit 1
        }
    fi

    kill_port $FRONTEND_PORT

    cd "$FRONTEND_DIR"
    # Run vite in background
    npm run dev -- --port $FRONTEND_PORT --host 0.0.0.0 > /tmp/agentforge_frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd "$PROJECT_DIR"

    success "Frontend is launching at ${CYAN}http://127.0.0.1:$FRONTEND_PORT${NC}"
}

# ── Main ──
case "${1:-all}" in
    stop)
        info "Stopping all AgentForge services..."
        kill_port $BACKEND_PORT
        kill_port $FRONTEND_PORT
        success "Cleanup complete."
        exit 0
        ;;
    backend)
        check_requirements
        start_backend
        echo -e "\n${GREEN}${BOLD}✅ Backend is running in background.${NC}"
        info "Tail logs with: ${YELLOW}tail -f /tmp/agentforge_backend.log${NC}"
        info "Press Ctrl+C to stop."
        wait $BACKEND_PID
        ;;
    frontend)
        check_requirements
        start_frontend
        echo -e "\n${GREEN}${BOLD}✅ Frontend is running in background.${NC}"
        info "Tail logs with: ${YELLOW}tail -f /tmp/agentforge_frontend.log${NC}"
        info "Press Ctrl+C to stop."
        wait $FRONTEND_PID
        ;;
    all|"")
        check_requirements
        start_backend
        start_frontend
        
        echo -e "\n${GREEN}${BOLD}🚀 AgentForge is fully operational!${NC}"
        echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "  📡 ${BOLD}Backend:${NC}   ${CYAN}http://127.0.0.1:$BACKEND_PORT${NC}"
        echo -e "  🎨 ${BOLD}Frontend:${NC}  ${CYAN}http://127.0.0.1:$FRONTEND_PORT${NC}"
        echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "  📝 Logs: ${YELLOW}tail -f /tmp/agentforge_backend.log /tmp/agentforge_frontend.log${NC}"
        echo ""
        info "Monitoring processes... Press ${RED}Ctrl+C${NC} to stop everything."
        
        # Monitor both processes
        while kill -0 $BACKEND_PID 2>/dev/null && kill -0 $FRONTEND_PID 2>/dev/null; do
            sleep 2
        done
        
        warn "One of the services has stopped unexpectedly."
        cleanup
        ;;
    *)
        echo -e "${RED}Usage:${NC} $0 [all|backend|frontend|stop]"
        exit 1
        ;;
esac
