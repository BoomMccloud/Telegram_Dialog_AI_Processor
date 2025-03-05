import os
import pytest
import asyncio
from typing import AsyncGenerator
import asyncpg
import pytest_asyncio

# Test database configuration
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_telegram_dialog")

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def db_pool(event_loop):
    """Create a test database and pool."""
    # Create test database
    sys_conn = await asyncpg.connect(
        "postgresql://postgres:postgres@localhost:5432/postgres",
        loop=event_loop
    )
    
    try:
        await sys_conn.execute(
            f'DROP DATABASE IF EXISTS {TEST_DATABASE_URL.split("/")[-1]}'
        )
        await sys_conn.execute(
            f'CREATE DATABASE {TEST_DATABASE_URL.split("/")[-1]}'
        )
    finally:
        await sys_conn.close()
    
    # Create pool
    pool = await asyncpg.create_pool(TEST_DATABASE_URL, loop=event_loop)
    
    # Run migrations
    async with pool.acquire() as conn:
        # Create sessions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                telegram_id INTEGER,
                status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'authenticated', 'error', 'expired')),
                token VARCHAR(500) NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)
    
    yield pool
    
    # Cleanup
    await pool.close()
    
    # Drop test database
    sys_conn = await asyncpg.connect(
        "postgresql://postgres:postgres@localhost:5432/postgres",
        loop=event_loop
    )
    try:
        await sys_conn.execute(
            f'DROP DATABASE IF EXISTS {TEST_DATABASE_URL.split("/")[-1]}'
        )
    finally:
        await sys_conn.close()

@pytest_asyncio.fixture
async def db(db_pool, event_loop):
    """Get a database connection for each test."""
    async with db_pool.acquire() as conn:
        # Start transaction
        tr = conn.transaction()
        await tr.start()
        
        yield conn
        
        # Rollback transaction
        await tr.rollback() 