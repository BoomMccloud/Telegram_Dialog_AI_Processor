import os
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import inspect, text

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(backend_dir)

from app.main import DATABASE_URL
from app.models.session import Session
from app.models.user import User

async def inspect_db():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        # Get table information
        result = await conn.execute(text("""
            SELECT tablename 
            FROM pg_catalog.pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result]
        print('Tables:', tables)
        
        # Get column information for each table
        for table in tables:
            result = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = :table
            """), {"table": table})
            columns = result.fetchall()
            print(f'\nColumns in {table}:')
            for col in columns:
                print(f'  {col[0]}: {col[1]}')

if __name__ == "__main__":
    asyncio.run(inspect_db()) 