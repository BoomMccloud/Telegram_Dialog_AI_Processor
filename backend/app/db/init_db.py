"""
Database initialization and migration utilities
"""

import asyncio
import logging
import sys
from pathlib import Path

from .database import get_raw_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def wait_for_postgres(max_retries=10, retry_interval=5):
    """
    Wait for PostgreSQL to be ready
    """
    for i in range(max_retries):
        try:
            logger.info(f"Attempting to connect to PostgreSQL (attempt {i+1}/{max_retries})...")
            conn = await get_raw_connection()
            await conn.close()
            logger.info("Successfully connected to PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            if i < max_retries - 1:
                logger.info(f"Retrying in {retry_interval} seconds...")
                await asyncio.sleep(retry_interval)
            else:
                logger.error("Max retries reached. Could not connect to PostgreSQL.")
                return False

async def run_migrations():
    """Run all pending database migrations"""
    try:
        # First wait for PostgreSQL to be ready
        if not await wait_for_postgres():
            raise Exception("Could not connect to PostgreSQL")

        conn = await get_raw_connection()
        try:
            # Create migrations table if it doesn't exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            
            # Get list of applied migrations
            applied = await conn.fetch("SELECT name FROM migrations")
            applied_names = {row['name'] for row in applied}
            
            # Get all migration files
            migrations_dir = Path(__file__).parent / 'migrations'
            migration_files = sorted([f for f in migrations_dir.glob('*.sql')])
            
            # Apply each migration that hasn't been applied yet
            for migration_file in migration_files:
                name = migration_file.name
                if name not in applied_names:
                    logger.info(f"Applying migration: {name}")
                    
                    # Read and execute migration
                    with open(migration_file) as f:
                        sql = f.read()
                        await conn.execute(sql)
                    
                    # Record migration as applied
                    await conn.execute(
                        "INSERT INTO migrations (name) VALUES ($1)",
                        name
                    )
                    logger.info(f"Successfully applied migration: {name}")
            
            logger.info("All migrations applied successfully")
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    try:
        asyncio.run(run_migrations())
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        sys.exit(1) 