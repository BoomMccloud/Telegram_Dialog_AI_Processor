from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from telethon.errors import RPCError as TelethonError
from .exceptions import BaseAppException
from ..utils.logging import get_logger
from app.core.exceptions import ValidationError, TelegramError, DatabaseError

logger = get_logger(__name__)

async def app_exception_handler(request: Request, exc: BaseAppException):
    """Handle all application specific exceptions"""
    logger.error(
        f"Application error: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy errors"""
    logger.error(
        f"Database error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "A database error occurred",
                "details": {"debug_message": str(exc)}
            }
        }
    )

async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Validation Error", "message": str(exc), "details": exc.details}
    )

async def telegram_error_handler(request: Request, exc: TelegramError):
    return JSONResponse(
        status_code=503,
        content={"error": "Telegram API Error", "message": str(exc), "details": exc.details}
    )

async def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(
        status_code=500,
        content={"error": "Database Error", "message": str(exc), "details": exc.details}
    )

async def telethon_error_handler(request: Request, exc: TelethonError):
    return JSONResponse(
        status_code=503,
        content={"error": "Telegram API Error", "message": str(exc)}
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions"""
    logger.error(
        f"Unhandled error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"debug_message": str(exc)} if not isinstance(exc, HTTPException) else {}
            }
        }
    )
