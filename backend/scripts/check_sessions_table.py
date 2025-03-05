from app.db.database import get_raw_connection
import asyncio

async def test():
    try:
        conn = await get_raw_connection()
        result = await conn.fetch("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'sessions'
            );
        """)
        if result[0][0]:
            print('Sessions table exists!')
            # Check table structure
            columns = await conn.fetch("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'sessions';
            """)
            print('\nColumns:')
            for col in columns:
                print(f'  {col["column_name"]}: {col["data_type"]}')
        else:
            print('Sessions table does not exist!')
        await conn.close()
    except Exception as e:
        print(f'Error checking sessions table: {str(e)}')

if __name__ == '__main__':
    asyncio.run(test()) 