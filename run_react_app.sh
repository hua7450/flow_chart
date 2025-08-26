#!/bin/bash

# Start Flask API in background
echo "Starting Flask API server on port 5001..."
python3 api.py &
API_PID=$!

# Wait for API to start
sleep 2

# Start React app
echo "Starting React frontend on port 3000..."
cd frontend && npm start &
FRONTEND_PID=$!

# Function to kill both processes on exit
cleanup() {
    echo "Shutting down servers..."
    kill $API_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}

# Set up trap to catch termination signals
trap cleanup INT TERM

echo "========================"
echo "Services running:"
echo "- Flask API: http://localhost:5001"
echo "- React App: http://localhost:3000"
echo "========================"
echo "Press Ctrl+C to stop both servers"

# Wait for both processes
wait $API_PID $FRONTEND_PID