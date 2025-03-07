"""
Tests for session management system
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.db.models.session import Session, SessionStatus, TokenType
from app.services.session_manager import SessionManager
from app.services.cleanup import cleanup_expired_sessions

pytestmark = pytest.mark.asyncio

async def test_create_session(db_session, session_manager):
    """Test creating a new session"""
    # Create session
    session = await session_manager.create_session(
        db=db_session,
        telegram_id=12345,
        device_info={"user_agent": "test-agent"}
    )
    
    # Verify session
    assert session.telegram_id == 12345
    assert session.status == SessionStatus.AUTHENTICATED
    assert session.token is not None
    assert session.refresh_token is not None
    assert session.token_type == TokenType.ACCESS
    assert session.device_info == {"user_agent": "test-agent"}
    assert session.expires_at > datetime.utcnow()
    
    # Verify session in database
    stmt = select(Session).where(Session.id == session.id)
    result = await db_session.execute(stmt)
    db_session = result.scalar_one()
    assert db_session.telegram_id == 12345

async def test_verify_session(db_session, session_manager):
    """Test verifying a session"""
    # Create session
    session = await session_manager.create_session(db=db_session)
    
    # Verify valid session
    verified = await session_manager.verify_session(db_session, session.token)
    assert verified.id == session.id
    
    # Verify invalid token
    with pytest.raises(Exception):
        await session_manager.verify_session(db_session, "invalid-token")

async def test_refresh_session(db_session, session_manager):
    """Test refreshing a session"""
    # Create session
    session = await session_manager.create_session(db=db_session)
    old_token = session.token
    
    # Refresh session
    new_session = await session_manager.refresh_session(db_session, session.refresh_token)
    
    # Verify new session
    assert new_session.id == session.id
    assert new_session.token != old_token
    assert new_session.refresh_token == session.refresh_token
    
    # Verify old token is invalid
    with pytest.raises(Exception):
        await session_manager.verify_session(db_session, old_token)

async def test_invalidate_session(db_session, session_manager):
    """Test invalidating a session"""
    # Create session
    session = await session_manager.create_session(db=db_session)
    
    # Invalidate session
    await session_manager.invalidate_session(db_session, session.token)
    
    # Verify session is invalid
    with pytest.raises(Exception):
        await session_manager.verify_session(db_session, session.token)

async def test_session_expiration(db_session, session_manager):
    """Test session expiration"""
    # Create session with short expiration
    test_settings = {
        "jwt_secret": "test-secret",
        "access_token_expire_minutes": 0,  # Expire immediately
        "refresh_token_expire_minutes": 0
    }
    session_manager = SessionManager(test_settings)
    session = await session_manager.create_session(db=db_session)
    
    # Wait for expiration
    await asyncio.sleep(1)
    
    # Verify session is expired
    with pytest.raises(Exception):
        await session_manager.verify_session(db_session, session.token)

async def test_cleanup_expired_sessions(db_session, session_manager):
    """Test cleaning up expired sessions"""
    # Create expired session
    test_settings = {
        "jwt_secret": "test-secret",
        "access_token_expire_minutes": 0,
        "refresh_token_expire_minutes": 0
    }
    session_manager = SessionManager(test_settings)
    session = await session_manager.create_session(db=db_session)
    
    # Create active session
    active_session = await session_manager.create_session(db=db_session)
    
    # Run cleanup
    await cleanup_expired_sessions(db_session)
    
    # Verify expired session is removed
    stmt = select(Session).where(Session.id == session.id)
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None
    
    # Verify active session remains
    stmt = select(Session).where(Session.id == active_session.id)
    result = await db_session.execute(stmt)
    assert result.scalar_one() is not None

async def test_session_activity_tracking(db_session, session_manager):
    """Test session activity tracking"""
    # Create session
    session = await session_manager.create_session(db=db_session)
    original_activity = session.last_activity
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Verify session
    verified = await session_manager.verify_session(db_session, session.token)
    assert verified.last_activity > original_activity

async def test_device_info_storage(db_session, session_manager):
    """Test device info storage in session"""
    device_info = {
        "user_agent": "test-browser",
        "platform": "test-platform",
        "device_type": "test-device"
    }
    
    # Create session with device info
    session = await session_manager.create_session(
        db=db_session,
        device_info=device_info
    )
    
    # Verify device info
    assert session.device_info == device_info
    
    # Verify in database
    stmt = select(Session).where(Session.id == session.id)
    result = await db_session.execute(stmt)
    db_session = result.scalar_one()
    assert db_session.device_info == device_info 