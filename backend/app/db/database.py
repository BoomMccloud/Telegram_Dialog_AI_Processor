import os
from typing import AsyncGenerator
import logging

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Get database connection parameters from environment variables
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "telegram_dialog")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_raw_connection():
    """
    Get a raw asyncpg connection for direct SQL execution
    """
    logger.debug(f"Creating raw database connection to {DB_HOST}:{DB_PORT}/{DB_NAME}")
    return await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT
    )

# Create a connection pool for better performance
_pool = None

async def get_db_pool():
    """Get or create the database connection pool"""
    global _pool
    if _pool is None:
        logger.info(f"Creating database connection pool to {DB_HOST}:{DB_PORT}/{DB_NAME}")
        try:
            _pool = await asyncpg.create_pool(
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                host=DB_HOST,
                port=DB_PORT,
                min_size=1,
                max_size=10
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Error creating database connection pool: {str(e)}", exc_info=True)
            raise
    return _pool

async def get_db_conn():
    """
    Get a database connection from the pool with async context management
    
    Usage:
        async with get_db_conn() as conn:
            await conn.fetch("SELECT * FROM table")
    """
    logger.debug("Acquiring connection from pool")
    try:
        pool = await get_db_pool()
        return pool.acquire()
    except Exception as e:
        logger.error(f"Error acquiring database connection: {str(e)}", exc_info=True)
        raise 