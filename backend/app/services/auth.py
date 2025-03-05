"""
Authentication service module for Telegram integration
"""

import qrcode
from io import BytesIO
import base64
import uuid
import os
import json
from telethon import TelegramClient
from datetime import datetime, timedelta
from typing import Optional, Dict
import asyncio
import logging
from fastapi import Request
from telethon.tl.custom import QRLogin
import io

# Configure logging
logger = logging.getLogger(__name__)

# Global storage for client sessions
client_sessions: Dict[str, Dict] = {}

async def create_telegram_client() -> tuple[TelegramClient, str]:
    """Create a new Telegram client instance"""
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables are required")
    
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # Create a new client instance
    client = TelegramClient(f'sessions/{session_id}', int(api_id), api_hash)
    
    # Connect to Telegram
    await client.connect()
    
    return client, session_id

async def create_auth_session() -> Dict:
    """Create a new QR code authentication session"""
    try:
        # Get session middleware from app state
        from ..main import app
        session_middleware = app.state.session_middleware
        
        # Create initial session in database
        async with app.state.db_pool() as db:
            session = await session_middleware.create_session(db=db, is_qr=True)
            token = session.token
        
        # Create Telegram client
        client = TelegramClient(
            'anon',
            api_id=int(os.getenv("TELEGRAM_API_ID")),
            api_hash=os.getenv("TELEGRAM_API_HASH")
        )
        
        # Connect and get QR login data
        await client.connect()
        qr_login = await client.qr_login()
        
        # Store client and QR login objects in memory
        client_sessions[token] = {
            "client": client,
            "qr_login": qr_login,
            "token": token,
            "status": "pending"
        }
        
        # Generate QR code
        qr = qrcode.QRCode()
        qr.add_data(qr_login.url)
        qr_image = qr.make_image()
        
        # Convert QR image to base64
        buffered = io.BytesIO()
        qr_image.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "token": token,
            "qr_code": qr_base64,
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Error creating auth session: {str(e)}", exc_info=True)
        raise

async def monitor_login(client, qr_login, token: str):
    """Monitor QR login process in the background"""
    try:
        logger.info(f"Waiting for QR login result for session {token}")
        # Wait for the login result
        login_result = await qr_login.wait()
        if login_result:
            # Get user info
            me = await client.get_me()
            telegram_id = me.id
            
            # Get session middleware from app state
            from ..main import app
            session_middleware = app.state.session_middleware
            
            # Update session in database
            async with app.state.db_pool() as db:
                await session_middleware.update_session(token, telegram_id, db)
                
            logger.info(f"Session {token} authenticated for user {telegram_id}")
        else:
            logger.warning(f"QR login failed for session {token}")
            # Mark session as error in database
            async with app.state.db_pool() as db:
                session = await session_middleware.verify_session(token, db)
                session.status = "error"
                await db.commit()
                
    except Exception as e:
        logger.error(f"Error monitoring login: {str(e)}", exc_info=True)
        raise

async def get_session_status(token: str) -> Optional[Dict]:
    """Get current status of an authentication session"""
    try:
        # Get session middleware from app state
        from ..main import app
        session_middleware = app.state.session_middleware
        
        # Get session from database
        async with app.state.db_pool() as db:
            session = await session_middleware.verify_session(token, db)
            
            return {
                "token": session.token,
                "status": session.status,
                "telegram_id": session.telegram_id
            }
            
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        return None

async def cleanup_sessions():
    """Clean up expired sessions"""
    try:
        # Get session middleware from app state
        from ..main import app
        session_middleware = app.state.session_middleware
        
        # Clean up expired sessions in database
        async with app.state.db_pool() as db:
            await session_middleware.cleanup_expired_sessions(db)
            
        # Clean up client sessions
        expired_tokens = []
        for token, session in client_sessions.items():
            try:
                async with app.state.db_pool() as db:
                    await session_middleware.verify_session(token, db)
            except:
                expired_tokens.append(token)
                
        for token in expired_tokens:
            if token in client_sessions:
                session = client_sessions[token]
                if "client" in session:
                    await session["client"].disconnect()
                del client_sessions[token]
                
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {str(e)}")

async def periodic_cleanup():
    """Run session cleanup periodically"""
    while True:
        await cleanup_sessions()
        await asyncio.sleep(300)  # Run every 5 minutes 