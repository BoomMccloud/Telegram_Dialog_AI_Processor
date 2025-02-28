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

# Configure logging
logger = logging.getLogger(__name__)

# Store client sessions temporarily (in memory)
client_sessions: Dict[str, dict] = {}

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
def get_or_load_session(session_id: str) -> Optional[Dict]:
    """
    Get session from memory or load from file if not in memory
    This function should be called at the beginning of any function
    that needs to access a session
    """
    # First check in-memory sessions
    if session_id in client_sessions:
        logger.debug(f"Session {session_id} found in memory")
        # Check if session is expired
        if datetime.utcnow() > client_sessions[session_id]["expires_at"]:
            logger.info(f"Session {session_id} has expired (in-memory)")
            client_sessions.pop(session_id, None)
            delete_session_file(session_id)
            return None
        return client_sessions[session_id]
    
    # If not in memory, try to load from file
    logger.info(f"Session {session_id} not in memory, trying to load from file")
    session_data = load_session_from_file(session_id)
    
    if session_data:
        # Check if session is expired
        if "expires_at" in session_data:
            if datetime.utcnow() > session_data["expires_at"]:
                logger.info(f"Session {session_id} has expired (from file)")
                delete_session_file(session_id)
                return None
                
        # We need to recreate client object
        if session_data.get("status") == "authenticated":
            # For authenticated sessions, create a real client
            api_id = os.getenv("TELEGRAM_API_ID")
            api_hash = os.getenv("TELEGRAM_API_HASH")
            
            if api_id and api_hash:
                try:
                    # Create the client but don't connect it yet
                    # We'll connect on first use
                    client = TelegramClient(f'sessions/{session_id}', int(api_id), api_hash)
                    session_data["client"] = client
                    
                    # Extend session expiration to ensure it doesn't immediately expire
                    # This helps with development and testing
                    if "expires_at" in session_data:
                        # Extend by 24 hours from now if close to expiring
                        time_left = session_data["expires_at"] - datetime.utcnow()
                        if time_left.total_seconds() < 3600:  # Less than 1 hour left
                            session_data["expires_at"] = datetime.utcnow() + timedelta(hours=24)
                            logger.info(f"Extended expiration for session {session_id}")
                            # Save updated expiration
                            save_session_to_file(session_id, session_data)
                    
                    # Store in memory
                    client_sessions[session_id] = session_data
                    logger.info(f"Loaded session {session_id} from file to memory")
                    return session_data
                except Exception as e:
                    logger.error(f"Error recreating client for session {session_id}: {str(e)}")
                    return None
            else:
                logger.error(f"Missing API credentials for session {session_id}")
                return None
        else:
            # For non-authenticated sessions, we can just load the data
            client_sessions[session_id] = session_data
            logger.info(f"Loaded non-authenticated session {session_id}")
            return session_data
    
    logger.warning(f"Session {session_id} not found in memory or file")
    return None

async def create_telegram_client() -> TelegramClient:
    """Create and connect to Telegram client"""
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        raise ValueError("Telegram API credentials not found in environment variables")
    
    # Create sessions directory if it doesn't exist
    os.makedirs('sessions', exist_ok=True)
    
    # Create a new session for this authentication attempt
    session_id = str(uuid.uuid4())
    client = TelegramClient(f'sessions/{session_id}', int(api_id), api_hash)
    
    try:
        print(f"Connecting client for session {session_id}")  # Debug log
        await client.connect()
        print(f"Client connected for session {session_id}")  # Debug log
    except Exception as e:
        print(f"Error connecting client for session {session_id}: {str(e)}")  # Debug log
        raise
    
    return client, session_id

async def create_auth_session() -> dict:
    """Create a new authentication session using Telethon's QR login"""
    client, session_id = await create_telegram_client()
    
    try:
        # Get the QR code login data from Telethon
        qr_login = await client.qr_login()
        print(f"Created QR login for session {session_id}")  # Debug log
        
        # Store session info with a longer timeout (5 minutes)
        session_data = {
            "client": client,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=5),
            "status": "pending",
            "user_id": None,
            "qr_login": qr_login
        }
        
        # Store in memory
        client_sessions[session_id] = session_data
        
        # Save to persistent storage
        print(f"Saving initial session {session_id} to file")  # Debug log
        save_session_to_file(session_id, session_data)
        
        # Verify the session was saved to file correctly
        file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if os.path.exists(file_path):
            print(f"Initial session file created successfully: {file_path}")
        else:
            print(f"WARNING: Initial session file creation failed: {file_path}")
        
        # Generate QR code from the login URL
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_login.url)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_code = base64.b64encode(buffered.getvalue()).decode()
        
        # Start monitoring the QR login in the background
        async def monitor_login():
            try:
                print(f"Waiting for QR login result for session {session_id}")  # Debug log
                # Wait for the login result
                login_result = await qr_login.wait()
                if login_result:
                    print(f"QR login successful for session {session_id}")  # Debug log
                    # Update session status
                    session = client_sessions.get(session_id)
                    if session:
                        me = await client.get_me()
                        session["user_id"] = me.id
                        session["status"] = "authenticated"
                        session["expires_at"] = datetime.utcnow() + timedelta(hours=24)
                        # Save the session to disk
                        await client.session.save()
                        # Save updated session to file
                        save_session_to_file(session_id, session)
                        print(f"Session {session_id} authenticated for user {me.id} and saved to file")  # More detailed debug
                        # Double check the file exists
                        file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
                        if os.path.exists(file_path):
                            print(f"Confirmed session file exists: {file_path}")
                        else:
                            print(f"WARNING: Session file still doesn't exist after save: {file_path}")
            except Exception as e:
                print(f"ERROR in QR login monitoring for session {session_id}: {str(e)}")  # More visible error
                logger.error(f"Error in QR login monitoring for session {session_id}: {str(e)}")
        
        # Start the monitoring task
        asyncio.create_task(monitor_login())
        
        return {
            "session_id": session_id,
            "qr_code": f"data:image/png;base64,{qr_code}",
            "expires_at": client_sessions[session_id]["expires_at"].isoformat()
        }
    except Exception as e:
        await client.disconnect()
        raise Exception(f"Failed to create QR login: {str(e)}")

async def get_session_status(session_id: str) -> Optional[dict]:
    """Get the status of an authentication session"""
    # Try to get or load session
    session = get_or_load_session(session_id)
    if not session:
        print(f"Session {session_id} not found in memory or file")  # Debug log
        return None
    
    client = session.get("client")
    
    # Check if session has expired
    if datetime.utcnow() > session["expires_at"]:
        print(f"Session {session_id} has expired")  # Debug log
        if client:
            await client.disconnect()
        client_sessions.pop(session_id, None)
        delete_session_file(session_id)
        return {"status": "expired", "message": "Session has expired. Please request a new QR code."}
    
    # Check if client is still connected
    if client and not client.is_connected():
        print(f"Reconnecting client for session {session_id}")  # Debug log
        try:
            await client.connect()
            print(f"Client reconnected for session {session_id}")  # Debug log
        except Exception as e:
            print(f"Error reconnecting client for session {session_id}: {str(e)}")  # Debug log
            return {"status": "error", "message": "Failed to reconnect client"}
    
    # Return current session status
    print(f"Returning status for session {session_id}: {session['status']}")  # Debug log
    return {
        "status": session["status"],
        "user_id": session["user_id"],
        "expires_at": session["expires_at"].isoformat()
    }

async def cleanup_sessions():
    """Clean up expired sessions"""
    now = datetime.utcnow()
    
    # First clean up in-memory sessions
    expired = [sid for sid, session in client_sessions.items() 
              if now > session["expires_at"]]
    
    for session_id in expired:
        print(f"Cleaning up expired session {session_id}")  # Debug log
        session = client_sessions[session_id]
        if session.get("client"):
            await session["client"].disconnect()
        client_sessions.pop(session_id, None)
        delete_session_file(session_id)
        
    # Also clean up file-based sessions
    for filename in os.listdir(SESSIONS_DIR):
        if not filename.endswith('.json'):
            continue
            
        session_id = filename[:-5]  # Remove .json
        
        # Skip if already cleaned up in memory
        if session_id in expired:
            continue
            
        # Load and check expiration
        session_data = load_session_from_file(session_id)
        if session_data and now > session_data["expires_at"]:
            print(f"Cleaning up expired session file {session_id}")
            delete_session_file(session_id)

async def periodic_cleanup():
    """
    Perform periodic cleanup of stale sessions.
    This function also cleans up pending QR login sessions that are 
    older than 10 minutes to avoid errors from monitoring tasks.
    
    This should be scheduled to run at regular intervals.
    """
    now = datetime.utcnow()
    logger.info("Running periodic session cleanup...")
    
    # Track counts for logging
    expired_count = 0
    pending_count = 0
    error_count = 0
    
    # 1. Clean up in-memory sessions
    sessions_to_remove = []
    for session_id, session in client_sessions.items():
        # Check expiration
        if now > session.get("expires_at", now):
            sessions_to_remove.append(session_id)
            expired_count += 1
            continue
            
        # Check for stale pending sessions
        if session.get("status") == "pending" and session.get("created_at"):
            age = now - session["created_at"]
            if age.total_seconds() > 600:  # 10 minutes
                sessions_to_remove.append(session_id)
                pending_count += 1
                continue
        
        # Clean up sessions in error state
        if session.get("status") == "error":
            sessions_to_remove.append(session_id)
            error_count += 1
            continue
    
    # Remove flagged sessions
    for session_id in sessions_to_remove:
        try:
            session = client_sessions[session_id]
            if session.get("client"):
                await session["client"].disconnect()
            client_sessions.pop(session_id, None)
            delete_session_file(session_id)
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    # 2. Clean up file-based sessions that aren't in memory
    for filename in os.listdir(SESSIONS_DIR):
        if not filename.endswith('.json'):
            continue
            
        session_id = filename[:-5]  # Remove .json
        
        # Skip if already handled in memory
        if session_id in client_sessions or session_id in sessions_to_remove:
            continue
            
        try:
            # Load the session data
            with open(os.path.join(SESSIONS_DIR, filename), 'r') as f:
                session_data = json.load(f)
                
            # Check expiration
            if "expires_at" in session_data:
                expires_at = datetime.fromisoformat(session_data["expires_at"]) if isinstance(session_data["expires_at"], str) else session_data["expires_at"]
                if now > expires_at:
                    delete_session_file(session_id)
                    expired_count += 1
                    continue
            
            # Check for stale pending sessions
            if session_data.get("status") == "pending" and "created_at" in session_data:
                created_at = datetime.fromisoformat(session_data["created_at"]) if isinstance(session_data["created_at"], str) else session_data["created_at"]
                age = now - created_at
                if age.total_seconds() > 600:  # 10 minutes
                    delete_session_file(session_id)
                    pending_count += 1
                    continue
                
            # Check for error state
            if session_data.get("status") == "error":
                delete_session_file(session_id)
                error_count += 1
                continue
                
        except Exception as e:
            # If we can't read the file, it's corrupted - remove it
            logger.error(f"Error processing session file {filename}: {e}")
            try:
                os.remove(os.path.join(SESSIONS_DIR, filename))
                error_count += 1
            except Exception as e2:
                logger.error(f"Failed to remove corrupted session file {filename}: {e2}")
    
    total = expired_count + pending_count + error_count
    logger.info(f"Periodic cleanup complete: {total} sessions removed " 
                f"({expired_count} expired, {pending_count} stale pending, {error_count} errors)")
    return total

def load_all_sessions():
    """
    Load all valid sessions from disk into memory.
    This function should be called on server startup to ensure
    session persistence across server restarts.
    
    Returns:
        int: Number of sessions loaded
    """
    if not os.path.exists(SESSIONS_DIR):
        logger.warning(f"Sessions directory {SESSIONS_DIR} does not exist. No sessions loaded.")
        return 0
    
    loaded_count = 0
    error_count = 0
    now = datetime.utcnow()
    
    print(f"Loading sessions from {SESSIONS_DIR}...")
    
    for filename in os.listdir(SESSIONS_DIR):
        if not filename.endswith('.json'):
            continue
            
        session_id = filename[:-5]  # Remove .json extension
        file_path = os.path.join(SESSIONS_DIR, filename)
        
        try:
            # Load session data from file
            with open(file_path, 'r') as f:
                session_data = json.load(f)
            
            # Convert ISO format dates to datetime objects
            if "created_at" in session_data and isinstance(session_data["created_at"], str):
                session_data["created_at"] = datetime.fromisoformat(session_data["created_at"])
            if "expires_at" in session_data and isinstance(session_data["expires_at"], str):
                session_data["expires_at"] = datetime.fromisoformat(session_data["expires_at"])
            
            # Check if session has expired
            if session_data.get("expires_at") and now > session_data["expires_at"]:
                print(f"Skipping expired session {session_id}")
                # Optionally delete expired session files
                # os.remove(file_path)
                continue
            
            # Skip sessions that aren't authenticated 
            if session_data.get("status") != "authenticated":
                print(f"Skipping non-authenticated session {session_id}")
                continue
                
            # For authenticated sessions, create client object
            if session_data.get("status") == "authenticated":
                api_id = os.getenv("TELEGRAM_API_ID")
                api_hash = os.getenv("TELEGRAM_API_HASH")
                
                if api_id and api_hash:
                    # Create client but don't connect yet
                    client = TelegramClient(f'sessions/{session_id}', int(api_id), api_hash)
                    session_data["client"] = client
            
            # Store in memory
            client_sessions[session_id] = session_data
            loaded_count += 1
            print(f"Loaded session {session_id} into memory")
        
        except Exception as e:
            print(f"Error loading session {session_id}: {str(e)}")
            error_count += 1
    
    print(f"Session loading complete: {loaded_count} sessions loaded, {error_count} errors")
    return loaded_count 