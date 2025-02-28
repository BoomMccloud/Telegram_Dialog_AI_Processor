# Dialog Selection API

This document describes the Dialog Selection API endpoints and how to use them in the Telegram Dialog Processor.

## Overview

The Dialog Selection API allows users to:
- Select which Telegram dialogs (chats) they want the system to process
- Specify processing settings for each dialog
- Enable or disable auto-replies for specific dialogs
- Set priorities for dialog processing
- Manage their selections through a web interface

## API Endpoints

### Select a Dialog

```
POST /api/dialogs/{session_id}/select
```

Adds a dialog to the user's selected dialogs list or updates an existing selection.

**Request Body:**
```json
{
  "dialog_id": 123456789,
  "dialog_name": "Chat Name",
  "processing_enabled": true,
  "auto_reply_enabled": false,
  "response_approval_required": true,
  "priority": 5,
  "processing_settings": {
    "max_context_messages": 10,
    "response_style": "concise"
  }
}
```

**Required Fields:**
- `dialog_id`: The Telegram dialog ID (integer)
- `dialog_name`: The name of the dialog (string)

**Optional Fields:**
- `processing_enabled`: Whether message processing is enabled (boolean, default: true)
- `auto_reply_enabled`: Whether auto-reply is enabled (boolean, default: false)
- `response_approval_required`: Whether response approval is required (boolean, default: true)
- `priority`: Processing priority (integer, default: 0)
- `processing_settings`: Additional processing settings (JSON object)

**Response:**
Returns the created or updated dialog selection record.

### Get Selected Dialogs

```
GET /api/dialogs/{session_id}/selected
```

Retrieves the list of dialogs that the user has selected for processing.

**Response:**
Returns an array of dialog selection records sorted by priority (highest first) and then by dialog name.

### Deselect a Dialog

```
DELETE /api/dialogs/{session_id}/selected/{dialog_id}
```

Removes a dialog from the user's selected dialogs list by marking it as inactive.

**Response:**
```json
{
  "status": "success",
  "message": "Dialog removed from selection"
}
```

## Database Schema

The dialog selections are stored in the `user_selected_dialogs` table with the following schema:

```sql
CREATE TABLE user_selected_dialogs (
    selection_id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL,
    dialog_id BIGINT NOT NULL,
    dialog_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    processing_enabled BOOLEAN DEFAULT true,
    auto_reply_enabled BOOLEAN DEFAULT false,
    response_approval_required BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_processed_at TIMESTAMP WITH TIME ZONE,
    processing_settings JSONB,
    UNIQUE(user_id, dialog_id)
)
```

## Testing

You can test these API endpoints using the `test_dialog_selection.py` script in the `backend/scripts` directory:

```bash
cd backend
source ../.venv/bin/activate
python scripts/test_dialog_selection.py
```

The script will:
1. Get or create a session ID
2. Test selecting a dialog
3. Test retrieving selected dialogs
4. Test deselecting a dialog
5. Test updating an existing dialog selection

## Mock API for Development

During development, you can use the mock API server which provides in-memory implementations of these endpoints:

```bash
cd backend
source ../.venv/bin/activate
python scripts/mock_api.py
```

The mock API will run on port 8001 by default and will automatically create test sessions as needed.

## Integration with Processing Logic

The dialog selection system integrates with the message processing pipeline in the following ways:

1. **Message Filtering**: Only messages from selected dialogs will be processed
2. **Processing Options**: Each dialog can have custom processing settings
3. **Auto-Reply Control**: You can enable or disable auto-replies on a per-dialog basis
4. **Prioritization**: Messages from higher-priority dialogs are processed first

## Frontend Integration

The frontend can use these API endpoints to:
1. Display a list of available Telegram dialogs
2. Allow users to select which dialogs to process
3. Configure processing settings for each dialog
4. Manage existing selections

For example, to select a dialog from the frontend:

```javascript
const response = await fetch(`/api/dialogs/${sessionId}/select`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    dialog_id: selectedDialog.id,
    dialog_name: selectedDialog.name,
    processing_enabled: true,
    auto_reply_enabled: false,
    priority: 5
  }),
});

const result = await response.json();
console.log('Dialog selected:', result);
``` 