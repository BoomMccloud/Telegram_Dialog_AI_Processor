"""
Authentication-related dependencies for FastAPI
"""

from typing import Optional
import os
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.session_manager import SessionManager
from app.models.session import Session, TokenType

# Initialize SessionManager with settings
def get_session_manager() -> SessionManager:
    """Get SessionManager instance with settings"""
    settings = {
        "jwt_secret": os.getenv("JWT_SECRET", "your-secret-key"),
        "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        "refresh_token_expire_minutes": int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))
    }
    return SessionManager(settings)

async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_manager: SessionManager = Depends(get_session_manager)
) -> Optional[Session]:
    """
    Get current session from request
    
    Args:
        request: FastAPI request
        db: Database session
        session_manager: SessionManager instance
        
    Returns:
        Current session if valid, None otherwise
        
    Raises:
        HTTPException: If session is invalid or expired
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
        
    token = auth_header.split(" ")[1]
    return await session_manager.verify_session(db, token)

async def get_refresh_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_manager: SessionManager = Depends(get_session_manager)
) -> Session:
    """
    Get session from refresh token
    
    Args:
        request: FastAPI request
        db: Database session
        session_manager: SessionManager instance
        
    Returns:
        Session if valid
        
    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
        
    token = auth_header.split(" ")[1]
    return await session_manager.verify_session(db, token, TokenType.REFRESH) 