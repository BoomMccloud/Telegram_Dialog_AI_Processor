# Telegram Dialog AI Processor - Backend Analysis

## Architecture Overview

This is a FastAPI-based backend for processing Telegram messages with AI. The system includes:

1. **Core Components**:
   - FastAPI application with structured middleware and error handling
   - Telethon integration for Telegram API access
   - SQLAlchemy ORM with AsyncPG for database operations
   - Alembic for database migrations
   - JWT-based authentication system
   - Background worker for async message processing

2. **Key Services**:
   - `telegram.py`: Telethon client management for Telegram API interactions
   - `dialog_processor.py`: Fetches and processes messages from Telegram dialogs
   - `response_generator.py`: Builds AI prompts and generates responses
   - `worker.py`: Background process for scheduled dialog processing
   - `llm_api.py`: Interface to Claude's AI model with token tracking
   - `auth.py`: Handles Telegram authentication via QR codes and session management

3. **Database Models**:
   - `User`: User account information
   - `Session`: Authentication sessions
   - `Dialog`: Telegram dialogs/chats
   - `Message`: Individual messages
   - `ProcessedResponse`: AI-generated responses for messages
   - `UserSelectedModel`: User's AI model preferences

4. **API Endpoints**:
   - `/auth`: QR login and JWT handling
   - `/dialogs`: List and manage dialogs
   - `/messages`: Retrieve message history
   - `/responses`: Manage AI-generated responses

5. **Background Worker**:
   - Runs on a configurable interval (10 minutes default)
   - Processes dialogs marked with `is_processing_enabled=True`
   - Fetches recent messages, analyzes context, and generates AI responses
   - Stores responses for user review in the `ProcessedResponse` table
   - Implements robust error handling and logging

## Implementation Details

1. **Dialog Processing Flow**:
   - Worker fetches dialogs with processing enabled
   - Groups dialogs by user for efficient processing
   - Retrieves user's authentication session token
   - Processes each dialog to fetch recent messages (last 20 by default)
   - Generates AI responses based on message context
   - Stores responses for user approval

2. **Response Generation**:
   - Builds contextual prompts from message history
   - Calls Claude's API with appropriate parameters
   - Implements retry logic for API failures
   - Uses file-based temporary storage for processing runs
   - Saves responses to database with metadata

3. **Telegram Integration**:
   - Uses Telethon's MTProto API client
   - Maintains persistent sessions for authenticated users
   - Provides mock implementations for development testing

4. **Error Handling & Resilience**:
   - Extensive logging throughout the application
   - Automatic retry mechanisms for API calls
   - Transaction-based database operations
   - Graceful failure handling for partial successes

## Development Progress

The codebase appears to be implementing a multi-phase plan as outlined in the instructions.md file:

1. **Completed**: Worker skeleton, Telegram fetch integration, database models
2. **In Progress**: AI integration, context building, response generation
3. **Upcoming**: Overwriting logic, robust logging, crash recovery

The system is designed with a clean separation of concerns, good error handling, and a focus on reliability for background operations.

## File and Component Details

### Root Configuration Files
- `Dockerfile`: Container configuration for deployment
- `alembic.ini`: Database migration configuration
- `requirements.txt`: Python package dependencies
- `.env`: Environment variables configuration (not in repo)
- `instructions.md`: Development and deployment guidelines

### Application Directory (`app/`)

#### Core Files
- `main.py`: FastAPI application entry point and configuration
  - Route registration
  - Middleware setup
  - Exception handlers
  - OpenAPI documentation

#### API Endpoints (`app/api/`)
- `dependencies.py`: Shared API dependencies and utilities
  - Authentication dependencies
  - Request validation
  - Common response models
- `auth.py`: Authentication endpoints
  - QR code generation
  - Session management
  - JWT token handling
- `dialogs.py`: Dialog management endpoints
  - List dialogs
  - Update processing settings
  - Dialog metadata
- `messages.py`: Message handling endpoints
  - Message history retrieval
  - Message search
  - Context management
- `responses.py`: AI response management
  - Response approval/rejection
  - Response modification
  - Auto-send configuration

#### Core Utilities (`app/core/`)
- `error_handlers.py`: Global exception handlers
  - API error responses
  - Validation error handling
  - Authentication failures
- `exceptions.py`: Custom exception classes
  - Business logic exceptions
  - API-specific errors
- `logging_config.py`: Logging configuration
  - Structured logging setup
  - Log rotation
  - Error tracking

#### Database Layer (`app/db/`)
1. **Core Database Files**:
   - `database.py`: Database connection and session management
   - `init_db.py`: Database initialization scripts
   - `check_db.py`: Database health checks
   - `schema_validator.py`: Schema validation utilities
   - `update_schema.py`: Schema update utilities
   - `utils.py`: Database helper functions

2. **Models Directory** (`app/db/models/`):
   - `user.py`: User account model
   - `session.py`: Authentication session model
   - `dialog.py`: Telegram dialog model
   - `message.py`: Message storage model
   - `response.py`: AI response model
   - `model_config.py`: AI model preferences

3. **Migrations Directory** (`app/db/migrations/`):
   - Alembic migration scripts
   - Version control for schema changes
   - Data migration utilities

#### Middleware (`app/middleware/`)
- `session.py`: Session management middleware
  - Token validation
  - User context injection
  - Rate limiting

#### Services (`app/services/`)

1. **Telegram Integration**:
   - `telegram.py`: Telethon client implementation
     - MTProto client setup
     - Message fetching
     - Dialog management
   - `mock_telegram.py`: Development testing utilities
     - Simulated responses
     - Test data generation

2. **Message Processing**:
   - `dialog_processor.py`: Dialog processing logic
     - Message extraction
     - Context building
     - Processing pipeline
   - `response_generator.py`: AI response generation
     - Prompt construction
     - Model interaction
     - Response formatting
   - `response_sender.py`: Response delivery
     - Message sending
     - Rate limiting
     - Error handling

3. **Background Processing**:
   - `worker.py`: Background task scheduler
     - Dialog processing queue
     - Task distribution
     - Error recovery
   - `background_tasks.py`: Task definitions
     - Periodic tasks
     - Cleanup jobs
   - `cleanup.py`: Data cleanup utilities
     - Old message purging
     - Session cleanup
     - Log rotation

4. **AI Integration**:
   - `llm_api.py`: Claude API integration
     - Model communication
     - Response parsing
     - Error handling
   - `token_tracker.py`: Token usage monitoring
     - Usage tracking
     - Cost calculation
     - Quota management

#### Utils (`app/utils/`)
1. **Logging Utilities**:
   - `logging.py`: Custom logging setup
     - Structured logging
     - Log formatting
     - Log routing

2. **Helper Functions**:
   - `retry.py`: Retry mechanism implementation
     - Exponential backoff
     - Error classification
     - Circuit breaker

3. **Storage Management** (`app/utils/storage/`):
   - File storage utilities
   - Temporary file management
   - Cache implementations

### Documentation (`docs/`)
- API documentation
- Deployment guides
- Development guidelines
- Architecture diagrams

### Logs Directory (`logs/`)
- `worker.log`: Background worker activity logs
- `dialog_count.log`: Dialog processing statistics
- Application logs (generated at runtime)
- Error logs (generated at runtime) 