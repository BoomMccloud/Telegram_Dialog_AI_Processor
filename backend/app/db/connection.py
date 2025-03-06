"""Database connection utilities"""

import os
from typing import AsyncGenerator
import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import make_url
from dotenv import load_dotenv
from app.utils.logging import get_logger
from app.core.exceptions import DatabaseError
from .utils import retry_database_operation, check_database_connection

logger = get_logger(__name__)

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "telegram_dialog_dev"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    # Timeouts in seconds
    "command_timeout": float(os.getenv("DB_COMMAND_TIMEOUT", "30.0")),
    "statement_timeout": int(os.getenv("DB_STATEMENT_TIMEOUT", "30000")),  # milliseconds
    "connect_timeout": float(os.getenv("DB_CONNECT_TIMEOUT", "10.0")),
}

# Log database configuration (excluding sensitive info)
logger.info("Database configuration:")
logger.info(f"Host: {DB_CONFIG['host']}")
logger.info(f"Port: {DB_CONFIG['port']}")
logger.info(f"Database: {DB_CONFIG['database']}")
logger.info(f"User: {DB_CONFIG['user']}")
logger.info(f"Command timeout: {DB_CONFIG['command_timeout']}s")
logger.info(f"Statement timeout: {DB_CONFIG['statement_timeout']}ms")
logger.info(f"Connect timeout: {DB_CONFIG['connect_timeout']}s")

# Construct database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Create async engine with timeouts
engine = create_async_engine(
    DATABASE_URL,
    # Query execution timeout
    connect_args={
        "command_timeout": DB_CONFIG["command_timeout"],
        "timeout": DB_CONFIG["connect_timeout"],
    }
)

# Create session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with async context management and retry mechanism
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        DatabaseError: If database connection fails after retries
    """
    async def _get_session():
        async with async_session() as session:
            # Verify connection is working
            is_healthy, error = await check_database_connection(session)
            if not is_healthy:
                raise DatabaseError(f"Database health check failed: {error}")
            return session

    try:
        # Retry session creation if needed
        session = await retry_database_operation(_get_session)
        try:
            yield session
        finally:
            await session.close()
    except Exception as e:
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to get database session", details={"error": str(e)})

async def get_raw_connection() -> asyncpg.Connection:
    """Get raw asyncpg connection with retry mechanism"""
    async def _connect():
        return await asyncpg.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            timeout=DB_CONFIG["connect_timeout"],
            command_timeout=DB_CONFIG["command_timeout"]
        )

    try:
        return await retry_database_operation(_connect)
    except Exception as e:
        logger.error(f"Failed to get raw connection: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to get raw database connection", details={"error": str(e)})

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