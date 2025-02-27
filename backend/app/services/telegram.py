from telethon import TelegramClient
from typing import List, Dict
import os
from datetime import datetime, timedelta
from .auth import client_sessions

async def get_recent_messages(session_id: str, limit: int = 20) -> List[Dict]:
    """Get recent messages from all dialogs"""
    session = client_sessions.get(session_id)
    if not session or not session.get("client"):
        raise ValueError("Invalid or expired session")
    
    client = session["client"]
    if not await client.is_user_authorized():
        raise ValueError("Client is not authorized")

    messages = []
    async for dialog in client.iter_dialogs():
        # Get messages from the last 24 hours
        since = datetime.now() - timedelta(days=1)
        
        async for message in client.iter_messages(dialog, limit=limit):
            if message.date < since:
                break
                
            messages.append({
                "dialog_id": dialog.id,
                "dialog_name": dialog.name,
                "message_id": message.id,
                "date": message.date.isoformat(),
                "sender": message.sender_id,
                "text": message.text,
                "is_unread": message.is_unread
            })
    
    # Sort messages by date, newest first
    messages.sort(key=lambda x: x["date"], reverse=True)
    return messages[:limit]

async def send_message(session_id: str, dialog_id: int, text: str) -> Dict:
    """Send a message to a specific dialog"""
    session = client_sessions.get(session_id)
    if not session or not session.get("client"):
        raise ValueError("Invalid or expired session")
    
    client = session["client"]
    if not await client.is_user_authorized():
        raise ValueError("Client is not authorized")

    message = await client.send_message(dialog_id, text)
    return {
        "dialog_id": dialog_id,
        "message_id": message.id,
        "date": message.date.isoformat(),
        "text": message.text,
        "sent": True
    } 