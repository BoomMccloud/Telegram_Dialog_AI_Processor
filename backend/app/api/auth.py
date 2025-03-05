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
from telethon import TelegramClient

from ..middleware.session import verify_session_dependency, SessionData
from ..utils.logging import get_logger

router = APIRouter(prefix="/api")
logger = get_logger(__name__)

# Global storage for Telegram clients during QR auth
telegram_clients: Dict[str, Dict] = {}

@router.post("/auth/qr")
async def create_qr_auth(request: Request):
    """Create a new QR code authentication session using Telethon"""
    logger.info("Starting QR code authentication request")
    try:
        # Get session middleware from app state
        session_middleware = request.app.state.session_middleware
        
        # Create initial session token
        token = await session_middleware.create_session(is_qr=True)
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
            "qr_code": qr_base64,
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Error creating QR auth session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/auth/session/verify")
async def verify_session(request: Request, token: str):
    """
    Verify a session's validity and status
    
    Args:
        token: JWT token to verify
        
    Returns:
        Session status information
    """
    try:
        # Get session middleware from app state
        session_middleware = request.app.state.session_middleware
        
        # Verify session in database
        session = await session_middleware.verify_session(token)
        
        return {
            "status": session.status,
            "telegram_id": session.telegram_id,
            "expires_at": session.expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

@router.post("/auth/logout")
async def logout(session: SessionData = Depends(verify_session_dependency)):
    """
    Explicitly log out a session and clean up all associated resources
    """
    try:
        # Clean up Telegram client if this was a QR session
        if session.token in telegram_clients:
            client_data = telegram_clients[session.token]
            if client_data["client"]:
                try:
                    await client_data["client"].disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting Telegram client: {str(e)}")
            del telegram_clients[session.token]
        
        # Mark session as expired in database
        session_middleware = request.app.state.session_middleware
        await session_middleware.update_session(
            session.token,
            {"status": "expired"}
        )
        
        return {"status": "success", "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during logout: {str(e)}"
        )

# Development-only routes
if os.getenv("APP_ENV", "development") == "development":
    @router.post("/auth/force-session")
    async def force_create_session(request: Request) -> Dict:
        """
        FOR DEVELOPMENT USE ONLY: Create an authenticated session
        """
        session_middleware = request.app.state.session_middleware
        token = await session_middleware.create_session(
            telegram_id=12345678,  # Mock telegram ID
            is_qr=False
        )
        
        return {
            "token": token,
            "status": "authenticated",
            "telegram_id": 12345678
        } 