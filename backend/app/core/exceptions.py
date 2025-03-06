from typing import Any, Dict, Optional
from fastapi import status

class BaseAppException(Exception):
    """Base exception for all application exceptions"""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class AuthenticationError(BaseAppException):
    """Authentication related errors"""
    def __init__(self, message: str, error_code: str = "AUTH_ERROR"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code
        )

class SessionError(AuthenticationError):
    """Session related errors"""
    def __init__(self, message: str):
        super().__init__(message=message, error_code="SESSION_ERROR")

class DatabaseError(BaseAppException):
    """Database related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details=details
        )

class ValidationError(BaseAppException):
    """Data validation errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details
        )

class TelegramError(BaseAppException):
    """Telegram API related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="TELEGRAM_ERROR",
            details=details
        )

class AIModelError(BaseAppException):
    """AI model (Claude) related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="AI_MODEL_ERROR",
            details=details
        )
