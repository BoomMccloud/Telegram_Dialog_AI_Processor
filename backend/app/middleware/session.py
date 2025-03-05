"""
JWT-based session middleware with PostgreSQL storage for user authentication

This module provides a JWT-based session management system with PostgreSQL storage
for handling user authentication in the FastAPI application.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import uuid

import jwt
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.utils.logging import get_logger
from app.db.database import get_raw_connection

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
    metadata: Dict = Field(default_factory=dict)

# List of paths that don't require authentication
PUBLIC_PATHS = {
    "/api/auth/qr",
    "/api/auth/session/verify",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json"
}

class SessionMiddleware:
    """JWT-based session management middleware with FastAPI"""
    
    def __init__(self, testing: bool = False):
        """
        Initialize the session middleware with configuration
        
        Args:
            testing: Whether the middleware is running in test mode
        """
        self.testing = testing
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # Default for development
        self.algorithm = "HS256"
        self.token_expiration = timedelta(minutes=60)  # 1 hour default
        logger.info("Session middleware initialized with JWT configuration")
        
        self.access_token_expire_minutes = 1440  # 24 hours
        self.qr_token_expire_minutes = 10  # 10 minutes for QR code sessions

    async def __call__(self, request: Request, call_next):
        """FastAPI middleware callable"""
        # Skip auth for public routes
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        
        # Get token from headers
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Verify the session
                session = await self.verify_session(token)
                # Add session data to request state
                request.state.session = session
            except Exception as e:
                logger.warning(f"Session verification failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired session"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required"
            )
        
        response = await call_next(request)
        return response
    
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
            logger.debug(f"Creating session: telegram_id={telegram_id}, is_qr={is_qr}")
            
            # Set expiration time based on session type
            expires_at = datetime.utcnow() + (
                timedelta(minutes=self.qr_token_expire_minutes) if is_qr 
                else timedelta(minutes=self.access_token_expire_minutes)
            )
            logger.debug(f"Session will expire at: {expires_at}")
            
            # Create token payload
            payload = {
                "jti": str(uuid.uuid4()),  # JWT ID
                "telegram_id": telegram_id,
                "exp": expires_at,
                "iat": datetime.utcnow(),
                "is_qr": is_qr
            }
            logger.debug(f"Created JWT payload: {payload}")
            
            # Create JWT token
            token = jwt.encode(
                payload,
                self.secret_key,
                algorithm=self.algorithm
            )
            logger.debug("JWT token created successfully")
            
            if not self.testing:
                # Store session in database
                logger.debug("Storing session in database...")
                conn = await get_raw_connection()
                try:
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
                    json.dumps({'is_qr': is_qr})  # Convert metadata to JSON string
                    )
                    logger.debug("Session stored in database successfully")
                finally:
                    await conn.close()
            
            logger.info(f"Created session token for user {telegram_id} (QR: {is_qr})")
            return token
            
        except Exception as e:
            logger.error(f"Error creating session token: {str(e)}", exc_info=True)
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
                
            if self.testing:
                # In test mode, just return session data from JWT payload
                return SessionData(
                    id=uuid.UUID(payload["jti"]),
                    telegram_id=payload.get("telegram_id"),
                    status="authenticated",
                    token=token,
                    created_at=datetime.fromtimestamp(payload["iat"]),
                    expires_at=datetime.fromtimestamp(payload["exp"]),
                    metadata={"is_qr": payload.get("is_qr", False)}
                )
                
            # Then verify session in database
            conn = await get_raw_connection()
            try:
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
            finally:
                await conn.close()
            
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
            
            if not self.testing:
                # Update session in database
                conn = await get_raw_connection()
                try:
                    await conn.execute("""
                        UPDATE sessions 
                        SET 
                            telegram_id = COALESCE($1, telegram_id),
                            status = COALESCE($2, status),
                            token = $3,
                            expires_at = COALESCE($4, expires_at),
                            metadata = COALESCE($5, metadata)
                        WHERE token = $6
                    """,
                    updates.get('telegram_id'),
                    updates.get('status'),
                    new_token,
                    updates.get('expires_at'),
                    updates.get('metadata'),
                    token
                    )
                finally:
                    await conn.close()
            
            logger.debug(f"Updated session for user {current_session.telegram_id}")
            return new_token
            
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update session: {str(e)}"
            )
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions from the database"""
        if self.testing:
            return
            
        try:
            conn = await get_raw_connection()
            try:
                result = await conn.execute("""
                    DELETE FROM sessions 
                    WHERE expires_at < NOW() 
                      OR status = 'expired'
                """)
                logger.info(f"Cleaned up expired sessions: {result}")
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}") 

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
        session = await session_middleware.verify_session(credentials.credentials)
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