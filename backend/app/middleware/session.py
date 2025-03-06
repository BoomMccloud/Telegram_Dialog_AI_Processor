"""
JWT-based session middleware with SQLAlchemy ORM for user authentication

This module provides a JWT-based session management system using SQLAlchemy ORM
for handling user authentication in the FastAPI application.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import uuid

import jwt
from fastapi import FastAPI, Request, Response, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logging import get_logger
from app.db.database import get_db
from app.models.session import Session, SessionStatus
from app.models.user import User
from app.core.exceptions import SessionError, AuthenticationError, DatabaseError

logger = get_logger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)

def utcnow() -> datetime:
    """Get current UTC datetime with timezone info"""
    return datetime.now(timezone.utc)

class SessionData(BaseModel):
    """Data structure for session information"""
    id: uuid.UUID
    telegram_id: Optional[int] = None
    status: str
    token: str
    created_at: datetime
    expires_at: datetime
    session_metadata: Dict = {}

    @model_validator(mode='before')
    def set_defaults(cls, values):
        if 'id' not in values:
            values['id'] = uuid.uuid4()
        if 'created_at' not in values:
            values['created_at'] = utcnow()
        if 'session_metadata' not in values:
            values['session_metadata'] = {}
        return values

# List of paths that don't require authentication
PUBLIC_PATHS = {
    "/api/auth/qr",
    "/api/auth/session/verify",
    "/api/auth/dev-login",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json"
}

class SessionMiddleware(BaseHTTPMiddleware):
    """JWT-based session management middleware with FastAPI"""
    
    def __init__(self, app: FastAPI):
        """
        Initialize the session middleware with configuration
        
        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
        self.app = app
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key")
        self.access_token_expire_minutes = 1440  # 24 hours
        self.qr_token_expire_minutes = 10  # 10 minutes for QR code sessions
        logger.info("Session middleware initialized with SQLAlchemy ORM")

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process each request through the session middleware"""
        # Always allow OPTIONS requests for CORS
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # Allow public paths without authentication
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth: Optional[HTTPAuthorizationCredentials] = await security(request)
        if not auth:
            raise AuthenticationError("Authorization header required")

        try:
            token = auth.credentials
            async with request.app.state.db_pool() as db:
                session = await self.verify_session(token, db=db)
                request.state.session = session
                request.state.user = None
                
                if session.telegram_id:
                    stmt = select(User).where(User.telegram_id == session.telegram_id)
                    result = await db.execute(stmt)
                    user = result.scalar_one_or_none()
                    if user:
                        request.state.user = user
                        
                response = await call_next(request)
                return response
        except (SessionError, AuthenticationError):
            raise
        except Exception as e:
            logger.error(f"Session middleware error: {str(e)}", exc_info=True)
            raise DatabaseError("Database operation failed", details={"error": str(e)})

    async def create_session(self, db: AsyncSession, telegram_id: Optional[int] = None, is_qr: bool = False, metadata: Dict = None) -> Session:
        """Create and store session in database using ORM"""
        try:
            # If telegram_id is provided, verify user exists
            if telegram_id:
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                if not user:
                    raise SessionError(f"User with telegram_id {telegram_id} not found")
            
            # Generate JWT token
            token_data = {
                "jti": str(uuid.uuid4()),
                "exp": utcnow() + timedelta(
                    minutes=self.qr_token_expire_minutes if is_qr else self.access_token_expire_minutes
                )
            }
            token = jwt.encode(token_data, self.jwt_secret, algorithm="HS256")
            
            # Create session
            session = Session(
                token=token,
                telegram_id=telegram_id,
                status=SessionStatus.PENDING if not telegram_id else SessionStatus.AUTHENTICATED,
                expires_at=token_data["exp"],
                metadata=metadata or {}
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
            return session
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to create session", details={"error": str(e)})
               
    async def verify_session(self, token: str, db: AsyncSession) -> Session:
        """Verify and return session data using ORM"""
        try:
            stmt = select(Session).where(
                Session.token == token,
                Session.expires_at > utcnow()
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                raise SessionError("Invalid or expired session")
            
            return session
        except SessionError:
            raise
        except Exception as e:
            logger.error(f"Session verification failed: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to verify session", details={"error": str(e)})
           
    async def update_session(self, token: str, telegram_id: int, db: AsyncSession) -> Session:
        """Update session after successful authentication using ORM"""
        try:
            # Verify user exists
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                raise SessionError(f"User with telegram_id {telegram_id} not found")
            
            # Get session
            stmt = select(Session).where(
                Session.token == token,
                Session.expires_at > utcnow()
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                raise SessionError("Session not found or expired")
            
            session.telegram_id = telegram_id
            session.status = SessionStatus.AUTHENTICATED
            session.expires_at = utcnow() + timedelta(days=7)
            
            await db.commit()
            await db.refresh(session)
            return session
        except SessionError:
            raise
        except Exception as e:
            logger.error(f"Failed to update session: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to update session", details={"error": str(e)})
        
    async def cleanup_expired_sessions(self, db: AsyncSession):
        """Clean up expired sessions using ORM"""
        try:
            stmt = delete(Session).where(Session.expires_at < utcnow())
            await db.execute(stmt)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to cleanup expired sessions", details={"error": str(e)})

async def verify_session_dependency(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> SessionData:
    """
    FastAPI dependency for verifying session in route handlers
    
    Args:
        request: FastAPI request object
        credentials: Optional HTTP authorization credentials
        
    Returns:
        The session data if valid
        
    Raises:
        HTTPException: If session is missing or invalid
    """
    if not credentials:
        raise AuthenticationError("Authorization header required")
    
    try:
        session_middleware = request.app.state.session_middleware
        async with request.app.state.db_pool() as db:
            session = await session_middleware.verify_session(credentials.credentials, db)
            return session
    except Exception as e:
        logger.warning(f"Session verification failed: {str(e)}")
        raise AuthenticationError("Invalid or expired session")

async def admin_only(session: SessionData = Depends(verify_session_dependency)) -> SessionData:
    """
    Verify that the user has admin privileges
    
    Args:
        session: Session data from verify_session dependency
        
    Returns:
        The session data if valid
        
    Raises:
        HTTPException: If user is not an admin
    """
    # This is a placeholder for future admin validation
    # For now, just return the session
    return session 