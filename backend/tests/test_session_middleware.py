"""
Tests for JWT-based session middleware
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, Depends
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
import uuid

from app.middleware.session import SessionMiddleware, verify_session_dependency, SessionData
from app.models.session import Session, SessionStatus
from app.models.user import User

def utcnow():
    """Helper function to get timezone-aware UTC datetime"""
    return datetime.now(timezone.utc)

# Counter for generating unique telegram_ids
_telegram_id_counter = 100000

@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user with a unique telegram_id"""
    global _telegram_id_counter
    _telegram_id_counter += 1
    user = User(
        telegram_id=_telegram_id_counter,
        username=f"testuser_{_telegram_id_counter}",
        first_name="Test",
        last_name="User"
    )
    db_session.add(user)
    await db_session.commit()
    return user

# Test cases
@pytest.mark.asyncio
async def test_create_session(test_app, db_session, test_user):
    """Test creating a new session"""
    session_middleware = test_app.state.session_middleware
    
    # Create a regular session
    session = await session_middleware.create_session(db=db_session, telegram_id=test_user.telegram_id)
    assert session.token is not None
    assert session.telegram_id == test_user.telegram_id
    assert session.status == SessionStatus.AUTHENTICATED
    
    # Create a QR session
    qr_session = await session_middleware.create_session(db=db_session, is_qr=True)
    assert qr_session.token is not None
    assert qr_session.status == SessionStatus.PENDING
    assert qr_session.telegram_id is None

@pytest.mark.asyncio
async def test_verify_session(test_app, db_session, test_user):
    """Test verifying a session"""
    session_middleware = test_app.state.session_middleware
    
    # Create and verify valid session
    session = await session_middleware.create_session(db=db_session, telegram_id=test_user.telegram_id)
    verified = await session_middleware.verify_session(session.token, db=db_session)
    assert verified is not None
    assert verified.telegram_id == test_user.telegram_id
    assert verified.status == SessionStatus.AUTHENTICATED
    
    # Test invalid token
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session("invalid-token", db=db_session)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_update_session(test_app, db_session, test_user):
    """Test updating a session"""
    session_middleware = test_app.state.session_middleware
    
    # Create initial session
    session = await session_middleware.create_session(db=db_session, is_qr=True)
    
    # Update session with telegram ID
    updated = await session_middleware.update_session(session.token, test_user.telegram_id, db=db_session)
    assert updated is not None
    assert updated.telegram_id == test_user.telegram_id
    assert updated.status == SessionStatus.AUTHENTICATED
    
    # Verify in database
    stmt = select(Session).where(Session.token == session.token)
    result = await db_session.execute(stmt)
    db_session = result.scalar_one()
    assert db_session.telegram_id == test_user.telegram_id
    assert db_session.status == SessionStatus.AUTHENTICATED

@pytest.mark.asyncio
async def test_session_expiration(test_app, db_session, test_user):
    """Test session expiration handling"""
    session_middleware = test_app.state.session_middleware
    
    # Create session
    session = await session_middleware.create_session(db=db_session, telegram_id=test_user.telegram_id)
    
    # Set expiration to past
    session.expires_at = utcnow() - timedelta(hours=1)
    await db_session.commit()
    
    # Verify expired session
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session(session.token, db=db_session)
    assert exc_info.value.status_code == 401

def test_http_endpoints(test_client):
    """Test session middleware in HTTP context"""
    # Public path should work without token
    response = test_client.get("/health")
    assert response.status_code == 200
    
    # Protected path should require token
    with pytest.raises(HTTPException) as exc_info:
        test_client.get("/api/protected")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authorization header required"
    
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid-token"}
    with pytest.raises(HTTPException) as exc_info:
        test_client.get("/api/protected", headers=headers)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_user_session(test_app, db_session, test_user):
    """Test session with user data"""
    session_middleware = test_app.state.session_middleware
    
    # Create session
    session = await session_middleware.create_session(db=db_session, telegram_id=test_user.telegram_id)
    
    # Verify session with user
    verified = await session_middleware.verify_session(session.token, db=db_session)
    assert verified is not None
    assert verified.telegram_id == test_user.telegram_id
    assert verified.status == SessionStatus.AUTHENTICATED

@pytest.mark.asyncio
async def test_cleanup_expired_sessions(test_app, db_session, test_user):
    """Test cleaning up expired sessions"""
    session_middleware = test_app.state.session_middleware
    
    # Create expired session
    expired = await session_middleware.create_session(db=db_session, telegram_id=test_user.telegram_id)
    expired.expires_at = utcnow() - timedelta(hours=1)
    await db_session.commit()
    
    # Create valid session
    valid = await session_middleware.create_session(db=db_session, telegram_id=test_user.telegram_id)
    
    # Run cleanup
    await session_middleware.cleanup_expired_sessions(db=db_session)
    
    # Verify expired session is removed
    stmt = select(Session).where(Session.token == expired.token)
    result = await db_session.execute(stmt)
    expired_db = result.scalar_one_or_none()
    assert expired_db is None
    
    # Verify valid session remains
    stmt = select(Session).where(Session.token == valid.token)
    result = await db_session.execute(stmt)
    valid_db = result.scalar_one_or_none()
    assert valid_db is not None

@pytest.mark.asyncio
async def test_jwt_token_validation(test_app, db_session, test_user):
    """Test JWT token validation specifics"""
    session_middleware = test_app.state.session_middleware
    
    # Test token expiration
    session = await session_middleware.create_session(db=db_session, telegram_id=test_user.telegram_id)
    token_data = jwt.decode(session.token, session_middleware.jwt_secret, algorithms=["HS256"])
    assert "exp" in token_data
    assert "jti" in token_data
    
    # Test token tampering
    tampered_token = session.token[:-1] + ("1" if session.token[-1] == "0" else "0")
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session(tampered_token, db=db_session)
    assert exc_info.value.status_code == 401
    
    # Test expired token
    expired_token_data = {
        "jti": str(uuid.uuid4()),
        "exp": utcnow() - timedelta(minutes=1)
    }
    expired_token = jwt.encode(expired_token_data, session_middleware.jwt_secret, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session(expired_token, db=db_session)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_public_paths_access(test_app, test_client):
    """Test access to public paths"""
    # Test all defined public paths
    public_paths = [
        "/health",
        "/api/auth/qr",
        "/api/auth/session/verify",
        "/api/auth/dev-login",
        "/docs",
        "/redoc",
        "/openapi.json"
    ]
    
    for path in public_paths:
        response = test_client.get(path)
        assert response.status_code != 401, f"Public path {path} should not require authentication"

@pytest.mark.asyncio
async def test_session_metadata(test_app, db_session, test_user):
    """Test session metadata handling"""
    session_middleware = test_app.state.session_middleware
    
    # Create session with metadata
    metadata = {"device": "test_device", "ip": "127.0.0.1"}
    session = await session_middleware.create_session(
        db=db_session,
        telegram_id=test_user.telegram_id,
        metadata=metadata
    )
    
    # Verify metadata is stored and retrieved
    verified = await session_middleware.verify_session(session.token, db=db_session)
    assert verified.metadata == metadata
    
    # Update metadata
    session.metadata = {"device": "new_device", "ip": "127.0.0.2"}
    await db_session.commit()
    
    # Verify updated metadata
    verified = await session_middleware.verify_session(session.token, db=db_session)
    assert verified.metadata == {"device": "new_device", "ip": "127.0.0.2"}

@pytest.mark.asyncio
async def test_session_update_errors(test_app, db_session, test_user):
    """Test error cases for session updates"""
    session_middleware = test_app.state.session_middleware
    
    # Test updating non-existent session
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.update_session("non-existent-token", test_user.telegram_id, db=db_session)
    assert exc_info.value.status_code == 401
    
    # Test updating expired session
    session = await session_middleware.create_session(db=db_session, is_qr=True)
    session.expires_at = utcnow() - timedelta(hours=1)
    await db_session.commit()
    
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.update_session(session.token, test_user.telegram_id, db=db_session)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_concurrent_sessions(test_app, db_session, test_user):
    """Test handling of concurrent sessions"""
    session_middleware = test_app.state.session_middleware
    
    # Create multiple sessions for same user
    sessions = []
    for _ in range(3):
        session = await session_middleware.create_session(db=db_session, telegram_id=test_user.telegram_id)
        sessions.append(session)
    
    # Verify all sessions are valid
    for session in sessions:
        verified = await session_middleware.verify_session(session.token, db=db_session)
        assert verified is not None
        assert verified.telegram_id == test_user.telegram_id
        assert verified.status == SessionStatus.AUTHENTICATED 