#!/usr/bin/env python3
"""
Script to drop all tables in the database.

This script will:
1. Connect to the database
2. Drop all tables in reverse order of dependencies
3. Drop all custom types (enums)
4. Drop extensions if specified
"""

import asyncio
import sys
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration from environment variables with defaults
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'telegram_dialog_dev'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
}

async def get_connection():
    """Get a database connection"""
    import asyncpg
    return await asyncpg.connect(**DB_CONFIG)

async def drop_all_tables(drop_extensions: bool = False):
    """Drop all tables and types from the database"""
    conn = await get_connection()
    try:
        # Start a transaction
        async with conn.transaction():
            # Drop tables in reverse order of dependencies
            logger.info("Dropping tables...")
            await conn.execute("""
                DROP TABLE IF EXISTS 
                    migrations,
                    user_selected_models,
                    processed_responses,
                    authentication_data,
                    sessions,
                    dialogs,
                    users
                CASCADE;
            """)
            
            # Drop custom types
            logger.info("Dropping custom types...")
            await conn.execute("""
                DROP TYPE IF EXISTS 
                    sessionstatus,
                    tokentype,
                    dialogtype,
                    processingstatus
                CASCADE;
            """)
            
            # Optionally drop extensions
            if drop_extensions:
                logger.info("Dropping extensions...")
                await conn.execute("""
                    DROP EXTENSION IF EXISTS pgcrypto CASCADE;
                    DROP EXTENSION IF EXISTS vector CASCADE;
                """)
            
            logger.info("Successfully dropped all database objects")
    
    except Exception as e:
        logger.error(f"Error dropping database objects: {e}")
        raise
    
    finally:
        await conn.close()

async def main():
    """Main entry point"""
    logger.info(f"Using database: {DB_CONFIG['database']} on {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    # Ask for confirmation
    response = input("Are you sure you want to drop all tables? This action cannot be undone! (y/N): ")
    if response.lower() != 'y':
        logger.info("Operation cancelled")
        return
    
    # Ask about extensions
    drop_exts = input("Do you also want to drop extensions (pgcrypto, vector)? (y/N): ")
    drop_extensions = drop_exts.lower() == 'y'
    
    await drop_all_tables(drop_extensions)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1) 