#!/bin/bash

# Function to kill both processes on exit
cleanup() {
    echo "Shutting down servers..."
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    # Also kill any remaining node/python processes related to our app
    pkill -f "python3 api.py" 2>/dev/null
    pkill -f "react-scripts start" 2>/dev/null
    exit
}

# Set up trap to catch termination signals
trap cleanup INT TERM EXIT

# Start Flask API in background
echo "Starting Flask API server on port 5001..."
(cd backend && python3 api.py) &
API_PID=$!

# Wait for API to start
echo "Waiting for Flask API to start..."
sleep 3

# Check if API is running
if ! lsof -i:5001 > /dev/null 2>&1; then
    echo "ERROR: Flask API failed to start on port 5001"
    echo "Please check if all Python dependencies are installed"
    cleanup
fi

# Start React app
# Using a subshell to ensure proper directory context
echo "Starting React frontend on port 3000..."
(cd frontend && PORT=3000 npm start) &
FRONTEND_PID=$!

# Wait for React to start (it takes longer)
echo "Waiting for React app to start (this may take up to 30 seconds)..."
for i in {1..30}; do
    if lsof -i:3000 > /dev/null 2>&1; then
        echo "React app started successfully!"
        break
    fi
    sleep 1
done

# Check if React is running
if ! lsof -i:3000 > /dev/null 2>&1; then
    echo "ERROR: React app failed to start on port 3000"
    echo "Please check if all npm dependencies are installed"
    echo "Run 'cd frontend && npm install' if needed"
    cleanup
fi

echo "========================"
echo "Services running:"
echo "- Flask API: http://localhost:5001"
echo "- React App: http://localhost:3000"
echo "========================"
echo "Press Ctrl+C to stop both servers"

# Wait for both processes
wait $API_PID $FRONTEND_PID