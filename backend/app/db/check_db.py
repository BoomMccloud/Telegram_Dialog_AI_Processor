"""
Simple script to test database connectivity
"""

import asyncio
import os
from app.utils.logging import get_logger
import asyncpg
from dotenv import load_dotenv

logger = get_logger(__name__)

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

async def test_connection():
    """Test database connection with the current configuration"""
    # Log environment variables
    logger.info("Database configuration:")
    logger.info(f"Host: {os.getenv('POSTGRES_HOST', 'localhost')}")
    logger.info(f"Port: {os.getenv('POSTGRES_PORT', '5432')}")
    logger.info(f"Database: {os.getenv('POSTGRES_DB', 'telegram_dialog_dev')}")
    logger.info(f"User: {os.getenv('POSTGRES_USER', 'postgres')}")
    
    try:
        # Try to connect
        conn = await asyncpg.connect(
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "telegram_dialog_dev")
        )
        
        # Test the connection
        version = await conn.fetchval("SELECT version();")
        logger.info(f"Successfully connected to database. PostgreSQL version: {version}")
        
        # List all databases
        databases = await conn.fetch("SELECT datname FROM pg_database;")
        logger.info("Available databases:")
        for db in databases:
            logger.info(f"  - {db['datname']}")
            
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection()) 