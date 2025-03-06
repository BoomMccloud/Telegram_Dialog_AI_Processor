import os
import json
import re
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any

# Import the raw database connection
from app.db.database import get_raw_connection
from app.utils.logging import get_logger
from app.services.claude_processor import ClaudeProcessor, get_available_claude_models
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.dialog import Dialog, Message
from app.db.models.processed_response import ProcessedResponse, ProcessingStatus
from app.services.base import BaseProcessor

logger = get_logger(__name__)

# --------------------------
# Configuration Constants
# --------------------------
MODEL_CONFIGS = {
    "llama3": {
        "model_path": "/models/llama-3-8b-instruct.Q4_K_M.gguf",
        "n_ctx": 8192,
        "n_gpu_layers": -1,
        "verbose": False,
        "n_batch": 512,
    },
    "llama2": {
        "model_path": "/models/llama-2-13b-chat.Q5_K_M.gguf",
        "n_ctx": 4096,
        "n_gpu_layers": -1,
        "verbose": False,
        "n_batch": 512,
    },
    "mistral": {
        "model_path": "/models/mistral-7b-instruct-v0.1.Q5_K_M.gguf",
        "n_ctx": 4096,
        "n_gpu_layers": -1,
        "verbose": False,
        "n_batch": 512,
    },
}

DEFAULT_GENERATION_PARAMS = {
    "max_tokens": 256,
    "temperature": 0.8, 
    "top_p": 0.95,
    "top_k": 50,
    "stop": ["<|eot_id|>", "\n## End", "```end"],
    "repeat_penalty": 1.1,
    "mirostat_tau": 5
}

DEFAULT_SYSTEM_PROMPT = """
You are a helpful assistant analyzing Telegram messages. Your job is to:
1. Understand the context of the conversation
2. Generate a concise, relevant response
3. Be natural and helpful in your tone
4. Only respond to messages that need a response
5. Keep your responses under 150 words unless more detail is explicitly needed
"""


# --------------------------
# Dialog Processor Class
# --------------------------
class DialogProcessor:
    def __init__(self, model_name: str = "llama3", system_prompt: Optional[str] = None):
        self.model_name = model_name
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.llm = None  # Will be initialized on demand

    async def init_model(self):
        """Initialize the language model asynchronously"""
        try:
            # Import here to avoid loading the module if not needed
            from llama_cpp import Llama
            
            # Get model config
            model_config = MODEL_CONFIGS.get(self.model_name)
            if not model_config:
                raise ValueError(f"Model {self.model_name} not configured")
                
            # Check if model file exists
            model_path = model_config.get("model_path")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found at {model_path}")
                
            self.llm = Llama(**model_config)
            logger.info(f"Initialized model {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Model initialization failed: {str(e)}")
            return False

    async def process_dialog(self, dialog_id: int, user_id: int, token: str) -> Dict[str, Any]:
        """Process messages from a dialog and store results"""
        try:
            # Initialize model if not yet initialized
            if not self.llm:
                success = await self.init_model()
                if not success:
                    return {"success": False, "error": "Failed to initialize model"}
            
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
        """Fetch messages for a specific dialog from the database"""
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
                for key, value in message.items():
                    if isinstance(value, datetime):
                        message[key] = value.isoformat()
            
            return messages
        
        except Exception as e:
            logger.error(f"Failed to fetch messages for dialog {dialog_id}: {str(e)}")
            return []
        
        finally:
            await conn.close()

    async def _process_message(self, message: Dict, dialog_id: int, user_id: int) -> Optional[Dict]:
        """Process a single message and store the result"""
        try:
            # Get context messages
            context_messages = await self._get_context_messages(dialog_id, message["message_id"])
            
            # Build prompt with context
            prompt = self._build_prompt(context_messages)
            
            # Generate response
            response_text = await self._generate_response(prompt)
            
            # Store the result
            result = await self._store_processing_result(message, response_text, context_messages, dialog_id, user_id)
            
            # Mark message as processed
            await self._mark_message_processed(message["message_id"])
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to process message {message.get('message_id')}: {str(e)}")
            return None

    async def _get_context_messages(self, dialog_id: int, current_message_id: str) -> List[Dict]:
        """Get context messages for a message"""
        conn = await get_raw_connection()
        try:
            # Get the 5 messages before this one for context
            rows = await conn.fetch(
                """
                SELECT * FROM message_history
                WHERE dialog_id = $1
                AND message_date <= (
                    SELECT message_date FROM message_history WHERE message_id = $2
                )
                ORDER BY message_date DESC
                LIMIT 5
                """,
                dialog_id, current_message_id
            )
            
            # Convert to list of dictionaries and reverse to get chronological order
            messages = [dict(row) for row in rows]
            messages.reverse()
            
            # Convert datetime objects to strings
            for message in messages:
                for key, value in message.items():
                    if isinstance(value, datetime):
                        message[key] = value.isoformat()
            
            return messages
        
        except Exception as e:
            logger.error(f"Failed to fetch context messages: {str(e)}")
            return []
        
        finally:
            await conn.close()

    def _build_prompt(self, messages: List[Dict]) -> str:
        """Build a prompt from context messages"""
        # Start with system prompt
        prompt = self.system_prompt
        
        # Add context
        if messages and len(messages) > 0:
            current_context = messages[-1]['message_text'][:130] if messages[-1]['message_text'] else ""
            prompt = prompt.replace("Current context: \"\"", f"Current context: \"{current_context}\"")
        
        # Add message history
        message_history = []
        for m in messages:
            sender_name = m.get('sender_name', 'user')
            role_type = "assistant" if sender_name == "You" else "user"
            
            message_block = [
                f"<|start_header_id|>{role_type}<|end_header_id|>",
                m.get('message_text', '')[:200].strip(),
                "<|end_message_id|>"
            ]
            message_history.append("\n".join(message_block))
        
        # Add message history to prompt
        if message_history:
            prompt += "\n\nMessage History:\n" + "\n".join(message_history)
        
        # Add final instruction
        prompt += "\n\nPlease analyze the conversation and generate a response if needed."
        
        return prompt

    async def _generate_response(self, prompt: str) -> str:
        """Generate a response using the language model"""
        try:
            # Generate response
            response = self.llm(
                prompt,
                **DEFAULT_GENERATION_PARAMS
            )
            
            # Post-process the response
            response_text = self._post_process(response["choices"][0]["text"])
            
            return response_text
        
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            return ""

    def _post_process(self, text: str) -> str:
        """Post-process the generated text"""
        # Remove any special tokens
        text = re.sub(r'<\|.*?\|>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove any remaining special characters
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        
        # Truncate if too long
        if len(text) > 500:
            text = text[:497] + "..."
            
        return text

    async def _store_processing_result(
        self, 
        message: Dict, 
        response_text: str, 
        context_messages: List[Dict],
        dialog_id: int,
        user_id: int
    ) -> Dict:
        """Store the processing result in the database"""
        conn = await get_raw_connection()
        try:
            # Generate a UUID for the result
            result_id = str(uuid.uuid4())
            
            # Store the result
            result = await conn.fetchrow(
                """
                INSERT INTO processing_results (
                    result_id,
                    user_id,
                    dialog_id,
                    message_id,
                    model_name,
                    system_prompt,
                    context_messages,
                    response_text,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
                """,
                result_id,
                user_id,
                dialog_id,
                message["message_id"],
                self.model_name,
                self.system_prompt,
                json.dumps(context_messages),
                response_text,
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            # Convert to dictionary
            result_dict = dict(result)
            
            # Convert datetime objects to strings
            for key, value in result_dict.items():
                if isinstance(value, datetime):
                    result_dict[key] = value.isoformat()
            
            return result_dict
        
        except Exception as e:
            logger.error(f"Failed to store processing result: {str(e)}")
            return {}
        
        finally:
            await conn.close()

    async def _mark_message_processed(self, message_id: str) -> bool:
        """Mark a message as processed"""
        conn = await get_raw_connection()
        try:
            await conn.execute(
                """
                UPDATE message_history
                SET is_processed = true,
                    processed_at = $1
                WHERE message_id = $2
                """,
                datetime.utcnow(),
                message_id
            )
            return True
        except Exception as e:
            logger.error(f"Failed to mark message {message_id} as processed: {str(e)}")
            return False
        finally:
            await conn.close()


async def process_dialog_queue_item(queue_id: str, token: str = None):
    """Process a dialog from the processing queue"""
    conn = await get_raw_connection()
    try:
        # Get the queue item
        queue_item = await conn.fetchrow(
            """
            SELECT * FROM processing_queue
            WHERE queue_id = $1
            """,
            queue_id
        )
        
        if not queue_item:
            logger.error(f"Queue item {queue_id} not found")
            return
        
        # Get the user's selected model
        user_id = queue_item["user_id"]
        dialog_id = queue_item["dialog_id"]
        
        user_model = await get_user_model(user_id)
        if not user_model:
            logger.error(f"No model selected for user {user_id}")
            return
        
        # Initialize processor
        processor = DialogProcessor(
            model_name=user_model["model_name"],
            system_prompt=user_model.get("system_prompt")
        )
        
        # Process the dialog
        result = await processor.process_dialog(dialog_id, user_id, token)
        
        # Update queue item status
        status = "completed" if result.get("success", False) else "failed"
        error = result.get("error", "") if not result.get("success", False) else None
        
        await conn.execute(
            """
            UPDATE processing_queue
            SET status = $1,
                error = $2,
                completed_at = $3,
                updated_at = $4
            WHERE queue_id = $5
            """,
            status,
            error,
            datetime.utcnow() if status == "completed" else None,
            datetime.utcnow(),
            queue_id
        )
        
    except Exception as e:
        logger.error(f"Failed to process queue item {queue_id}: {str(e)}")
        # Update queue item with error
        await conn.execute(
            """
            UPDATE processing_queue
            SET status = 'failed',
                error = $1,
                updated_at = $2
            WHERE queue_id = $3
            """,
            str(e),
            datetime.utcnow(),
            queue_id
        )
    finally:
        await conn.close()


# --------------------------
# Background Task Functions
# --------------------------
async def enqueue_dialog_for_processing(dialog_id: int, user_id: int) -> Dict:
    """Add a dialog to the processing queue"""
    conn = await get_raw_connection()
    try:
        # Get recent unprocessed messages for this dialog
        rows = await conn.fetch(
            """
            SELECT * FROM message_history
            WHERE dialog_id = $1 AND is_processed = false
            ORDER BY message_date DESC
            LIMIT 20
            """,
            dialog_id
        )
        
        if not rows:
            return {
                "success": False,
                "error": "No unprocessed messages found for this dialog"
            }
        
        # Enqueue each message for processing
        queue_items = []
        for row in rows:
            # Generate queue item ID
            queue_id = str(uuid.uuid4())
            
            # Add to queue
            await conn.execute(
                """
                INSERT INTO processing_queue (
                    queue_id,
                    message_id,
                    priority,
                    status,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5)
                """,
                queue_id,
                row["message_id"],
                1,  # Default priority
                "pending",
                datetime.utcnow()
            )
            
            queue_items.append(queue_id)
        
        return {
            "success": True,
            "dialog_id": dialog_id,
            "queued_items": len(queue_items),
            "queue_ids": queue_items
        }
    
    except Exception as e:
        logger.error(f"Error enqueuing dialog {dialog_id} for processing: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    
    finally:
        await conn.close()


# --------------------------
# User Model Selection Functions
# --------------------------
async def get_available_models() -> List[Dict]:
    """
    Get list of available models
    
    Returns:
        List of model configurations
    """
    models = []
    
    # Add local LLM models
    for model_id in MODEL_CONFIGS.keys():
        models.append({
            "id": model_id,
            "name": model_id.capitalize(),
            "description": f"Local {model_id.capitalize()} model"
        })
    
    # Add Claude models
    claude_models = await get_available_claude_models()
    models.extend(claude_models)
    
    return models


async def select_model_for_user(user_id: int, model_name: str, system_prompt: Optional[str] = None) -> Dict:
    """
    Select a model for a user
    
    Args:
        user_id: User ID
        model_name: Model name to select
        system_prompt: Optional system prompt to use
        
    Returns:
        Dictionary with operation result
    """
    conn = await get_raw_connection()
    try:
        # Validate model
        available_models = await get_available_models()
        valid_model_ids = [model["id"] for model in available_models]
        
        if model_name not in valid_model_ids:
            return {
                "success": False, 
                "error": f"Invalid model: {model_name}. Valid models: {', '.join(valid_model_ids)}"
            }
        
        # Use default system prompt if none provided
        if not system_prompt:
            system_prompt = DEFAULT_SYSTEM_PROMPT
        
        # Check if user has existing selection
        existing = await conn.fetchrow(
            """
            SELECT * FROM user_selected_models 
            WHERE user_id = $1
            """,
            user_id
        )
        
        if existing:
            # Update existing selection
            await conn.execute(
                """
                UPDATE user_selected_models 
                SET model_name = $1, 
                    system_prompt = $2,
                    updated_at = NOW()
                WHERE user_id = $3
                """,
                model_name,
                system_prompt,
                user_id
            )
        else:
            # Create new selection
            await conn.execute(
                """
                INSERT INTO user_selected_models 
                (user_id, model_name, system_prompt, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                user_id,
                model_name,
                system_prompt
            )
        
        return {
            "success": True,
            "model_name": model_name,
            "system_prompt": system_prompt
        }
    
    except Exception as e:
        logger.error(f"Error selecting model: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        await conn.close()


async def get_user_model(user_id: int) -> Dict:
    """Get the user's currently selected model"""
    conn = await get_raw_connection()
    try:
        model = await conn.fetchrow(
            """
            SELECT * FROM user_selected_models
            WHERE user_id = $1
            """,
            user_id
        )
        
        if not model:
            # Return default model
            return {
                "model_id": "default",
                "model_name": "llama3",
                "is_default": True
            }
        
        # Convert to dictionary
        result = dict(model)
        
        # Convert datetime objects to strings
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting model for user {user_id}: {str(e)}")
        return {
            "model_id": "error",
            "error": str(e)
        }
    
    finally:
        await conn.close()


class ModelProcessor(BaseProcessor):
    def __init__(self, db: AsyncSession, model_name: str):
        self.db = db
        self.model_name = model_name
        
    async def get_pending_messages(self, limit: int = 10) -> List[Message]:
        """Get messages that need processing"""
        # Get messages that don't have a processing result for this model
        # or have a pending/error status
        subquery = (
            select(ProcessedResponse.message_id)
            .where(
                ProcessedResponse.model_name == self.model_name,
                ProcessedResponse.status == ProcessingStatus.COMPLETED
            )
            .scalar_subquery()
        )
        
        stmt = (
            select(Message)
            .outerjoin(ProcessedResponse)
            .where(Message.id.notin_(subquery))
            .options(selectinload(Message.dialog))
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
        
    async def get_processing_result(self, message_id: str) -> Optional[ProcessedResponse]:
        """Get processing result for a message"""
        stmt = (
            select(ProcessedResponse)
            .where(
                ProcessedResponse.message_id == message_id,
                ProcessedResponse.model_name == self.model_name
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
        
    async def create_processing_result(self, message_id: str) -> ProcessedResponse:
        """Create a new processing result entry"""
        result = ProcessedResponse(
            message_id=message_id,
            model_name=self.model_name,
            status=ProcessingStatus.PENDING
        )
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        return result
        
    async def update_processing_result(
        self,
        result_id: str,
        status: ProcessingStatus,
        result_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> ProcessedResponse:
        """Update processing result status and data"""
        stmt = (
            select(ProcessedResponse)
            .where(ProcessedResponse.id == result_id)
        )
        result = await self.db.execute(stmt)
        processing_result = result.scalar_one_or_none()
        
        if not processing_result:
            raise ValueError(f"Processing result {result_id} not found")
            
        processing_result.status = status
        if result_data is not None:
            processing_result.result = result_data
        if error is not None:
            processing_result.error = error
        if status == ProcessingStatus.COMPLETED:
            processing_result.completed_at = datetime.utcnow()
            
        await self.db.commit()
        await self.db.refresh(processing_result)
        return processing_result
        
    async def get_dialog_messages(self, dialog_id: str, limit: int = 100) -> List[Message]:
        """Get messages from a dialog with their processing results"""
        stmt = (
            select(Message)
            .where(Message.dialog_id == dialog_id)
            .options(
                selectinload(Message.processed_responses)
            )
            .order_by(Message.date.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
        
    async def get_dialog_by_telegram_id(self, telegram_dialog_id: str) -> Optional[Dialog]:
        """Get dialog by Telegram ID"""
        stmt = (
            select(Dialog)
            .where(Dialog.telegram_dialog_id == telegram_dialog_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
        
    async def create_or_update_dialog(
        self,
        telegram_dialog_id: str,
        name: str,
        type: str,
        unread_count: int = 0,
        last_message: Optional[Dict[str, Any]] = None
    ) -> Dialog:
        """Create or update a dialog"""
        dialog = await self.get_dialog_by_telegram_id(telegram_dialog_id)
        
        if dialog:
            dialog.name = name
            dialog.type = type
            dialog.unread_count = unread_count
            dialog.last_message = last_message
        else:
            dialog = Dialog(
                telegram_dialog_id=telegram_dialog_id,
                name=name,
                type=type,
                unread_count=unread_count,
                last_message=last_message
            )
            self.db.add(dialog)
            
        await self.db.commit()
        await self.db.refresh(dialog)
        return dialog
        
    async def create_message(
        self,
        dialog_id: str,
        telegram_message_id: str,
        text: str,
        sender_id: str,
        sender_name: str,
        date: datetime,
        is_outgoing: bool = False
    ) -> Message:
        """Create a new message"""
        message = Message(
            dialog_id=dialog_id,
            telegram_message_id=telegram_message_id,
            text=text,
            sender_id=sender_id,
            sender_name=sender_name,
            date=date,
            is_outgoing=is_outgoing
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message 