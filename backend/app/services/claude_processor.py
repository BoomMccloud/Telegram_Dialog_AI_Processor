"""
Claude API Integration for Telegram Dialog Processing

This module provides the ClaudeProcessor class that adapts the existing
DialogProcessor pattern to use Anthropic's Claude API for processing
Telegram messages.
"""

import os
import json
import aiohttp
import re
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

# Import the raw database connection
from app.db.database import get_raw_connection
from app.utils.logging import get_logger

logger = get_logger(__name__)

# --------------------------
# Configuration Constants
# --------------------------
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
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
    """
    Get list of available Claude models
    
    Returns:
        List of Claude model configurations
    """
    if not CLAUDE_API_KEY:
        logger.warning("CLAUDE_API_KEY is not set. Claude models will not be available.")
        return []
    
    models = []
    for model_id, model_config in CLAUDE_MODELS.items():
        models.append(model_config)
    
    return models


class ClaudeProcessor:
    """
    Processor for Telegram dialogs using Claude API
    
    This class handles the processing of Telegram messages using Anthropic's
    Claude API, managing the entire pipeline from fetching messages to
    generating responses and storing results.
    """
    
    def __init__(self, model_name: str = "claude-3-sonnet", system_prompt: Optional[str] = None):
        """
        Initialize the Claude processor
        
        Args:
            model_name: Claude model to use
            system_prompt: Optional system prompt override
        """
        self.model_name = model_name
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        
        # Validate model name
        if model_name not in CLAUDE_MODELS:
            logger.warning(f"Unknown Claude model: {model_name}. Defaulting to claude-3-sonnet.")
            self.model_name = "claude-3-sonnet"
        
        # Check for API key
        if not CLAUDE_API_KEY:
            logger.error("CLAUDE_API_KEY is not set. Claude processor will not work.")
    
    async def process_dialog(self, dialog_id: int, user_id: int, session_id: str) -> Dict[str, Any]:
        """
        Process messages from a dialog and store results
        
        Args:
            dialog_id: ID of the dialog to process
            user_id: ID of the user
            session_id: User session ID
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Get messages for this dialog
            messages = await self._fetch_messages_for_dialog(dialog_id)
            if not messages:
                return {"success": False, "error": "No messages found for this dialog"}
            
            # Process recent unprocessed messages
            results = []
            for message in messages:
                if not message.get("is_processed", False):
                    # Process the message
                    result = await self._process_message(message, dialog_id, user_id)
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
    
    async def _fetch_messages_for_dialog(self, dialog_id: int) -> List[Dict]:
        """
        Fetch messages for a specific dialog from the database
        
        Args:
            dialog_id: ID of the dialog to fetch messages for
            
        Returns:
            List of message dictionaries
        """
        conn = await get_raw_connection()
        try:
            # Get the most recent messages for this dialog
            rows = await conn.fetch(
                """
                SELECT * FROM message_history
                WHERE dialog_id = $1
                ORDER BY message_date DESC
                LIMIT 20
                """,
                dialog_id
            )
            
            # Convert to list of dictionaries
            messages = [dict(row) for row in rows]
            
            # Convert datetime objects to strings
            for message in messages:
                if "message_date" in message and isinstance(message["message_date"], datetime):
                    message["message_date"] = message["message_date"].isoformat()
            
            # Reverse to get chronological order
            return list(reversed(messages))
            
        finally:
            await conn.close()
    
    async def _process_message(self, message: Dict, dialog_id: int, user_id: int) -> Optional[Dict]:
        """
        Process a single message
        
        Args:
            message: Message data
            dialog_id: Dialog ID
            user_id: User ID
            
        Returns:
            Processing result or None if message should be skipped
        """
        # Skip if missing text
        if not message.get("message_text"):
            await self._mark_message_processed(message["message_id"])
            return None
        
        # Skip processing of very short messages or typical chat noise
        text = message.get("message_text", "").strip()
        if len(text) < 3 or text.lower() in ["ok", "yes", "no", "hi", "hello", "thanks", "thank you"]:
            await self._mark_message_processed(message["message_id"])
            return None
        
        try:
            # Get context messages for this dialog
            context_messages = await self._get_context_messages(dialog_id, message["message_id"])
            
            # Generate prompt and get response
            response = await self._generate_response(message, context_messages)
            
            # Store the result
            result = await self._store_processing_result(
                message, response, context_messages, dialog_id, user_id
            )
            
            # Mark message as processed
            await self._mark_message_processed(message["message_id"])
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing message {message['message_id']}: {str(e)}")
            return None
    
    async def _get_context_messages(self, dialog_id: int, current_message_id: str) -> List[Dict]:
        """
        Get context messages for a specific message
        
        Args:
            dialog_id: Dialog ID
            current_message_id: Current message ID
            
        Returns:
            List of context messages
        """
        conn = await get_raw_connection()
        try:
            # Get previous messages as context
            rows = await conn.fetch(
                """
                SELECT * FROM message_history
                WHERE dialog_id = $1 AND message_id != $2
                ORDER BY message_date DESC
                LIMIT 10
                """,
                dialog_id, current_message_id
            )
            
            # Convert to list of dictionaries
            context = [dict(row) for row in rows]
            
            # Convert datetime objects to strings
            for message in context:
                if "message_date" in message and isinstance(message["message_date"], datetime):
                    message["message_date"] = message["message_date"].isoformat()
            
            # Reverse to get chronological order for context
            return list(reversed(context))
            
        finally:
            await conn.close()
    
    async def _generate_response(self, message: Dict, context_messages: List[Dict]) -> str:
        """
        Generate a response using Claude API
        
        Args:
            message: Current message
            context_messages: Context messages
            
        Returns:
            Generated response text
        """
        if not CLAUDE_API_KEY:
            return "Error: Claude API key not configured"
        
        # Prepare headers
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": CLAUDE_API_VERSION,
            "content-type": "application/json"
        }
        
        # Prepare context for Claude
        claude_messages = []
        
        # Add context messages
        for ctx in context_messages:
            sender = ctx.get("from_user_name") or ctx.get("from_user_id") or "User"
            claude_messages.append({
                "role": "user" if ctx.get("is_outgoing") else "assistant", 
                "content": f"{sender}: {ctx.get('message_text', '')}"
            })
        
        # Add current message
        current_sender = message.get("from_user_name") or message.get("from_user_id") or "User"
        claude_messages.append({
            "role": "user",
            "content": f"{current_sender}: {message.get('message_text', '')}"
        })
        
        # Prepare payload
        payload = {
            "model": self.model_name,
            "system": self.system_prompt,
            "messages": claude_messages,
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(CLAUDE_API_URL, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Claude API error: {response.status} - {error_text}")
                        return f"Error: Claude API returned {response.status}"
                    
                    data = await response.json()
                    return data.get("content", [{}])[0].get("text", "No response generated")
                    
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    async def _store_processing_result(self, message: Dict, response_text: str, 
                                      context_messages: List[Dict], dialog_id: int, 
                                      user_id: int) -> Dict:
        """
        Store the processing result in the database
        
        Args:
            message: Message that was processed
            response_text: Generated response text
            context_messages: Context messages used
            dialog_id: Dialog ID
            user_id: User ID
            
        Returns:
            Dictionary with stored result details
        """
        conn = await get_raw_connection()
        try:
            # Insert into processed_responses table
            row = await conn.fetchrow(
                """
                INSERT INTO processed_responses
                (message_id, dialog_id, user_id, response_text, model_name, 
                system_prompt, context_messages, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                RETURNING id, created_at, status
                """,
                message["message_id"],
                dialog_id,
                user_id,
                response_text,
                self.model_name,
                self.system_prompt,
                json.dumps(context_messages),
                "pending"  # Initial status is pending review
            )
            
            # Create result dict with IDs and timestamps
            result = {
                "message_id": message["message_id"],
                "message_text": message.get("message_text", ""),
                "response_id": row["id"],
                "response_text": response_text,
                "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"],
                "status": row["status"]
            }
            
            return result
            
        finally:
            await conn.close()
    
    async def _mark_message_processed(self, message_id: str) -> bool:
        """
        Mark a message as processed
        
        Args:
            message_id: ID of the message to mark
            
        Returns:
            True if successful, False otherwise
        """
        conn = await get_raw_connection()
        try:
            # Update the is_processed flag
            await conn.execute(
                """
                UPDATE message_history
                SET is_processed = true, updated_at = NOW()
                WHERE message_id = $1
                """,
                message_id
            )
            return True
        
        except Exception as e:
            logger.error(f"Error marking message as processed: {str(e)}")
            return False
            
        finally:
            await conn.close() 