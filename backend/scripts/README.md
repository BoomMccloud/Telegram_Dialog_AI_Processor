# Testing Scripts

This directory contains utility scripts for development and testing of the Telegram Dialog Processor.

## Mock API for Testing

These scripts allow you to test the frontend without needing to log in to Telegram. They provide dummy data and session handling for development purposes.

### Available Scripts

1. **create_dummy_session.py** - Creates a dummy session ID that can be used with the real API (if you've monkey-patched the client_sessions dictionary)
2. **generate_dummy_dialogs.py** - Generates random dialog and message data for testing
3. **mock_api.py** - Runs a standalone FastAPI server with mocked endpoints that return dummy data
4. **test_dialog_selection.py** - Tests the dialog selection API endpoints (select, list, deselect)

## Understanding Session Management

The Telegram Dialog Processor uses a dual-dictionary approach to session management:

1. **Client Sessions Management**:
   - `client_sessions` in `app/services/auth.py` stores authentic Telegram client connections
   - All API endpoints check this dictionary for valid sessions
   - Each session contains a Telegram client object, expiry time, and authentication status

2. **Mock Sessions Management**:
   - Our mock API uses both `mock_sessions` (for simplified management) and properly syncs to `client_sessions`
   - The `sync_to_client_sessions()` function ensures both dictionaries contain consistent data
   - A session must exist in both dictionaries for the mock API to work correctly

**Common Error**: If you experience "Invalid or expired session" errors, it's likely because the session exists in one dictionary but not the other, or has expired.

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

### Testing Dialog Selection API

To test the dialog selection API endpoints:

```bash
cd backend
source ../.venv/bin/activate  # Activate the virtual environment
python scripts/test_dialog_selection.py
```

This will:
1. Get or create a session ID
2. Test selecting a dialog from the available dialogs
3. Test retrieving selected dialogs
4. Test deselecting a dialog
5. Test updating an existing dialog selection with new settings

The script will output detailed information about each step and any errors encountered.

### Available API Endpoints

The mock API provides the following endpoints:

1. **Authentication Endpoints**:
   - `POST /api/auth/qr` - Create a mock authentication session
   - `GET /api/auth/session/{session_id}` - Check session status

2. **Dialog Endpoints**:
   - `GET /api/dialogs/{session_id}` - Get list of available dialogs
   - `POST /api/dialogs/{session_id}/select` - Select a dialog for processing
   - `GET /api/dialogs/{session_id}/selected` - Get list of selected dialogs
   - `DELETE /api/dialogs/{session_id}/selected/{dialog_id}` - Deselect a dialog

3. **Message Endpoints**:
   - `GET /api/messages/{session_id}` - Get messages from all dialogs
   - `POST /api/messages/{session_id}/send` - Mock sending a message

### Using the Mock API with the Frontend

When developing the frontend, you can point it to the mock API by setting the appropriate environment variables:

1. Edit your frontend `.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:8001/api
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
- All mock sessions are automatically authenticated with a fake user ID (12345678).
- The mock API properly handles CORS, allowing frontend development from any origin. 