"""
Authentication service module for Telegram integration
"""

import qrcode
from io import BytesIO
import base64
import uuid
import os
import json
import fcntl
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

# Path to store sessions persistently
# Convert to absolute path to avoid any confusion
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions", "data")

print(f"DEBUG: Initializing auth service with SESSIONS_DIR={SESSIONS_DIR}")
print(f"DEBUG: Checking if directory exists: {os.path.exists(SESSIONS_DIR)}")
print(f"DEBUG: Checking if directory is writable: {os.access(SESSIONS_DIR, os.W_OK) if os.path.exists(SESSIONS_DIR) else False}")

def ensure_sessions_dir():
    """
    Ensure the sessions directory exists.
    This function creates the sessions directory if it doesn't exist.
    """
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    telethon_dir = os.path.join(os.path.dirname(SESSIONS_DIR), '')  # Parent of data dir
    os.makedirs(telethon_dir, exist_ok=True)
    
    logger.info(f"Ensured sessions directory exists: {SESSIONS_DIR}")
    logger.info(f"Ensured Telethon directory exists: {telethon_dir}")

def save_session_to_file(session_id: str, session_data: dict):
    """Save session data to file for persistence"""
    try:
        # Create a serializable copy
        serializable_data = {**session_data}
        
        # Remove non-serializable objects
        if "client" in serializable_data:
            serializable_data["client"] = None
        if "qr_login" in serializable_data:
            serializable_data["qr_login"] = None
        
        # Convert dates to ISO format
        if "created_at" in serializable_data and isinstance(serializable_data["created_at"], datetime):
            serializable_data["created_at"] = serializable_data["created_at"].isoformat()
        if "expires_at" in serializable_data and isinstance(serializable_data["expires_at"], datetime):
            serializable_data["expires_at"] = serializable_data["expires_at"].isoformat()
        
        # Ensure the sessions directory exists
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        
        # Write to file with locking for thread safety
        file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        print(f"DEBUG: Writing session {session_id} to file {file_path}")
        print(f"DEBUG: Session data: {json.dumps(serializable_data, indent=2)}")
        
        with open(file_path, 'w') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(serializable_data, f)
            fcntl.flock(f, fcntl.LOCK_UN)
        
        # Verify the file was created with additional debug info
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            file_permissions = oct(os.stat(file_path).st_mode)[-3:]
            print(f"DEBUG: Session file created: {file_path}, size: {file_size} bytes, permissions: {file_permissions}")
            
            # Double-check file content can be read back
            try:
                with open(file_path, 'r') as f:
                    content = json.load(f)
                print(f"DEBUG: Successfully verified file can be read, keys: {list(content.keys())}")
            except Exception as re:
                print(f"DEBUG: Error reading back the file just written: {str(re)}")
        else:
            print(f"WARNING: Session file not created despite no exceptions: {file_path}")
            
        logger.info(f"Session {session_id} saved to file")
    except Exception as e:
        print(f"ERROR saving session {session_id} to file: {str(e)}")
        print(f"DEBUG: SESSIONS_DIR = {SESSIONS_DIR}")
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        logger.error(f"Error saving session {session_id} to file: {str(e)}")

def load_session_from_file(session_id: str) -> Optional[Dict]:
    """Load session data from file"""
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    
    if not os.path.exists(file_path):
        logger.debug(f"Session file not found: {file_path}")
        return None
        
    try:
        with open(file_path, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
            
        # Convert ISO dates back to datetime
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "expires_at" in data and isinstance(data["expires_at"], str):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
            
        logger.debug(f"Successfully loaded session {session_id} from file")
        return data
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {str(e)}")
        return None

def delete_session_file(session_id: str):
    """Delete session file"""
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"Session file for {session_id} deleted")

# Add a new function to synchronize in-memory and file storage
def get_or_load_session(token: str) -> Optional[Dict]:
    """
    Get session data from a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Session data if valid, None if invalid
    """
    try:
        return session_middleware.verify_session(token)
    except Exception as e:
        logger.error(f"Error verifying session token: {str(e)}")
        return None

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
        
        # Create initial session token
        token = await session_middleware.create_session(is_qr=True)
        
        # Create Telegram client
        client = TelegramClient(
            'anon',
            api_id=int(os.getenv("TELEGRAM_API_ID")),
            api_hash=os.getenv("TELEGRAM_API_HASH")
        )
        
        # Connect and get QR login data
        await client.connect()
        qr_login = await client.qr_login()
        
        # Store session data
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

async def monitor_login(client, qr_login, session_id):
    """Monitor QR login process in the background"""
    try:
        logger.info(f"Waiting for QR login result for session {session_id}")
        # Wait for the login result
        login_result = await qr_login.wait()
        if login_result:
            # Get user info
            me = await client.get_me()
            telegram_id = me.id
            
            # Update session with user info
            session_data = client_sessions.get(session_id)
            if session_data:
                token = session_data["token"]
                # Update session in database
                await session_middleware.update_session(token, {
                    "telegram_id": telegram_id,
                    "status": "authenticated",
                    "metadata": {
                        "telegram_id": telegram_id,
                        "username": me.username,
                        "first_name": me.first_name,
                        "last_name": me.last_name
                    }
                })
                logger.info(f"Session {session_id} authenticated for user {telegram_id}")
        else:
            logger.warning(f"QR login failed for session {session_id}")
            # Mark session as error in database
            session_data = client_sessions.get(session_id)
            if session_data:
                token = session_data["token"]
                await session_middleware.update_session(token, {
                    "status": "error"
                })
    except Exception as e:
        logger.error(f"Error in QR login monitoring: {str(e)}")
        # Mark session as error in database
        session_data = client_sessions.get(session_id)
        if session_data:
            token = session_data["token"]
            await session_middleware.update_session(token, {
                "status": "error"
            })
    finally:
        # Clean up client session from memory
        if session_id in client_sessions:
            await client_sessions[session_id]["client"].disconnect()
            del client_sessions[session_id]

async def get_session_status(token: str) -> Optional[Dict]:
    """Get the status of an authentication session"""
    try:
        # Get session middleware from app state
        from ..main import app
        session_middleware = app.state.session_middleware
        
        # Verify session in database
        session = await session_middleware.verify_session(token)
        if not session:
            return None
            
        return {
            "status": session.status,
            "telegram_id": session.telegram_id,
            "expires_at": session.expires_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error verifying session token: {str(e)}")
        return None

async def cleanup_sessions():
    """Clean up all active sessions"""
    for session_id, session in list(client_sessions.items()):
        if "client" in session and session["client"]:
            try:
                await session["client"].disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client for session {session_id}: {str(e)}")
    
    client_sessions.clear()
    logger.info("All sessions cleaned up")

async def periodic_cleanup():
    """Periodically clean up expired sessions"""
    cleanup_count = 0
    
    # Clean up client sessions
    for session_id, session in list(client_sessions.items()):
        try:
            # Try to verify the token
            session_middleware.verify_session(session["token"])
        except Exception:
            # Token is invalid or expired, clean up the session
            if "client" in session and session["client"]:
                try:
                    await session["client"].disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting client for session {session_id}: {str(e)}")
            
            del client_sessions[session_id]
            cleanup_count += 1
    
    logger.info(f"Cleaned up {cleanup_count} expired sessions")
    return cleanup_count

def load_all_sessions():
    """
    Load all valid sessions from disk into memory.
    This function should be called on server startup to ensure
    session persistence across server restarts.
    
    Returns:
        int: Number of sessions loaded
    """
    # With JWT-based sessions, we don't need to load from disk anymore
    # But we'll keep the function for compatibility
    return 0 