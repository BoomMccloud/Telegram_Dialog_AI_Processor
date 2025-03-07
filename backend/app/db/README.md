# Database Schema and Management

## Overview

This directory contains the database models, migrations, and utilities for the Telegram Dialog AI Processor. The system uses PostgreSQL with SQLAlchemy ORM for database management.

## Data Flow

### 1. User Registration and Authentication
1. New user initiates registration via QR code
   ```
   users table: Create temporary user with null telegram_id
   → sessions table: Create initial web session (PENDING)
   → User scans QR code
   → users table: Update with real telegram_id or create new permanent user
   → authentication_data table: Store encrypted Telegram credentials
   → sessions table: Update to AUTHENTICATED
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
   telegram_id BIGINT UNIQUE NULL     -- Telegram's user identifier (nullable for temporary users)
   username VARCHAR(255)               -- Telegram username
   first_name, last_name VARCHAR(255)  -- User's display name
   ```
   - Used by:
     - Authentication system for user lookup
     - Dialog management for ownership
     - Frontend for displaying user information
     - QR authentication for temporary users
   - Special cases:
     - `telegram_id` can be NULL for temporary users during QR authentication
     - Temporary users are cleaned up after successful QR authentication
     - Only one active session per temporary user

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

## System Architecture

### 1. API Layer (`/backend/app/api/`)

#### 1.1 Authentication Endpoints (`/api/auth/`)
- `routes.py`: Main router for auth endpoints
  - POST `/login`: QR code-based login initiation
  - POST `/verify`: QR code verification
  - POST `/refresh`: Token refresh
  - POST `/logout`: Session termination

#### 1.2 Dialog Management (`/api/dialogs/`)
- `routes.py`: Dialog management endpoints
  - GET `/`: List user's dialogs
  - POST `/`: Add new dialog for processing
  - PATCH `/{dialog_id}`: Update dialog settings
  - DELETE `/{dialog_id}`: Remove dialog from processing

#### 1.3 Response Management (`/api/responses/`)
- `routes.py`: Response handling endpoints
  - GET `/pending`: Get pending responses
  - POST `/{response_id}/approve`: Approve response
  - POST `/{response_id}/reject`: Reject response
  - PUT `/{response_id}`: Edit response
  - GET `/history`: Get sent response history

#### 1.4 User Settings (`/api/settings/`)
- `routes.py`: User preference endpoints
  - GET `/models`: Get available AI models
  - PUT `/models`: Update model preferences
  - GET `/profile`: Get user profile
  - PUT `/profile`: Update user settings

### 2. Service Layer (`/backend/app/services/`)

#### 2.1 Authentication Service (`auth_service.py`)
- Handle QR code generation and verification
- Manage session creation and validation
- Handle Telegram credential encryption/decryption
- Token generation and validation

#### 2.2 Dialog Service (`dialog_service.py`)
- Dialog registration and configuration
- Dialog state management
- Processing status tracking
- Integration with Telegram API for dialog info

#### 2.3 Processing Service (`processing_service.py`)
- Message batch processing
- AI model integration
- Response generation
- Context management

#### 2.4 Response Service (`response_service.py`)
- Response storage and retrieval
- Status management
- Response sending via Telegram
- History tracking

#### 2.5 User Service (`user_service.py`)
- User profile management
- Preference handling
- Model configuration
- Session management

### 3. Background Workers (`/backend/app/workers/`)

#### 3.1 Message Processor (`message_processor.py`)
- Poll for new messages
- Batch processing coordination
- Response generation scheduling

#### 3.2 Response Sender (`response_sender.py`)
- Handle approved response sending
- Retry logic for failed sends
- Status updates

#### 3.3 Cleanup Worker (`cleanup_worker.py`)
- Expired session cleanup
- Temporary user cleanup
- Old response pruning

### 4. Utilities (`/backend/app/utils/`)

#### 4.1 Telegram Utils (`telegram_utils.py`)
- Telegram API client wrapper
- Message formatting
- Error handling

#### 4.2 Security Utils (`security_utils.py`)
- Encryption/decryption helpers
- Token management
- Password hashing

#### 4.3 Database Utils (`db_utils.py`)
- Connection management
- Transaction helpers
- Query builders

#### 4.4 Validation Utils (`validation_utils.py`)
- Input validation
- Schema validation
- Type checking

### 5. System Data Flows

#### 5.1 Message Processing Flow
```
MessageProcessor
→ DialogService (get active dialogs)
→ TelegramUtils (fetch messages)
→ ProcessingService (generate response)
→ ResponseService (store response)
```

#### 5.2 Response Approval Flow
```
API (approve endpoint)
→ ResponseService (update status)
→ ResponseSender (queue for sending)
→ TelegramUtils (send message)
→ ResponseService (update status to SENT)
```

#### 5.3 Authentication Flow
```
API (login endpoint)
→ AuthService (generate QR)
→ UserService (create temporary user)
→ AuthService (verify QR scan)
→ UserService (update with Telegram ID)
→ AuthService (create session)
```

### 6. Architecture Principles

The system follows clean architecture principles with:
- Clear separation of concerns
- Dependency injection
- Service-oriented design
- Background task management
- Proper error handling
- Scalable component organization

Each component is designed to be testable and maintainable, with clear interfaces between layers. The services act as an abstraction layer between the API endpoints and the database models, ensuring business logic is properly encapsulated.

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

## Database Migrations

### Using Alembic

The project uses Alembic for database migrations. Migrations are stored in `app/db/migrations/versions/`.

To create a new migration:
```bash
# From backend directory
PYTHONPATH=. alembic revision --autogenerate -m "description of change"
```

To apply migrations:
```bash
# From backend directory
PYTHONPATH=. alembic upgrade head
```

### Migration History

1. **Initial Schema** (001_initial_schema.sql)
   - Base tables and relationships
   - Core functionality setup

2. **Make telegram_id Nullable** (20250307_1145_f231678720fb)
   - Allow NULL values for users.telegram_id
   - Support temporary users during QR authentication
   - Enable cleanup of temporary users after authentication

### Future Migrations

When adding new migrations:
1. Create migration file using Alembic
2. Review autogenerated changes
3. Test upgrade and downgrade paths
4. Document changes in this README 