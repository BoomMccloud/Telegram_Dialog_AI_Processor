"""
Script to check database state
"""
import asyncio
import logging

from .database import get_raw_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_database():
    """Check database tables and their structure"""
    try:
        conn = await get_raw_connection()
        try:
            # List all tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            logger.info("Database tables:")
            for table in tables:
                table_name = table['table_name']
                logger.info(f"\nTable: {table_name}")
                
                # Get columns for this table
                columns = await conn.fetch("""
                    SELECT column_name, data_type, column_default, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = $1
                """, table_name)
                
                logger.info("Columns:")
                for col in columns:
                    logger.info(f"  - {col['column_name']}: {col['data_type']} "
                              f"(nullable: {col['is_nullable']}, default: {col['column_default']})")
                
                # Get row count
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                logger.info(f"Row count: {count}")
                
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(check_database()) 