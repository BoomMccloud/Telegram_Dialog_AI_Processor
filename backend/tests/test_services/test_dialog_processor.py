"""
Tests for the dialog processor service
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.services.dialog_processor import DialogProcessor
from app.db.models.dialog import Dialog
from app.db.models.message import Message
from app.db.models.user import User
from app.utils.storage import ProcessingRunMetadata, ProcessingStatus

@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session

@pytest.fixture
def mock_dialog():
    """Create a mock dialog"""
    return Dialog(
        id=uuid4(),
        telegram_dialog_id="123456789",
        user_id=uuid4(),
        title="Test Dialog",
        type="PRIVATE",
        is_processing_enabled=True
    )

@pytest.fixture
def mock_messages():
    """Create mock messages"""
    return [
        {
            "dialog_id": 123456789,
            "message_id": 1,
            "date": datetime.utcnow().isoformat(),
            "sender": {
                "id": 987654321,
                "name": "Test User"
            },
            "text": "Hello, world!",
            "is_outgoing": False,
            "is_unread": False
        },
        {
            "dialog_id": 123456789,
            "message_id": 2,
            "date": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            "sender": {
                "id": 123456789,
                "name": "Another User"
            },
            "text": "How are you?",
            "is_outgoing": True,
            "is_unread": False
        }
    ]

@pytest.mark.asyncio
@patch("app.services.dialog_processor.get_recent_messages")
@patch("app.services.dialog_processor.MessageFileStorage")
async def test_fetch_messages(mock_storage_class, mock_get_recent_messages, mock_db_session, mock_dialog, mock_messages):
    """Test fetching messages for a dialog"""
    # Setup mocks
    mock_get_recent_messages.return_value = mock_messages
    mock_storage = MagicMock()
    mock_storage_class.return_value = mock_storage
    
    # Create processor
    processor = DialogProcessor(mock_db_session)
    
    # Call fetch_messages
    result = await processor.fetch_messages(mock_dialog, "test_token")
    
    # Verify results
    assert result == mock_messages
    mock_get_recent_messages.assert_called_once_with(
        "test_token", 
        limit=processor.message_limit,
        dialog_id=int(mock_dialog.telegram_dialog_id)
    )

@pytest.mark.asyncio
@patch("app.services.dialog_processor.get_recent_messages")
@patch("app.services.dialog_processor.MessageFileStorage")
async def test_process_dialog(mock_storage_class, mock_get_recent_messages, mock_db_session, mock_dialog, mock_messages):
    """Test processing a dialog"""
    # Setup mocks
    mock_get_recent_messages.return_value = mock_messages
    mock_storage = MagicMock()
    mock_storage_class.return_value = mock_storage
    
    # Setup metadata
    metadata = ProcessingRunMetadata(
        run_id="test_run",
        user_id=str(mock_dialog.user_id),
        dialog_id=str(mock_dialog.id),
        timestamp=datetime.utcnow(),
        message_count=len(mock_messages),
        status=ProcessingStatus.IN_PROGRESS
    )
    mock_storage.create_processing_run.return_value = metadata
    
    # Create processor
    processor = DialogProcessor(mock_db_session)
    
    # Call process_dialog
    result = await processor.process_dialog(mock_dialog, "test_token")
    
    # Verify results
    assert result is True
    mock_get_recent_messages.assert_called_once_with(
        "test_token", 
        limit=processor.message_limit,
        dialog_id=int(mock_dialog.telegram_dialog_id)
    )
    mock_storage.create_processing_run.assert_called_once_with(
        user_id=str(mock_dialog.user_id),
        dialog_id=str(mock_dialog.id)
    )
    mock_storage.save_messages.assert_called_once()
    mock_db_session.commit.assert_called_once()
    
    # Verify dialog was updated
    assert mock_dialog.last_processed_message_id == str(mock_messages[0]["message_id"])
    assert mock_dialog.last_processed_at is not None

@pytest.mark.asyncio
async def test_process_dialog_no_messages(mock_db_session, mock_dialog):
    """Test processing a dialog with no new messages"""
    with patch("app.services.dialog_processor.get_recent_messages", new_callable=AsyncMock) as mock_get_messages:
        mock_get_messages.return_value = []
        
        processor = DialogProcessor(mock_db_session)
        success = await processor.process_dialog(mock_dialog, "test_token")
        
        assert success is True
        assert mock_db_session.add.call_count == 0
        assert mock_db_session.commit.call_count == 0

@pytest.mark.asyncio
async def test_process_dialog_error(mock_db_session, mock_dialog):
    """Test processing a dialog with an error"""
    with patch("app.services.dialog_processor.get_recent_messages", new_callable=AsyncMock) as mock_get_messages:
        mock_get_messages.side_effect = Exception("API Error")
        
        processor = DialogProcessor(mock_db_session)
        success = await processor.process_dialog(mock_dialog, "test_token")
        
        assert success is False
        mock_db_session.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_process_dialogs(mock_db_session, mock_dialog, mock_messages):
    """Test processing multiple dialogs"""
    # Mock both get_recent_messages and the Message class
    with patch("app.services.dialog_processor.get_recent_messages", new_callable=AsyncMock) as mock_get_messages, \
         patch("app.services.dialog_processor.Message") as mock_message_class:
        
        mock_get_messages.return_value = mock_messages
        mock_message_instance = MagicMock()
        mock_message_class.return_value = mock_message_instance
        
        processor = DialogProcessor(mock_db_session)
        results = await processor.process_dialogs([mock_dialog], "test_token")
        
        assert len(results) == 1
        assert results[mock_dialog.id] is True
        assert mock_db_session.add.call_count == 2
        mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_process_dialogs_mixed_results(mock_db_session):
    """Test processing multiple dialogs with mixed results"""
    dialog1 = Dialog(
        id=uuid4(),
        telegram_dialog_id="123456",
        user_id=uuid4(),
        title="Dialog 1",
        type="PRIVATE",
        is_processing_enabled=True
    )
    dialog2 = Dialog(
        id=uuid4(),
        telegram_dialog_id="789012",
        user_id=uuid4(),
        title="Dialog 2",
        type="PRIVATE",
        is_processing_enabled=True
    )
    
    # Mock both get_recent_messages and the Message class
    with patch("app.services.dialog_processor.get_recent_messages", new_callable=AsyncMock) as mock_get_messages, \
         patch("app.services.dialog_processor.Message") as mock_message_class:
        
        # First call succeeds, second call fails
        mock_get_messages.side_effect = [
            [{"dialog_id": "123456", "message_id": "1", "text": "Hello", "sender": {"id": "user1", "name": "User 1"}, "date": datetime.utcnow().isoformat()}],
            Exception("API Error")
        ]
        
        mock_message_instance = MagicMock()
        mock_message_class.return_value = mock_message_instance
        
        processor = DialogProcessor(mock_db_session)
        results = await processor.process_dialogs([dialog1, dialog2], "test_token")
        
        assert len(results) == 2
        assert results[dialog1.id] is True
        assert results[dialog2.id] is False
        assert mock_db_session.add.call_count == 1
        assert mock_db_session.commit.call_count == 1
        assert mock_db_session.rollback.call_count == 1 