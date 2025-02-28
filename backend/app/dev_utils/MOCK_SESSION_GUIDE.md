# Mock Session Development Guide

This guide explains how to effectively use the mock session system for developing and testing the Telegram Dialog Processor without requiring a real Telegram connection.

## Overview

The improved mock session system provides:

1. **Persistent Sessions**: Sessions are stored in files and memory, ensuring they survive server restarts
2. **Mock Client Objects**: Each session includes a mock Telegram client that responds to essential methods
3. **Development-Only API Routes**: Special routes return mock data when in development mode
4. **Simple Testing Workflow**: Easy to create, inject, and use mock sessions

## Quick Start Guide

### 1. Start the Backend Server in Development Mode

```bash
# From the backend directory
PYTHONPATH=. APP_ENV=development uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Generate a Mock Session

```bash
# From the backend directory
PYTHONPATH=. python -m app.dev_utils.inject_mock_session
```

This will output a session ID and save it to `app/dev_utils/mock_session.txt`.

### 3. Set the Session ID in the Frontend

Option 1: Open your browser console in the frontend application and run:
```javascript
localStorage.setItem('sessionId', 'your-session-id-here');
console.log('Session ID set!');
```

Option 2: Copy the content from `get_session_for_frontend.js` to your browser console.

### 4. Navigate to the Messages Page

The frontend should now load mock dialogs and messages without needing a real Telegram connection.

## How It Works

### Mock Session Injection

The `inject_mock_session.py` script:
1. Creates a UUID for the session
2. Instantiates a `MockTelegramClient` object that simulates Telegram methods
3. Stores the session in both memory (`client_sessions`) and on disk
4. Outputs the session ID for use with API endpoints

### Development API Routes

The `dev_routes.py` file contains development-only API routes that:
1. Override the standard routes with the same URL patterns
2. Only validate that the session exists (not that it's connected to Telegram)
3. Return mock data from `dependencies.py` functions
4. Have higher priority in the FastAPI router

### Mock Telegram Client

The `MockTelegramClient` class in `inject_mock_session.py`:
1. Always reports itself as authorized (`is_user_authorized()` returns True)
2. Implements stub methods for `iter_dialogs()`, `iter_messages()`, etc.
3. Allows the development API endpoints to validate sessions correctly

## Troubleshooting

### "Invalid or expired session" Error

If you encounter this error:
1. Check that your server is running in development mode (`APP_ENV=development`)
2. Generate a new mock session using `inject_mock_session.py`
3. Update the session ID in your frontend localStorage
4. Verify the session file exists in the `sessions/data` directory

### Development Routes Not Loading

If the development routes aren't being used:
1. Ensure `APP_ENV=development` is set when starting the server
2. Check that the server output includes "Development routes added with priority"
3. Verify the route priority in `main.py` (dev routes should be added first)

### Frontend Can't Connect to API

If your frontend can't connect to the API:
1. Check browser console for CORS errors
2. Verify the API URL in `.env.local` matches your backend server
3. Ensure the session ID in localStorage is valid
4. Test the API directly using curl as shown in this guide

## API Testing Examples

```bash
# Test session status
curl -X GET "http://localhost:8000/api/auth/session/{session_id}" | json_pp

# Get mock dialogs
curl -X GET "http://localhost:8000/api/dialogs/{session_id}" | json_pp

# Get mock messages
curl -X GET "http://localhost:8000/api/messages/{session_id}" | json_pp
```

## Notes for Developers

1. The mock session implementation is in `app/dev_utils/inject_mock_session.py`
2. Development API routes are in `app/api/dev_routes.py`
3. Mock data generators are in `app/api/dependencies.py`
4. The session ID is persisted to `app/dev_utils/mock_session.txt` for reference
5. Session files are stored in `sessions/data/` with JSON format 