from app.db.database import get_raw_connection
import asyncio

async def test():
    try:
        conn = await get_raw_connection()
        print('Connected to database!')
        await conn.close()
    except Exception as e:
        print(f'Error connecting to database: {str(e)}')

if __name__ == '__main__':
    asyncio.run(test()) 