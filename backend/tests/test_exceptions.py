import pytest
from fastapi import status
from app.core.exceptions import (
    BaseAppException,
    AuthenticationError,
    SessionError,
    DatabaseError,
    ValidationError,
    TelegramError,
    AIModelError
)

def test_base_app_exception():
    """Test BaseAppException creation and attributes"""
    exc = BaseAppException(
        message="Test error",
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code="TEST_ERROR",
        details={"test": "detail"}
    )
    
    assert exc.message == "Test error"
    assert exc.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.error_code == "TEST_ERROR"
    assert exc.details == {"test": "detail"}
    assert str(exc) == "Test error"

def test_authentication_error():
    """Test AuthenticationError defaults"""
    exc = AuthenticationError("Auth failed")
    
    assert exc.message == "Auth failed"
    assert exc.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.error_code == "AUTH_ERROR"
    assert exc.details == {}

def test_session_error():
    """Test SessionError defaults"""
    exc = SessionError("Session invalid")
    
    assert exc.message == "Session invalid"
    assert exc.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.error_code == "SESSION_ERROR"
    assert exc.details == {}

def test_database_error():
    """Test DatabaseError with details"""
    details = {"table": "users", "operation": "insert"}
    exc = DatabaseError("DB error", details=details)
    
    assert exc.message == "DB error"
    assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.error_code == "DATABASE_ERROR"
    assert exc.details == details

def test_validation_error():
    """Test ValidationError with details"""
    details = {"field": "email", "error": "invalid format"}
    exc = ValidationError("Invalid data", details=details)
    
    assert exc.message == "Invalid data"
    assert exc.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.error_code == "VALIDATION_ERROR"
    assert exc.details == details

def test_telegram_error():
    """Test TelegramError with details"""
    details = {"api_error": "connection failed"}
    exc = TelegramError("Telegram API error", details=details)
    
    assert exc.message == "Telegram API error"
    assert exc.status_code == status.HTTP_502_BAD_GATEWAY
    assert exc.error_code == "TELEGRAM_ERROR"
    assert exc.details == details

def test_ai_model_error():
    """Test AIModelError with details"""
    details = {"model": "claude", "error": "token limit exceeded"}
    exc = AIModelError("Model error", details=details)
    
    assert exc.message == "Model error"
    assert exc.status_code == status.HTTP_502_BAD_GATEWAY
    assert exc.error_code == "AI_MODEL_ERROR"
    assert exc.details == details 