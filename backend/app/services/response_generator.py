"""
Response generator service for generating AI responses to messages
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message
from app.db.models.dialog import Dialog
from app.db.models.processed_response import ProcessedResponse
from app.db.models.types import ProcessingStatus
from app.services.llm_api import query_llm
from app.utils.storage import MessageFileStorage, ProcessingRunMetadata, ProcessingStatus as FileProcessingStatus
from app.utils.retry import async_retry
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()

class ResponseMetadata:
    """Metadata for a generated response"""
    def __init__(
        self,
        response_id: str = None,
        dialog_id: str = None,
        user_id: str = None,
        last_message_id: str = None,
        timestamp: datetime = None,
        model_name: str = None,
        status: str = "PENDING_APPROVAL",
        error: Optional[str] = None
    ):
        self.response_id = response_id or str(uuid4())
        self.dialog_id = dialog_id
        self.user_id = user_id
        self.last_message_id = last_message_id
        self.timestamp = timestamp or datetime.utcnow()
        self.model_name = model_name
        self.status = status
        self.error = error
        
    def to_dict(self) -> Dict:
        """Convert metadata to dictionary"""
        return {
            "response_id": self.response_id,
            "dialog_id": self.dialog_id,
            "user_id": self.user_id,
            "last_message_id": self.last_message_id,
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "status": self.status,
            "error": self.error
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'ResponseMetadata':
        """Create metadata from dictionary"""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

class ResponseFileStorage:
    """Utility for managing response files"""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize the response file storage utility
        
        Args:
            base_dir: Base directory for storing response files
        """
        if base_dir is None:
            # Use a directory within the project by default
            base_dir = str(PROJECT_ROOT / "response_storage")
            
        self.base_dir = Path(base_dir)
        self._ensure_base_dir()
        logger.info(f"Response storage initialized at: {self.base_dir}")
    
    def _ensure_base_dir(self) -> None:
        """Ensure the base directory exists"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_user_dir(self, user_id: str) -> Path:
        """Get the directory for a user"""
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    def get_dialog_dir(self, user_id: str, dialog_id: str) -> Path:
        """Get the directory for a dialog"""
        dialog_dir = self.get_user_dir(user_id) / str(dialog_id)
        dialog_dir.mkdir(exist_ok=True)
        return dialog_dir
        
    def save_response(
        self, 
        user_id: str, 
        dialog_id: str, 
        response_text: str, 
        last_message_id: str,
        model_name: str = "claude-3-5-sonnet-20241022"
    ) -> ResponseMetadata:
        """
        Save a generated response to file
        
        Args:
            user_id: User ID
            dialog_id: Dialog ID
            response_text: Generated response text
            last_message_id: ID of the last message in the dialog
            model_name: Name of the model used for generation
            
        Returns:
            Metadata for the saved response
        """
        # Create metadata
        metadata = ResponseMetadata(
            dialog_id=dialog_id,
            user_id=user_id,
            last_message_id=last_message_id,
            model_name=model_name
        )
        
        # Create response directory
        dialog_dir = self.get_dialog_dir(user_id, dialog_id)
        response_file = dialog_dir / f"response_{metadata.response_id}.json"
        
        # Save response and metadata
        response_data = {
            "metadata": metadata.to_dict(),
            "response_text": response_text
        }
        
        with open(response_file, "w") as f:
            json.dump(response_data, f, default=str)
            
        # Create latest symlink
        latest_link = dialog_dir / "latest_response"
        if latest_link.exists():
            if latest_link.is_symlink():
                latest_link.unlink()
            else:
                latest_link.unlink()
                
        try:
            # Use relative path for the symlink
            relative_path = os.path.relpath(response_file, dialog_dir)
            os.symlink(relative_path, latest_link)
        except Exception as e:
            logger.error(f"Failed to create symlink: {str(e)}")
            
        return metadata
        
    def get_latest_response(self, user_id: str, dialog_id: str) -> Optional[Dict]:
        """
        Get the latest response for a dialog
        
        Args:
            user_id: User ID
            dialog_id: Dialog ID
            
        Returns:
            Dictionary containing response text and metadata, or None if no response exists
        """
        latest_link = self.get_dialog_dir(user_id, dialog_id) / "latest_response"
        
        if not latest_link.exists() or not latest_link.is_symlink():
            return None
            
        response_file = latest_link.resolve()
        
        if not response_file.exists():
            return None
            
        with open(response_file, "r") as f:
            response_data = json.load(f)
            
        # Convert metadata dict to object
        if "metadata" in response_data:
            response_data["metadata"] = ResponseMetadata.from_dict(response_data["metadata"])
            
        return response_data

class ResponseGenerator:
    """Service for generating AI responses to messages"""
    
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022", db_session: Optional[AsyncSession] = None):
        """
        Initialize the response generator
        
        Args:
            model_name: Name of the model to use for generation
            db_session: Database session for storing responses
        """
        self.model_name = model_name
        self.message_storage = MessageFileStorage()
        self.response_storage = ResponseFileStorage()
        self.db_session = db_session
        logger.info(f"Response generator initialized with model: {model_name}")
        
    def _build_prompt(self, messages: List[Message], dialog: Dialog, iam: str = "Assistant") -> str:
        """
        Build a prompt for the AI model
        
        Args:
            messages: List of messages to include in the prompt
            dialog: Dialog information
            iam: Name of the assistant
            
        Returns:
            Formatted prompt string
        """
        # Sort messages by date
        sorted_messages = sorted(messages, key=lambda m: m.date)
        
        # Take the last 5 messages for context
        context_messages = sorted_messages[-5:]
        
        system_directives = f"""
# Role Definition
You are {iam}, respond to the user with:

# Critical Directives
✦ MUST analyze ALL historical messages
✦ ALWAYS prioritize context-based responses
✦ If context is unclear: Ask SPECIFIC follow-up questions
✦ Minimum action verbs per response: 1 (e.g. "confirm", "schedule", "review")

# Tone Guidelines
✦ Professional yet approachable
✦ Balanced formality (avoid both stiff and casual extremes)
✦ Show appreciation when appropriate
✦ Use concise but complete sentences

# Response Strategy
1. Extract key entities (names/dates/actions)
2. Mirror the partner's communication style
3. Propose concrete next steps when possible

# Response Template Examples
[Positive] "Confirmed, the materials will reach you by EOD Wednesday. Appreciate your patience."
[Neutral] "Let's schedule a brief sync tomorrow AM. Please share your availability."
[Urgent] "Need the signed docs by 3PM CST today. Will follow up via email."

# Strict Prohibitions
1. Never use emoticons or slang
2. Avoid jargon like "leverage" or "synergy"
3. Never make promises beyond authority

Current context: "{context_messages[-1].text[:130] if context_messages else ""}"
"""

        # Add message history
        message_history = []
        for m in context_messages:
            role = "assistant" if m.is_outgoing else "user"
            sender = iam if m.is_outgoing else m.sender_name
            message_history.append(f"{sender} ({role}): {m.text}")
            
        # Combine system directives and message history
        prompt = system_directives + "\n\n" + "\n".join(message_history)
        
        # Add final instruction
        prompt += "\n\nPlease provide a response to the latest message:"
        
        return prompt
    
    async def save_response_to_db(
        self, 
        dialog: Dialog, 
        response_text: str, 
        last_message_id: str,
        last_message_timestamp: datetime,
        db_session: AsyncSession = None
    ) -> ProcessedResponse:
        """
        Save a generated response to the database
        
        Args:
            dialog: Dialog to save response for
            response_text: Generated response text
            last_message_id: ID of the last message in the dialog
            last_message_timestamp: Timestamp of the last message
            db_session: Database session to use
            
        Returns:
            Saved ProcessedResponse object
        """
        session = db_session or self.db_session
        if not session:
            logger.error("No database session available for saving response")
            raise ValueError("Database session is required to save response")
            
        try:
            # Check if a response already exists for this dialog
            query = select(ProcessedResponse).where(ProcessedResponse.dialog_id == dialog.id)
            result = await session.execute(query)
            existing_response = result.scalar_one_or_none()
            
            if existing_response:
                # Update existing response
                existing_response.last_message_id = last_message_id
                existing_response.last_message_timestamp = last_message_timestamp
                existing_response.suggested_response = response_text
                existing_response.model_name = self.model_name
                existing_response.status = ProcessingStatus.PENDING_APPROVAL
                existing_response.processed_at = datetime.utcnow()
                existing_response.error = None
                
                await session.commit()
                logger.info(f"Updated existing response for dialog {dialog.title}")
                return existing_response
            else:
                # Create new response
                new_response = ProcessedResponse(
                    dialog_id=dialog.id,
                    last_message_id=last_message_id,
                    last_message_timestamp=last_message_timestamp,
                    suggested_response=response_text,
                    model_name=self.model_name,
                    status=ProcessingStatus.PENDING_APPROVAL
                )
                
                session.add(new_response)
                await session.commit()
                logger.info(f"Created new response for dialog {dialog.title}")
                return new_response
                
        except Exception as e:
            await session.rollback()
            logger.error(f"Error saving response to database: {str(e)}", exc_info=True)
            raise
        
    @async_retry(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(ValueError, Exception)
    )
    async def generate_response(self, dialog: Dialog, db_session: AsyncSession = None) -> Optional[Dict]:
        """
        Generate a response for a dialog
        
        Args:
            dialog: Dialog to generate a response for
            db_session: Database session to use
            
        Returns:
            Dictionary containing response text and metadata, or None if generation failed
        """
        try:
            # Use provided session or instance session
            session = db_session or self.db_session
            
            # Get the latest messages
            messages = self.message_storage.get_latest_messages(
                user_id=str(dialog.user_id),
                dialog_id=str(dialog.id)
            )
            
            if not messages:
                logger.warning(f"No messages found for dialog {dialog.title}")
                return None
                
            # Sort messages by date
            sorted_messages = sorted(messages, key=lambda m: m.date)
            
            # Get the last message ID and timestamp
            last_message = sorted_messages[-1]
            last_message_id = last_message.telegram_message_id
            last_message_timestamp = last_message.date
            
            # Check if we already have a response for this message in the database
            if session:
                query = select(ProcessedResponse).where(
                    ProcessedResponse.dialog_id == dialog.id,
                    ProcessedResponse.last_message_id == last_message_id
                )
                result = await session.execute(query)
                existing_db_response = result.scalar_one_or_none()
                
                if existing_db_response:
                    logger.info(f"Response already exists in database for dialog {dialog.title}, last message ID: {last_message_id}")
                    return {
                        "db_response": existing_db_response,
                        "response_text": existing_db_response.suggested_response
                    }
            
            # Check if we already have a response in file storage
            existing_file_response = self.response_storage.get_latest_response(
                user_id=str(dialog.user_id),
                dialog_id=str(dialog.id)
            )
            
            if existing_file_response and existing_file_response["metadata"].last_message_id == last_message_id:
                logger.info(f"Response already exists in file storage for dialog {dialog.title}, last message ID: {last_message_id}")
                
                # If we have a database session, save to database as well
                if session:
                    db_response = await self.save_response_to_db(
                        dialog=dialog,
                        response_text=existing_file_response["response_text"],
                        last_message_id=last_message_id,
                        last_message_timestamp=last_message_timestamp,
                        db_session=session
                    )
                    
                    return {
                        "metadata": existing_file_response["metadata"],
                        "response_text": existing_file_response["response_text"],
                        "db_response": db_response
                    }
                
                return existing_file_response
                
            # Build prompt
            prompt = self._build_prompt(messages, dialog)
            
            # Generate response
            logger.info(f"Generating response for dialog {dialog.title}")
            response_text = query_llm(
                prompt=prompt,
                provider="anthropic",
                model=self.model_name
            )
            
            if not response_text:
                logger.error(f"Failed to generate response for dialog {dialog.title}")
                return None
                
            # Save response to file storage
            metadata = self.response_storage.save_response(
                user_id=str(dialog.user_id),
                dialog_id=str(dialog.id),
                response_text=response_text,
                last_message_id=last_message_id,
                model_name=self.model_name
            )
            
            # Save response to database if session is available
            db_response = None
            if session:
                db_response = await self.save_response_to_db(
                    dialog=dialog,
                    response_text=response_text,
                    last_message_id=last_message_id,
                    last_message_timestamp=last_message_timestamp,
                    db_session=session
                )
            
            logger.info(f"Response generated and saved for dialog {dialog.title}")
            
            return {
                "metadata": metadata,
                "response_text": response_text,
                "db_response": db_response
            }
            
        except Exception as e:
            logger.error(f"Error generating response for dialog {dialog.title}: {str(e)}", exc_info=True)
            return None 