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
from fastapi import FastAPI, Depends
from httpx import AsyncClient
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.base import Base
from app.middleware.session import SessionMiddleware, verify_session_dependency, SessionData
from app.services.background_tasks import BackgroundTaskManager

# Load environment variables
load_dotenv()

# Get database configuration from environment
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "telegram_dialog_dev")

# Database URLs
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Test settings
test_settings = {
    "jwt_secret": os.getenv("JWT_SECRET_KEY", "test-secret-key-for-testing-only"),
    "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
    "refresh_token_expire_minutes": 10080
}

@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a test database engine."""
    # Create the engine with test settings
    test_engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=NullPool,  # Disable connection pooling for tests
        echo=True,  # Enable SQL logging
    )

    async with test_engine.begin() as conn:
        # Drop all tables and recreate them for a clean test environment
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield test_engine
    finally:
        await test_engine.dispose()

@pytest_asyncio.fixture
async def db_session(engine):
    """Create a test database session."""
    # Create session factory
    async_session = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    # Create session
    async with async_session() as session:
        try:
            # Clean up tables before each test
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            yield session
        finally:
            await session.rollback()
            await session.close()

@pytest_asyncio.fixture
async def session_middleware(db_session):
    """Create session middleware for testing"""
    # Set JWT secret in environment
    os.environ["JWT_SECRET"] = test_settings["jwt_secret"]
    
    # Create middleware
    middleware = SessionMiddleware(app=None)  # We'll set this later when adding to the app
    middleware.db = db_session  # Ensure the middleware has access to the db session
    return middleware

@pytest_asyncio.fixture
def background_tasks():
    """Create background task manager for testing"""
    return BackgroundTaskManager()

@pytest_asyncio.fixture
async def test_app(db_session, session_middleware, background_tasks):
    """Create test application with dependencies"""
    # Create a new FastAPI instance for testing
    app = FastAPI()
    
    # Set up app state
    app.state.db_pool = lambda: db_session
    app.state.session_middleware = session_middleware
    app.state.background_tasks = background_tasks
    
    # Add session middleware to the middleware stack
    app.add_middleware(SessionMiddleware)
    
    # Add test routes
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
        
    @app.get("/api/protected")
    async def protected_route(session: SessionData = Depends(verify_session_dependency)):
        return {"session_id": str(session.id)}
    
    return app

@pytest_asyncio.fixture
async def client(test_app):
    """Create test client"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client

@pytest.fixture
def test_client(test_app):
    """Create a test client for the FastAPI application"""
    client = TestClient(test_app)
    client.app = test_app  # Ensure the app is properly set
    return client 