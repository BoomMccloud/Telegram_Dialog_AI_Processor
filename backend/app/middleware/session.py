"""
JWT-based session middleware for user authentication

This module provides a JWT-based session management system for handling
user authentication in the FastAPI application.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from starlette.types import ASGIApp, Receive, Scope, Send

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)

class SessionData(BaseModel):
    """Data structure for session information"""
    user_id: int
    exp: datetime
    iat: datetime
    is_authenticated: bool = False
    telegram_id: Optional[int] = None

class SessionMiddleware:
    """JWT-based session management middleware"""
    
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
                session = self.verify_session(token)
                # Add session data to scope
                scope["session"] = session
            except Exception as e:
                logger.warning(f"Session verification failed: {str(e)}")
                # Continue without session for error handling in the route
                pass
        
        # Continue processing the request
        await self.app(scope, receive, send)
    
    def create_session(self, user_id: int, is_qr: bool = False) -> str:
        """
        Create a new session token
        
        Args:
            user_id: The user's ID (0 for pending QR sessions)
            is_qr: Whether this is a QR login session
            
        Returns:
            JWT token string
        """
        try:
            # Set expiration time
            exp = datetime.utcnow() + self.token_expiration
            
            # Create token payload
            payload = {
                "user_id": user_id,
                "exp": exp,
                "iat": datetime.utcnow(),
                "is_authenticated": not is_qr,  # QR sessions start unauthenticated
                "telegram_id": None  # Will be set after QR login
            }
            
            # Create token
            token = jwt.encode(
                payload,
                self.secret_key,
                algorithm=self.algorithm
            )
            
            logger.debug(f"Created session token for user {user_id} (QR: {is_qr})")
            return token
            
        except Exception as e:
            logger.error(f"Error creating session token: {str(e)}")
            raise
    
    def verify_session(self, token: str) -> Optional[Dict]:
        """
        Verify and decode a session token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload if valid, None if invalid
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
                
            # Verify and decode token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            logger.debug(f"Verified session token for user {payload.get('user_id')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Session token expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error verifying session token: {str(e)}")
            raise
    
    def update_session(self, token: str, updates: Dict) -> str:
        """
        Update session data and create a new token
        
        Args:
            token: Current JWT token
            updates: Dictionary of fields to update
            
        Returns:
            New JWT token with updated data
        """
        current_data = self.verify_session(token)
        if not current_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session to update"
            )
        
        # Update the session data
        current_data.update(updates)
        
        # Create new token with updated data
        encoded_jwt = jwt.encode(
            current_data,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        logger.info(f"Updated session for user {current_data.get('user_id')}")
        return encoded_jwt 