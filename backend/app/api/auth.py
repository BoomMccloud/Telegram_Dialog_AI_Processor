"""
Authentication routes for Telegram integration
"""

import qrcode
from io import BytesIO
import base64
import os
from typing import Dict, Optional, Any
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from telethon import TelegramClient
from pathlib import Path

from ..utils.logging import get_logger
from ..db.database import get_db
from ..db.models.session import Session, SessionStatus
from ..db.models.user import User
from ..middleware.session import SessionMiddleware, verify_session_dependency
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from telethon.client import TelegramClient
from telethon.tl.custom import QRLogin

from app.core.exceptions import (
    AuthenticationError,
    SessionError,
    DatabaseError,
    TelegramError
)

router = APIRouter()
logger = get_logger(__name__)

# Create sessions directory if it doesn't exist
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

class DevLoginRequest(BaseModel):
    """Request model for development login"""
    telegram_id: int

class QRAuthResponse(BaseModel):
    """Response model for QR authentication"""
    session_id: str
    qr_code: str
    expires_at: str

@router.post("/qr", response_model=QRAuthResponse)
async def create_qr_auth(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new QR code authentication session"""
    try:
        # Create initial session
        session_middleware = request.app.state.session_middleware
        session = await session_middleware.create_session(db=db, is_qr=True)
        
        # Create Telegram client with session file in sessions directory
        session_file = str(SESSIONS_DIR / f'session_{session.id}')
        client = TelegramClient(
            session_file,
            api_id=int(os.getenv("TELEGRAM_API_ID")),
            api_hash=os.getenv("TELEGRAM_API_HASH")
        )
        
        # Connect and get QR login data
        try:
            await client.connect()
            qr_login = await client.qr_login()
        except Exception as e:
            raise TelegramError("Failed to connect to Telegram", details={"error": str(e)})
        
        # Generate QR code
        qr = qrcode.QRCode()
        qr.add_data(qr_login.url)
        qr_image = qr.make_image()
        
        # Convert QR image to base64
        buffered = BytesIO()
        qr_image.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Start monitoring QR login in background
        request.app.state.background_tasks.add_task(
            monitor_qr_login(
                client,
                qr_login,
                str(session.id),
                db,
                session_middleware
            )
        )
        
        return {
            "session_id": str(session.id),
            "qr_code": qr_base64,
            "expires_at": session.expires_at.isoformat()
        }
        
    except (SessionError, TelegramError):
        raise
    except Exception as e:
        logger.error(f"QR code generation failed: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to create QR authentication", details={"error": str(e)})

@router.post("/logout")
async def logout(
    request: Request,
    session: Session = Depends(verify_session_dependency)
):
    """Log out and invalidate the current session"""
    try:
        # Delete session from database
        async with request.app.state.db_pool() as db:
            stmt = delete(Session).where(Session.id == session.id)
            await db.execute(stmt)
            await db.commit()
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to logout", details={"error": str(e)})

@router.get("/session/verify")
async def verify_session_status(
    session: Session = Depends(verify_session_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Verify session status and return user data if authenticated"""
    try:
        # Get user data if authenticated
        user = None
        if session.telegram_id:
            stmt = select(User).where(User.telegram_id == session.telegram_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
        
        return {
            "status": session.status,
            "telegram_id": session.telegram_id,
            "expires_at": session.expires_at.isoformat(),
            "user": user.to_dict() if user else None
        }
        
    except Exception as e:
        logger.error(f"Session verification failed: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to verify session status", details={"error": str(e)})

async def monitor_qr_login(
    client: TelegramClient,
    qr_login: QRLogin,
    session_id: str,
    db: AsyncSession,
    session_middleware: SessionMiddleware
):
    """Monitor QR login process in the background"""
    try:
        # Wait for QR login completion
        try:
            sign_in_result = await qr_login.wait()
            user = await client.get_me()
        except Exception as e:
            raise TelegramError("QR login failed", details={"error": str(e)})
            
        # Get or create user
        stmt = select(User).where(User.telegram_id == user.id)
        result = await db.execute(stmt)
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            db.add(db_user)
            
        # Update session with user
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise SessionError(f"Session {session_id} not found")
            
        session.telegram_id = user.id
        session.status = SessionStatus.AUTHENTICATED
        await db.commit()
        
    except (SessionError, TelegramError):
        raise
    except Exception as e:
        logger.error(f"Error in QR login monitoring: {str(e)}", exc_info=True)
        # Mark session as error
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            session.status = SessionStatus.ERROR
            await db.commit()
    finally:
        # Clean up client
        await client.disconnect()
        # Remove session file
        session_file = SESSIONS_DIR / f'session_{session_id}'
        if session_file.exists():
            session_file.unlink()

@router.post("/dev-login")
async def dev_login(
    request: Request,
    login_data: DevLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Development-only endpoint for quick login"""
    if os.getenv("ENVIRONMENT") != "development":
        raise AuthenticationError("This endpoint is only available in development mode")
        
    try:
        # Check if user exists, create if not
        stmt = select(User).where(User.telegram_id == login_data.telegram_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=login_data.telegram_id,
                username=f"test_user_{login_data.telegram_id}",
                first_name="Test",
                last_name="User"
            )
            db.add(user)
            await db.commit()
            logger.info(f"Created test user with telegram_id {login_data.telegram_id}")
        
        session_middleware = request.app.state.session_middleware
        session = await session_middleware.create_session(db=db, telegram_id=login_data.telegram_id)
        
        return {
            "session_id": str(session.id),
            "token": session.token,
            "expires_at": session.expires_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Dev login failed: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to create development login", details={"error": str(e)}) 