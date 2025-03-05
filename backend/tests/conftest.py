"""
Test configuration and fixtures
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator
import asyncpg
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
from httpx import AsyncClient

from app.main import app
from app.db.base import Base
from app.services.session_manager import SessionManager
from app.services.background_tasks import BackgroundTaskManager

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_processor_test"

# Test settings
test_settings = {
    "jwt_secret": "test-secret-key-for-testing-only",
    "access_token_expire_minutes": 60,
    "refresh_token_expire_minutes": 10080
}

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Clean up old tables
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(engine):
    """Create database session for testing"""
    TestingSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
def session_manager():
    """Create session manager for testing"""
    return SessionManager(test_settings)

@pytest_asyncio.fixture
def background_tasks():
    """Create background task manager for testing"""
    return BackgroundTaskManager()

@pytest_asyncio.fixture
async def test_app(db_session, session_manager, background_tasks):
    """Create test application with dependencies"""
    app.state.db_pool = lambda: db_session
    app.state.background_tasks = background_tasks
    return app

@pytest_asyncio.fixture
async def client(test_app):
    """Create test client"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
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