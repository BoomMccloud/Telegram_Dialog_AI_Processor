# Database Schema and Management

## Overview

This directory contains the database models, migrations, and utilities for the Telegram Dialog AI Processor. The system uses PostgreSQL with SQLAlchemy ORM for database management.

## Schema Structure

### Enums

- **SessionStatus**
  - Values: `PENDING`, `AUTHENTICATED`, `ERROR`, `EXPIRED`
  - Used for tracking web session states
  - `PENDING`: Initial state when session is created
  - `AUTHENTICATED`: User has successfully logged in
  - `ERROR`: Authentication failed
  - `EXPIRED`: Session has timed out or been invalidated

- **TokenType**
  - Values: `ACCESS`, `REFRESH`
  - Used for JWT token types in web authentication
  - `ACCESS`: Short-lived token for API access
  - `REFRESH`: Long-lived token for obtaining new access tokens

- **DialogType**
  - Values: `PRIVATE`, `GROUP`, `CHANNEL`
  - Represents different types of Telegram dialogs
  - Affects how messages are processed and responses are sent

- **ProcessingStatus**
  - Values: `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `SENT`, `FAILED`
  - Tracks the status of AI-processed responses
  - `PENDING_APPROVAL`: Response generated, waiting for user review
  - `APPROVED`: User has approved the response
  - `REJECTED`: User has rejected the response
  - `SENT`: Successfully sent to Telegram
  - `FAILED`: Failed to send to Telegram

- **TaskStatus** (Queue System)
  - Values: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `CANCELLED`
  - Tracks background task status

- **TaskPriority** (Queue System)
  - Values: `LOW`, `NORMAL`, `HIGH`
  - Defines priority levels for tasks

- **TaskType** (Queue System)
  - Values: `DIALOG`, `USER`, `SYSTEM`
  - Categorizes different types of background tasks

### Tables and Usage

#### Core Tables

1. **users**
   - Primary user information and Telegram identity
   ```sql
   telegram_id BIGINT UNIQUE NOT NULL  -- Telegram's user identifier
   username VARCHAR(255)               -- Telegram username
   first_name, last_name VARCHAR(255)  -- User's display name
   ```
   - Used by:
     - Authentication system for user lookup
     - Dialog management for ownership
     - Frontend for displaying user information

2. **dialogs**
   - Represents Telegram chats that should be processed
   ```sql
   telegram_dialog_id VARCHAR(255)     -- Telegram's chat identifier
   user_id UUID                        -- Owner of this dialog
   type dialogtype                     -- PRIVATE/GROUP/CHANNEL
   is_processing_enabled BOOLEAN       -- Whether to process this dialog
   auto_send_enabled BOOLEAN          -- Whether to auto-send approved responses
   last_processed_message_id          -- Track processing progress
   ```
   - Used by:
     - Background worker to determine which chats to process
     - Frontend for dialog selection and configuration
     - Processing system for tracking progress

3. **processed_responses**
   - Stores the latest AI response for each dialog
   ```sql
   dialog_id UUID                     -- Dialog this response is for
   last_message_id VARCHAR(255)       -- ID of latest message when processed
   last_message_timestamp            -- When that message was sent
   suggested_response TEXT           -- AI generated response
   edited_response TEXT              -- User's edited version
   status processingstatus          -- Current state of response
   ```
   - Used by:
     - Background worker to store generated responses
     - Frontend for displaying/editing responses
     - Sending system for approved messages

#### Authentication & Session Management

4. **sessions**
   - Manages web application sessions
   ```sql
   user_id UUID                      -- User this session belongs to
   token VARCHAR(500)                -- JWT access token
   refresh_token VARCHAR(500)        -- JWT refresh token
   expires_at TIMESTAMPTZ           -- When session expires
   session_metadata JSONB           -- Additional session information
   device_info JSONB               -- Client device details
   ```
   - Used by:
     - Authentication middleware
     - Frontend for session management
     - API endpoints for authorization

5. **authentication_data**
   - Stores Telegram credentials for background processing
   ```sql
   user_id UUID                      -- User these credentials belong to
   encrypted_credentials BYTEA       -- Encrypted Telegram session data
   is_active BOOLEAN                -- Whether these credentials are valid
   ```
   - Used by:
     - Background worker for Telegram access
     - Authentication system for credential management

#### AI Configuration

6. **user_selected_models**
   - User's LLM preferences
   ```sql
   user_id UUID                      -- User these preferences belong to
   model_name VARCHAR(255)           -- Selected LLM model
   system_prompt TEXT                -- Custom system prompt
   ```
   - Used by:
     - Background worker for processing configuration
     - Frontend for model selection

### Processing Workflow

1. **Background Worker (Every 30 minutes)**
   ```python
   for dialog in Dialogs.get_active():
       if dialog.is_processing_enabled:
           messages = telegram.get_recent_messages(dialog.telegram_dialog_id)
           if messages[-1].id != dialog.last_processed_message_id:
               response = generate_response(messages)
               store_processed_response(dialog, response)
   ```

2. **User Review Process**
   ```python
   # Frontend fetches pending responses
   responses = ProcessedResponses.get_pending()
   
   # User approves/edits
   response.approve(edited_text)
   
   # Background worker sends approved responses
   for response in ProcessedResponses.get_approved():
       telegram.send_message(response.dialog_id, response.text)
   ```

### Key Features

- Minimal data storage: No message content stored
- Real-time processing: Messages fetched from Telegram when needed
- Single active response per dialog
- Support for message editing before sending
- Automatic invalidation of old responses when new messages arrive

## Extensions

The database uses:
- `pgcrypto`: For UUID generation
- `vector`: For potential future vector operations

## Initialization

To initialize the database:

```bash
# From project root
python backend/scripts/init_db.py
```

## Environment Configuration
Required environment variables:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=telegram_dialog_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

## Development

### Adding New Models
1. Create model in `models/` directory
2. Import in `__init__.py`
3. Update initialization script if needed

### Database Migrations
- Initial schema in `migrations/001_initial_schema.sql`
- Future migrations should be numbered sequentially

### Environment Configuration
Required environment variables:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=telegram_dialog_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
``` 