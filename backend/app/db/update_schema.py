"""
Script to update database schema
"""

import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.utils.logging import get_logger
from app.db.models.base import Base
from app.db.models.user import User
from app.db.models.session import Session
from app.db.models.dialog import Dialog
from app.db.models.authentication_data import AuthenticationData

logger = get_logger(__name__)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "telegram_dialog_dev"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
}

# Construct database URL
DATABASE_URL = f"postgresql+asyncpg://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

async def update_schema():
    """Update database schema"""
    try:
        logger.info("Creating async engine...")
        engine = create_async_engine(DATABASE_URL)

        logger.info("Updating database schema...")
        async with engine.begin() as conn:
            # First ensure pgcrypto extension exists
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
            
            # Update schema
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Schema update completed successfully")
        
    except Exception as e:
        logger.error(f"Error updating schema: {str(e)}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    logger.info("Starting schema update...")
    asyncio.run(update_schema()) 