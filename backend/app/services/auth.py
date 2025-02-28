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

# Store client sessions temporarily (in memory)
client_sessions: Dict[str, dict] = {}

# Path to store sessions persistently
SESSIONS_DIR = "sessions/data"
os.makedirs(SESSIONS_DIR, exist_ok=True)

def save_session_to_file(session_id: str, session_data: dict):
    """Save session data to file for persistence"""
    # Create a serializable copy
    serializable_data = {**session_data}
    
    # Remove non-serializable objects
    if "client" in serializable_data:
        serializable_data["client"] = None
    if "qr_login" in serializable_data:
        serializable_data["qr_login"] = None
    
    # Convert dates to ISO format
    if "created_at" in serializable_data:
        serializable_data["created_at"] = serializable_data["created_at"].isoformat()
    if "expires_at" in serializable_data:
        serializable_data["expires_at"] = serializable_data["expires_at"].isoformat()
    
    # Write to file with locking for thread safety
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    with open(file_path, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(serializable_data, f)
        fcntl.flock(f, fcntl.LOCK_UN)
    
    print(f"Session {session_id} saved to file")

def load_session_from_file(session_id: str) -> Optional[Dict]:
    """Load session data from file"""
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    
    if not os.path.exists(file_path):
        return None
        
    try:
        with open(file_path, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
            
        # Convert ISO dates back to datetime
        if "created_at" in data:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "expires_at" in data:
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
            
        return data
    except Exception as e:
        print(f"Error loading session {session_id}: {str(e)}")
        return None

def delete_session_file(session_id: str):
    """Delete session file"""
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Session file for {session_id} deleted")

# Add a new function to synchronize in-memory and file storage
def get_or_load_session(session_id: str) -> Optional[Dict]:
    """
    Get session from memory or load from file if not in memory
    This function should be called at the beginning of any function
    that needs to access a session
    """
    # First check in-memory sessions
    if session_id in client_sessions:
        return client_sessions[session_id]
    
    # If not in memory, try to load from file
    session_data = load_session_from_file(session_id)
    if session_data:
        # We need to recreate client object
        if session_data.get("status") == "authenticated":
            # For authenticated sessions, create a real client
            api_id = os.getenv("TELEGRAM_API_ID")
            api_hash = os.getenv("TELEGRAM_API_HASH")
            
            if api_id and api_hash:
                # Create the client but don't connect it yet
                # We'll connect on first use
                client = TelegramClient(f'sessions/{session_id}', int(api_id), api_hash)
                session_data["client"] = client
                
                # Store in memory
                client_sessions[session_id] = session_data
                print(f"Loaded session {session_id} from file to memory")
                return session_data
        else:
            # For non-authenticated sessions, we need a new client
            client_sessions[session_id] = session_data
            return session_data
    
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
        save_session_to_file(session_id, session_data)
        
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
                        print(f"Session {session_id} authenticated for user {me.id} and saved")  # Debug log
            except Exception as e:
                print(f"Error in QR login monitoring for session {session_id}: {str(e)}")  # Debug log
        
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