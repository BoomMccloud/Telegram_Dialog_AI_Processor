"""
Script to check sessions in the database
"""
import asyncio
import logging

from .database import get_raw_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_sessions():
    """Check all sessions in the database"""
    try:
        conn = await get_raw_connection()
        try:
            sessions = await conn.fetch('SELECT * FROM sessions')
            if not sessions:
                logger.info("No sessions found in database")
                return
                
            logger.info(f"Found {len(sessions)} sessions:")
            for session in sessions:
                logger.info("\nSession details:")
                logger.info(f"  ID: {session['id']}")
                logger.info(f"  Status: {session['status']}")
                logger.info(f"  Telegram ID: {session['telegram_id']}")
                logger.info(f"  Created at: {session['created_at']}")
                logger.info(f"  Expires at: {session['expires_at']}")
                logger.info(f"  Metadata: {session['metadata']}")
                
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error checking sessions: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(check_sessions()) 