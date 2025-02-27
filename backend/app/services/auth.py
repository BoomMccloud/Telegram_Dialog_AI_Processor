import qrcode
from io import BytesIO
import base64
import uuid
import os
from telethon import TelegramClient
from datetime import datetime, timedelta
from typing import Optional, Dict

# Store client sessions temporarily (in production, use Redis or similar)
client_sessions: Dict[str, dict] = {}

async def create_telegram_client() -> TelegramClient:
    """Create and connect to Telegram client"""
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        raise ValueError("Telegram API credentials not found in environment variables")
    
    # Create a new session for this authentication attempt
    session_id = str(uuid.uuid4())
    client = TelegramClient(f'sessions/{session_id}', int(api_id), api_hash)
    await client.connect()
    
    return client, session_id

async def create_auth_session() -> dict:
    """Create a new authentication session using Telethon's QR login"""
    client, session_id = await create_telegram_client()
    
    try:
        # Get the QR code login data from Telethon
        qr_login = await client.qr_login()
        
        # Store session info with a shorter timeout (30 seconds)
        client_sessions[session_id] = {
            "client": client,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(seconds=30),  # Shorter timeout
            "status": "pending",
            "user_id": None,
            "qr_login": qr_login  # Store QR login object for potential refresh
        }
        
        # Generate QR code from the login URL
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_login.url)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_code = base64.b64encode(buffered.getvalue()).decode()
        
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
    session = client_sessions.get(session_id)
    if not session:
        return None
    
    client = session["client"]
    
    # Check if session has expired
    if datetime.utcnow() > session["expires_at"]:
        await client.disconnect()
        client_sessions.pop(session_id, None)
        return {"status": "expired", "message": "Session has expired. Please request a new QR code."}
    
    # Check if user is authenticated
    try:
        if await client.is_user_authorized():
            if session["status"] == "pending":
                # Get user info
                me = await client.get_me()
                session["user_id"] = me.id
                session["status"] = "authenticated"
        
        return {
            "status": session["status"],
            "user_id": session["user_id"],
            "expires_at": session["expires_at"].isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def cleanup_sessions():
    """Clean up expired sessions"""
    now = datetime.utcnow()
    expired = [sid for sid, session in client_sessions.items() 
              if now > session["expires_at"]]
    
    for session_id in expired:
        session = client_sessions[session_id]
        await session["client"].disconnect()
        client_sessions.pop(session_id, None) 