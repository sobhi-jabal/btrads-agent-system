#!/bin/bash

echo "Starting BT-RADS Multi-Agent System..."

# Check if running on macOS or Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open_cmd="open"
else
    # Linux
    open_cmd="xdg-open"
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "Checking prerequisites..."

if ! command_exists python3; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

if ! command_exists npm; then
    echo "Error: Node.js/npm is not installed"
    exit 1
fi

if ! command_exists ollama; then
    echo "Warning: Ollama is not installed. The system requires Ollama for LLM functionality."
    echo "Please install Ollama from: https://ollama.ai"
fi

# Start backend
echo "Starting backend server..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
echo "Installing backend dependencies..."
pip install -r requirements.txt

# Start FastAPI in background
echo "Starting FastAPI server on http://localhost:8000..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

# Start frontend
echo "Starting frontend..."
cd ../frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start Next.js development server
echo "Starting Next.js server on http://localhost:3000..."
npm run dev &
FRONTEND_PID=$!

# Wait a bit for frontend to start
sleep 5

# Open browser
echo "Opening browser..."
$open_cmd http://localhost:3000

# Function to cleanup on exit
cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}

# Set up trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Keep script running
echo "System is running. Press Ctrl+C to stop."
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"

# Wait for background processes
wait