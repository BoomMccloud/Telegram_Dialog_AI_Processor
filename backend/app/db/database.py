"""Database connection utilities"""

import os
from typing import AsyncGenerator
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.utils.logging import get_logger
from app.core.exceptions import DatabaseError

logger = get_logger(__name__)

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

# Log database configuration
logger.info("Database configuration:")
logger.info(f"Host: {os.getenv('POSTGRES_HOST', 'localhost')}")
logger.info(f"Port: {os.getenv('POSTGRES_PORT', '5432')}")
logger.info(f"Database: {os.getenv('POSTGRES_DB', 'telegram_dialog_dev')}")
logger.info(f"User: {os.getenv('POSTGRES_USER', 'postgres')}")

# Use environment variables with defaults
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql+asyncpg://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'telegram_dialog_dev')}")

logger.info(f"Database URL: {DATABASE_URL}")

# Create async engine
engine = create_async_engine(DATABASE_URL)

# Create session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with async context management
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        DatabaseError: If database connection fails
    """
    try:
        async with async_session() as session:
            yield session
    except Exception as e:
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to get database session", details={"error": str(e)})

async def get_raw_connection() -> asyncpg.Connection:
    """Get raw asyncpg connection for migrations and direct queries"""
    conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "telegram_dialog_dev")
    )
    return conn

async def get_raw_pool() -> asyncpg.Pool:
    """Get connection pool for asyncpg"""
    pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "telegram_dialog_dev"),
        min_size=1,
        max_size=10
    )
    return pool

# Create a connection pool for better performance
_pool = None

async def get_db_pool():
    """
    Get database connection pool
    
    Returns:
        asyncpg.Pool: Database connection pool
        
    Raises:
        DatabaseError: If pool creation fails
    """
    try:
        # Parse connection parameters from DATABASE_URL
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        database = os.getenv("POSTGRES_DB", "telegram_dialog_dev")
        
        # Create connection pool
        pool = await asyncpg.create_pool(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            min_size=5,
            max_size=20
        )
        
        if not pool:
            raise DatabaseError("Failed to create database pool")
            
        return pool
        
    except asyncpg.PostgresError as e:
        logger.error(f"PostgreSQL error: {str(e)}", exc_info=True)
        raise DatabaseError("PostgreSQL connection error", details={"error": str(e)})
    except Exception as e:
        logger.error(f"Database pool error: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to create database pool", details={"error": str(e)})

async def get_db_conn():
    """
    Get a database connection from the pool with async context management
    
    Returns:
        asyncpg.Connection: Database connection
        
    Raises:
        DatabaseError: If connection acquisition fails
    """
    logger.debug("Acquiring connection from pool")
    try:
        pool = await get_db_pool()
        return pool.acquire()
    except Exception as e:
        logger.error(f"Error acquiring database connection: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to acquire database connection", details={"error": str(e)}) 