"""
Authentication routes for Telegram integration
"""

import qrcode
from io import BytesIO
import base64
import os
import logging
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from telethon import TelegramClient
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.session import verify_session_dependency, SessionData
from ..utils.logging import get_logger
from ..db.database import get_db
from ..models.user import User
from ..models.session import Session, SessionStatus

router = APIRouter(prefix="/api")
logger = get_logger(__name__)

# Global storage for Telegram clients during QR auth
telegram_clients: Dict[str, Dict] = {}

class DevLoginRequest(BaseModel):
    """Request model for development login"""
    telegram_id: int

@router.post("/auth/dev-login")
async def dev_login(
    request: Request,
    login_data: DevLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Development-only endpoint to create an authenticated session"""
    if os.getenv("APP_ENV") != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode"
        )
    
    try:
        # Get session middleware from app state
        session_middleware = request.app.state.session_middleware
        
        # Create authenticated session
        session_data = await session_middleware.create_session(telegram_id=login_data.telegram_id)
        
        # Update session to authenticated state
        session_data = await session_middleware.update_session(
            session_data.token,
            login_data.telegram_id
        )
        
        logger.info(f"Development login successful for Telegram ID: {login_data.telegram_id}")
        return {
            "token": session_data.token,
            "status": session_data.status,
            "telegram_id": login_data.telegram_id
        }
        
    except Exception as e:
        logger.error(f"Development login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/auth/qr")
async def create_qr_auth(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new QR code authentication session using Telethon"""
    logger.info("Starting QR code authentication request")
    try:
        # Get session middleware from app state
        session_middleware = request.app.state.session_middleware
        
        # Create initial session
        session_data = await session_middleware.create_session(is_qr=True, db=db)
        token = session_data.token
        logger.debug(f"Created initial QR session token: {token}")
        
        # Create Telegram client
        client = TelegramClient(
            'anon',
            api_id=int(os.getenv("TELEGRAM_API_ID")),
            api_hash=os.getenv("TELEGRAM_API_HASH")
        )
        
        # Connect and get QR login data
        await client.connect()
        qr_login = await client.qr_login()
        
        # Store client info for QR monitoring
        telegram_clients[token] = {
            "client": client,
            "qr_login": qr_login
        }
        
        # Generate QR code
        qr = qrcode.QRCode()
        qr.add_data(qr_login.url)
        qr_image = qr.make_image()
        
        # Convert QR image to base64
        buffered = BytesIO()
        qr_image.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "token": token,
            "qr_code": qr_base64
        }
        
    except Exception as e:
        logger.error(f"QR code generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/auth/session/verify")
async def verify_session_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session: Optional[SessionData] = Depends(verify_session_dependency)
):
    """Verify session status and return user data if authenticated"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = auth_header.split(" ")[1]
        
        # Get session middleware from app state
        session_middleware = request.app.state.session_middleware
        
        # Verify session
        session_data = await session_middleware.verify_session(token, db=db)
        
        return {
            "status": session_data.status,
            "telegram_id": session_data.telegram_id,
            "expires_at": session_data.expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session verification failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/auth/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session: SessionData = Depends(verify_session_dependency)
):
    """Log out and invalidate the current session"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = auth_header.split(" ")[1]
        
        # Get session middleware from app state
        session_middleware = request.app.state.session_middleware
        
        # Delete session
        await session_middleware.delete_session(db, token)
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Development-only routes
if os.getenv("APP_ENV", "development") == "development":
    @router.post("/auth/force-session")
    async def force_create_session(request: Request) -> Dict:
        """
        FOR DEVELOPMENT USE ONLY: Create an authenticated session
        """
        session_middleware = request.app.state.session_middleware
        session = await session_middleware.create_session(telegram_id=12345678)
        
        return {
            "token": session.token,
            "status": "authenticated",
            "telegram_id": 12345678
        } 