"""
JWT-based session middleware with SQLAlchemy ORM for user authentication

This module provides a JWT-based session management system using SQLAlchemy ORM
for handling user authentication in the FastAPI application.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import uuid

import jwt
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logging import get_logger
from app.db.database import get_db
from app.models.session import Session, SessionStatus
from app.models.user import User

logger = get_logger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)

class SessionData(BaseModel):
    """Data structure for session information"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    telegram_id: Optional[int] = None
    status: str
    token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    session_metadata: Dict = Field(default_factory=dict)

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

class SessionMiddleware:
    """JWT-based session management middleware with FastAPI"""
    
    def __init__(self, app: FastAPI):
        """
        Initialize the session middleware with configuration
        
        Args:
            app: FastAPI application instance
        """
        self.app = app
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key")
        self.access_token_expire_minutes = 1440  # 24 hours
        self.qr_token_expire_minutes = 10  # 10 minutes for QR code sessions
        logger.info("Session middleware initialized with SQLAlchemy ORM")

    async def create_session(self, telegram_id: Optional[int] = None, is_qr: bool = False, db: AsyncSession = Depends(get_db)) -> Session:
        """Create and store session in database using ORM
        
        Args:
            telegram_id: Optional Telegram user ID for pre-authenticated sessions
            is_qr: Whether this is a QR code authentication session
            db: SQLAlchemy AsyncSession
            
        Returns:
            The created session object
        """
        # Generate JWT token
        token_data = {
            "jti": str(uuid.uuid4()),
            "exp": datetime.utcnow() + timedelta(
                minutes=self.qr_token_expire_minutes if is_qr else self.access_token_expire_minutes
            )
        }
        token = jwt.encode(token_data, self.jwt_secret, algorithm="HS256")
        
        # Create session
        session = Session(
            token=token,
            telegram_id=telegram_id,
            status=SessionStatus.PENDING if not telegram_id else SessionStatus.AUTHENTICATED,
            expires_at=token_data["exp"]
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
               
    async def verify_session(self, token: str, db: AsyncSession) -> Session:
        """Verify and return session data using ORM"""
        stmt = select(Session).where(
            Session.token == token,
            Session.expires_at > datetime.utcnow()
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(401, "Invalid or expired session")
            
        return session
           
    async def update_session(self, token: str, telegram_id: int) -> Session:
        """Update session after successful authentication using ORM"""
        stmt = select(Session).where(Session.token == token)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(401, "Session not found")
            
        session.telegram_id = telegram_id
        session.status = SessionStatus.AUTHENTICATED
        session.expires_at = datetime.utcnow() + timedelta(days=7)
        
        await self.db.commit()
        await self.db.refresh(session)
        return session
        
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions using ORM"""
        stmt = delete(Session).where(Session.expires_at < datetime.utcnow())
        await self.db.execute(stmt)
        await self.db.commit()
        
    async def __call__(self, request: Request, call_next) -> Response:
        """Process each request through the session middleware"""
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth: Optional[HTTPAuthorizationCredentials] = await security(request)
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required"
            )

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
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session middleware error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    try:
        session_middleware = request.app.state.session_middleware
        async with request.app.state.db_pool() as db:
            session = await session_middleware.verify_session(credentials.credentials, db)
            return session
    except Exception as e:
        logger.warning(f"Session verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

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