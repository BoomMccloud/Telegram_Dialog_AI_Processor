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

from ..dependencies.auth import get_session_manager, get_current_session, get_refresh_session
from ..utils.logging import get_logger
from ..db.database import get_db
from ..models.session import Session, SessionStatus
from ..models.user import User
from ..services.session_manager import SessionManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter(prefix="/api/auth")
logger = get_logger(__name__)

# Create sessions directory if it doesn't exist
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

class DevLoginRequest(BaseModel):
    """Request model for development login"""
    telegram_id: int

class TokenResponse(BaseModel):
    """Response model for token endpoints"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class QRAuthResponse(BaseModel):
    """Response model for QR authentication"""
    session_id: str
    qr_code: str
    expires_in: int

@router.post("/qr", response_model=QRAuthResponse)
async def create_qr_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_manager = Depends(get_session_manager)
):
    """Create a new QR code authentication session"""
    try:
        # Create initial session
        session = await session_manager.create_session(
            db=db,
            device_info={"user_agent": request.headers.get("user-agent")}
        )
        
        # Create Telegram client with session file in sessions directory
        session_file = str(SESSIONS_DIR / f'session_{session.id}')
        client = TelegramClient(
            session_file,
            api_id=int(os.getenv("TELEGRAM_API_ID")),
            api_hash=os.getenv("TELEGRAM_API_HASH")
        )
        
        # Connect and get QR login data
        await client.connect()
        qr_login = await client.qr_login()
        
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
                session_manager
            )
        )
        
        return {
            "session_id": str(session.id),
            "qr_code": qr_base64,
            "expires_in": session_manager.access_token_expire * 60  # Convert to seconds
        }
        
    except Exception as e:
        logger.error(f"QR code generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(get_refresh_session)
):
    """Create new access token using refresh token"""
    try:
        session_manager = get_session_manager()
        new_session = await session_manager.refresh_session(db, session.refresh_token)
        
        return {
            "access_token": new_session.token,
            "refresh_token": new_session.refresh_token,
            "token_type": "bearer",
            "expires_in": session_manager.access_token_expire * 60  # Convert to seconds
        }
        
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/logout")
async def logout(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(get_current_session)
):
    """Log out and invalidate the current session"""
    try:
        session_manager = get_session_manager()
        await session_manager.invalidate_session(db, session.token)
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/session/verify")
async def verify_session_status(
    session: Session = Depends(get_current_session),
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def monitor_qr_login(
    client: TelegramClient,
    qr_login: Any,
    session_id: str,
    db: AsyncSession,
    session_manager: SessionManager
):
    """Monitor QR login process in the background"""
    try:
        logger.info(f"Waiting for QR login result for session {session_id}")
        # Wait for the login result
        login_result = await qr_login.wait()
        if login_result:
            # Get user info
            me = await client.get_me()
            telegram_id = me.id
            
            # Find session
            stmt = select(Session).where(Session.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if session:
                # Update session with user info
                session.telegram_id = telegram_id
                session.status = SessionStatus.AUTHENTICATED
                session.session_metadata.update({
                    "telegram_id": telegram_id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "last_name": me.last_name
                })
                
                # Create or update user
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    user = User(
                        telegram_id=telegram_id,
                        username=me.username,
                        first_name=me.first_name,
                        last_name=me.last_name
                    )
                    db.add(user)
                
                await db.commit()
                logger.info(f"Session {session_id} authenticated for user {telegram_id}")
            
        else:
            logger.warning(f"QR login failed for session {session_id}")
            # Mark session as error
            stmt = select(Session).where(Session.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if session:
                session.status = SessionStatus.ERROR
                await db.commit()
                
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
        if client:
            await client.disconnect()

# Development-only routes
if os.getenv("APP_ENV") == "development":
    @router.post("/dev-login", response_model=TokenResponse)
    async def dev_login(
        request: Request,
        login_data: DevLoginRequest,
        db: AsyncSession = Depends(get_db),
        session_manager = Depends(get_session_manager)
    ):
        """Development-only endpoint to create an authenticated session"""
        try:
            # Check if user exists, create if not
            stmt = select(User).where(User.telegram_id == login_data.telegram_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    telegram_id=login_data.telegram_id,
                    username=f"dev_user_{login_data.telegram_id}",
                    first_name="Dev",
                    last_name="User"
                )
                db.add(user)
                await db.commit()
                logger.info(f"Created development user with telegram_id={login_data.telegram_id}")
            
            # Create authenticated session
            session = await session_manager.create_session(
                db=db,
                telegram_id=login_data.telegram_id,
                device_info={"user_agent": request.headers.get("user-agent")}
            )
            
            return {
                "access_token": session.token,
                "refresh_token": session.refresh_token,
                "token_type": "bearer",
                "expires_in": session_manager.access_token_expire * 60  # Convert to seconds
            }
            
        except Exception as e:
            logger.error(f"Development login failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            ) 