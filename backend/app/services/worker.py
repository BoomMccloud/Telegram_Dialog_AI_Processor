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
from app.db.models.user import User
from app.db.models.session import Session
from app.services.dialog_processor import DialogProcessor
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
    
    async def process_dialogs(self, dialogs: list):
        """
        Process a list of dialogs
        
        Args:
            dialogs: List of dialogs to process
        """
        async with async_session() as session:
            try:
                # Create dialog processor
                processor = DialogProcessor(session)
                
                # Group dialogs by user to process them efficiently
                dialogs_by_user = {}
                for dialog in dialogs:
                    if dialog.user_id not in dialogs_by_user:
                        dialogs_by_user[dialog.user_id] = []
                    dialogs_by_user[dialog.user_id].append(dialog)
                
                # Process dialogs for each user
                total_success_count = 0
                for user_id, user_dialogs in dialogs_by_user.items():
                    # Get user
                    user_query = select(User).where(User.id == user_id)
                    user_result = await session.execute(user_query)
                    user = user_result.scalar_one_or_none()
                    
                    if not user:
                        logger.error(f"User not found for ID {user_id}")
                        continue
                    
                    # Get user's active session token
                    session_query = select(Session).where(
                        Session.user_id == user_id
                    ).order_by(Session.last_activity.desc())
                    session_result = await session.execute(session_query)
                    user_session = session_result.scalar_one_or_none()
                    
                    if not user_session or not user_session.token:
                        logger.error(f"No valid session token found for user {user_id}")
                        continue
                        
                    # Process dialogs for this user
                    results = await processor.process_dialogs(user_dialogs, user_session.token)
                    
                    # Log results
                    success_count = sum(1 for success in results.values() if success)
                    total_success_count += success_count
                    logger.info(
                        f"Processed {success_count}/{len(results)} dialogs successfully "
                        f"for user {user_id}"
                    )
                
                return total_success_count
                    
            except Exception as e:
                logger.error(f"Error processing dialogs: {str(e)}", exc_info=True)
                return 0
    
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
                
                # Get dialogs to process
                dialogs = await self.get_processing_enabled_dialogs()
                
                if dialogs:
                    # Process the dialogs
                    success_count = await self.process_dialogs(dialogs)
                    logger.info(f"Processed {success_count} dialogs successfully")
                else:
                    logger.info("No dialogs to process")
                
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
    worker = DialogWorker(interval_seconds=600)  # Run every 10 minutes
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