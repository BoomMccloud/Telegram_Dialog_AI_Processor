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
from app.utils.storage import MessageFileStorage, ProcessingRunMetadata

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
        self.file_storage = MessageFileStorage()
        
    @async_retry(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(ValueError, Exception)
    )
    async def fetch_messages(self, dialog: Dialog, token: str, db_session=None) -> List[Dict]:
        """
        Fetch recent messages for a dialog with retry logic
        
        Args:
            dialog: Dialog to fetch messages for
            token: User's session token
            db_session: Optional database session for standalone worker
            
        Returns:
            List of message dictionaries
        """
        try:
            logger.info(f"Fetching last {self.message_limit} messages for dialog {dialog.title} (ID: {dialog.telegram_dialog_id})")
            
            # Convert telegram_dialog_id to int
            dialog_id = int(dialog.telegram_dialog_id)
            
            # Fetch messages for this specific dialog
            messages = await get_recent_messages(
                token, 
                limit=self.message_limit,
                dialog_id=dialog_id
            )
            
            if not messages:
                logger.info(f"No messages found for dialog {dialog.title} (ID: {dialog.telegram_dialog_id})")
            else:
                logger.info(f"Found {len(messages)} messages for dialog {dialog.title}")
                
            return messages
        except Exception as e:
            logger.error(
                f"Error fetching messages for dialog {dialog.title}: {str(e)}",
                exc_info=True
            )
            raise
            
    async def process_dialog(self, dialog: Dialog, token: str, db_session=None) -> bool:
        """
        Process a single dialog by fetching and storing its messages
        
        Args:
            dialog: Dialog to process
            token: User's session token
            db_session: Optional database session for standalone worker
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Fetch messages with retry logic
            raw_messages = await self.fetch_messages(dialog, token, db_session)
            
            if not raw_messages:
                logger.info(f"No messages found for dialog {dialog.title}")
                return True
                
            # Update dialog's last processed message
            latest_message = raw_messages[0]  # Messages are sorted newest first
            dialog.last_processed_message_id = str(latest_message.get("message_id"))
            dialog.last_processed_at = datetime.utcnow()
            
            # Create a new processing run
            metadata = self.file_storage.create_processing_run(
                user_id=str(dialog.user_id),
                dialog_id=str(dialog.id)
            )
            
            # Create run directory path
            run_dir = self.file_storage.get_dialog_dir(
                str(dialog.user_id), 
                str(dialog.id)
            ) / f"processing_{metadata.timestamp.strftime('%Y%m%d_%H%M%S')}_{metadata.run_id}"
            
            # Convert raw messages to Message objects
            messages = []
            for msg in raw_messages:
                message = Message(
                    telegram_message_id=str(msg.get("message_id")),
                    dialog_id=str(dialog.id),
                    text=msg.get("text", ""),
                    sender_id=str(msg.get("sender", {}).get("id", "")),
                    sender_name=msg.get("sender", {}).get("name", "Unknown"),
                    date=datetime.fromisoformat(msg.get("date", "")),
                    is_outgoing=msg.get("is_outgoing", False),
                    metadata=msg.get("metadata", {})
                )
                messages.append(message)
            
            # Save messages to file
            self.file_storage.save_messages(run_dir, messages)
            
            # Update dialog in database
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
            
    async def process_dialogs(self, dialogs: List[Dialog], token: str, db_session=None) -> Dict[str, bool]:
        """
        Process multiple dialogs
        
        Args:
            dialogs: List of dialogs to process
            token: User's session token
            db_session: Optional database session for standalone worker
            
        Returns:
            Dictionary mapping dialog IDs to success status
        """
        results = {}
        for dialog in dialogs:
            success = await self.process_dialog(dialog, token, db_session)
            results[dialog.id] = success
        
        # Schedule cleanup of old runs
        try:
            deleted_count = await self.file_storage.cleanup_old_runs(max_age_days=7)
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old processing runs")
        except Exception as e:
            logger.error(f"Error cleaning up old runs: {str(e)}")
        
        return results
        
    def get_latest_messages(self, dialog: Dialog) -> List[Message]:
        """
        Get the latest messages for a dialog from file storage
        
        Args:
            dialog: Dialog to get messages for
            
        Returns:
            List of messages
        """
        return self.file_storage.get_latest_messages(
            user_id=str(dialog.user_id),
            dialog_id=str(dialog.id)
        ) 