import asyncio
import asyncpg

async def create_test_db():
    """Create test database if it doesn't exist"""
    # Connect to default database to create test database
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="postgres",
        host="localhost",
        port=5432
    )
    
    try:
        # Check if database exists
        exists = await conn.fetchval("""
            SELECT 1 FROM pg_database WHERE datname = 'test_telegram_dialog'
        """)
        
        if not exists:
            # Create database
            await conn.execute("CREATE DATABASE test_telegram_dialog")
            print("Created test database: test_telegram_dialog")
        else:
            print("Test database already exists")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_test_db()) 