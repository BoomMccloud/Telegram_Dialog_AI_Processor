"""
Tests for the background worker service
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.services.worker import DialogWorker
from app.db.models.dialog import Dialog
from app.db.models.user import User
from app.db.models.session import Session
from app.db.database import async_session

@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = AsyncMock()
    db.query = MagicMock()
    db.execute = AsyncMock()
    return db

@pytest.fixture
def mock_dialog():
    """Create a mock dialog"""
    return Dialog(
        id=uuid4(),
        telegram_dialog_id="123456",
        user_id=uuid4(),
        title="Test Dialog",
        type="PRIVATE",
        is_processing_enabled=True
    )

@pytest.fixture
def mock_user():
    """Create a mock user"""
    return User(
        id=uuid4(),
        telegram_id=123456,
        username="test_user"
    )

@pytest.fixture
def mock_session():
    """Create a mock session"""
    return Session(
        id=uuid4(),
        user_id=uuid4(),
        token="test_token",
        expires_at=datetime.now()
    )

@pytest.mark.asyncio
async def test_get_processing_enabled_dialogs(mock_db, mock_dialog):
    """Test getting processing enabled dialogs"""
    # Setup mock response for execute
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_dialog]
    
    # Setup mock for count query
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 1
    
    # Configure the execute method to return different results on each call
    mock_db.execute = AsyncMock()
    mock_db.execute.side_effect = [mock_result, mock_count_result]
    
    # Create a context manager that returns our mock_db
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_db
    mock_session_cm.__aexit__.return_value = None
    
    with patch('app.services.worker.async_session', return_value=mock_session_cm):
        worker = DialogWorker()
        dialogs = await worker.get_processing_enabled_dialogs()
        
        assert len(dialogs) == 1
        assert dialogs[0].id == mock_dialog.id
        assert mock_db.execute.call_count == 2

@pytest.mark.asyncio
async def test_process_dialogs(mock_db, mock_dialog, mock_user, mock_session):
    """Test processing dialogs for a user"""
    # Mock user query result
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = mock_user
    
    # Mock session query result
    mock_session_result = MagicMock()
    mock_session_result.scalar_one_or_none.return_value = mock_session
    
    # Configure the execute method
    mock_db.execute = AsyncMock()
    mock_db.execute.side_effect = [mock_user_result, mock_session_result]
    
    # Create a context manager that returns our mock_db
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_db
    mock_session_cm.__aexit__.return_value = None
    
    # Mock dialog processor
    mock_processor_instance = AsyncMock()
    mock_processor_instance.process_dialogs.return_value = {mock_dialog.id: True}
    mock_processor_class = MagicMock(return_value=mock_processor_instance)
    
    with patch('app.services.worker.async_session', return_value=mock_session_cm):
        with patch('app.services.worker.DialogProcessor', mock_processor_class):
            worker = DialogWorker()
            result = await worker.process_dialogs([mock_dialog])
            
            # Verify dialog processor was called with correct arguments
            mock_processor_instance.process_dialogs.assert_called_once_with(
                [mock_dialog], mock_session.token
            )
            assert result == 1

@pytest.mark.asyncio
async def test_process_dialogs_no_user(mock_db, mock_dialog):
    """Test processing dialogs when user not found"""
    # Mock user query result with no user found
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = None
    
    # Configure the execute method
    mock_db.execute = AsyncMock()
    mock_db.execute.return_value = mock_user_result
    
    # Create a context manager that returns our mock_db
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_db
    mock_session_cm.__aexit__.return_value = None
    
    with patch('app.services.worker.async_session', return_value=mock_session_cm):
        worker = DialogWorker()
        result = await worker.process_dialogs([mock_dialog])
        
        # Verify no further processing was attempted
        assert mock_db.execute.call_count == 1
        assert result == 0

@pytest.mark.asyncio
async def test_run_once(mock_db, mock_dialog, mock_user, mock_session):
    """Test running a single processing cycle"""
    # Mock get_processing_enabled_dialogs
    with patch.object(DialogWorker, 'get_processing_enabled_dialogs', 
                     return_value=[mock_dialog]) as mock_get_dialogs:
        
        # Mock process_dialogs
        with patch.object(DialogWorker, 'process_dialogs', 
                         return_value=1) as mock_process:
            worker = DialogWorker(mock_db)
            await worker.run_once()
            
            # Verify methods were called
            mock_get_dialogs.assert_called_once()
            mock_process.assert_called_once_with([mock_dialog])

@pytest.mark.asyncio
async def test_run_once_no_dialogs(mock_db):
    """Test running a single processing cycle with no dialogs"""
    # Mock get_processing_enabled_dialogs returning empty list
    with patch.object(DialogWorker, 'get_processing_enabled_dialogs', 
                     return_value=[]) as mock_get_dialogs:
        
        # Mock process_dialogs
        with patch.object(DialogWorker, 'process_dialogs') as mock_process:
            worker = DialogWorker(mock_db)
            await worker.run_once()
            
            # Verify get_dialogs was called but process_dialogs was not
            mock_get_dialogs.assert_called_once()
            mock_process.assert_not_called()

@pytest.mark.asyncio
async def test_run_once_error(mock_db):
    """Test running a single processing cycle with an error"""
    # Mock get_processing_enabled_dialogs raising an exception
    with patch.object(DialogWorker, 'get_processing_enabled_dialogs', 
                     side_effect=Exception("Test error")) as mock_get_dialogs:
        
        worker = DialogWorker(mock_db)
        await worker.run_once()
        
        # Verify method was called and exception was handled
        mock_get_dialogs.assert_called_once() 