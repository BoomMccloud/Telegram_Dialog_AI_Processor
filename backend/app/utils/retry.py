"""
Retry utility for handling API call retries
"""

import asyncio
import logging
from typing import TypeVar, Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    Decorator for retrying async functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
        on_retry: Optional callback function called on each retry
        
    Returns:
        Decorated function that implements retry logic
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        if on_retry:
                            on_retry(e, attempt + 1)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                            f"Retrying in {current_delay:.2f} seconds..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed. Last error: {str(e)}"
                        )
                        raise last_exception
                        
            raise last_exception
            
        return wrapper
    return decorator 