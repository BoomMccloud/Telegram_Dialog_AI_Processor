import pytest
from fastapi import Request, status
from sqlalchemy.exc import SQLAlchemyError
from telethon.errors import TelegramError as TelethonError
from app.core.exceptions import (
    BaseAppException,
    AuthenticationError,
    DatabaseError
)
from app.core.error_handlers import (
    app_exception_handler,
    sqlalchemy_exception_handler,
    telegram_exception_handler,
    unhandled_exception_handler
)

@pytest.fixture
def mock_request():
    """Create a mock request for testing"""
    class MockRequest:
        def __init__(self):
            self.url = type('URL', (), {'path': '/test/path'})()
    return MockRequest()

async def test_app_exception_handler(mock_request):
    """Test handling of BaseAppException"""
    exc = BaseAppException(
        message="Test error",
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code="TEST_ERROR",
        details={"test": "detail"}
    )
    
    response = await app_exception_handler(mock_request, exc)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.body == b'{"error":{"code":"TEST_ERROR","message":"Test error","details":{"test":"detail"}}}'

async def test_sqlalchemy_exception_handler(mock_request):
    """Test handling of SQLAlchemy errors"""
    exc = SQLAlchemyError("Database connection failed")
    
    response = await sqlalchemy_exception_handler(mock_request, exc)
    
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert b'"code":"DATABASE_ERROR"' in response.body
    assert b'"message":"A database error occurred"' in response.body
    assert b'"debug_message":"Database connection failed"' in response.body

async def test_telegram_exception_handler(mock_request):
    """Test handling of Telegram errors"""
    exc = TelethonError("API connection failed")
    
    response = await telegram_exception_handler(mock_request, exc)
    
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert b'"code":"TELEGRAM_ERROR"' in response.body
    assert b'"message":"Error communicating with Telegram"' in response.body
    assert b'"debug_message":"API connection failed"' in response.body

async def test_unhandled_exception_handler(mock_request):
    """Test handling of unhandled exceptions"""
    exc = ValueError("Unexpected error")
    
    response = await unhandled_exception_handler(mock_request, exc)
    
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert b'"code":"INTERNAL_ERROR"' in response.body
    assert b'"message":"An unexpected error occurred"' in response.body
    assert b'"debug_message":"Unexpected error"' in response.body 