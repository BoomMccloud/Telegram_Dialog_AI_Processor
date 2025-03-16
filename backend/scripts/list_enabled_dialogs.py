import asyncio
from sqlalchemy import select
from app.db.database import async_session
from app.db.models.dialog import Dialog

async def list_enabled_dialogs():
    async with async_session() as session:
        query = select(Dialog).where(Dialog.is_processing_enabled == True)
        result = await session.execute(query)
        dialogs = result.scalars().all()
        
        print(f'Found {len(dialogs)} enabled dialogs:')
        for d in dialogs:
            print(f'ID: {d.id}, Title: {d.title}')

if __name__ == "__main__":
    asyncio.run(list_enabled_dialogs()) 