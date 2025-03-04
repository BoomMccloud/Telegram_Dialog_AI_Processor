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

from app.db.database import get_raw_connection
from app.services.claude_processor import ClaudeProcessor
from app.services.model_processor import DialogProcessor
from app.utils.logging import get_logger

logger = get_logger(__name__)

# In-memory queue for tasks
processing_queue: Dict[str, Dict] = {}
# Active tasks currently being processed
active_tasks: Dict[str, asyncio.Task] = {}
# Set of dialog IDs currently being processed
processing_dialogs: Set[int] = set()

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