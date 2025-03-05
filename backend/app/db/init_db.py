"""
Database initialization and migration management.
"""

import os
import logging
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.base import Base
from app.utils.logging import get_logger

logger = get_logger(__name__)

async def init_db(db: AsyncSession) -> None:
    """Initialize database with all models and run migrations"""
    try:
        # Create all tables
        async with db.begin():
            await db.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
            await db.run_sync(Base.metadata.create_all)
            
        # Run migrations
        await run_migrations(db)
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

async def run_migrations(db: AsyncSession) -> None:
    """Run SQL migrations from the migrations directory"""
    try:
        # Get migrations directory
        migrations_dir = Path(__file__).parent / "migrations"
        if not migrations_dir.exists():
            logger.warning("No migrations directory found")
            return
            
        # Get applied migrations
        result = await db.execute(text("SELECT name FROM migrations"))
        applied = {row[0] for row in result.fetchall()}
        
        # Get migration files
        migration_files = sorted([
            f for f in migrations_dir.glob("*.sql")
            if f.stem not in applied
        ])
        
        if not migration_files:
            logger.info("No new migrations to apply")
            return
            
        # Apply migrations in order
        for migration_file in migration_files:
            logger.info(f"Applying migration: {migration_file.name}")
            
            # Read and execute migration
            sql = migration_file.read_text()
            async with db.begin():
                await db.execute(text(sql))
                
                # Record migration
                await db.execute(
                    text("INSERT INTO migrations (name) VALUES (:name)"),
                    {"name": migration_file.stem}
                )
            
            logger.info(f"Applied migration: {migration_file.name}")
            
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    try:
        asyncio.run(init_db(get_db()))
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        sys.exit(1) 