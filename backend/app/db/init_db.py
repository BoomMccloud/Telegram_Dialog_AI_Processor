"""
Database initialization and migration management.
"""

import os
import sys
import asyncio
import logging
import re
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from app.utils.logging import get_logger
from app.db.database import engine, async_session
from app.db.models.base import Base

logger = get_logger(__name__)

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

# Log database configuration
logger.info("Database configuration for initialization:")
logger.info(f"Host: {os.getenv('POSTGRES_HOST', 'localhost')}")
logger.info(f"Port: {os.getenv('POSTGRES_PORT', '5432')}")
logger.info(f"Database: {os.getenv('POSTGRES_DB', 'telegram_dialog_dev')}")
logger.info(f"User: {os.getenv('POSTGRES_USER', 'postgres')}")

def split_sql_statements(sql: str) -> list[str]:
    """Split SQL into individual statements, preserving DO blocks"""
    statements = []
    current_stmt = []
    in_do_block = False
    
    for line in sql.split('\n'):
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('--'):
            continue
            
        # Check for DO block start
        if 'DO $$' in stripped:
            in_do_block = True
            
        current_stmt.append(line)
        
        # Check for DO block end
        if in_do_block and '$$;' in stripped:
            in_do_block = False
            statements.append('\n'.join(current_stmt))
            current_stmt = []
            continue
            
        # Normal statement end
        if not in_do_block and stripped.endswith(';'):
            statements.append('\n'.join(current_stmt))
            current_stmt = []
            
    # Add any remaining statement
    if current_stmt:
        statements.append('\n'.join(current_stmt))
        
    return [stmt.strip() for stmt in statements if stmt.strip()]

async def init_db() -> None:
    """Initialize database with all models and run migrations"""
    try:
        # Create all tables using the engine
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
            await conn.run_sync(Base.metadata.create_all)
            
        # Run migrations using a session
        async with async_session() as db:
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
            
        # Create migrations table if it doesn't exist
        async with db.begin():
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    name VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """))
            
        # Get applied migrations
        async with db.begin():
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
            
            # Read migration file
            sql = migration_file.read_text()
            
            # Split into individual statements
            statements = split_sql_statements(sql)
            
            # Execute each statement in a separate transaction
            for stmt in statements:
                logger.debug(f"Executing statement:\n{stmt}")
                async with db.begin():
                    await db.execute(text(stmt))
            
            # Record migration
            async with db.begin():
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
        asyncio.run(init_db())
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        sys.exit(1) 