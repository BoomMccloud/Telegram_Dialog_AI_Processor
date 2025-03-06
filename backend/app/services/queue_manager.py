"""
Queue Manager for Background Message Processing

This module handles the background processing of messages with Claude,
managing a queue of tasks for asynchronous execution.
"""

import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
import logging

from app.db.database import get_raw_connection, get_session
from app.services.claude_processor import ClaudeProcessor
from app.services.model_processor import DialogProcessor
from app.services.dialog_processor import DialogProcessorService
from app.utils.logging import get_logger

logger = get_logger(__name__)

# In-memory queue for tasks
processing_queue: Dict[str, Dict] = {}
# Active tasks currently being processed
active_tasks: Dict[str, asyncio.Task] = {}
# Set of dialog IDs currently being processed
processing_dialogs: Set[str] = set()

# Queue processing settings
MAX_CONCURRENT_TASKS = 5
QUEUE_CHECK_INTERVAL = 10  # seconds
TASK_TIMEOUT = 300  # seconds


async def start_queue_processor():
    """
    Start the background queue processor
    
    This function starts an infinite loop that checks for tasks in the queue
    and processes them asynchronously.
    """
    logger.info("Starting message queue processor")
    while True:
        try:
            # Check if we can start more tasks
            if len(active_tasks) < MAX_CONCURRENT_TASKS and processing_queue:
                # Get the next task from the queue
                queue_id, task_data = next(iter(processing_queue.items()))
                
                # Remove from queue and add to active tasks
                del processing_queue[queue_id]
                
                # Start the task
                task = asyncio.create_task(
                    process_queue_item(queue_id, task_data)
                )
                active_tasks[queue_id] = task
                
                logger.info(f"Started processing task {queue_id} ({len(active_tasks)}/{MAX_CONCURRENT_TASKS} active)")
            
            # Check for completed tasks
            completed_tasks = []
            for task_id, task in active_tasks.items():
                if task.done():
                    completed_tasks.append(task_id)
                    # Get the result or exception
                    try:
                        result = task.result()
                        logger.info(f"Task {task_id} completed successfully: {result}")
                    except Exception as e:
                        logger.error(f"Task {task_id} failed: {str(e)}")
            
            # Remove completed tasks
            for task_id in completed_tasks:
                if task_id in active_tasks:
                    del active_tasks[task_id]
            
            # Wait before checking again
            await asyncio.sleep(QUEUE_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in queue processor: {str(e)}")
            await asyncio.sleep(QUEUE_CHECK_INTERVAL)


async def process_queue_item(task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a queue item
    
    Args:
        task_id: ID of the task
        task_data: Task data containing processing information
        
    Returns:
        Processing result
    """
    try:
        # Check task type
        task_type = task_data.get("type", "message")
        
        if task_type == "dialog":
            # Process dialog messages
            return await process_dialog_task(task_id, task_data)
        else:
            # Default: process individual message
            return await process_message_task(task_id, task_data)
            
    except Exception as e:
        logger.error(f"Error processing queue item {task_id}: {str(e)}")
        return {
            "status": "error",
            "message": f"Error processing queue item: {str(e)}"
        }
        
    finally:
        # Ensure dialog is removed from processing set
        dialog_id = task_data.get("dialog_id")
        if dialog_id and dialog_id in processing_dialogs:
            processing_dialogs.remove(dialog_id)


async def process_dialog_task(task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a dialog task
    
    Args:
        task_id: ID of the task
        task_data: Task data containing dialog processing information
        
    Returns:
        Processing result
    """
    try:
        dialog_id = task_data.get("dialog_id")
        model_name = task_data.get("model_name", "claude-3-sonnet")
        
        if not dialog_id:
            return {
                "status": "error",
                "message": "No dialog ID provided"
            }
            
        # Mark dialog as being processed
        processing_dialogs.add(dialog_id)
        
        # Get database session
        async with get_session() as db:
            # Create dialog processor service
            dialog_processor = DialogProcessorService(db)
            
            # Process dialog
            result = await dialog_processor.process_dialog(dialog_id, model_name)
            
            return {
                "status": "success",
                "task_id": task_id,
                "dialog_id": dialog_id,
                "result": result
            }
            
    except Exception as e:
        logger.error(f"Error processing dialog task {task_id}: {str(e)}")
        return {
            "status": "error",
            "task_id": task_id,
            "dialog_id": dialog_id if 'dialog_id' in locals() else None,
            "message": f"Error processing dialog: {str(e)}"
        }


async def process_message_task(task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a message task
    
    Args:
        task_id: ID of the task
        task_data: Task data containing message processing information
        
    Returns:
        Processing result
    """
    # Implementation for processing individual messages
    # This can be filled in as needed
    return {
        "status": "error",
        "message": "Message processing not implemented"
    }


def add_task_to_queue(task_data: Dict[str, Any]) -> str:
    """
    Add a task to the processing queue
    
    Args:
        task_data: Task data containing processing information
        
    Returns:
        Task ID
    """
    # Generate task ID if not provided
    task_id = task_data.get("task_id", str(uuid.uuid4()))
    
    # Add timestamp if not provided
    if "timestamp" not in task_data:
        task_data["timestamp"] = datetime.now().isoformat()
        
    # Store task in queue
    processing_queue[task_id] = task_data
    
    # If it's a dialog task, track the dialog ID
    if task_data.get("type") == "dialog" and "dialog_id" in task_data:
        dialog_id = task_data["dialog_id"]
        logger.info(f"Added dialog {dialog_id} to processing queue with task ID {task_id}")
    
    return task_id


def get_queue_status() -> Dict[str, Any]:
    """
    Get the current status of the processing queue
    
    Returns:
        Dict with queue status information
    """
    return {
        "queue_size": len(processing_queue),
        "active_tasks": len(active_tasks),
        "processing_dialogs": list(processing_dialogs),
        "queue_items": list(processing_queue.keys()),
        "active_items": list(active_tasks.keys()),
        "max_concurrent_tasks": MAX_CONCURRENT_TASKS
    }


def clear_queue() -> Dict[str, Any]:
    """
    Clear the processing queue
    
    Returns:
        Dict with status information
    """
    queue_size = len(processing_queue)
    processing_queue.clear()
    
    return {
        "status": "success",
        "message": f"Cleared {queue_size} items from the processing queue"
    } 