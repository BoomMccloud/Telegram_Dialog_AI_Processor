#!/usr/bin/env python3
"""
Script to initialize the database using SQLAlchemy ORM.

This script will:
1. Create required extensions
2. Create all tables using SQLAlchemy models
3. Add any initial data if needed
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'telegram_dialog_dev'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
}

# SQLAlchemy async engine URL
DATABASE_URL = f"postgresql+asyncpg://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.db.base import Base
from app.models import *  # This imports all our models

async def create_extensions():
    """Create required PostgreSQL extensions"""
    conn = await asyncpg.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database']
    )
    
    try:
        # Create extensions
        await conn.execute("""
            CREATE EXTENSION IF NOT EXISTS pgcrypto;
            CREATE EXTENSION IF NOT EXISTS vector;
        """)
        logger.info("Created extensions: pgcrypto, vector")
    
    finally:
        await conn.close()

async def create_tables():
    """Create all tables using SQLAlchemy models"""
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Created all database tables")
    await engine.dispose()

async def add_initial_data():
    """Add any initial/seed data to the database"""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Add any initial data here if needed
        # For example:
        # admin_user = User(...)
        # session.add(admin_user)
        await session.commit()
    
    await engine.dispose()

async def init_database():
    """Initialize the complete database"""
    logger.info(f"Initializing database: {DB_CONFIG['database']}")
    
    # Create extensions
    await create_extensions()
    
    # Create tables
    await create_tables()
    
    # Add initial data
    # await add_initial_data()  # Uncomment if needed
    
    logger.info("Database initialization completed successfully")

async def main():
    """Main entry point"""
    # Ask for confirmation
    response = input("This will initialize the database. Are you sure? (y/N): ")
    if response.lower() != 'y':
        logger.info("Operation cancelled")
        return
    
    await init_database()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1) 