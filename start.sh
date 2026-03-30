#!/bin/bash

# Configuration
BACKEND_PORT=8888
FRONTEND_PORT=5173

echo "🚀 Starting AI Orchestrator..."

# 1. Start Backend
echo "🌐 Starting Backend on port $BACKEND_PORT..."
cd backend
python3 -m uvicorn main:app --reload --port $BACKEND_PORT &
BACKEND_PID=$!
cd ..

# 2. Start Frontend
echo "💻 Starting Frontend on port $FRONTEND_PORT..."
cd frontend
npm run dev -- --port $FRONTEND_PORT &
FRONTEND_PID=$!
cd ..

echo "✅ Both services are starting!"
echo "📡 Backend: http://127.0.0.1:$BACKEND_PORT"
echo "🎨 Frontend: http://127.0.0.1:$FRONTEND_PORT"
echo "----------------------------------------"
echo "To stop everything, run: kill $BACKEND_PID $FRONTEND_PID"

# Wait for background processes
wait
