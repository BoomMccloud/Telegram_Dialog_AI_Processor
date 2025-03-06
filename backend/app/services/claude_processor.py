"""
Claude API Integration for Telegram Dialog Processing

This module provides the ClaudeProcessor class that adapts the existing
DialogProcessor pattern to use Anthropic's Claude API for processing
Telegram messages.
"""

import os
import json
import aiohttp
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.dialog import Dialog, Message
from app.db.models.processed_response import ProcessedResponse, ProcessingStatus
from app.services.model_processor import ModelProcessor
from app.utils.logging import get_logger
from app.core.exceptions import AIModelError

logger = get_logger(__name__)

# --------------------------
# Configuration Constants
# --------------------------
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL", "https://api.anthropic.com/v1/messages")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_VERSION = "2023-06-01"  # Update to latest version

CLAUDE_MODELS = {
    "claude-3-5-sonnet": {
        "id": "claude-3-5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "description": "Most capable Claude model - best balance of intelligence and speed"
    },
    "claude-3-opus": {
        "id": "claude-3-opus",
        "name": "Claude 3 Opus",
        "description": "Most powerful Claude model for complex tasks"
    },
    "claude-3-sonnet": {
        "id": "claude-3-sonnet",
        "name": "Claude 3 Sonnet",
        "description": "Balanced Claude model for general use cases"
    },
    "claude-3-haiku": {
        "id": "claude-3-haiku",
        "name": "Claude 3 Haiku",
        "description": "Fastest and most compact Claude model"
    }
}

DEFAULT_SYSTEM_PROMPT = """
You are a helpful assistant analyzing Telegram messages. Your job is to:
1. Understand the context of the conversation
2. Generate a concise, relevant response
3. Be natural and helpful in your tone
4. Only respond to messages that need a response
5. Keep your responses under 150 words unless more detail is explicitly needed
"""

async def get_available_claude_models() -> List[Dict]:
    """Get list of available Claude models"""
    if not CLAUDE_API_KEY:
        logger.warning("CLAUDE_API_KEY is not set. Claude models will not be available.")
        return []
    
    return list(CLAUDE_MODELS.values())

class ClaudeProcessor(ModelProcessor):
    """Processor for Telegram dialogs using Claude API"""
    
    def __init__(self, db: AsyncSession, model_name: str = "claude-3-sonnet", system_prompt: Optional[str] = None):
        """
        Initialize the Claude processor
        
        Args:
            db: SQLAlchemy AsyncSession
            model_name: Claude model to use
            system_prompt: Optional system prompt override
        """
        super().__init__(db, model_name)
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        
        # Validate model name
        if model_name not in CLAUDE_MODELS:
            logger.warning(f"Unknown Claude model: {model_name}. Defaulting to claude-3-sonnet.")
            self.model_name = "claude-3-sonnet"
        
        # Check for API key
        if not CLAUDE_API_KEY:
            logger.error("CLAUDE_API_KEY is not set. Claude processor will not work.")
    
    async def process_dialog(self, dialog_id: str) -> Dict[str, Any]:
        """
        Process messages from a dialog and store results
        
        Args:
            dialog_id: ID of the dialog to process
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Get unprocessed messages for this dialog
            messages = await self.get_pending_messages(dialog_id)
            if not messages:
                return {"success": False, "error": "No messages found for this dialog"}
            
            # Process messages
            results = []
            for message in messages:
                result = await self.process_message(message.id)
                if result:
                    results.append(result)
            
            return {
                "success": True,
                "dialog_id": dialog_id,
                "processed_count": len(results),
                "results": results
            }
        
        except Exception as e:
            logger.error(f"Error processing dialog {dialog_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def process_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Process a single message using Claude API
        
        Args:
            message_id: ID of the message to process
            
        Returns:
            Processing result or None if message should be skipped
        """
        # Get message with context
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .options(selectinload(Message.dialog))
        )
        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()
        
        if not message:
            logger.error(f"Message {message_id} not found")
            return None
            
        # Skip if missing text
        if not message.text:
            return None
        
        # Skip processing of very short messages or typical chat noise
        text = message.text.strip()
        if len(text) < 3 or text.lower() in ["ok", "yes", "no", "hi", "hello", "thanks", "thank you"]:
            return None
        
        try:
            # Get context messages
            context_messages = await self.get_dialog_messages(message.dialog_id)
            
            # Generate prompt and get response
            response = await self._generate_response(message, context_messages)
            
            # Store the result
            result = await self.create_processing_result(
                message_id=message.id,
                result_data=response,
                status=ProcessingStatus.COMPLETED
            )
            
            return {
                "message_id": message.id,
                "response": response,
                "result_id": result.id
            }
            
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {str(e)}")
            await self.create_processing_result(
                message_id=message.id,
                error=str(e),
                status=ProcessingStatus.ERROR
            )
            return None
    
    def _prepare_messages(self, message: Message, context_messages: List[Message]) -> List[Dict[str, Any]]:
        """Prepare messages for Claude API format"""
        formatted_messages = []
        
        # Add system prompt
        formatted_messages.append({
            "role": "system",
            "content": self.system_prompt
        })
        
        # Add context messages
        for ctx_msg in context_messages:
            formatted_messages.append({
                "role": "user" if ctx_msg.is_outgoing else "assistant",
                "content": ctx_msg.text
            })
            
        # Add current message
        formatted_messages.append({
            "role": "user",
            "content": message.text
        })
        
        return formatted_messages
        
    async def _generate_response(self, message: Message, context_messages: List[Message]) -> str:
        """Generate response using Claude API"""
        if not CLAUDE_API_KEY:
            raise AIModelError("Claude API key not configured")
            
        messages = self._prepare_messages(message, context_messages)
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(CLAUDE_API_URL, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Claude API error: {response.status} - {error_text}")
                        raise AIModelError(
                            "Claude API request failed",
                            details={
                                "status_code": response.status,
                                "error": error_text
                            }
                        )
                    
                    data = await response.json()
                    content = data.get("content", [{}])[0].get("text")
                    if not content:
                        raise AIModelError("No response generated by Claude")
                    return content
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling Claude API: {str(e)}")
            raise AIModelError("Failed to connect to Claude API", details={"error": str(e)})
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            raise AIModelError("Unexpected error calling Claude API", details={"error": str(e)}) 