"""
Integration tests for authentication endpoints
"""

import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.session import Session, SessionStatus
from app.models.user import User
from app.services.session_manager import SessionManager

pytestmark = pytest.mark.asyncio

async def test_dev_login(client: AsyncClient, db_session):
    """Test development login endpoint"""
    # Make login request
    response = await client.post(
        "/api/auth/dev-login",
        json={"telegram_id": 12345}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    
    # Verify session in database
    stmt = select(Session).where(Session.telegram_id == 12345)
    result = await db_session.execute(stmt)
    session = result.scalar_one()
    assert session.status == SessionStatus.AUTHENTICATED

async def test_refresh_token(client: AsyncClient, db_session, session_manager):
    """Test token refresh endpoint"""
    # Create initial session
    session = await session_manager.create_session(
        db=db_session,
        telegram_id=12345
    )
    
    # Refresh token
    response = await client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {session.refresh_token}"}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] != session.token
    assert data["refresh_token"] == session.refresh_token
    
    # Verify old token is invalid
    response = await client.get(
        "/api/auth/session/verify",
        headers={"Authorization": f"Bearer {session.token}"}
    )
    assert response.status_code == 401

async def test_logout(client: AsyncClient, db_session, session_manager):
    """Test logout endpoint"""
    # Create session
    session = await session_manager.create_session(
        db=db_session,
        telegram_id=12345
    )
    
    # Logout
    response = await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {session.token}"}
    )
    
    # Verify response
    assert response.status_code == 200
    
    # Verify session is invalid
    response = await client.get(
        "/api/auth/session/verify",
        headers={"Authorization": f"Bearer {session.token}"}
    )
    assert response.status_code == 401

async def test_verify_session(client: AsyncClient, db_session, session_manager):
    """Test session verification endpoint"""
    # Create session and user
    user = User(
        telegram_id=12345,
        username="testuser",
        first_name="Test",
        last_name="User"
    )
    db_session.add(user)
    await db_session.commit()
    
    session = await session_manager.create_session(
        db=db_session,
        telegram_id=12345
    )
    
    # Verify session
    response = await client.get(
        "/api/auth/session/verify",
        headers={"Authorization": f"Bearer {session.token}"}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == SessionStatus.AUTHENTICATED
    assert data["telegram_id"] == 12345
    assert data["user"]["username"] == "testuser"

async def test_invalid_token(client: AsyncClient):
    """Test invalid token handling"""
    response = await client.get(
        "/api/auth/session/verify",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401

async def test_missing_token(client: AsyncClient):
    """Test missing token handling"""
    response = await client.get("/api/auth/session/verify")
    assert response.status_code == 401

async def test_expired_token(client: AsyncClient, db_session):
    """Test expired token handling"""
    # Create session with immediate expiration
    test_settings = {
        "jwt_secret": "test-secret",
        "access_token_expire_minutes": 0,
        "refresh_token_expire_minutes": 0
    }
    session_manager = SessionManager(test_settings)
    session = await session_manager.create_session(db=db_session)
    
    # Wait for expiration
    await asyncio.sleep(1)
    
    # Verify session
    response = await client.get(
        "/api/auth/session/verify",
        headers={"Authorization": f"Bearer {session.token}"}
    )
    assert response.status_code == 401 