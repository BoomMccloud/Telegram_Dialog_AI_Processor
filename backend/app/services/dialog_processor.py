"""
Dialog processor service for handling message fetching and processing
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dialog import Dialog
from app.db.models.message import Message
from app.services.telegram import get_recent_messages
from app.utils.retry import async_retry
from app.utils.logging import get_logger

logger = get_logger(__name__)

class DialogProcessor:
    """Service for processing dialog messages"""
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the dialog processor
        
        Args:
            db_session: Database session for storing messages
        """
        self.db_session = db_session
        self.message_limit = 20  # Number of messages to fetch per dialog
        
    @async_retry(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(ValueError, Exception)
    )
    async def fetch_messages(self, dialog: Dialog, token: str) -> List[Dict]:
        """
        Fetch recent messages for a dialog with retry logic
        
        Args:
            dialog: Dialog to fetch messages for
            token: User's session token
            
        Returns:
            List of message dictionaries
        """
        try:
            messages = await get_recent_messages(token, self.message_limit)
            # Filter messages for this dialog
            dialog_messages = [
                msg for msg in messages 
                if str(msg.get("dialog_id")) == dialog.telegram_dialog_id
            ]
            return dialog_messages
        except Exception as e:
            logger.error(
                f"Error fetching messages for dialog {dialog.title}: {str(e)}",
                exc_info=True
            )
            raise
            
    async def process_dialog(self, dialog: Dialog, token: str) -> bool:
        """
        Process a single dialog by fetching and storing its messages
        
        Args:
            dialog: Dialog to process
            token: User's session token
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Fetch messages with retry logic
            messages = await self.fetch_messages(dialog, token)
            
            if not messages:
                logger.info(f"No new messages found for dialog {dialog.title}")
                return True
                
            # Update dialog's last processed message
            latest_message = messages[0]  # Messages are sorted newest first
            dialog.last_processed_message_id = str(latest_message.get("message_id"))
            dialog.last_processed_at = datetime.utcnow()
            
            # Store messages in database
            for msg in messages:
                message = Message(
                    telegram_message_id=str(msg.get("message_id")),
                    dialog_id=dialog.id,
                    text=msg.get("text", ""),
                    sender_id=str(msg.get("sender", {}).get("id", "")),
                    sender_name=msg.get("sender", {}).get("name", "Unknown"),
                    date=datetime.fromisoformat(msg.get("date", "")),
                    is_outgoing=msg.get("is_outgoing", False),
                    metadata=msg.get("metadata", {})
                )
                self.db_session.add(message)
                
            await self.db_session.commit()
            logger.info(f"Successfully processed {len(messages)} messages for dialog {dialog.title}")
            return True
            
        except Exception as e:
            logger.error(
                f"Error processing dialog {dialog.title}: {str(e)}",
                exc_info=True
            )
            await self.db_session.rollback()
            return False
            
    async def process_dialogs(self, dialogs: List[Dialog], token: str) -> Dict[str, bool]:
        """
        Process multiple dialogs
        
        Args:
            dialogs: List of dialogs to process
            token: User's session token
            
        Returns:
            Dictionary mapping dialog IDs to success status
        """
        results = {}
        for dialog in dialogs:
            success = await self.process_dialog(dialog, token)
            results[dialog.id] = success
        return results 