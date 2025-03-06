# Database Schema and Management

## Overview

This directory contains the database models, migrations, and utilities for the Telegram Dialog AI Processor. The system uses PostgreSQL with SQLAlchemy ORM for database management.

## Data Flow

### 1. User Registration and Authentication
1. New user initiates registration
   ```
   users table: Create new user entry
   → authentication_data table: Store encrypted Telegram credentials
   → sessions table: Create initial web session
   ```

2. Authentication flow
   ```
   sessions table: JWT tokens managed here
   ↔ authentication_data table: Telegram credentials retrieved for API access
   ```

### 2. Dialog Selection and Configuration
1. User selects dialogs to process
   ```
   dialogs table: Create entries for selected Telegram chats
   → Set is_processing_enabled = true for chosen dialogs
   → Set auto_send_enabled based on user preference
   ```

2. User configures AI preferences
   ```
   user_selected_models table: Store model choice and custom prompts
   ```

### 3. Message Processing (Message-less Architecture)
1. Processing trigger
   ```
   dialogs table: Check is_processing_enabled and last_processed_message_id
   → Fetch messages directly from Telegram API (not stored in database)
   → Process all new messages in single batch
   → processed_responses table: Store only the final suggested response
   ```

2. Key aspects of message-less processing:
   - No message content stored in database
   - Messages fetched and processed in real-time
   - Only final AI responses stored
   - Previous context reconstructed from Telegram when needed
   - Reduces storage requirements and simplifies privacy compliance

### 4. Response Management
1. User reviews pending responses
   ```
   processed_responses table:
   → status = PENDING_APPROVAL: Shown in UI for review
   → User can:
     - Approve: status → APPROVED
     - Edit: edited_response updated, status → APPROVED
     - Reject: status → REJECTED
   ```

2. Response sending
   ```
   processed_responses table:
   → Find APPROVED responses
   → Send via Telegram API
   → Update status → SENT (success) or FAILED (error)
   ```

### 5. Session Management
- Active sessions tracked in sessions table
- Automatic cleanup of expired sessions
- Refresh tokens handled for longer sessions

### Data Lifecycle Example
```
1. New User Registration
   users.create() → authentication_data.store() → sessions.create()
   
2. Dialog Selection
   dialogs.create(is_processing_enabled=true)
   
3. Processing Cycle
   a. Check for new messages (Telegram API)
   b. Process in memory (no storage)
   c. Store only final response:
      processed_responses.create(
          dialog_id=X,
          suggested_response="AI response",
          status=PENDING_APPROVAL
      )
   
4. User Review
   processed_responses.update(
       status=APPROVED,
       edited_response="Modified response"  # if edited
   )
   
5. Send Response
   processed_responses.update(status=SENT)
```

## Current Implementation

### Existing Enums

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

### Existing Tables and Usage

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
     - Frontend for model selection

### Current Features

- JWT-based session management
- User authentication and authorization
- Dialog configuration and management
- AI model preferences
- Secure credential storage
- Support for message editing before sending
- Single active response per dialog

### Extensions

The database uses:
- `pgcrypto`: For UUID generation
- `vector`: For potential future vector operations

## Planned Implementations

### Background Worker System (In Development)

#### Queue System Enums (Coming in next migration)
- **TaskStatus**
  - Values: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `CANCELLED`
  - For tracking background task states

- **TaskPriority**
  - Values: `LOW`, `NORMAL`, `HIGH`
  - For task scheduling and execution order

- **TaskType**
  - Values: `DIALOG`, `USER`, `SYSTEM`
  - For categorizing different types of background tasks

#### Planned Processing Workflow
```python
# Background Worker (Every 30 minutes)
for dialog in Dialogs.get_active():
    if dialog.is_processing_enabled:
        messages = telegram.get_recent_messages(dialog.telegram_dialog_id)
        if messages[-1].id != dialog.last_processed_message_id:
            response = generate_response(messages)
            store_processed_response(dialog, response)

# User Review Process
responses = ProcessedResponses.get_pending()
response.approve(edited_text)

# Background worker sends approved responses
for response in ProcessedResponses.get_approved():
    telegram.send_message(response.dialog_id, response.text)
```

#### Planned Features
- Real-time message processing
- Automatic message fetching from Telegram
- Task queue management
- Worker process implementation
- Task monitoring and recovery
- Error handling and retry logic
- Automatic response invalidation when new messages arrive

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

## Initialization

To initialize the database:

```bash
# From project root
python backend/scripts/init_db.py
``` 