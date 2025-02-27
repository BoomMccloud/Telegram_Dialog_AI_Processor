import qrcode
from io import BytesIO
import base64
import uuid
import os
from telethon import TelegramClient
from datetime import datetime, timedelta
from typing import Optional, Dict
import asyncio

# Store client sessions temporarily (in production, use Redis or similar)
client_sessions: Dict[str, dict] = {}

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
        client_sessions[session_id] = {
            "client": client,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=5),
            "status": "pending",
            "user_id": None,
            "qr_login": qr_login
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
    session = client_sessions.get(session_id)
    if not session:
        print(f"Session {session_id} not found")  # Debug log
        return None
    
    client = session["client"]
    
    # Check if session has expired
    if datetime.utcnow() > session["expires_at"]:
        print(f"Session {session_id} has expired")  # Debug log
        await client.disconnect()
        client_sessions.pop(session_id, None)
        return {"status": "expired", "message": "Session has expired. Please request a new QR code."}
    
    # Check if client is still connected
    if not client.is_connected():
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
    expired = [sid for sid, session in client_sessions.items() 
              if now > session["expires_at"]]
    
    for session_id in expired:
        print(f"Cleaning up expired session {session_id}")  # Debug log
        session = client_sessions[session_id]
        await session["client"].disconnect()
        client_sessions.pop(session_id, None) 