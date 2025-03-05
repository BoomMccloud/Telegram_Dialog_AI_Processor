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
    app.state.session_middleware = session_middleware
    
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
    session = await session_middleware.create_session(telegram_id=123456, db=db)
    assert session.token is not None
    
    # Verify session in database
    db_session = await db.fetchrow("SELECT * FROM sessions WHERE token = $1", session.token)
    assert db_session is not None
    assert db_session['telegram_id'] == 123456
    assert db_session['status'] == 'authenticated'
    
    # Create a QR session
    qr_session = await session_middleware.create_session(is_qr=True, db=db)
    assert qr_session.token is not None
    
    # Verify QR session in database
    qr_db_session = await db.fetchrow("SELECT * FROM sessions WHERE token = $1", qr_session.token)
    assert qr_db_session is not None
    assert qr_db_session['status'] == 'pending'
    assert qr_db_session['telegram_id'] is None

@pytest.mark.asyncio
async def test_verify_session(app, db):
    """Test verifying a session"""
    session_middleware = app.state.session_middleware
    
    # Create and verify valid session
    session = await session_middleware.create_session(telegram_id=123456, db=db)
    verified_session = await session_middleware.verify_session(session.token, db=db)
    assert verified_session is not None
    assert verified_session.telegram_id == 123456
    assert verified_session.status == 'authenticated'
    
    # Test invalid token
    with pytest.raises(HTTPException) as exc_info:
        await session_middleware.verify_session("invalid-token", db=db)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_update_session(app, db):
    """Test updating a session"""
    session_middleware = app.state.session_middleware
    
    # Create initial session
    session = await session_middleware.create_session(is_qr=True, db=db)
    
    # Update session with telegram ID
    updated_session = await session_middleware.update_session(
        session.token,
        123456,
        db=db
    )
    
    assert updated_session is not None
    assert updated_session.telegram_id == 123456
    assert updated_session.status == 'authenticated'
    
    # Verify in database
    db_session = await db.fetchrow("SELECT * FROM sessions WHERE token = $1", session.token)
    assert db_session['telegram_id'] == 123456
    assert db_session['status'] == 'authenticated'

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
    session = session_middleware.create_session(telegram_id=123456)
    
    # Test with valid token
    headers = {"Authorization": f"Bearer {session.token}"}
    response = test_client.get("/api/protected", headers=headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_session_cleanup(app, db):
    """Test session cleanup functionality"""
    session_middleware = app.state.session_middleware
    
    # Create expired session
    expired_session = await session_middleware.create_session(telegram_id=123456, db=db)
    await db.execute("""
        UPDATE sessions 
        SET expires_at = NOW() - interval '1 hour'
        WHERE token = $1
    """, expired_session.token)
    
    # Create valid session
    valid_session = await session_middleware.create_session(telegram_id=789012, db=db)
    
    # Run cleanup
    await session_middleware.cleanup_expired_sessions(db=db)
    
    # Verify expired session is removed
    expired_db_session = await db.fetchrow(
        "SELECT * FROM sessions WHERE token = $1",
        expired_session.token
    )
    assert expired_db_session is None
    
    # Verify valid session remains
    valid_db_session = await db.fetchrow(
        "SELECT * FROM sessions WHERE token = $1",
        valid_session.token
    )
    assert valid_db_session is not None 