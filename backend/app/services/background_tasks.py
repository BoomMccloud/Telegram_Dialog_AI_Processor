"""
Background task manager for handling async tasks
"""

import asyncio
from typing import Set, Coroutine, Any
from ..utils.logging import get_logger

logger = get_logger(__name__)

class BackgroundTaskManager:
    """Manages background tasks in the FastAPI application"""
    
    def __init__(self):
        """Initialize the task manager"""
        self._tasks: Set[asyncio.Task] = set()
        
    def add_task(self, coro: Coroutine) -> asyncio.Task:
        """
        Add a new background task
        
        Args:
            coro: Coroutine to run in the background
            
        Returns:
            Created task
        """
        task = asyncio.create_task(self._run_and_cleanup(coro))
        self._tasks.add(task)
        return task
        
    async def cleanup(self):
        """Clean up all running tasks"""
        if not self._tasks:
            return
            
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                
        # Wait for all tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
    async def _run_and_cleanup(self, coro: Coroutine) -> Any:
        """
        Run a coroutine and clean up the task when done
        
        Args:
            coro: Coroutine to run
            
        Returns:
            Result of the coroutine
        """
        task = asyncio.current_task()
        try:
            return await coro
        except asyncio.CancelledError:
            logger.info(f"Task {task.get_name()} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in background task {task.get_name()}: {str(e)}", exc_info=True)
            raise
        finally:
            self._tasks.discard(task) 