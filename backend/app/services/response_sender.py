"""
Service for sending approved responses to Telegram
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.processed_response import ProcessedResponse
from app.db.models.dialog import Dialog
from app.db.models.user import User
from app.db.models.types import ProcessingStatus
from app.services.telegram import send_message
from app.services.auth import find_session_file_for_user, load_telegram_client_from_session
from app.utils.retry import async_retry
from app.utils.logging import get_logger

logger = get_logger(__name__)

class ResponseSender:
    """Service for sending approved responses to Telegram"""
    
    def __init__(self):
        """Initialize the response sender service"""
        pass
    
    @async_retry(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(Exception,)
    )
    async def send_response(self, response_id: str, db_session: AsyncSession) -> bool:
        """
        Send an approved response to Telegram
        
        Args:
            response_id: ID of the response to send
            db_session: Database session
            
        Returns:
            True if the response was sent successfully, False otherwise
        """
        try:
            # Get the response with dialog and user information
            query = (
                select(ProcessedResponse)
                .join(Dialog, ProcessedResponse.dialog_id == Dialog.id)
                .join(User, Dialog.user_id == User.id)
                .where(
                    ProcessedResponse.id == response_id,
                    ProcessedResponse.status == ProcessingStatus.APPROVED
                )
                .options(
                    joinedload(ProcessedResponse.dialog).joinedload(Dialog.user)
                )
            )
            
            result = await db_session.execute(query)
            response = result.unique().scalar_one_or_none()
            
            if not response:
                logger.warning(f"Response {response_id} not found or not approved")
                return False
            
            # Get the dialog and user information
            dialog = response.dialog
            user = dialog.user
            
            if not user or not user.telegram_id:
                logger.error(f"User not found or has no telegram_id for dialog {dialog.id}")
                
                # Update response status to FAILED
                response.status = ProcessingStatus.FAILED
                response.error = "User not found or has no Telegram ID"
                await db_session.commit()
                
                return False
            
            # Get the message to send (edited response if available, otherwise suggested response)
            message_text = response.edited_response or response.suggested_response
            
            # Send the message
            logger.info(f"Sending response to dialog {dialog.title}")
            
            # Find session file for the user
            session_file = await find_session_file_for_user(user.telegram_id)
            if not session_file:
                logger.error(f"No session file found for user {user.id} (Telegram ID: {user.telegram_id})")
                
                # Update response status to FAILED
                response.status = ProcessingStatus.FAILED
                response.error = "No Telegram session file found for user"
                await db_session.commit()
                
                return False
            
            # Load client from session file
            client = await load_telegram_client_from_session(session_file)
            if not client:
                logger.error(f"Failed to load Telegram client for user {user.id}")
                
                # Update response status to FAILED
                response.status = ProcessingStatus.FAILED
                response.error = "Failed to load Telegram client"
                await db_session.commit()
                
                return False
            
            # Send the message
            try:
                sent_message = await client.send_message(
                    dialog.telegram_dialog_id,
                    message_text
                )
                
                # Update response status to SENT
                response.status = ProcessingStatus.SENT
                response.sent_at = datetime.utcnow()
                await db_session.commit()
                
                # Disconnect the client
                await client.disconnect()
                
                logger.info(f"Response sent successfully to dialog {dialog.title}")
                return True
                
            except Exception as e:
                logger.error(f"Error sending message to dialog {dialog.title}: {str(e)}", exc_info=True)
                
                # Disconnect the client
                if client:
                    await client.disconnect()
                
                # Update response status to FAILED
                response.status = ProcessingStatus.FAILED
                response.error = f"Failed to send message: {str(e)}"
                await db_session.commit()
                
                return False
                
        except Exception as e:
            logger.error(f"Error sending response {response_id}: {str(e)}", exc_info=True)
            return False
    
    async def send_all_approved_responses(self, db_session: AsyncSession) -> Dict[str, Any]:
        """
        Send all approved responses to Telegram
        
        Args:
            db_session: Database session
            
        Returns:
            Dictionary with success and failure counts
        """
        # Get all approved responses with dialog and user information
        query = (
            select(ProcessedResponse)
            .join(Dialog, ProcessedResponse.dialog_id == Dialog.id)
            .join(User, Dialog.user_id == User.id)
            .where(
                ProcessedResponse.status == ProcessingStatus.APPROVED,
                Dialog.auto_send_enabled == True
            )
            .options(
                joinedload(ProcessedResponse.dialog).joinedload(Dialog.user)
            )
        )
        
        result = await db_session.execute(query)
        responses = result.unique().scalars().all()
        
        if not responses:
            logger.info("No approved responses to send")
            return {"success": 0, "failure": 0, "total": 0}
        
        # Send each response
        success_count = 0
        failure_count = 0
        
        for response in responses:
            success = await self.send_response(response.id, db_session)
            
            if success:
                success_count += 1
            else:
                failure_count += 1
        
        logger.info(f"Sent {success_count} responses successfully, {failure_count} failed")
        
        return {
            "success": success_count,
            "failure": failure_count,
            "total": len(responses)
        } 