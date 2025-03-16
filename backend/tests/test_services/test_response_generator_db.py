"""
Tests for the database integration of the response generator service
"""

import os
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dialog import Dialog
from app.db.models.message import Message
from app.db.models.processed_response import ProcessedResponse
from app.db.models.types import ProcessingStatus
from app.services.response_generator import ResponseGenerator
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

class TestResponseGeneratorDB:
    """Tests for the database integration of the ResponseGenerator class"""
    
    @pytest.mark.asyncio
    @patch('app.services.response_generator.query_llm')
    @patch('app.services.response_generator.MessageFileStorage')
    async def test_save_response_to_db(self, mock_message_storage, mock_query_llm, mock_dialog, mock_messages):
        """Test saving a response to the database"""
        # Setup mocks
        mock_message_storage_instance = MagicMock()
        mock_message_storage.return_value = mock_message_storage_instance
        mock_message_storage_instance.get_latest_messages.return_value = mock_messages
        
        # Mock LLM response
        mock_query_llm.return_value = "I'd be happy to help with your project. What kind of project are you working on?"
        
        # Mock database session
        mock_session = MagicMock(spec=AsyncSession)
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute_result
        
        # Create response generator
        generator = ResponseGenerator(db_session=mock_session)
        
        # Save response to database
        last_message = mock_messages[-1]
        response = await generator.save_response_to_db(
            dialog=mock_dialog,
            response_text="I'd be happy to help with your project. What kind of project are you working on?",
            last_message_id=last_message.telegram_message_id,
            last_message_timestamp=last_message.date,
            db_session=mock_session
        )
        
        # Verify response
        assert response is not None
        
        # Verify session methods were called
        mock_session.execute.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify the added object is a ProcessedResponse
        added_object = mock_session.add.call_args[0][0]
        assert isinstance(added_object, ProcessedResponse)
        assert added_object.dialog_id == mock_dialog.id
        assert added_object.last_message_id == last_message.telegram_message_id
        assert added_object.suggested_response == "I'd be happy to help with your project. What kind of project are you working on?"
        assert added_object.status == ProcessingStatus.PENDING_APPROVAL
    
    @pytest.mark.asyncio
    @patch('app.services.response_generator.query_llm')
    @patch('app.services.response_generator.MessageFileStorage')
    async def test_update_existing_response(self, mock_message_storage, mock_query_llm, mock_dialog, mock_messages):
        """Test updating an existing response in the database"""
        # Setup mocks
        mock_message_storage_instance = MagicMock()
        mock_message_storage.return_value = mock_message_storage_instance
        mock_message_storage_instance.get_latest_messages.return_value = mock_messages
        
        # Mock LLM response
        mock_query_llm.return_value = "I'd be happy to help with your project. What kind of project are you working on?"
        
        # Create existing response
        existing_response = ProcessedResponse(
            id="test-response-id",
            dialog_id=mock_dialog.id,
            last_message_id="2",  # Old message ID
            last_message_timestamp=datetime(2023, 1, 1, 10, 1),
            suggested_response="Previous response",
            model_name="old-model",
            status=ProcessingStatus.PENDING_APPROVAL
        )
        
        # Mock database session
        mock_session = MagicMock(spec=AsyncSession)
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = existing_response
        mock_session.execute.return_value = mock_execute_result
        
        # Create response generator
        generator = ResponseGenerator(db_session=mock_session)
        
        # Save response to database
        last_message = mock_messages[-1]
        response = await generator.save_response_to_db(
            dialog=mock_dialog,
            response_text="New response text",
            last_message_id=last_message.telegram_message_id,
            last_message_timestamp=last_message.date,
            db_session=mock_session
        )
        
        # Verify response
        assert response is not None
        assert response is existing_response
        
        # Verify session methods were called
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify the existing response was updated
        assert existing_response.last_message_id == last_message.telegram_message_id
        assert existing_response.last_message_timestamp == last_message.date
        assert existing_response.suggested_response == "New response text"
        assert existing_response.status == ProcessingStatus.PENDING_APPROVAL
    
    @pytest.mark.asyncio
    @patch('app.services.response_generator.query_llm')
    @patch('app.services.response_generator.MessageFileStorage')
    async def test_generate_response_with_db(self, mock_message_storage, mock_query_llm, mock_dialog, mock_messages):
        """Test generating a response with database integration"""
        # Setup mocks
        mock_message_storage_instance = MagicMock()
        mock_message_storage.return_value = mock_message_storage_instance
        mock_message_storage_instance.get_latest_messages.return_value = mock_messages
        
        # Mock LLM response
        mock_query_llm.return_value = "I'd be happy to help with your project. What kind of project are you working on?"
        
        # Mock database session
        mock_session = MagicMock(spec=AsyncSession)
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute_result
        
        # Create response generator
        generator = ResponseGenerator(db_session=mock_session)
        
        # Generate response
        response = await generator.generate_response(mock_dialog, db_session=mock_session)
        
        # Verify response
        assert response is not None
        assert "response_text" in response
        assert "db_response" in response
        assert response["response_text"] == "I'd be happy to help with your project. What kind of project are you working on?"
        
        # Verify session methods were called
        assert mock_session.execute.call_count == 2  # Once to check for existing response, once to save
        mock_session.add.assert_called_once()
        assert mock_session.commit.call_count == 1
        
        # Verify the added object is a ProcessedResponse
        added_object = mock_session.add.call_args[0][0]
        assert isinstance(added_object, ProcessedResponse)
        assert added_object.dialog_id == mock_dialog.id
        assert added_object.last_message_id == "3"
        assert added_object.suggested_response == "I'd be happy to help with your project. What kind of project are you working on?"
        assert added_object.status == ProcessingStatus.PENDING_APPROVAL 