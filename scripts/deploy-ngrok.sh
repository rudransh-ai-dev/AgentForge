#!/bin/bash
# ── ngrok Public Deploy ──
# Exposes the frontend (port 5173) and backend (port 8888) publicly via ngrok.
# Usage: ./deploy-ngrok.sh [ngrok-authtoken]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# ── Auth token ──
if [ -n "$1" ]; then
    ngrok config add-authtoken "$1"
elif [ -z "$NGROK_AUTHTOKEN" ]; then
    echo -e "${YELLOW}⚠  No authtoken provided. If tunnels fail, run:${NC}"
    echo -e "   ngrok config add-authtoken <your-token>"
    echo -e "   Get a free token at: https://dashboard.ngrok.com/get-started/your-authtoken"
fi

# ── Check services are up ──
echo -e "${CYAN}Checking backend (port 8888)...${NC}"
if ! curl -s http://127.0.0.1:8888/health > /dev/null 2>&1; then
    echo -e "${YELLOW}Backend not running. Starting it...${NC}"
    bash "$SCRIPTS_DIR/start-backend.sh" &
    sleep 5
fi

echo -e "${CYAN}Checking frontend (port 5173)...${NC}"
if ! curl -s http://127.0.0.1:5173 > /dev/null 2>&1; then
    echo -e "${YELLOW}Frontend not running. Starting it...${NC}"
    bash "$SCRIPTS_DIR/start-frontend.sh" &
    sleep 5
fi

# ── Write ngrok config ──
NGROK_CONFIG="$PROJECT_DIR/.ngrok.yml"
cat > "$NGROK_CONFIG" << EOF
version: "2"
tunnels:
  frontend:
    proto: http
    addr: 5173
    inspect: false
  backend:
    proto: http
    addr: 8888
    inspect: false
EOF

# ── Start ngrok ──
echo ""
echo -e "${BOLD}${GREEN}Starting ngrok tunnels...${NC}"
echo -e "${YELLOW}Ctrl+C to stop${NC}"
echo ""

ngrok start --all --config "$NGROK_CONFIG" &
NGROK_PID=$!

# ── Wait for ngrok API to come up ──
sleep 3

# ── Print public URLs ──
TUNNELS=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null)
if [ -n "$TUNNELS" ]; then
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${GREEN}  Public URLs${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "$TUNNELS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('tunnels', []):
    name = t.get('name', '?')
    url = t.get('public_url', '?')
    label = 'Frontend (UI)' if 'frontend' in name else 'Backend  (API)'
    print(f'  {label}: {url}')
" 2>/dev/null || echo "$TUNNELS"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}ngrok dashboard: http://127.0.0.1:4040${NC}"
else
    echo -e "${YELLOW}ngrok starting... check http://127.0.0.1:4040 for URLs${NC}"
fi

wait $NGROK_PID
