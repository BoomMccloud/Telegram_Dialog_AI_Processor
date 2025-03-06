"""Database utility functions for connection management and health checks"""

import asyncio
import time
from typing import Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from app.utils.logging import get_logger
from app.core.exceptions import DatabaseError

logger = get_logger(__name__)

async def check_database_connection(session: AsyncSession) -> Tuple[bool, Optional[str]]:
    """
    Check database connection by executing a simple query
    
    Args:
        session: SQLAlchemy async session
        
    Returns:
        Tuple of (is_healthy: bool, error_message: Optional[str])
    """
    try:
        # Execute simple query with timeout
        result = await asyncio.wait_for(
            session.execute(text("SELECT 1")),
            timeout=5.0
        )
        await session.commit()
        return True, None
    except asyncio.TimeoutError:
        msg = "Database health check timed out after 5 seconds"
        logger.error(msg)
        await session.rollback()
        return False, msg
    except Exception as e:
        msg = f"Database health check failed: {str(e)}"
        logger.error(msg, exc_info=True)
        await session.rollback()
        return False, msg

async def retry_database_operation(operation: Any, max_retries: int = 3, initial_delay: float = 1.0) -> Any:
    """
    Retry a database operation with exponential backoff
    
    Args:
        operation: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        
    Returns:
        Result of the operation
        
    Raises:
        DatabaseError: If all retries fail
    """
    last_error = None
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.warning(f"Retrying database operation (attempt {attempt}/{max_retries})")
            return await operation()
            
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                # Log the error but continue with retry
                logger.warning(
                    f"Database operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}",
                    exc_info=True
                )
                # Wait with exponential backoff
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                # Log the final failure
                logger.error(
                    f"Database operation failed after {max_retries} retries: {str(e)}",
                    exc_info=True
                )
                raise DatabaseError(
                    f"Database operation failed after {max_retries} retries",
                    details={"error": str(e), "last_attempt": attempt}
                ) from last_error

async def get_database_metrics() -> dict:
    """
    Get database metrics for monitoring
    
    Returns:
        Dict containing database metrics
    """
    # This is a placeholder for future metrics collection
    return {
        "last_check_time": time.time(),
        "status": "connected",
        # Add more metrics as needed
    } 