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
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from telethon.client import TelegramClient
from telethon.tl.custom import QRLogin
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
import jwt
import uuid

from ..utils.logging import get_logger
from ..db.database import get_db
from ..db.models.session import Session, SessionStatus
from ..db.models.user import User
from ..middleware.session import SessionMiddleware, verify_session_dependency, security
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

# Add these models for phone auth
class PhoneAuthRequest(BaseModel):
    """Request model for phone number authentication"""
    phone_number: str

class PhoneCodeAuthRequest(BaseModel):
    """Request model for phone code verification"""
    phone_number: str
    code: str
    session_id: str

class PhoneAuthResponse(BaseModel):
    """Response model for phone number authentication"""
    session_id: str
    expires_at: str
    phone_code_hash: Optional[str] = None

class SessionVerifyResponse(BaseModel):
    """Response model for session verification"""
    status: str
    telegram_id: Optional[int] = None
    expires_at: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

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
        logger.info(f"Starting background task to monitor QR login for session {session.id}")
        
        # Create a coroutine that will be executed by add_task
        # We need to create an actual coroutine object, not call it immediately
        coro = monitor_qr_login(
            client,
            qr_login,
            str(session.id),
            db,
            session_middleware
        )
        
        request.app.state.background_tasks.add_task(coro)
        logger.info(f"Background task added successfully for session {session.id}")
        
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
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Verify session status and return user data if authenticated"""
    try:
        # If no credentials provided, return an unauthenticated response without error
        if not credentials:
            return {
                "status": "UNAUTHENTICATED",
                "telegram_id": None,
                "expires_at": None,
                "user": None,
                "access_token": None,
                "refresh_token": None
            }
            
        # Try to verify the session
        session_middleware = request.app.state.session_middleware
        try:
            session = await session_middleware.verify_session(credentials.credentials, db)
        except (AuthenticationError, SessionError):
            # If session verification fails, return unauthenticated status without error
            return {
                "status": "UNAUTHENTICATED",
                "telegram_id": None,
                "expires_at": None,
                "user": None,
                "access_token": None,
                "refresh_token": None
            }
            
        # Get user data if authenticated
        user = None
        if session.status == SessionStatus.AUTHENTICATED and session.user_id:
            stmt = select(User).where(User.id == session.user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            # If authenticated, also generate new access token
            if user:
                # Generate new JWT token for this session
                access_token = session.token
                
                # For authenticated users, also return a refresh token
                refresh_token = None
                if not session.refresh_token:
                    # Generate a refresh token if one doesn't exist
                    refresh_token_data = {
                        "jti": str(uuid.uuid4()),
                        "exp": datetime.utcnow() + timedelta(days=30),  # 30 day refresh token
                        "type": "refresh"
                    }
                    refresh_token = jwt.encode(refresh_token_data, session_middleware.jwt_secret, algorithm="HS256")
                    
                    # Save refresh token to session
                    session.refresh_token = refresh_token
                    await db.commit()
                else:
                    refresh_token = session.refresh_token
                
                return {
                    "status": session.status,
                    "telegram_id": user.telegram_id if user else None,
                    "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                    "user": user.to_dict() if user else None,
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }
        
        # Default response for non-authenticated sessions
        return {
            "status": session.status,
            "telegram_id": user.telegram_id if user else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "user": user.to_dict() if user else None,
            "access_token": None,
            "refresh_token": None
        }
        
    except Exception as e:
        # Log internal errors but don't expose them to the client
        logger.error(f"Session verification failed: {str(e)}", exc_info=True)
        # Return a generic response for other unexpected errors
        return {
            "status": "ERROR",
            "telegram_id": None,
            "expires_at": None,
            "user": None,
            "access_token": None,
            "refresh_token": None
        }

async def monitor_qr_login(
    client: TelegramClient,
    qr_login: QRLogin,
    session_id: str,
    db: AsyncSession,
    session_middleware: SessionMiddleware
):
    """Monitor QR login process in the background"""
    logger.info(f"QR login monitor started for session {session_id}")
    try:
        # Wait for QR login completion
        try:
            logger.info(f"Waiting for QR code to be scanned for session {session_id}")
            sign_in_result = await qr_login.wait()
            logger.info(f"QR code scanned successfully for session {session_id}")
            user = await client.get_me()
            logger.info(f"Retrieved Telegram user: {user.id} ({user.username}) for session {session_id}")
        except Exception as e:
            logger.error(f"QR login failed for session {session_id}: {str(e)}", exc_info=True)
            raise TelegramError("QR login failed", details={"error": str(e)})
            
        # Get session
        logger.info(f"Retrieving session {session_id} from database")
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            logger.error(f"Session {session_id} not found")
            raise SessionError(f"Session {session_id} not found")
            
        # Get or create permanent user
        logger.info(f"Looking for existing user with Telegram ID {user.id}")
        stmt = select(User).where(User.telegram_id == user.id)
        result = await db.execute(stmt)
        permanent_user = result.scalar_one_or_none()
        
        if not permanent_user:
            logger.info(f"Creating new user for Telegram ID {user.id}")
            permanent_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            db.add(permanent_user)
            await db.commit()
            await db.refresh(permanent_user)
            logger.info(f"New user created with ID {permanent_user.id} for Telegram ID {user.id}")
            
        # Get temporary user to delete
        logger.info(f"Looking for temporary user with ID {session.user_id}")
        stmt = select(User).where(User.id == session.user_id)
        result = await db.execute(stmt)
        temp_user = result.scalar_one_or_none()
        
        # Update session with permanent user
        logger.info(f"Updating session {session_id} to authenticated status")
        session.user_id = permanent_user.id
        session.status = SessionStatus.AUTHENTICATED
        session.expires_at = datetime.utcnow() + timedelta(days=7)
        
        # Delete temporary user if it exists and has no other sessions
        if temp_user and temp_user.telegram_id is None:
            # Check if temporary user has other active sessions
            logger.info(f"Checking if temporary user {temp_user.id} has other sessions")
            stmt = select(Session).where(
                Session.user_id == temp_user.id,
                Session.id != session_id
            )
            result = await db.execute(stmt)
            other_sessions = result.scalar_one_or_none()
            
            if not other_sessions:
                logger.info(f"Deleting temporary user {temp_user.id} with no other sessions")
                await db.delete(temp_user)
        
        await db.commit()
        logger.info(f"QR login completed successfully for session {session_id}")
        
    except (SessionError, TelegramError) as e:
        logger.error(f"Error in QR login process for session {session_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in QR login monitoring for session {session_id}: {str(e)}", exc_info=True)
        # Mark session as error
        try:
            stmt = select(Session).where(Session.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if session:
                logger.info(f"Marking session {session_id} as ERROR due to exception")
                session.status = SessionStatus.ERROR
                await db.commit()
        except Exception as inner_e:
            logger.error(f"Failed to mark session {session_id} as error: {str(inner_e)}", exc_info=True)
    finally:
        # Clean up client
        try:
            logger.info(f"Disconnecting Telegram client for session {session_id}")
            await client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting Telegram client for session {session_id}: {str(e)}")
            
        # Remove session file
        try:
            session_file = SESSIONS_DIR / f'session_{session_id}'
            if session_file.exists():
                logger.info(f"Removing session file for {session_id}")
                session_file.unlink()
        except Exception as e:
            logger.error(f"Error removing session file for session {session_id}: {str(e)}")

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
        
        # Create authenticated session with the user
        session_middleware = request.app.state.session_middleware
        session = await session_middleware.create_session(
            db=db, 
            telegram_id=login_data.telegram_id
        )
        
        # Ensure the session is in authenticated state and associated with the user
        session.status = SessionStatus.AUTHENTICATED
        session.user_id = user.id
        await db.commit()
        
        return {
            "session_id": str(session.id),
            "token": session.token,
            "expires_at": session.expires_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Dev login failed: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to create development login", details={"error": str(e)})

@router.post("/phone", response_model=PhoneAuthResponse)
async def phone_auth(
    request: Request,
    auth_data: PhoneAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start phone number authentication by sending code"""
    try:
        # Create initial session
        session_middleware = request.app.state.session_middleware
        session = await session_middleware.create_session(db=db)
        
        # Create Telegram client with session file in sessions directory
        session_file = str(SESSIONS_DIR / f'session_{session.id}')
        client = TelegramClient(
            session_file,
            api_id=int(os.getenv("TELEGRAM_API_ID")),
            api_hash=os.getenv("TELEGRAM_API_HASH")
        )
        
        # Connect and send verification code
        try:
            await client.connect()
            # Send code to phone
            result = await client.send_code_request(auth_data.phone_number)
            phone_code_hash = result.phone_code_hash
            
            # Store in session metadata
            session.session_metadata = {
                "phone_number": auth_data.phone_number,
                "phone_code_hash": phone_code_hash
            }
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to send code: {str(e)}", exc_info=True)
            raise TelegramError("Failed to send verification code", details={"error": str(e)})
        finally:
            await client.disconnect()
            
        return {
            "session_id": str(session.id),
            "expires_at": session.expires_at.isoformat(),
            "phone_code_hash": phone_code_hash
        }
        
    except (SessionError, TelegramError):
        raise
    except Exception as e:
        logger.error(f"Phone authentication failed: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to initiate phone authentication", details={"error": str(e)})

@router.post("/phone/verify", response_model=SessionVerifyResponse)
async def verify_phone_code(
    request: Request,
    verify_data: PhoneCodeAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify phone code and complete authentication"""
    try:
        # Get session by ID
        stmt = select(Session).where(Session.id == verify_data.session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise SessionError(f"Session {verify_data.session_id} not found")
            
        # Create Telegram client with session file
        session_file = str(SESSIONS_DIR / f'session_{session.id}')
        client = TelegramClient(
            session_file,
            api_id=int(os.getenv("TELEGRAM_API_ID")),
            api_hash=os.getenv("TELEGRAM_API_HASH")
        )
        
        try:
            await client.connect()
            
            # Sign in with code
            try:
                phone_code_hash = session.session_metadata.get("phone_code_hash")
                if not phone_code_hash:
                    raise SessionError("Phone code hash not found in session")
                    
                await client.sign_in(
                    phone=verify_data.phone_number,
                    code=verify_data.code,
                    phone_code_hash=phone_code_hash
                )
                user = await client.get_me()
                logger.info(f"User logged in via phone: {user.id} ({user.username})")
            except Exception as e:
                logger.error(f"Phone code verification failed: {str(e)}", exc_info=True)
                raise TelegramError("Failed to verify phone code", details={"error": str(e)})
                
            # Get or create permanent user
            stmt = select(User).where(User.telegram_id == user.id)
            result = await db.execute(stmt)
            permanent_user = result.scalar_one_or_none()
            
            if not permanent_user:
                permanent_user = User(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                db.add(permanent_user)
                await db.commit()
                await db.refresh(permanent_user)
                
            # Update session
            session.user_id = permanent_user.id
            session.status = SessionStatus.AUTHENTICATED
            session.expires_at = datetime.utcnow() + timedelta(days=7)
            
            # Generate access token and refresh token
            session_middleware = request.app.state.session_middleware
            access_token_data = {
                "jti": str(uuid.uuid4()),
                "exp": datetime.utcnow() + timedelta(hours=24)
            }
            access_token = jwt.encode(access_token_data, session_middleware.jwt_secret, algorithm="HS256")
            
            refresh_token_data = {
                "jti": str(uuid.uuid4()),
                "exp": datetime.utcnow() + timedelta(days=30),
                "type": "refresh"
            }
            refresh_token = jwt.encode(refresh_token_data, session_middleware.jwt_secret, algorithm="HS256")
            
            # Update session with new tokens
            session.token = access_token
            session.refresh_token = refresh_token
            
            await db.commit()
            
            # Return session details
            return {
                "status": session.status,
                "telegram_id": permanent_user.telegram_id,
                "expires_at": session.expires_at.isoformat(),
                "user": permanent_user.to_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        finally:
            await client.disconnect()
            
    except (SessionError, TelegramError):
        raise
    except Exception as e:
        logger.error(f"Phone code verification failed: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to verify phone code", details={"error": str(e)}) 