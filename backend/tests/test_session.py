import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timedelta
import asyncpg

from app.middleware.session import SessionMiddleware
from app.db.database import get_raw_connection
from app.main import app

# Test app fixture
@pytest.fixture
def app():
    app = FastAPI()
    session_middleware = SessionMiddleware(app)
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
        
    @app.get("/api/protected")
    async def protected_route():
        return {"message": "success"}
        
    return app

@pytest.fixture
def test_client():
    with TestClient(app=app, base_url="http://testserver") as client:
        yield client

@pytest_asyncio.fixture
async def db(db_pool, event_loop):
    async with db_pool.acquire() as conn:
        tr = conn.transaction()
        await tr.start()
        yield conn
        await tr.rollback()

# Test cases
@pytest.mark.asyncio
async def test_create_session(app, db):
    """Test creating a new session"""
    session_middleware = app.state.session_middleware
    
    # Create a regular session
    token = await session_middleware.create_session(telegram_id=123456)
    assert token is not None
    
    # Verify session in database
    session = await db.fetchrow("SELECT * FROM sessions WHERE token = $1", token)
    assert session is not None
    assert session['telegram_id'] == 123456
    assert session['status'] == 'authenticated'
    
    # Create a QR session
    qr_token = await session_middleware.create_session(is_qr=True)
    assert qr_token is not None
    
    # Verify QR session in database
    qr_session = await db.fetchrow("SELECT * FROM sessions WHERE token = $1", qr_token)
    assert qr_session is not None
    assert qr_session['status'] == 'pending'
    assert qr_session['telegram_id'] is None

@pytest.mark.asyncio
async def test_verify_session(app, db):
    """Test verifying a session"""
    session_middleware = app.state.session_middleware
    
    # Create and verify valid session
    token = await session_middleware.create_session(telegram_id=123456)
    session = await session_middleware.verify_session(token)
    assert session is not None
    assert session.telegram_id == 123456
    assert session.status == 'authenticated'
    
    # Test expired token
    expired_payload = {
        "jti": "test-id",
        "telegram_id": 123456,
        "exp": datetime.utcnow() - timedelta(hours=1),
        "iat": datetime.utcnow() - timedelta(hours=2)
    }
    expired_token = jwt.encode(
        expired_payload,
        session_middleware.secret_key,
        algorithm=session_middleware.algorithm
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session(expired_token)
    assert exc_info.value.status_code == 401
    
    # Test invalid token
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session("invalid-token")
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_update_session(app, db):
    """Test updating a session"""
    session_middleware = app.state.session_middleware
    
    # Create initial session
    token = await session_middleware.create_session(is_qr=True)
    
    # Update session with telegram ID
    updated_session = await session_middleware.update_session(
        token,
        {"telegram_id": 123456, "status": "authenticated"}
    )
    
    assert updated_session is not None
    assert updated_session.telegram_id == 123456
    assert updated_session.status == 'authenticated'
    
    # Verify in database
    session = await db.fetchrow("SELECT * FROM sessions WHERE token = $1", token)
    assert session['telegram_id'] == 123456
    assert session['status'] == 'authenticated'

def test_session_middleware_http(test_client, app):
    """Test session middleware in HTTP context"""
    # Public path should work without token
    response = test_client.get("/health")
    assert response.status_code == 200
    
    # Protected path should require token
    response = test_client.get("/api/protected")
    assert response.status_code == 401
    
    # Create valid session
    session_middleware = app.state.session_middleware
    token = session_middleware.create_session(telegram_id=123456)
    
    # Test with valid token
    headers = {"Authorization": f"Bearer {token}"}
    response = test_client.get("/api/protected", headers=headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_session_cleanup(app, db):
    """Test session cleanup functionality"""
    session_middleware = app.state.session_middleware
    
    # Create expired session
    expired_token = await session_middleware.create_session(telegram_id=123456)
    await db.execute("""
        UPDATE sessions 
        SET expires_at = NOW() - interval '1 hour'
        WHERE token = $1
    """, expired_token)
    
    # Create valid session
    valid_token = await session_middleware.create_session(telegram_id=789012)
    
    # Run cleanup
    from app.services.cleanup import cleanup_expired_sessions
    await cleanup_expired_sessions()
    
    # Verify expired session is removed
    expired_session = await db.fetchrow(
        "SELECT * FROM sessions WHERE token = $1",
        expired_token
    )
    assert expired_session is None
    
    # Verify valid session remains
    valid_session = await db.fetchrow(
        "SELECT * FROM sessions WHERE token = $1",
        valid_token
    )
    assert valid_session is not None 