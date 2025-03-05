"""
Tests for JWT-based session middleware
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, Depends
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.session import SessionMiddleware, verify_session_dependency, SessionData
from app.models.session import Session, SessionStatus
from app.models.user import User
from app.db.database import get_db

# Test app fixture
@pytest.fixture
def test_app():
    app = FastAPI()
    app.add_middleware(SessionMiddleware)
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
        
    @app.get("/api/protected")
    async def protected_route(session: SessionData = Depends(verify_session_dependency)):
        return {"message": "success", "telegram_id": session.telegram_id}
    
    return app

@pytest.fixture
def test_client(test_app):
    with TestClient(test_app) as client:
        yield client

@pytest_asyncio.fixture
async def db(db_pool):
    async with db_pool.acquire() as conn:
        tr = conn.transaction()
        await tr.start()
        yield conn
        await tr.rollback()

# Test cases
@pytest.mark.asyncio
async def test_create_session(test_app, db):
    """Test creating a new session"""
    session_middleware = test_app.state.session_middleware
    
    # Create a regular session
    session = await session_middleware.create_session(db=db, telegram_id=123456)
    assert session.token is not None
    assert session.telegram_id == 123456
    assert session.status == SessionStatus.AUTHENTICATED
    
    # Create a QR session
    qr_session = await session_middleware.create_session(db=db, is_qr=True)
    assert qr_session.token is not None
    assert qr_session.status == SessionStatus.PENDING
    assert qr_session.telegram_id is None

@pytest.mark.asyncio
async def test_verify_session(test_app, db):
    """Test verifying a session"""
    session_middleware = test_app.state.session_middleware
    
    # Create and verify valid session
    session = await session_middleware.create_session(db=db, telegram_id=123456)
    verified = await session_middleware.verify_session(session.token, db=db)
    assert verified is not None
    assert verified.telegram_id == 123456
    assert verified.status == SessionStatus.AUTHENTICATED
    
    # Test invalid token
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session("invalid-token", db=db)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_update_session(test_app, db):
    """Test updating a session"""
    session_middleware = test_app.state.session_middleware
    
    # Create initial session
    session = await session_middleware.create_session(db=db, is_qr=True)
    
    # Update session with telegram ID
    updated = await session_middleware.update_session(session.token, 123456, db=db)
    assert updated is not None
    assert updated.telegram_id == 123456
    assert updated.status == SessionStatus.AUTHENTICATED
    
    # Verify in database
    db_session = await db.fetchrow("SELECT * FROM sessions WHERE token = $1", session.token)
    assert db_session['telegram_id'] == 123456
    assert db_session['status'] == 'authenticated'

@pytest.mark.asyncio
async def test_session_expiration(test_app, db):
    """Test session expiration handling"""
    session_middleware = test_app.state.session_middleware
    
    # Create session
    session = await session_middleware.create_session(db=db, telegram_id=123456)
    
    # Set expiration to past
    await db.execute("""
        UPDATE sessions 
        SET expires_at = NOW() - interval '1 hour'
        WHERE token = $1
    """, session.token)
    
    # Verify expired session
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session(session.token, db=db)
    assert exc_info.value.status_code == 401

def test_http_endpoints(test_client):
    """Test session middleware in HTTP context"""
    # Public path should work without token
    response = test_client.get("/health")
    assert response.status_code == 200
    
    # Protected path should require token
    response = test_client.get("/api/protected")
    assert response.status_code == 401
    
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid-token"}
    response = test_client.get("/api/protected", headers=headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_user_session(test_app, db):
    """Test session with user data"""
    session_middleware = test_app.state.session_middleware
    
    # Create user
    user = User(
        telegram_id=123456,
        username="testuser",
        first_name="Test",
        last_name="User"
    )
    await db.execute("""
        INSERT INTO users (telegram_id, username, first_name, last_name)
        VALUES ($1, $2, $3, $4)
    """, user.telegram_id, user.username, user.first_name, user.last_name)
    
    # Create session
    session = await session_middleware.create_session(db=db, telegram_id=123456)
    
    # Verify session with user
    verified = await session_middleware.verify_session(session.token, db=db)
    assert verified is not None
    assert verified.telegram_id == 123456
    assert verified.status == SessionStatus.AUTHENTICATED

@pytest.mark.asyncio
async def test_cleanup_expired_sessions(test_app, db):
    """Test cleaning up expired sessions"""
    session_middleware = test_app.state.session_middleware
    
    # Create expired session
    expired = await session_middleware.create_session(db=db, telegram_id=123456)
    await db.execute("""
        UPDATE sessions 
        SET expires_at = NOW() - interval '1 hour'
        WHERE token = $1
    """, expired.token)
    
    # Create valid session
    valid = await session_middleware.create_session(db=db, telegram_id=789012)
    
    # Run cleanup
    await session_middleware.cleanup_expired_sessions()
    
    # Verify expired session is removed
    expired_db = await db.fetchrow("SELECT * FROM sessions WHERE token = $1", expired.token)
    assert expired_db is None
    
    # Verify valid session remains
    valid_db = await db.fetchrow("SELECT * FROM sessions WHERE token = $1", valid.token)
    assert valid_db is not None 