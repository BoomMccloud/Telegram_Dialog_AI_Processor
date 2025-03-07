import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Use absolute imports
from app.main import app, DATABASE_URL
from app.db.models.base import Base
from app.db.database import get_db
from app.middleware.session import SessionMiddleware
from app.db.models.user import User
from app.db.models.session import Session

# Create test engine using the main database URL
test_engine = create_async_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="function")
async def test_db():
    """Create test database tables"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
def test_client(test_db):
    """Create test client with test database"""
    app.state.session_middleware = SessionMiddleware(testing=True)
    
    # Override the get_db dependency
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_dev_login_success(test_client):
    """Test successful development login"""
    # Set development environment
    os.environ["APP_ENV"] = "development"
    
    # Test login
    response = test_client.post(
        "/api/auth/dev-login",
        json={"telegram_id": 12345}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "authenticated"
    assert data["telegram_id"] == 12345
    assert "token" in data

@pytest.mark.asyncio
async def test_dev_login_invalid_input(test_client):
    """Test development login with invalid input"""
    # Set development environment
    os.environ["APP_ENV"] = "development"
    
    # Test with missing telegram_id
    response = test_client.post(
        "/api/auth/dev-login",
        json={}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_dev_login_production_mode(test_client):
    """Test development login in production mode"""
    # Set production environment
    os.environ["APP_ENV"] = "production"
    
    # Test login
    response = test_client.post(
        "/api/auth/dev-login",
        json={"telegram_id": 12345}
    )
    
    assert response.status_code == 403 