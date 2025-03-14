"""
Background worker for processing Telegram dialogs.

This module implements a standalone worker that periodically checks
the database for user-selected dialogs and processes them.
"""

import asyncio
import os
import datetime
import time
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.db.models.dialog import Dialog
from app.utils.logging import get_logger

# Configure main logger
logger = get_logger(__name__)

# Configure file logger
log_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "logs"
log_dir.mkdir(exist_ok=True)

file_handler = RotatingFileHandler(
    log_dir / "worker.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5
)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(file_handler)

# Global flag for graceful shutdown
should_exit = False

class DialogWorker:
    """Worker process for dialog processing"""
    
    def __init__(self, interval_seconds=60):
        """
        Initialize the worker
        
        Args:
            interval_seconds: Interval between processing cycles in seconds
        """
        self.interval_seconds = interval_seconds
        self.processing_lock = asyncio.Lock()
        self.last_run_time = None
        logger.info(f"Worker initialized with {interval_seconds}s interval")
        
    async def get_processing_enabled_dialogs(self) -> list:
        """
        Get all dialogs where processing is enabled
        
        Returns:
            List of dialogs with processing enabled
        """
        async with async_session() as session:
            try:
                # Query for dialogs with processing enabled
                query = select(Dialog).where(Dialog.is_processing_enabled == True)
                result = await session.execute(query)
                dialogs = result.scalars().all()
                
                # Count query
                count_query = select(func.count()).select_from(Dialog).where(
                    Dialog.is_processing_enabled == True
                )
                count_result = await session.execute(count_query)
                count = count_result.scalar()
                
                logger.info(f"Found {count} dialogs with processing enabled")
                return dialogs
            except Exception as e:
                logger.error(f"Error fetching processing-enabled dialogs: {str(e)}", exc_info=True)
                return []
    
    async def log_dialog_count(self):
        """
        Log the count of processing-enabled dialogs to a file
        """
        try:
            # Get current timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get dialog count
            dialogs = await self.get_processing_enabled_dialogs()
            dialog_count = len(dialogs)
            
            # Format message
            message = f"{timestamp} - Found {dialog_count} dialogs with processing enabled\n"
            
            # Log to file
            count_log_path = log_dir / "dialog_count.log"
            with open(count_log_path, "a") as f:
                f.write(message)
                
            logger.info(f"Logged dialog count ({dialog_count}) to {count_log_path}")
            
            # Also log some details about the dialogs
            if dialog_count > 0:
                for i, dialog in enumerate(dialogs[:5]):  # Limit to first 5 for brevity
                    # Use dialog_metadata property if available, otherwise display empty dict
                    metadata_str = getattr(dialog, 'dialog_metadata', {}) or {}
                    
                    # Log info about unread_count and last_message
                    unread_count = getattr(dialog, 'unread_count', 0) or 0
                    last_message_info = "No messages" if not getattr(dialog, 'last_message', None) else "Has last message"
                    
                    logger.info(f"Dialog {i+1}: ID={dialog.id}, Title={dialog.title}, "
                               f"Type={dialog.type}, Unread={unread_count}, "
                               f"Last processed: {dialog.last_processed_at}, "
                               f"Metadata: {metadata_str}")
                
                if dialog_count > 5:
                    logger.info(f"... and {dialog_count - 5} more dialogs")
                    
        except Exception as e:
            logger.error(f"Error logging dialog count: {str(e)}", exc_info=True)
    
    async def run_once(self):
        """
        Run a single processing cycle
        """
        # Use a lock to prevent concurrent execution
        if self.processing_lock.locked():
            logger.warning("Previous processing cycle still running, skipping")
            return
            
        async with self.processing_lock:
            try:
                logger.info("Starting processing cycle")
                self.last_run_time = datetime.datetime.now()
                
                # Perform the main worker tasks
                await self.log_dialog_count()
                
                # Later phases will add more processing logic here
                
                cycle_time = (datetime.datetime.now() - self.last_run_time).total_seconds()
                logger.info(f"Processing cycle completed in {cycle_time:.2f} seconds")
            except Exception as e:
                logger.error(f"Error in processing cycle: {str(e)}", exc_info=True)
    
    async def run_forever(self):
        """
        Run the worker in an infinite loop until signaled to stop
        """
        logger.info("Starting worker process")
        
        while not should_exit:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"Unexpected error in worker cycle: {str(e)}", exc_info=True)
                
            # Sleep until next interval
            for _ in range(int(self.interval_seconds)):
                if should_exit:
                    break
                await asyncio.sleep(1)
                
        logger.info("Worker process shutting down")

def handle_signal(sig, frame):
    """
    Handle termination signals
    """
    global should_exit
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    should_exit = True

async def main():
    """
    Main entry point for the worker
    """
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Create and run worker
    worker = DialogWorker(interval_seconds=60)  # Run every minute for testing
    await worker.run_forever()

if __name__ == "__main__":
    try:
        # Run the main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker terminated by keyboard interrupt")
    except Exception as e:
        logger.error(f"Unhandled exception in worker: {str(e)}", exc_info=True)
        sys.exit(1)
    sys.exit(0) 