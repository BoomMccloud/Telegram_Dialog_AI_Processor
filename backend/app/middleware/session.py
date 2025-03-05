"""
JWT-based session middleware with PostgreSQL storage for user authentication

This module provides a JWT-based session management system with PostgreSQL storage
for handling user authentication in the FastAPI application.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable
import uuid

import jwt
from fastapi import HTTPException, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from starlette.types import ASGIApp, Receive, Scope, Send

from app.utils.logging import get_logger
from app.db.database import get_raw_connection

logger = get_logger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)

class SessionData(BaseModel):
    """Data structure for session information"""
    id: uuid.UUID
    telegram_id: Optional[int]
    status: str
    token: str
    created_at: datetime
    expires_at: datetime
    metadata: Dict = {}

class SessionMiddleware:
    """JWT-based session management middleware with PostgreSQL storage"""
    
    def __init__(self, app: Optional[ASGIApp] = None):
        """
        Initialize the session middleware with configuration
        
        Args:
            app: Optional ASGI application
        """
        self.app = app
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # Default for development
        self.algorithm = "HS256"
        self.token_expiration = timedelta(minutes=60)  # 1 hour default
        logger.info("Session middleware initialized with JWT configuration")
        
        self.access_token_expire_minutes = 1440  # 24 hours
        self.qr_token_expire_minutes = 10  # 10 minutes for QR code sessions
        
        # Store self in app state if app is provided
        if app and hasattr(app, 'state'):
            app.state.session_middleware = self
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """
        ASGI middleware implementation
        
        Args:
            scope: The ASGI connection scope
            receive: The ASGI receive function
            send: The ASGI send function
        """
        if not self.app:
            raise RuntimeError("SessionMiddleware requires an ASGI application when used as middleware")
            
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Add middleware instance to scope for access in endpoints
        scope["session_middleware"] = self
        
        # Skip auth for non-protected routes
        path = scope.get("path", "")
        if path in ["/api/auth/qr", "/api/auth/session", "/health"]:
            await self.app(scope, receive, send)
            return
            
        # Get token from headers
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Verify the session
                session = await self.verify_session(token)
                # Add session data to scope
                scope["session"] = session
            except Exception as e:
                logger.warning(f"Session verification failed: {str(e)}")
                # Continue without session for error handling in the route
                pass
        
        # Continue processing the request
        await self.app(scope, receive, send)
    
    async def create_session(self, telegram_id: Optional[int] = None, is_qr: bool = False) -> str:
        """
        Create a new session token and store in database
        
        Args:
            telegram_id: The user's Telegram ID (None for pending QR sessions)
            is_qr: Whether this is a QR login session
            
        Returns:
            JWT token string
        """
        try:
            # Set expiration time based on session type
            expires_at = datetime.utcnow() + (
                timedelta(minutes=self.qr_token_expire_minutes) if is_qr 
                else timedelta(minutes=self.access_token_expire_minutes)
            )
            
            # Create token payload
            payload = {
                "jti": str(uuid.uuid4()),  # JWT ID
                "telegram_id": telegram_id,
                "exp": expires_at,
                "iat": datetime.utcnow(),
                "is_qr": is_qr
            }
            
            # Create JWT token
            token = jwt.encode(
                payload,
                self.secret_key,
                algorithm=self.algorithm
            )
            
            # Store session in database
            async with await get_raw_connection() as conn:
                session = await conn.fetchrow("""
                    INSERT INTO sessions (
                        telegram_id, status, token, expires_at, 
                        metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5
                    ) RETURNING *
                """, 
                telegram_id,
                'pending' if is_qr else 'authenticated',
                token,
                expires_at,
                {'is_qr': is_qr}
                )
            
            logger.debug(f"Created session token for user {telegram_id} (QR: {is_qr})")
            return token
            
        except Exception as e:
            logger.error(f"Error creating session token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create session: {str(e)}"
            )
    
    async def verify_session(self, token: str) -> Optional[SessionData]:
        """
        Verify and retrieve session from database
        
        Args:
            token: JWT token string
            
        Returns:
            Session data if valid
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
                
            # First verify JWT signature and expiration
            try:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm]
                )
            except jwt.ExpiredSignatureError:
                logger.warning("JWT token expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired"
                )
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT token: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session token"
                )
                
            # Then verify session in database
            async with await get_raw_connection() as conn:
                session = await conn.fetchrow("""
                    SELECT * FROM sessions 
                    WHERE token = $1 
                      AND status != 'expired'
                      AND expires_at > NOW()
                """, token)
                
                if not session:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session not found or expired"
                    )
                    
                # Convert to SessionData model
                return SessionData(**dict(session))
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying session token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Session verification failed: {str(e)}"
            )
    
    async def update_session(self, token: str, updates: Dict) -> str:
        """
        Update session data in database and create new token
        
        Args:
            token: Current JWT token
            updates: Dictionary of fields to update
            
        Returns:
            New JWT token with updated data
        """
        try:
            # First verify current session
            current_session = await self.verify_session(token)
            
            # Create new token with updated data
            new_token = jwt.encode(
                {
                    "jti": str(uuid.uuid4()),
                    "telegram_id": updates.get('telegram_id', current_session.telegram_id),
                    "exp": updates.get('expires_at', current_session.expires_at),
                    "iat": datetime.utcnow()
                },
                self.secret_key,
                algorithm=self.algorithm
            )
            
            # Update database
            async with await get_raw_connection() as conn:
                session = await conn.fetchrow("""
                    UPDATE sessions 
                    SET 
                        telegram_id = COALESCE($1, telegram_id),
                        status = COALESCE($2, status),
                        token = $3,
                        expires_at = COALESCE($4, expires_at),
                        metadata = COALESCE($5, metadata)
                    WHERE token = $6
                    RETURNING *
                """,
                updates.get('telegram_id'),
                updates.get('status'),
                new_token,
                updates.get('expires_at'),
                updates.get('metadata'),
                token
                )
                
                if not session:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Session not found"
                    )
            
            logger.info(f"Updated session for user {session['telegram_id']}")
            return new_token
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update session: {str(e)}"
            )
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions from database"""
        try:
            async with await get_raw_connection() as conn:
                await conn.execute("""
                    UPDATE sessions 
                    SET status = 'expired'
                    WHERE (expires_at < NOW() OR status = 'pending')
                      AND status != 'expired'
                """)
                
            logger.info("Cleaned up expired sessions")
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}")
            # Don't raise exception as this is a background task 