# Testing Scripts

This directory contains utility scripts for development and testing of the Telegram Dialog Processor.

## Mock API for Testing

These scripts allow you to test the frontend without needing to log in to Telegram. They provide dummy data and session handling for development purposes.

### Available Scripts

1. **create_dummy_session.py** - Creates a dummy session ID that can be used with the real API (if you've monkey-patched the client_sessions dictionary)
2. **generate_dummy_dialogs.py** - Generates random dialog and message data for testing
3. **mock_api.py** - Runs a standalone FastAPI server with mocked endpoints that return dummy data

## Usage

### Running the Mock API Server

This is the simplest way to start testing without a real Telegram connection. It creates a standalone server on port 8001 that mimics the real API:

```bash
cd backend
source ../.venv/bin/activate  # Activate the virtual environment
python scripts/mock_api.py
```

This will:
1. Start a FastAPI server on http://localhost:8001
2. Generate a random session ID
3. Save the session ID to `dummy_session.txt`
4. Automatically generate test data for dialogs and messages
5. Log API requests to the console for debugging

### Using the Mock API with the Frontend

When developing the frontend, you can point it to the mock API by setting the appropriate environment variables:

1. Edit your frontend `.env.local` file:
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001/api
```

2. Start your frontend development server and use the session ID from `dummy_session.txt` for testing.

### Creating Just a Dummy Session

If you want to create a dummy session ID for use with the regular backend API:

```bash
cd backend
source ../.venv/bin/activate
python scripts/create_dummy_session.py
```

This will print and save a session ID that you can use for testing.

### Generating Dummy Dialog Data

If you want to generate sample dialog and message data for testing:

```bash
cd backend
source ../.venv/bin/activate
python scripts/generate_dummy_dialogs.py
```

This will:
1. Create a dummy session
2. Generate random dialog and message data
3. Save the data to `dummy_dialogs.json` and `dummy_messages.json`

## Important Notes

- These scripts are for **development purposes only** and should not be used in production.
- The dummy data is randomly generated each time and doesn't persist between server restarts.
- No actual connection to Telegram is established when using these mocks. 