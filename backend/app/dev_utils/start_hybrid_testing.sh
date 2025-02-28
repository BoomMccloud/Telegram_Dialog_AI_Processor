#!/bin/bash

# Start Hybrid Testing Environment for Telegram Dialog Processor
#
# This script:
# 1. Starts the FastAPI server with APP_ENV=development
# 2. Creates a mock session for testing
# 3. Provides example API commands

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a port is in use
is_port_in_use() {
  lsof -i:"$1" >/dev/null 2>&1
  return $?
}

echo -e "${BLUE}=== Starting Hybrid Testing Environment ===${NC}"

# Check if we're in the right directory
if [ ! -d "app" ]; then
  echo -e "${YELLOW}This script should be run from the backend directory.${NC}"
  echo -e "Current directory: $(pwd)"
  echo -e "Please run: cd backend && ./app/dev_utils/start_hybrid_testing.sh"
  exit 1
fi

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
  echo -e "${YELLOW}Python virtual environment not activated.${NC}"
  echo -e "Please run: source ../.venv/bin/activate"
  exit 1
fi

# Check if port 8000 is already in use
if is_port_in_use 8000; then
  echo -e "${YELLOW}Port 8000 is already in use. There may be another server running.${NC}"
  echo -e "You can either:"
  echo -e "1. Kill the existing process using: kill \$(lsof -ti:8000)"
  echo -e "2. Use a different port by modifying this script"
  
  read -p "Would you like to kill the existing process? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    kill $(lsof -ti:8000)
    echo -e "Process killed. Continuing..."
  else
    echo -e "Aborting. Please stop the existing server before running this script."
    exit 1
  fi
fi

# Run backend server in a background process
echo -e "${BLUE}Starting FastAPI server with development environment...${NC}"
APP_ENV=development PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > server.log 2>&1 &
SERVER_PID=$!

# Give server time to start
echo -e "Waiting for server to start..."
sleep 3

# Check if server started successfully
if ! is_port_in_use 8000; then
  echo -e "${YELLOW}Failed to start server. Check server.log for details.${NC}"
  kill $SERVER_PID 2>/dev/null
  exit 1
fi

echo -e "${GREEN}Server running with PID: $SERVER_PID${NC}"

# Set up the hybrid testing environment
echo -e "${BLUE}Setting up hybrid testing environment...${NC}"
PYTHONPATH=. python -m app.dev_utils.setup_hybrid_testing

echo -e "\n${BLUE}=== Hybrid Testing Environment Ready ===${NC}"
echo -e "• API server is running on: http://localhost:8000"
echo -e "• Check server.log for API server output"
echo -e "• To stop the server, run: kill $SERVER_PID"
echo -e "• Mock session ID is saved in: app/dev_utils/mock_session.txt"

# Read the session ID
if [ -f "app/dev_utils/mock_session.txt" ]; then
  SESSION_ID=$(cat app/dev_utils/mock_session.txt)
  
  echo -e "\n${BLUE}Example curl commands:${NC}"
  echo -e "export SESSION_ID=$SESSION_ID"
  echo -e "curl -X GET http://localhost:8000/api/dialogs/\$SESSION_ID"
  echo -e "curl -X POST http://localhost:8000/api/dialogs/\$SESSION_ID/select -H \"Content-Type: application/json\" -d '{\"dialog_id\": -10000000, \"dialog_name\": \"Laura\"}'"
  echo -e "curl -X GET http://localhost:8000/api/dialogs/\$SESSION_ID/selected"
  echo -e "curl -X DELETE http://localhost:8000/api/dialogs/\$SESSION_ID/selected/-10000000"
fi

echo -e "\n${GREEN}Hybrid testing environment is ready! Press Ctrl+C to exit.${NC}"

# Keep script running until user interrupts
trap "echo -e '\n${YELLOW}Shutting down server...${NC}'; kill $SERVER_PID; echo -e '${GREEN}Server stopped.${NC}'; exit 0" INT
while true; do sleep 1; done 