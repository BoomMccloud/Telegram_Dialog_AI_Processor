"""Manual test to check database connection"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Get database configuration from environment
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "telegram_dialog_dev")

# Database URL
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

async def check_database_connection(session):
    """Check if database connection is healthy"""
    try:
        result = await session.execute(text("SELECT 1"))
        await session.commit()
        print("Database connection is healthy!")
        return True, None
    except Exception as e:
        print(f"Database connection is unhealthy: {str(e)}")
        await session.rollback()
        return False, str(e)

async def main():
    # Create engine and session
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Test database connection
    async with async_session() as session:
        is_healthy, error = await check_database_connection(session)
        print(f"Connection status: {'Healthy' if is_healthy else 'Unhealthy'}")
        if error:
            print(f"Error: {error}")

if __name__ == "__main__":
    asyncio.run(main()) 