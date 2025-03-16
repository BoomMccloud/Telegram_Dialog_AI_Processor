from telethon import TelegramClient
from typing import List, Dict, Optional, Tuple
import os
import logging
from datetime import datetime, timedelta
from .auth import client_sessions, load_telegram_client_from_session, find_session_file_for_user
from .mock_telegram import mock_telegram
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.user import User

# Configure logging
logger = logging.getLogger(__name__)

# Check if we're in development mode
IS_DEVELOPMENT = os.getenv("ENV", "development") == "development"
USE_MOCK = os.getenv("USE_MOCK_TELEGRAM", "false").lower() == "true"

async def get_or_reload_client(token: str, db_session=None) -> TelegramClient:
    """
    Get a client from memory or reload it from a session file
    
    Args:
        token: JWT token for the session
        db_session: Optional database session (for standalone worker)
        
    Returns:
        TelegramClient instance
        
    Raises:
        ValueError: If the client cannot be loaded
    """
    # Get client from memory
    session = client_sessions.get(token)
    if not session or not session.get("client"):
        logger.info(f"Client not found in memory for token {token}, attempting to reload")
        
        # Try to reload the client from session file
        try:
            # Get session middleware from app state
            from ..main import app
            
            # Get user's telegram_id from the database session
            async with app.state.db_pool() as db:
                # Get session from database
                session_middleware = app.state.session_middleware
                db_session = await session_middleware.verify_session(token, db)
                
                # Get user from database
                stmt = select(User).where(User.id == db_session.user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user or not user.telegram_id:
                    logger.error(f"User not found or has no telegram_id for token {token}")
                    raise ValueError("Invalid or expired session")
                
                # Find session file for this user
                session_file = await find_session_file_for_user(user.telegram_id)
                if not session_file:
                    logger.error(f"No session file found for user {user.telegram_id}")
                    raise ValueError("No Telegram session file found")
                
                # Load client from session file
                client = await load_telegram_client_from_session(session_file)
                if not client:
                    logger.error(f"Failed to load client from session file {session_file}")
                    raise ValueError("Failed to load Telegram session")
                
                # Store client in memory for future use
                client_sessions[token] = {
                    "client": client,
                    "status": "authenticated",
                    "telegram_id": user.telegram_id
                }
                
                logger.info(f"Successfully reloaded client for user {user.telegram_id} from {session_file}")
                session = client_sessions[token]
        except Exception as e:
            logger.error(f"Error reloading session: {str(e)}", exc_info=True)
            raise ValueError("Invalid or expired session")
    
    client = session["client"]
    
    # Check if client is connected
    if not client.is_connected():
        logger.info(f"Client not connected, connecting now for session {token}")
        await client.connect()
    
    if not await client.is_user_authorized():
        logger.error(f"Client is not authorized for session {token}")
        raise ValueError("Client is not authorized")
        
    return client

async def get_dialogs(token: str) -> List[Dict]:
    """Get list of dialogs (chats)"""
    # Use mock service in development mode if configured
    if IS_DEVELOPMENT and USE_MOCK:
        logger.info("Using mock telegram service for dialogs")
        return await mock_telegram.get_dialogs()
        
    logger.info(f"Getting dialogs for session {token}")
    
    # Get or reload client
    client = await get_or_reload_client(token)

    dialogs = []
    try:
        logger.info(f"Starting to fetch dialogs for session {token}")
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
        
        logger.info(f"Total dialogs found: {count} for session {token}")
    except Exception as e:
        logger.error(f"Error fetching dialogs: {str(e)}")
        raise ValueError(f"Failed to fetch dialogs: {str(e)}")
    
    return dialogs

async def get_recent_messages(token: str, limit: int = 20, dialog_id: Optional[int] = None, db_session=None) -> List[Dict]:
    """
    Get recent messages from a specific dialog or all dialogs
    
    Args:
        token: JWT token for the session
        limit: Maximum number of messages to return
        dialog_id: Optional dialog ID to filter messages
        db_session: Optional database session (for standalone worker)
        
    Returns:
        List of message dictionaries
    """
    # Use mock service in development mode if configured
    if IS_DEVELOPMENT and USE_MOCK:
        logger.info("Using mock telegram service for messages")
        return await mock_telegram.get_messages("all", limit)
    
    # Get or reload client
    client = await get_or_reload_client(token, db_session)

    messages = []
    
    if dialog_id:
        # Get messages from a specific dialog
        logger.info(f"Fetching {limit} messages from dialog {dialog_id}")
        async for message in client.iter_messages(dialog_id, limit=limit):
            sender = await message.get_sender()
            sender_name = getattr(sender, 'first_name', 'Unknown')
            if hasattr(sender, 'last_name') and sender.last_name:
                sender_name += f" {sender.last_name}"
                
            # Check if is_unread attribute exists before accessing it
            is_unread = False
            if hasattr(message, 'is_unread'):
                is_unread = message.is_unread
                
            messages.append({
                "dialog_id": dialog_id,
                "message_id": message.id,
                "date": message.date.isoformat(),
                "sender": {
                    "id": sender.id if sender else None,
                    "name": sender_name
                },
                "text": message.text or "",
                "is_outgoing": message.out,
                "is_unread": is_unread
            })
    else:
        # Get messages from all dialogs
        logger.info(f"Fetching messages from all dialogs (limit: {limit})")
        async for dialog in client.iter_dialogs():
            # Get messages from each dialog
            dialog_messages = []
            async for message in client.iter_messages(dialog, limit=limit):
                sender = await message.get_sender()
                sender_name = getattr(sender, 'first_name', 'Unknown')
                if hasattr(sender, 'last_name') and sender.last_name:
                    sender_name += f" {sender.last_name}"
                    
                # Check if is_unread attribute exists before accessing it
                is_unread = False
                if hasattr(message, 'is_unread'):
                    is_unread = message.is_unread
                    
                dialog_messages.append({
                    "dialog_id": dialog.id,
                    "dialog_name": dialog.name,
                    "message_id": message.id,
                    "date": message.date.isoformat(),
                    "sender": {
                        "id": sender.id if sender else None,
                        "name": sender_name
                    },
                    "text": message.text or "",
                    "is_outgoing": message.out,
                    "is_unread": is_unread
                })
            
            messages.extend(dialog_messages)
    
    # Sort messages by date, newest first
    messages.sort(key=lambda x: x["date"], reverse=True)
    return messages[:limit]

async def send_message(token: str, dialog_id: int, text: str) -> Dict:
    """Send a message to a specific dialog"""
    # Use mock service in development mode if configured
    if IS_DEVELOPMENT and USE_MOCK:
        logger.info("Using mock telegram service for sending message")
        return await mock_telegram.send_message(str(dialog_id), text)
    
    # Get or reload client
    client = await get_or_reload_client(token)

    message = await client.send_message(dialog_id, text)
    return {
        "dialog_id": dialog_id,
        "message_id": message.id,
        "date": message.date.isoformat(),
        "text": message.text,
        "sent": True
    } 