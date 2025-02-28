from telethon import TelegramClient
from typing import List, Dict
import os
import logging
from datetime import datetime, timedelta
from .auth import get_or_load_session

# Configure logging
logger = logging.getLogger(__name__)

async def get_dialogs(session_id: str) -> List[Dict]:
    """Get list of dialogs (chats)"""
    logger.info(f"Getting dialogs for session {session_id}")
    
    session = get_or_load_session(session_id)
    if not session or not session.get("client"):
        logger.error(f"Invalid or expired session: {session_id}")
        raise ValueError("Invalid or expired session")
    
    client = session["client"]
    
    # Check if client is connected
    if not client.is_connected():
        logger.info(f"Client not connected, connecting now for session {session_id}")
        await client.connect()
    
    if not await client.is_user_authorized():
        logger.error(f"Client is not authorized for session {session_id}")
        raise ValueError("Client is not authorized")

    dialogs = []
    try:
        logger.info(f"Starting to fetch dialogs for session {session_id}")
        count = 0
        async for dialog in client.iter_dialogs():
            count += 1
            # Determine dialog type
            dialog_type = "private"
            if dialog.is_group:
                dialog_type = "group"
            elif dialog.is_channel:
                dialog_type = "channel"
                
            dialog_info = {
                "id": dialog.id,
                "name": dialog.name or "Unknown",
                "unread_count": dialog.unread_count,
                "is_group": dialog.is_group,
                "is_channel": dialog.is_channel,
                "is_user": dialog.is_user,
                "type": dialog_type  # Add type field for frontend compatibility
            }
            dialogs.append(dialog_info)
            logger.info(f"Found dialog: {dialog_info['name']} (ID: {dialog_info['id']}, Type: {dialog_type})")
        
        logger.info(f"Total dialogs found: {count} for session {session_id}")
    except Exception as e:
        logger.error(f"Error fetching dialogs: {str(e)}")
        raise ValueError(f"Failed to fetch dialogs: {str(e)}")
    
    return dialogs

async def get_recent_messages(session_id: str, limit: int = 20) -> List[Dict]:
    """Get recent messages from all dialogs"""
    session = get_or_load_session(session_id)
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
    session = get_or_load_session(session_id)
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