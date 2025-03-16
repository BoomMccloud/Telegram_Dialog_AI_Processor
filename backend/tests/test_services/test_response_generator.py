"""
Tests for the response generator service
"""

import os
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.db.models.dialog import Dialog
from app.db.models.message import Message
from app.services.response_generator import ResponseGenerator, ResponseFileStorage
from app.utils.storage import MessageFileStorage

# Mock data
@pytest.fixture
def mock_dialog():
    """Create a mock dialog for testing"""
    return Dialog(
        id="test-dialog-id",
        user_id="test-user-id",
        telegram_dialog_id="12345",
        title="Test Dialog",
        is_processing_enabled=True
    )

@pytest.fixture
def mock_messages():
    """Create mock messages for testing"""
    return [
        Message(
            telegram_message_id="1",
            dialog_id="test-dialog-id",
            text="Hello, how are you?",
            sender_id="sender1",
            sender_name="User",
            date=datetime(2023, 1, 1, 10, 0),
            is_outgoing=False
        ),
        Message(
            telegram_message_id="2",
            dialog_id="test-dialog-id",
            text="I'm doing well, thanks for asking!",
            sender_id="me",
            sender_name="Assistant",
            date=datetime(2023, 1, 1, 10, 1),
            is_outgoing=True
        ),
        Message(
            telegram_message_id="3",
            dialog_id="test-dialog-id",
            text="Can you help me with a project?",
            sender_id="sender1",
            sender_name="User",
            date=datetime(2023, 1, 1, 10, 2),
            is_outgoing=False
        )
    ]

class TestResponseGenerator:
    """Tests for the ResponseGenerator class"""
    
    @pytest.mark.asyncio
    @patch('app.services.response_generator.query_llm')
    @patch('app.services.response_generator.MessageFileStorage')
    async def test_generate_response(self, mock_message_storage, mock_query_llm, mock_dialog, mock_messages):
        """Test generating a response for a dialog"""
        # Setup mocks
        mock_message_storage_instance = MagicMock()
        mock_message_storage.return_value = mock_message_storage_instance
        mock_message_storage_instance.get_latest_messages.return_value = mock_messages
        
        # Mock LLM response
        mock_query_llm.return_value = "I'd be happy to help with your project. What kind of project are you working on?"
        
        # Create response generator
        generator = ResponseGenerator()
        
        # Generate response
        response = await generator.generate_response(mock_dialog)
        
        # Verify response
        assert response is not None
        assert "response_text" in response
        assert response["response_text"] == "I'd be happy to help with your project. What kind of project are you working on?"
        assert "metadata" in response
        assert response["metadata"].dialog_id == "test-dialog-id"
        assert response["metadata"].user_id == "test-user-id"
        assert response["metadata"].last_message_id == "3"
        
        # Verify LLM was called with correct prompt
        mock_query_llm.assert_called_once()
        prompt_arg = mock_query_llm.call_args[1]["prompt"]
        assert "Role Definition" in prompt_arg
        assert "User (user): Can you help me with a project?" in prompt_arg
        
        # Cleanup
        response_storage = ResponseFileStorage()
        response_dir = response_storage.get_dialog_dir("test-user-id", "test-dialog-id")
        if os.path.exists(response_dir):
            import shutil
            shutil.rmtree(response_dir)
    
    @pytest.mark.asyncio
    @patch('app.services.response_generator.query_llm')
    @patch('app.services.response_generator.MessageFileStorage')
    async def test_no_duplicate_responses(self, mock_message_storage, mock_query_llm, mock_dialog, mock_messages):
        """Test that duplicate responses are not generated"""
        # Setup mocks
        mock_message_storage_instance = MagicMock()
        mock_message_storage.return_value = mock_message_storage_instance
        mock_message_storage_instance.get_latest_messages.return_value = mock_messages
        
        # Mock LLM response
        mock_query_llm.return_value = "I'd be happy to help with your project. What kind of project are you working on?"
        
        # Create response generator
        generator = ResponseGenerator()
        
        # Generate response first time
        response1 = await generator.generate_response(mock_dialog)
        assert response1 is not None
        
        # Generate response second time (should return existing response)
        response2 = await generator.generate_response(mock_dialog)
        assert response2 is not None
        
        # Verify LLM was only called once
        mock_query_llm.assert_called_once()
        
        # Verify both responses are the same
        assert response1["metadata"].response_id == response2["metadata"].response_id
        
        # Cleanup
        response_storage = ResponseFileStorage()
        response_dir = response_storage.get_dialog_dir("test-user-id", "test-dialog-id")
        if os.path.exists(response_dir):
            import shutil
            shutil.rmtree(response_dir)

class TestResponseFileStorage:
    """Tests for the ResponseFileStorage class"""
    
    def test_save_and_get_response(self, mock_dialog):
        """Test saving and retrieving a response"""
        # Create storage
        storage = ResponseFileStorage()
        
        # Save response
        response_text = "This is a test response"
        metadata = storage.save_response(
            user_id="test-user-id",
            dialog_id="test-dialog-id",
            response_text=response_text,
            last_message_id="123"
        )
        
        # Verify metadata
        assert metadata is not None
        assert metadata.dialog_id == "test-dialog-id"
        assert metadata.user_id == "test-user-id"
        assert metadata.last_message_id == "123"
        
        # Get response
        response = storage.get_latest_response("test-user-id", "test-dialog-id")
        
        # Verify response
        assert response is not None
        assert response["response_text"] == response_text
        assert response["metadata"].dialog_id == "test-dialog-id"
        
        # Cleanup
        response_dir = storage.get_dialog_dir("test-user-id", "test-dialog-id")
        if os.path.exists(response_dir):
            import shutil
            shutil.rmtree(response_dir) 