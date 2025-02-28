# Development Utilities for Telegram Dialog Processor

This directory contains development utilities for testing and debugging the Telegram Dialog Processor without requiring an actual Telegram connection.

## Session Management Improvements

The application now uses a persistent file-based session storage system that offers several advantages:

1. **Server Restart Resilience**: Sessions persist across server restarts
2. **Cross-Process Communication**: Sessions created in one process (scripts) are accessible to others (FastAPI server)
3. **Improved Reliability**: More robust handling of session expiry and validation
4. **Debug Visibility**: Session files can be examined for troubleshooting

Session files are stored in the `sessions/data` directory, with one JSON file per session.

## Hybrid Testing Environment

The hybrid testing environment allows you to:

1. Use mock Telegram authentication for development
2. Test database operations with real PostgreSQL
3. Use mock dialogs and messages for UI development
4. Easily switch between development and production modes

### Setting Up the Hybrid Testing Environment

To set up the hybrid testing environment:

```bash
# Activate the virtual environment
source ../.venv/bin/activate

# Make sure you're in the backend directory
cd backend

# Start the hybrid testing environment
bash ./app/dev_utils/start_hybrid_testing.sh
```

This script will:

1. Start the FastAPI server with development configuration
2. Generate mock dialog and message data
3. Inject a mock authenticated session
4. Provide example API commands for testing

### Mock Session Injection

The `inject_mock_session.py` script creates a mock authenticated session that can be used with the real API endpoints:

```python
# Run from the backend directory:
PYTHONPATH=. python -m app.dev_utils.inject_mock_session
```

This will:

1. Create a mock session with fake user_id (12345678)
2. Add it to both in-memory storage and persistent file storage
3. Return a session ID that can be used with real API endpoints
4. Save the session ID to `app/dev_utils/mock_session.txt` for reference

If you encounter "Invalid or expired session" errors, try:

1. Ensure the FastAPI server is running with APP_ENV=development
2. Re-inject a mock session
3. Verify the session file exists in sessions/data directory
4. Check if the session has expired (24-hour lifetime)

### Mock Data Generation

The `mock_data_generator.py` script creates realistic mock dialog and message data:

```python
# Run from the backend directory:
PYTHONPATH=. python -m app.dev_utils.mock_data_generator
```

This generates:

1. **mock_dialogs.json**: A list of mock Telegram dialogs (chats)
2. **mock_messages.json**: A collection of mock messages for each dialog

## Development Routes

When the application runs with `APP_ENV=development`, special development routes are enabled:

1. **GET /api/dialogs/{session_id}**: Returns mock dialogs instead of real Telegram data
2. **GET /api/messages/{session_id}**: Returns mock messages instead of real Telegram data

These routes use the same authentication mechanism as the regular routes but return mock data.

## Additional Documentation

For more detailed information about the mock session system, including troubleshooting and API testing examples, please refer to the [Mock Session Development Guide](./MOCK_SESSION_GUIDE.md). 