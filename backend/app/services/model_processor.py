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
        
    async def process_dialog(self, dialog_id: str) -> Dict[str, Any]:
        """Process a dialog and generate a response"""
        try:
            # Get dialog data from database
            dialog = await self._get_dialog(dialog_id)
            if not dialog:
                raise ValueError(f"Dialog {dialog_id} not found")
                
            # Generate response using the model
            response = await self._generate_response(dialog)
            
            # Update processing status
            await self._update_dialog_status(dialog_id, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to process dialog {dialog_id}: {str(e)}")
            raise
            
    async def _get_dialog(self, dialog_id: str) -> Optional[Dict]:
        """Get dialog data from database"""
        conn = await get_raw_connection()
        try:
            row = await conn.fetchrow(
                """
                SELECT * FROM dialogs
                WHERE id = $1
                """,
                dialog_id
            )
            
            if not row:
                return None
                
            dialog = dict(row)
            
            # Convert datetime objects to strings
            for key, value in dialog.items():
                if isinstance(value, datetime):
                    dialog[key] = value.isoformat()
                    
            return dialog
            
        except Exception as e:
            logger.error(f"Failed to get dialog {dialog_id}: {str(e)}")
            return None
            
        finally:
            await conn.close()
            
    async def _generate_response(self, dialog: Dict) -> Dict[str, Any]:
        """Generate a response for the dialog using the model"""
        try:
            # Format dialog context for the model
            context = self._format_dialog_context(dialog)
            
            # Call model API
            response = await call_model_api(
                model_name=self.model_name,
                system_prompt=self.system_prompt,
                context=context
            )
            
            return {
                'dialog_id': dialog['id'],
                'response': response,
                'model_name': self.model_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response for dialog {dialog['id']}: {str(e)}")
            raise
            
    def _format_dialog_context(self, dialog: Dict) -> str:
        """Format dialog data as context for the model"""
        # Format dialog data as needed for the model
        # This will depend on your specific requirements
        return f"Dialog: {dialog['name']}\nLast message: {dialog.get('last_message', {}).get('text', '')}"
        
    async def _update_dialog_status(self, dialog_id: str, response: Dict[str, Any]) -> None:
        """Update dialog processing status"""
        conn = await get_raw_connection()
        try:
            await conn.execute(
                """
                UPDATE dialogs
                SET last_processed_at = $1,
                    is_processing_enabled = true
                WHERE id = $2
                """,
                datetime.utcnow(),
                dialog_id
            )
        except Exception as e:
            logger.error(f"Failed to update dialog {dialog_id} status: {str(e)}")
            raise
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
        result = await processor.process_dialog(dialog_id)
        
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
        
    async def get_pending_dialogs(self, limit: int = 10) -> List[Dialog]:
        """Get dialogs that need processing"""
        # Get dialogs that don't have a processing result for this model
        # or have a pending/error status
        subquery = (
            select(ProcessedResponse.dialog_id)
            .where(
                ProcessedResponse.model_name == self.model_name,
                ProcessedResponse.status == ProcessingStatus.COMPLETED
            )
            .scalar_subquery()
        )
        
        stmt = (
            select(Dialog)
            .outerjoin(ProcessedResponse)
            .where(Dialog.id.notin_(subquery))
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
        
    async def get_processing_result(self, dialog_id: str) -> Optional[ProcessedResponse]:
        """Get processing result for a dialog"""
        stmt = (
            select(ProcessedResponse)
            .where(
                ProcessedResponse.dialog_id == dialog_id,
                ProcessedResponse.model_name == self.model_name
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
        
    async def create_processing_result(self, dialog_id: str) -> ProcessedResponse:
        """Create a new processing result entry"""
        result = ProcessedResponse(
            dialog_id=dialog_id,
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