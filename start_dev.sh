#!/bin/bash

# Bengali Dataset Manager - Development Startup Script
# This runs API server and Frontend together

echo "=================================================="
echo "🚀 Bengali Dataset Manager - Starting Dev Server"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "Run: python3.11 -m venv .venv"
    exit 1
fi

# Set Python path to use virtual environment
PYTHON_BIN=".venv/bin/python"
echo "🐍 Using Python: $PYTHON_BIN"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "Run: cp .env.example .env and configure it"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check database connection
echo "📊 Testing database connection..."
psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Database connection failed"
    echo "Check your DATABASE_URL in .env"
    exit 1
fi
echo "✅ Database connected"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $API_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Servers stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start API server
echo "🔧 Starting API server on port 5000..."
cd api
../$PYTHON_BIN app.py > ../logs/api.log 2>&1 &
API_PID=$!
cd ..

# Wait for API to start
sleep 3

# Check if API started successfully
curl -s http://localhost:5000/api/health > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ API server failed to start"
    echo "Check logs/api.log for details"
    kill $API_PID 2>/dev/null
    exit 1
fi
echo "✅ API server running (PID: $API_PID)"
echo ""

# Start Frontend
echo "🎨 Starting Frontend on port 3000..."
cd frontend
npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "=================================================="
echo "✅ Development servers started successfully!"
echo "=================================================="
echo ""
echo "🌐 Frontend:  http://localhost:3000"
echo "🔧 API:       http://localhost:5000"
echo "📊 API Health: http://localhost:5000/api/health"
echo ""
echo "📝 Logs:"
echo "   API:      tail -f logs/api.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for processes
wait $API_PID $FRONTEND_PID