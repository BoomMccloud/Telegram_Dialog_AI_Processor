"""
Tests for the dialog processor background worker.

These tests ensure that the background worker correctly processes dialogs
with the selected LLM provider and presents the results for user approval.
"""

import os
import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.dialog import Dialog, Message
from app.models.processing import ProcessingResult, ProcessingStatus
from app.models.user import User
from app.services.background_tasks import BackgroundTaskManager
from app.services.queue_manager import add_task_to_queue

# Constants for testing
TEST_USER = {
    "telegram_id": 12345678,
    "username": "test_user",
    "first_name": "Test",
    "last_name": "User"
}

TEST_DIALOGS = [
    {
        "telegram_dialog_id": "123456789",
        "name": "Test Private Chat",
        "type": "private",
        "unread_count": 5,
        "last_message": {"text": "Hello there", "date": "2023-01-01T12:00:00Z"}
    },
    {
        "telegram_dialog_id": "987654321",
        "name": "Test Group Chat",
        "type": "group",
        "unread_count": 10,
        "last_message": {"text": "Group message", "date": "2023-01-02T14:30:00Z"}
    }
]

TEST_MESSAGES = [
    # Messages for first dialog
    {
        "telegram_message_id": "msg1",
        "text": "Hello, how are you?",
        "sender_id": "sender1",
        "sender_name": "John Doe",
        "date": datetime.now() - timedelta(days=1),
        "is_outgoing": False
    },
    {
        "telegram_message_id": "msg2",
        "text": "I'm doing well, thanks for asking!",
        "sender_id": "me",
        "sender_name": "Test User",
        "date": datetime.now() - timedelta(days=1, hours=23),
        "is_outgoing": True
    },
    # Messages for second dialog
    {
        "telegram_message_id": "msg3",
        "text": "Welcome to the group!",
        "sender_id": "admin",
        "sender_name": "Admin User",
        "date": datetime.now() - timedelta(days=2),
        "is_outgoing": False
    },
    {
        "telegram_message_id": "msg4",
        "text": "Thanks for having me.",
        "sender_id": "me",
        "sender_name": "Test User",
        "date": datetime.now() - timedelta(days=2, hours=23),
        "is_outgoing": True
    }
]

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in the database."""
    user = User(**TEST_USER)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def test_dialogs(db_session: AsyncSession) -> List[Dialog]:
    """Create test dialogs in the database."""
    dialogs = []
    for dialog_data in TEST_DIALOGS:
        dialog = Dialog(**dialog_data)
        db_session.add(dialog)
        await db_session.commit()
        await db_session.refresh(dialog)
        dialogs.append(dialog)
    return dialogs

@pytest.fixture
async def test_messages(db_session: AsyncSession, test_dialogs: List[Dialog]) -> List[Message]:
    """Create test messages in the database."""
    messages = []
    # Add messages to first dialog
    for i in range(2):
        message_data = TEST_MESSAGES[i].copy()
        message_data["dialog_id"] = test_dialogs[0].id
        message = Message(**message_data)
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        messages.append(message)
    
    # Add messages to second dialog
    for i in range(2, 4):
        message_data = TEST_MESSAGES[i].copy()
        message_data["dialog_id"] = test_dialogs[1].id
        message = Message(**message_data)
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        messages.append(message)
    
    return messages

@pytest.fixture
def background_task_manager() -> BackgroundTaskManager:
    """Create a BackgroundTaskManager for testing."""
    task_manager = BackgroundTaskManager()
    yield task_manager
    # Clean up any running tasks
    asyncio.run(task_manager.cleanup())

class TestDialogProcessor:
    """Tests for the dialog processor functionality."""

    @pytest.mark.asyncio
    async def test_select_dialogs_for_processing(self, client: AsyncClient, test_user: User, test_dialogs: List[Dialog]):
        """Test the API endpoint for selecting dialogs to process."""
        # TODO: Implement test for selecting dialogs
        # 1. Mock user authentication
        # 2. Make API request to select dialogs
        # 3. Verify response format
        # 4. Check that dialogs are queued for processing
        assert len(test_dialogs) > 0
        assert test_user is not None

    @pytest.mark.asyncio
    async def test_fetch_messages_from_dialog(self, db_session: AsyncSession, test_dialogs: List[Dialog], test_messages: List[Message]):
        """Test fetching messages from a dialog."""
        # TODO: Implement test for message fetching
        # 1. Get a dialog ID
        # 2. Call the message fetching function
        # 3. Verify messages are retrieved correctly
        dialog_id = test_dialogs[0].id
        # This is a placeholder for the actual implementation
        assert len(test_messages) > 0
        assert test_dialogs[0].messages is not None

    @pytest.mark.asyncio
    async def test_process_messages_with_llm(self, db_session: AsyncSession, test_messages: List[Message]):
        """Test processing messages with LLM."""
        # TODO: Implement test for message processing
        # 1. Mock LLM processing
        # 2. Process messages
        # 3. Check results
        assert len(test_messages) > 0

    @pytest.mark.asyncio
    async def test_queue_dialog_for_processing(self, background_task_manager: BackgroundTaskManager, test_dialogs: List[Dialog]):
        """Test queuing dialogs for processing."""
        # TODO: Implement test for queuing dialogs
        # 1. Add dialog to queue
        # 2. Verify it's in the queue
        # 3. Check queue processing starts
        dialog_id = str(test_dialogs[0].id)
        model_name = "claude-3-sonnet"  # Example LLM model
        
        # This is a placeholder for the actual queue implementation
        # The actual implementation will depend on the queue_manager.py design
        queue_item = {
            "dialog_id": dialog_id,
            "model_name": model_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Here we'll need to call the queue manager's add_task method
        # add_task_to_queue(queue_item)
        
        # Then verify the dialog is in the queue
        assert test_dialogs[0] is not None

    @pytest.mark.asyncio
    async def test_store_processing_results(self, db_session: AsyncSession, test_messages: List[Message]):
        """Test storing processing results in the database."""
        # TODO: Implement test for storing results
        # 1. Create a processing result
        # 2. Store it
        # 3. Verify it's in the database
        message = test_messages[0]
        
        # Create a processing result
        result = ProcessingResult(
            message_id=message.id,
            model_name="claude-3-sonnet",
            status=ProcessingStatus.COMPLETED,
            result={"suggested_reply": "This is a test response"},
            completed_at=datetime.now()
        )
        
        db_session.add(result)
        await db_session.commit()
        await db_session.refresh(result)
        
        # Verify it was stored
        assert result.id is not None
        assert result.status == ProcessingStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_retrieve_processing_results(self, db_session: AsyncSession, test_messages: List[Message]):
        """Test retrieving processing results for user approval."""
        # TODO: Implement test for retrieving results
        # 1. Store a processing result
        # 2. Retrieve it
        # 3. Verify content
        message = test_messages[0]
        
        # Create and store a processing result
        result = ProcessingResult(
            message_id=message.id,
            model_name="claude-3-sonnet",
            status=ProcessingStatus.COMPLETED,
            result={"suggested_reply": "This is a test response"},
            completed_at=datetime.now()
        )
        
        db_session.add(result)
        await db_session.commit()
        
        # Query for the result
        stmt = select(ProcessingResult).where(ProcessingResult.message_id == message.id)
        query_result = await db_session.execute(stmt)
        retrieved_result = query_result.scalar_one_or_none()
        
        # Verify retrieval
        assert retrieved_result is not None
        assert retrieved_result.status == ProcessingStatus.COMPLETED
        assert retrieved_result.result["suggested_reply"] == "This is a test response"

    @pytest.mark.asyncio
    async def test_approve_processing_result(self, client: AsyncClient, test_user: User, test_messages: List[Message]):
        """Test approving a processing result."""
        # TODO: Implement test for approving results
        # 1. Store a processing result
        # 2. Make approval API request
        # 3. Verify status update
        assert test_user is not None
        assert len(test_messages) > 0

    @pytest.mark.asyncio
    async def test_reject_processing_result(self, client: AsyncClient, test_user: User, test_messages: List[Message]):
        """Test rejecting a processing result."""
        # TODO: Implement test for rejecting results
        # 1. Store a processing result
        # 2. Make rejection API request
        # 3. Verify status update
        assert test_user is not None
        assert len(test_messages) > 0

    @pytest.mark.asyncio
    async def test_background_worker_processes_dialogs(self, background_task_manager: BackgroundTaskManager, test_dialogs: List[Dialog], test_messages: List[Message]):
        """Test that the background worker processes dialogs correctly."""
        # TODO: Implement test for background worker
        # 1. Start worker
        # 2. Queue dialogs
        # 3. Verify processing occurs
        # 4. Check results
        assert background_task_manager is not None
        assert len(test_dialogs) > 0
        assert len(test_messages) > 0 