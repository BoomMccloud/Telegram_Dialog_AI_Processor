"""
Dialog Processor Service

This module handles background processing of chat dialogs using LLM.
It provides functionality to:
1. Select dialogs for processing
2. Fetch messages from selected dialogs
3. Process messages with the chosen LLM
4. Store and retrieve processing results
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.db.models.dialog import Dialog, Message
from app.db.models.processed_response import ProcessedResponse, ProcessingStatus
from app.db.models.user import User
from app.services.model_processor import DialogProcessor
from app.services.claude_processor import ClaudeProcessor
from app.utils.logging import get_logger

logger = get_logger(__name__)

class DialogProcessorService:
    """Service for processing chat dialogs with LLM."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the dialog processor service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.claude_processor = ClaudeProcessor()
    
    async def select_dialogs_for_processing(self, dialog_ids: List[str], model_name: str) -> Dict[str, Any]:
        """Queue dialogs for processing with the specified model.
        
        Args:
            dialog_ids: List of dialog IDs to process
            model_name: Name of the LLM model to use for processing
            
        Returns:
            Dict with status and task info
        """
        try:
            # Validate that dialogs exist
            for dialog_id in dialog_ids:
                stmt = select(Dialog).where(Dialog.id == uuid.UUID(dialog_id))
                result = await self.db.execute(stmt)
                dialog = result.scalar_one_or_none()
                
                if not dialog:
                    return {
                        "status": "error",
                        "message": f"Dialog with ID {dialog_id} not found"
                    }
            
            # Create queue items for each dialog
            task_ids = []
            for dialog_id in dialog_ids:
                task_id = str(uuid.uuid4())
                
                # Create a processing record for tracking
                # This would be implemented in queue_manager.py
                # add_task_to_queue({
                #     "task_id": task_id,
                #     "dialog_id": dialog_id,
                #     "model_name": model_name,
                #     "status": "pending",
                #     "created_at": datetime.now().isoformat()
                # })
                
                task_ids.append(task_id)
            
            return {
                "status": "success",
                "message": f"Queued {len(dialog_ids)} dialogs for processing",
                "task_ids": task_ids
            }
            
        except Exception as e:
            logger.error(f"Error queueing dialogs for processing: {str(e)}")
            return {
                "status": "error",
                "message": f"Error queueing dialogs: {str(e)}"
            }
    
    async def fetch_messages_from_dialog(self, dialog_id: str, limit: int = 100) -> List[Message]:
        """Fetch messages from a dialog.
        
        Args:
            dialog_id: ID of the dialog to fetch messages from
            limit: Maximum number of messages to fetch
            
        Returns:
            List of messages
        """
        try:
            stmt = (
                select(Message)
                .where(Message.dialog_id == uuid.UUID(dialog_id))
                .order_by(desc(Message.date))
                .limit(limit)
            )
            
            result = await self.db.execute(stmt)
            messages = result.scalars().all()
            
            # Return messages in chronological order
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Error fetching messages from dialog {dialog_id}: {str(e)}")
            return []
    
    async def process_messages_with_llm(
        self, 
        messages: List[Message], 
        model_name: str
    ) -> List[ProcessedResponse]:
        """Process messages with the specified LLM.
        
        Args:
            messages: List of messages to process
            model_name: Name of the LLM model to use
            
        Returns:
            List of processing results
        """
        processing_results = []
        
        try:
            # Process each message
            for message in messages:
                # Skip outgoing messages (from the user)
                if message.is_outgoing:
                    continue
                
                # Create processing result record
                result = ProcessedResponse(
                    message_id=message.id,
                    model_name=model_name,
                    status=ProcessingStatus.PROCESSING
                )
                
                self.db.add(result)
                await self.db.commit()
                await self.db.refresh(result)
                
                try:
                    # Get conversation context (previous messages)
                    conversation = await self._get_conversation_context(message)
                    
                    # Process with appropriate LLM
                    if model_name.startswith("claude"):
                        # Use Claude processor
                        llm_result = await self.claude_processor.process_message(
                            message.text,
                            conversation,
                            model_name
                        )
                    else:
                        # Use generic processor or other models
                        dialog_processor = DialogProcessor()
                        llm_result = await dialog_processor.process_message(
                            message.text, 
                            conversation, 
                            model_name
                        )
                    
                    # Update result with LLM response
                    result.result = {
                        "suggested_reply": llm_result,
                        "processed_at": datetime.now().isoformat()
                    }
                    result.status = ProcessingStatus.COMPLETED
                    result.completed_at = datetime.now()
                    
                except Exception as e:
                    # Handle processing error
                    logger.error(f"Error processing message {message.id}: {str(e)}")
                    result.status = ProcessingStatus.ERROR
                    result.error = str(e)
                
                # Save updates
                await self.db.commit()
                await self.db.refresh(result)
                processing_results.append(result)
                
            return processing_results
            
        except Exception as e:
            logger.error(f"Error in process_messages_with_llm: {str(e)}")
            return processing_results
    
    async def _get_conversation_context(self, message: Message) -> List[Dict[str, Any]]:
        """Get conversation context for a message.
        
        Args:
            message: The message to get context for
            
        Returns:
            List of message dictionaries representing the conversation
        """
        # Fetch previous messages in the dialog (up to 10)
        stmt = (
            select(Message)
            .where(
                and_(
                    Message.dialog_id == message.dialog_id,
                    Message.date < message.date
                )
            )
            .order_by(desc(Message.date))
            .limit(10)
        )
        
        result = await self.db.execute(stmt)
        prev_messages = list(reversed(result.scalars().all()))
        
        # Format messages for LLM processing
        conversation = []
        for msg in prev_messages:
            conversation.append({
                "role": "assistant" if msg.is_outgoing else "user",
                "content": msg.text,
                "name": msg.sender_name
            })
            
        return conversation
    
    async def get_processing_results(
        self, 
        dialog_id: Optional[str] = None,
        status: Optional[ProcessingStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve processing results.
        
        Args:
            dialog_id: Optional dialog ID to filter by
            status: Optional status to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of processing results with message info
        """
        try:
            # Build query
            query = (
                select(ProcessedResponse)
                .options(selectinload(ProcessedResponse.message))
            )
            
            # Add filters
            filters = []
            if dialog_id:
                # Join with Message to filter by dialog_id
                filters.append(ProcessedResponse.message.has(Message.dialog_id == uuid.UUID(dialog_id)))
                
            if status:
                filters.append(ProcessedResponse.status == status)
                
            if filters:
                query = query.where(and_(*filters))
                
            # Add limit and order
            query = query.order_by(desc(ProcessedResponse.created_at)).limit(limit)
            
            # Execute query
            result = await self.db.execute(query)
            processing_results = result.scalars().all()
            
            # Format response
            formatted_results = []
            for pr in processing_results:
                formatted_results.append({
                    "id": str(pr.id),
                    "message_id": str(pr.message_id),
                    "dialog_id": str(pr.message.dialog_id) if pr.message else None,
                    "message_text": pr.message.text if pr.message else None,
                    "sender_name": pr.message.sender_name if pr.message else None,
                    "model_name": pr.model_name,
                    "status": pr.status.value,
                    "result": pr.result,
                    "error": pr.error,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "completed_at": pr.completed_at.isoformat() if pr.completed_at else None
                })
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error retrieving processing results: {str(e)}")
            return []
    
    async def update_processing_result(
        self, 
        result_id: str, 
        status: ProcessingStatus,
        custom_reply: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a processing result (approve/reject/modify).
        
        Args:
            result_id: ID of the processing result to update
            status: New status (completed/error)
            custom_reply: Optional custom reply to use instead of suggested reply
            
        Returns:
            Dict with status and result info
        """
        try:
            # Fetch the processing result
            stmt = select(ProcessedResponse).where(ProcessedResponse.id == uuid.UUID(result_id))
            query_result = await self.db.execute(stmt)
            processing_result = query_result.scalar_one_or_none()
            
            if not processing_result:
                return {
                    "status": "error",
                    "message": f"Processing result with ID {result_id} not found"
                }
                
            # Update status
            processing_result.status = status
            
            # Update result with custom reply if provided
            if custom_reply and processing_result.result:
                processing_result.result = {
                    **processing_result.result,
                    "custom_reply": custom_reply,
                    "original_reply": processing_result.result.get("suggested_reply"),
                    "modified_at": datetime.now().isoformat()
                }
                
            # Save changes
            await self.db.commit()
            await self.db.refresh(processing_result)
            
            return {
                "status": "success",
                "message": f"Processing result updated to {status.value}",
                "result_id": str(processing_result.id)
            }
            
        except Exception as e:
            logger.error(f"Error updating processing result {result_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error updating processing result: {str(e)}"
            }
    
    async def process_dialog(self, dialog_id: str, model_name: str) -> Dict[str, Any]:
        """Process all messages in a dialog.
        
        This is the main method called by the background worker.
        
        Args:
            dialog_id: ID of the dialog to process
            model_name: Name of the LLM model to use
            
        Returns:
            Dict with status and processing info
        """
        try:
            # Fetch messages from dialog
            messages = await self.fetch_messages_from_dialog(dialog_id)
            
            if not messages:
                return {
                    "status": "error",
                    "message": f"No messages found for dialog {dialog_id}"
                }
                
            # Process messages with LLM
            results = await self.process_messages_with_llm(messages, model_name)
            
            return {
                "status": "success",
                "message": f"Processed {len(results)} messages in dialog {dialog_id}",
                "processed_count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Error processing dialog {dialog_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing dialog: {str(e)}"
            } 