"""
Session middleware for validating user authentication

This module provides middleware functions for verifying session validity
before allowing access to protected API endpoints.
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Security scheme for session headers
security = HTTPBearer(auto_error=False)

async def verify_session(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict:
    """
    Verify that the session is valid and active
    
    This function extracts the session ID from the request and validates
    that the session exists and is active. It can be used as a dependency
    for protected API endpoints.
    
    Args:
        request: FastAPI request object
        credentials: Optional HTTP authorization credentials
        
    Returns:
        The session data if valid
        
    Raises:
        HTTPException: If session is missing or invalid
    """
    # Get session ID from path parameters if present
    session_id = None
    if "session_id" in request.path_params:
        session_id = request.path_params["session_id"]
        logger.debug(f"Using session ID from path: {session_id}")
    
    # If not in path, try X-Session-ID header
    if not session_id:
        session_id = request.headers.get("X-Session-ID")
        logger.debug(f"Using session ID from header: {session_id}")
    
    # If not in header, try Authorization bearer token
    if not session_id and credentials:
        session_id = credentials.credentials
        logger.debug(f"Using session ID from Authorization: {session_id}")
    
    # If still no session ID, this is an unauthorized request
    if not session_id:
        logger.warning("Request without session ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID required for authentication",
        )
    
    # Get the session middleware instance from app state
    session_middleware = request.app.state.session_middleware
    if not session_middleware:
        logger.error("Session middleware not initialized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session middleware not initialized",
        )
    
    # Validate the session
    try:
        session = session_middleware.verify_session(session_id)
    except Exception as e:
        logger.warning(f"Invalid session ID: {session_id} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    
    # Check for required session data
    if "user_id" not in session:
        logger.warning(f"Session missing user_id: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session authentication incomplete",
        )
    
    # Return the session for use in the endpoint
    return session


async def admin_only(session: Dict = Depends(verify_session)) -> Dict:
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