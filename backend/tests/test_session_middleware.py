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
import uuid

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

@pytest.mark.asyncio
async def test_jwt_token_validation(test_app, db):
    """Test JWT token validation specifics"""
    session_middleware = test_app.state.session_middleware
    
    # Test token expiration
    session = await session_middleware.create_session(db=db, telegram_id=123456)
    token_data = jwt.decode(session.token, session_middleware.jwt_secret, algorithms=["HS256"])
    assert "exp" in token_data
    assert "jti" in token_data
    
    # Test token tampering
    tampered_token = session.token[:-1] + ("1" if session.token[-1] == "0" else "0")
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session(tampered_token, db=db)
    assert exc_info.value.status_code == 401
    
    # Test expired token
    expired_token_data = {
        "jti": str(uuid.uuid4()),
        "exp": datetime.utcnow() - timedelta(minutes=1)
    }
    expired_token = jwt.encode(expired_token_data, session_middleware.jwt_secret, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session(expired_token, db=db)
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
async def test_session_metadata(test_app, db):
    """Test session metadata handling"""
    session_middleware = test_app.state.session_middleware
    
    # Create session with metadata
    metadata = {"device": "test_device", "ip": "127.0.0.1"}
    session = await session_middleware.create_session(
        db=db,
        telegram_id=123456,
        metadata=metadata
    )
    
    # Verify metadata is stored and retrieved
    verified = await session_middleware.verify_session(session.token, db=db)
    assert verified.metadata == metadata
    
    # Update metadata
    updated_metadata = {"device": "new_device", "ip": "127.0.0.2"}
    session.metadata = updated_metadata
    await db.commit()
    
    # Verify updated metadata
    verified = await session_middleware.verify_session(session.token, db=db)
    assert verified.metadata == updated_metadata

@pytest.mark.asyncio
async def test_session_update_errors(test_app, db):
    """Test error cases for session updates"""
    session_middleware = test_app.state.session_middleware
    
    # Test updating non-existent session
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.update_session("non-existent-token", 123456, db=db)
    assert exc_info.value.status_code == 401
    
    # Test updating expired session
    session = await session_middleware.create_session(db=db, is_qr=True)
    await db.execute("""
        UPDATE sessions 
        SET expires_at = NOW() - interval '1 hour'
        WHERE token = $1
    """, session.token)
    
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.update_session(session.token, 123456, db=db)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_concurrent_sessions(test_app, db):
    """Test handling of concurrent sessions"""
    session_middleware = test_app.state.session_middleware
    
    # Create multiple sessions for same user
    telegram_id = 123456
    session1 = await session_middleware.create_session(db=db, telegram_id=telegram_id)
    session2 = await session_middleware.create_session(db=db, telegram_id=telegram_id)
    
    # Verify both sessions are valid
    verified1 = await session_middleware.verify_session(session1.token, db=db)
    verified2 = await session_middleware.verify_session(session2.token, db=db)
    
    assert verified1.telegram_id == telegram_id
    assert verified2.telegram_id == telegram_id
    assert verified1.token != verified2.token 