import os
import json
import re
import uuid
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any

# Import the raw database connection
from app.db.database import get_raw_connection

logger = logging.getLogger(__name__)

# --------------------------
# Configuration Constants
# --------------------------
MODEL_CONFIGS = {
    "llama3": {
        "model_path": os.getenv("LLAMA_MODEL_PATH", "/path/to/llama-3-8b.gguf"),
        "n_gpu_layers": -1,  # Automatically detect the optimal number of layers
        "n_ctx": 4096, 
        "chat_format": "llama-3",  # Must specify the correct format
        "verbose": False
    },
    # Can be extended with other models
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

DEFAULT_SYSTEM_PROMPT = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
# Role Definition
You are an AI assistant, respond to messages with:

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
3. Never make promises beyond authority<|eot_id|>"""


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

    async def process_dialog(self, dialog_id: int, user_id: int, session_id: str) -> Dict[str, Any]:
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
                "<|eot_id|>"
            ]
            message_history.append("\n".join(message_block))
        
        return (
            prompt +
            "\n".join(message_history) +
            "\n<|start_header_id|>assistant<|end_header_id|>\n"
        )

    async def _generate_response(self, prompt: str) -> str:
        """Generate a response using the language model"""
        try:
            if not self.llm:
                await self.init_model()
                if not self.llm:
                    return "Error: Model not initialized"
            
            # Run in an executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.llm.create_completion(prompt=prompt, **DEFAULT_GENERATION_PARAMS)
            )
            
            response = result['choices'][0]['text'].strip()
            return self._post_process(response)
        
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "Error generating response. Please try again later."

    def _post_process(self, text: str) -> str:
        """Clean up the generated response"""
        # Basic cleaning
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove anything after EOT marker
        if "<|eot_id|>" in text:
            text = text.split("<|eot_id|>")[0].strip()
        
        # Filter obviously invalid content
        invalid_patterns = [
            r'\[\w+\]',  # Filter marked content
            r'\.{3,}',  # Delete ellipsis
            r'\b(n/a|undefined)\b'
        ]
        for p in invalid_patterns:
            text = re.sub(p, '', text)
        
        return text.strip() or "I need more information to provide a helpful response."

    async def _store_processing_result(self, message: Dict, response_text: str, 
                                      context_messages: List[Dict], dialog_id: int, 
                                      user_id: int) -> Dict:
        """Store the processing result in the database"""
        conn = await get_raw_connection()
        try:
            # Generate a new UUID for the response
            response_id = str(uuid.uuid4())
            
            # Prepare context messages JSON
            context_json = json.dumps([
                {
                    "message_id": m.get("message_id", ""),
                    "sender_name": m.get("sender_name", ""),
                    "message_text": m.get("message_text", ""),
                    "message_date": m.get("message_date", "")
                } for m in context_messages
            ])
            
            # Insert into processed_responses table
            result = await conn.fetchrow(
                """
                INSERT INTO processed_responses (
                    response_id,
                    message_id,
                    dialog_id,
                    user_id,
                    response_text,
                    created_at,
                    status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                response_id,
                message.get("message_id", ""),
                dialog_id,
                user_id,
                response_text,
                datetime.utcnow(),
                "pending"
            )
            
            # Insert into processing_results table for compatibility
            await conn.execute(
                """
                INSERT INTO processing_results (
                    result_id,
                    message_id,
                    processed_text,
                    response_text,
                    context_messages,
                    processing_date,
                    auto_reply_sent,
                    user_interaction_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                str(uuid.uuid4()),
                message.get("message_id", ""),
                message.get("message_text", ""),
                response_text,
                context_json,
                datetime.utcnow(),
                False,
                "pending"
            )
            
            # Convert result to dictionary
            result_dict = dict(result)
            
            # Convert datetime objects to strings
            for key, value in result_dict.items():
                if isinstance(value, datetime):
                    result_dict[key] = value.isoformat()
            
            return result_dict
        
        except Exception as e:
            logger.error(f"Failed to store processing result: {str(e)}")
            return {
                "response_id": "error",
                "message_id": message.get("message_id", ""),
                "error": str(e)
            }
        
        finally:
            await conn.close()

    async def _mark_message_processed(self, message_id: str) -> bool:
        """Mark a message as processed"""
        conn = await get_raw_connection()
        try:
            await conn.execute(
                """
                UPDATE message_history
                SET is_processed = true
                WHERE message_id = $1
                """,
                message_id
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to mark message as processed: {str(e)}")
            return False
        
        finally:
            await conn.close()


# --------------------------
# Background Task Functions
# --------------------------
async def process_dialog_queue_item(queue_id: str, session_id: str = None):
    """Process a single item from the processing queue"""
    conn = await get_raw_connection()
    try:
        # Get the queue item
        queue_item = await conn.fetchrow(
            """
            SELECT q.*, m.dialog_id 
            FROM processing_queue q
            JOIN message_history m ON q.message_id = m.message_id
            WHERE q.queue_id = $1
            """,
            queue_id
        )
        
        if not queue_item:
            logger.warning(f"Queue item {queue_id} not found")
            return False
        
        # Mark as started
        await conn.execute(
            """
            UPDATE processing_queue
            SET status = 'processing', started_at = $1
            WHERE queue_id = $2
            """,
            datetime.utcnow(), queue_id
        )
        
        # Get the user ID for this dialog
        dialog_selection = await conn.fetchrow(
            """
            SELECT user_id
            FROM user_selected_dialogs
            WHERE dialog_id = $1 AND is_active = true
            LIMIT 1
            """,
            queue_item["dialog_id"]
        )
        
        if not dialog_selection:
            logger.warning(f"No active dialog selection found for dialog {queue_item['dialog_id']}")
            await conn.execute(
                """
                UPDATE processing_queue
                SET status = 'error', error_message = $1, completed_at = $2
                WHERE queue_id = $3
                """,
                "No active dialog selection found", datetime.utcnow(), queue_id
            )
            return False
        
        # Get the model details from user_selected_models
        user_id = dialog_selection["user_id"]
        model_selection = await conn.fetchrow(
            """
            SELECT model_name, system_prompt
            FROM user_selected_models
            WHERE user_id = $1
            LIMIT 1
            """,
            user_id
        )
        
        # Use default model if none selected
        model_name = model_selection["model_name"] if model_selection else "llama3"
        system_prompt = model_selection["system_prompt"] if model_selection and model_selection["system_prompt"] else DEFAULT_SYSTEM_PROMPT
        
        # Process the message
        processor = DialogProcessor(model_name=model_name, system_prompt=system_prompt)
        result = await processor.process_dialog(
            queue_item["dialog_id"], 
            user_id,
            session_id
        )
        
        # Update queue item status
        if result.get("success", False):
            await conn.execute(
                """
                UPDATE processing_queue
                SET status = 'completed', completed_at = $1
                WHERE queue_id = $2
                """,
                datetime.utcnow(), queue_id
            )
            return True
        else:
            await conn.execute(
                """
                UPDATE processing_queue
                SET status = 'error', error_message = $1, completed_at = $2
                WHERE queue_id = $3
                """,
                result.get("error", "Unknown error"), datetime.utcnow(), queue_id
            )
            return False
    
    except Exception as e:
        logger.error(f"Error processing queue item {queue_id}: {str(e)}")
        try:
            await conn.execute(
                """
                UPDATE processing_queue
                SET status = 'error', error_message = $1, completed_at = $2
                WHERE queue_id = $3
                """,
                str(e), datetime.utcnow(), queue_id
            )
        except:
            pass
        return False
    
    finally:
        await conn.close()


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
    """Get list of available models"""
    # For now, just return the hardcoded models
    models = []
    for model_name, config in MODEL_CONFIGS.items():
        models.append({
            "model_id": model_name,
            "model_name": model_name.capitalize(),
            "description": f"Language model using {model_name} architecture",
            "is_default": model_name == "llama3"
        })
    
    return models


async def select_model_for_user(user_id: int, model_name: str, system_prompt: Optional[str] = None) -> Dict:
    """Set a model as the user's default"""
    conn = await get_raw_connection()
    try:
        # Generate a model ID
        model_id = str(uuid.uuid4())
        
        # Check if model exists in configuration
        if model_name not in MODEL_CONFIGS:
            return {
                "success": False,
                "error": f"Model {model_name} not available"
            }
        
        # Check if user already has a model selected
        existing_model = await conn.fetchrow(
            """
            SELECT model_id, system_prompt FROM user_selected_models
            WHERE user_id = $1
            """,
            user_id
        )
        
        # If system_prompt not provided, keep existing one if available
        if system_prompt is None and existing_model and existing_model["system_prompt"]:
            system_prompt = existing_model["system_prompt"]
        elif system_prompt is None:
            system_prompt = DEFAULT_SYSTEM_PROMPT
        
        if existing_model:
            # Update existing model
            await conn.execute(
                """
                UPDATE user_selected_models
                SET model_name = $1, system_prompt = $2, updated_at = $3
                WHERE user_id = $4
                """,
                model_name, system_prompt, datetime.utcnow(), user_id
            )
            
            model_id = existing_model["model_id"]
        else:
            # Insert new model selection
            await conn.execute(
                """
                INSERT INTO user_selected_models (
                    model_id,
                    user_id,
                    model_name,
                    system_prompt,
                    is_default,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                model_id,
                user_id,
                model_name,
                system_prompt,
                True,
                datetime.utcnow(),
                datetime.utcnow()
            )
        
        return {
            "success": True,
            "user_id": user_id,
            "model_id": model_id,
            "model_name": model_name,
            "system_prompt": system_prompt
        }
    
    except Exception as e:
        logger.error(f"Error selecting model for user {user_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    
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