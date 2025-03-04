"""
Logging utility module for the application.

This module provides consistent logging configuration across the application.
"""

import logging
import os
from typing import Optional

def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger with consistent formatting and the specified log level.
    
    Args:
        name: Name of the logger (typically __name__)
        level: Optional logging level (defaults to INFO or value from env var)
        
    Returns:
        Configured logger instance
    """
    # Get log level from environment or default to INFO
    default_level = os.getenv("LOG_LEVEL", "INFO")
    log_level = level or getattr(logging, default_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Only add handler if logger doesn't have handlers
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add formatter to handler
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
    
    return logger 