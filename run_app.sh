#!/bin/bash

# Start Flask API in background
echo "Starting Flask API server..."
python3 api.py &
API_PID=$!

# Wait for API to start
sleep 2

# Start React app
echo "Starting React frontend..."
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

# Wait for both processes
wait $API_PID $FRONTEND_PID