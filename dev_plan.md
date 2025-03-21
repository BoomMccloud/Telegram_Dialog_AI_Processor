# Telegram Dialog Message Processing - Development Plan

## Overview

This plan outlines the implementation of message processing and response generation for the Telegram Dialog AI Processor application. The feature allows users to refresh their Telegram dialogs and automatically generate AI responses for unread messages in private chats and mentions in group chats.

## Current Implementation Status

### Frontend Components

1. **Dialog Management**
   - ✅ `useDialogs` hook exists for fetching and filtering dialogs
   - ✅ Dialog filtering implemented with modes: 'all-unread', 'unread-dms', 'unread-groups', 'all'
   - ✅ Refresh functionality implemented in Telegram page (basic refresh of current dialogs)
   - ❌ Missing filtering for unread messages and mentions specifically

2. **Message Fetching**
   - ✅ `useRecentMessages` hook exists for fetching messages by dialog ID
   - ✅ API endpoints for fetching messages are implemented
   - ❌ Missing logic to fetch specific unread messages or messages with mentions

3. **Response Generation**
   - ✅ API endpoints for response generation exist (private and group)
   - ✅ Response generation is callable from the API service
   - ✅ API endpoints for managing responses (approve, reject, edit, send) are implemented
   - ❌ Missing batch processing functionality for multiple dialogs
   - ❌ Missing progress tracking during generation

4. **UI Components**
   - ✅ Basic refresh button exists in the Telegram page
   - ✅ Dialog list view with selection functionality
   - ✅ Conversation view for displaying messages
   - ❌ Missing progress dialog for tracking batch operations
   - ❌ Missing specific UI for unread message processing

### Current Edge Case Handling

1. **Dialog with Existing Response, No New Messages**
   - ❌ No implementation for detecting if message_id matches last_processed_message_id
   - ❌ Missing logic to skip processing for dialogs with no new messages

2. **Dialog with Existing Response, New Messages**
   - ❌ No implementation for checking response status before updating
   - ✅ Basic response status tracking exists in the `useResponses` hook
   - ✅ Response generation API calls exist in `Messages/index.tsx` but without status-based conditionals

3. **Concurrent Operations**
   - ❌ No implementation for preventing multiple refresh operations
   - ❌ Missing progress dialog and processing state management
   - ❌ No UI locks during processing

4. **Error Handling**
   - ✅ Basic error handling exists in API calls and hooks
   - ❌ Missing retry logic with exponential backoff
   - ❌ No detailed error feedback in the UI for processing operations

5. **UI Feedback**
   - ❌ No implementation for showing processing progress
   - ✅ Basic loading states exist but not specific to batch operations
   - ❌ Missing cancellation functionality

### Backend Support

The backend has comprehensive support for:
- ✅ Response generation for both private and group chats
- ✅ Response management (approve, reject, edit, send)
- ✅ Dialog and message fetching

### What Needs to be Implemented

1. **Frontend Processing Logic**
   - Implement the refresh workflow to process multiple dialogs
   - Add filtering for unread messages and mentions
   - Create progress tracking during batch operations
   - Implement error handling with retries

2. **UI Enhancements**
   - Create a progress dialog component
   - Add user feedback for processing status
   - Implement dialog-level response management

3. **API Extensions**
   - Consider creating a batch processing endpoint for efficiency
   - Add endpoints for clearing message history and responses

## Data Model Approach

### Response Storage Strategy

1. **One Response Per Dialog**
   - Maintain the existing unique constraint on `dialog_id` in the `ProcessedResponse` table
   - Each dialog will have at most one active response at any time
   - When new messages are processed, the existing response may be updated or preserved based on its status

2. **User Privacy and Data Management**
   - Implement dialog-level and global cleanup functionality to allow users to delete message history and responses

### ID Relationships and Management

1. **Dual ID System**
   - Each dialog maintains two types of IDs:
     - Internal UUID (`id`): Used for database relationships and internal references
     - Telegram ID (`telegram_dialog_id`): Used for Telegram API communication
   - The `ProcessedResponse` table uses the internal UUID for its `dialog_id` foreign key

2. **ID Formats**
   - Internal UUID: Generated automatically for each new dialog
   - Telegram ID formats (stored as strings):
     - Private chats: Positive numbers (e.g., "123456789")
     - Groups: Negative numbers (e.g., "-123456789")
     - Supergroups/Channels: Special format (e.g., "-100123456789")

3. **ID Usage**
   - Frontend → Backend: Uses Telegram IDs for API requests
   - Backend → Database: Uses UUIDs for relationships
   - Backend → Telegram API: Uses Telegram IDs
   - Database Constraints:
     - Primary key: UUID
     - Unique constraint on (user_id, telegram_dialog_id) pair

4. **Benefits**
   - Consistent internal referencing using UUIDs
   - Compatibility with Telegram's various ID formats
   - Clean separation between internal and external identifiers
   - Data integrity through unique constraints

## Processing Logic

### Refresh Workflow

1. User initiates refresh from the Telegram tab UI
2. System fetches all dialogs and filters for:
   - Unread private messages
   - Group dialogs where the user is mentioned
3. For each filtered dialog, fetch 50 messages starting from:
   - The earliest unread message (for private chats)
   - The earliest user mention (for group chats)
4. Generate AI responses for these messages
5. Store responses in the database
6. Update UI to show processing status and results

### Edge Case Handling

1. **Dialog with Existing Response, No New Messages**
   - Compare `last_message_id` from Telegram with `last_processed_message_id`
   - If they match, skip processing for that dialog
   - No changes to existing response

2. **Dialog with Existing Response, New Messages**
   - Check status of existing response:
     - If `PENDING_APPROVAL` or `FAILED`: Update with new response for latest message
     - If `APPROVED`, `REJECTED`, or `SENT`: Preserve existing response, user must manually delete before regenerating

3. **Concurrent Operations**
   - Display processing state in UI
   - Prevent multiple refresh operations with UI locks
   - Show progress dialog during processing

4. **Error Handling**
   - Implement retry logic for network failures
   - Log detailed errors for debugging
   - Show user-friendly error messages in UI

## UI Components

1. **Refresh Button**
   - Add to Telegram tab navigation
   - Trigger dialog refresh and message processing

2. **Progress Dialog**
   - Show during processing with current status
   - Display counts of dialogs processed and remaining
   - Allow cancellation of operation

3. **Response List**
   - Display generated responses grouped by dialog
   - Allow viewing, editing, approving, rejecting responses

4. **Clear/Delete Options**
   - Add dialog-level "Clear" button to remove response and message history
   - Add global "Clear All" option for bulk cleanup

## Implementation Phases

1. **Backend Updates**
   - ✅ Update ProcessingStatus enum with missing statuses
   - Refine response generation endpoint to respect existing response states

2. **Frontend Implementation**
   - Add refresh button to Telegram tab
   - Implement progress dialog component
   - Add processing state management
   - Create response list view

3. **Testing**
   - Test with various dialog states and message volumes
   - Verify edge case handling
   - Test error recovery

4. **Cleanup Features**
   - Implement dialog clearing functionality
   - Add global cleanup options
