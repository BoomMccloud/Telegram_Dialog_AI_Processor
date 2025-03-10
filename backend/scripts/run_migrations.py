#!/usr/bin/env python3
"""
Script to run database migrations using Alembic.
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
from alembic.config import Config
from alembic import command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run all pending database migrations"""
    try:
        # Get the directory containing this script
        current_dir = Path(__file__).resolve().parent
        backend_dir = current_dir.parent
        
        # Add the backend directory to Python path
        sys.path.append(str(backend_dir))
        
        # Load environment variables from .env file if it exists
        env_path = backend_dir / '.env'
        if env_path.exists():
            from dotenv import load_dotenv
            load_dotenv(env_path)
        
        logger.info("Starting database migration...")
        
        # Get Alembic configuration
        alembic_cfg = Config(str(backend_dir / "alembic.ini"))
        
        # Override sqlalchemy.url in config to use Docker container
        alembic_cfg.set_main_option(
            "sqlalchemy.url",
            "postgresql://postgres:postgres@telegram-dialog-processor-db:5432/telegram_dialog_dev"
        )
        
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations() 