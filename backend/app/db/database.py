"""Database connection utilities"""

import os
from typing import AsyncGenerator
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Use environment variables with defaults
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql+asyncpg://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'postgres')}")

# Create async engine
engine = create_async_engine(DATABASE_URL)

# Create session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_raw_connection() -> asyncpg.Connection:
    """Get raw asyncpg connection for migrations and direct queries"""
    conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "postgres")
    )
    return conn

async def get_raw_pool() -> asyncpg.Pool:
    """Get connection pool for asyncpg"""
    pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "postgres"),
        min_size=1,
        max_size=10
    )
    return pool

# Create a connection pool for better performance
_pool = None

async def get_db_pool():
    """Get or create the database connection pool"""
    global _pool
    if _pool is None:
        logger.info(f"Creating database connection pool to {DATABASE_URL}")
        try:
            _pool = await asyncpg.create_pool(
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                database=os.getenv("POSTGRES_DB", "telegram_dialog"),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
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