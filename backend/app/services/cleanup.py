"""
Cleanup service for maintaining database hygiene
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import delete, and_, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.session import Session
from app.db.models.types import SessionStatus
from app.utils.logging import get_logger

logger = get_logger(__name__)

async def cleanup_expired_sessions(db: AsyncSession):
    """
    Clean up expired sessions from the database
    
    Args:
        db: Database session
    """
    try:
        # Delete sessions that are:
        # 1. Not authenticated and expired
        # 2. Authenticated but inactive for 7 days
        
        # First, delete non-authenticated expired sessions
        stmt = delete(Session).where(
            and_(
                Session.status.cast(String) != SessionStatus.AUTHENTICATED.value,
                Session.expires_at < datetime.utcnow()
            )
        )
        await db.execute(stmt)
        
        # Then, delete inactive authenticated sessions
        stmt = delete(Session).where(
            and_(
                Session.status.cast(String) == SessionStatus.AUTHENTICATED.value,
                Session.last_activity < datetime.utcnow() - timedelta(days=7)
            )
        )
        await db.execute(stmt)
        
        await db.commit()
        logger.info("Cleaned up expired sessions")
        
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {str(e)}", exc_info=True)
        await db.rollback()

async def run_periodic_cleanup(db_pool, interval_seconds: int = 3600):
    """
    Run periodic cleanup tasks
    
    Args:
        db_pool: Database session pool
        interval_seconds: Interval between cleanup runs in seconds
    """
    while True:
        try:
            async with db_pool() as db:
                await cleanup_expired_sessions(db)
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {str(e)}", exc_info=True)
            
        await asyncio.sleep(interval_seconds) 