import asyncio
from sqlalchemy import select
from app.db.database import async_session
from app.db.models.session import Session

async def list_session_tokens():
    async with async_session() as session:
        # Get all authenticated sessions
        query = select(Session).where(Session.status == 'AUTHENTICATED').order_by(Session.last_activity.desc())
        result = await session.execute(query)
        sessions = result.scalars().all()
        
        if sessions:
            print(f"Found {len(sessions)} authenticated sessions:")
            for i, user_session in enumerate(sessions):
                print(f"\nSession #{i+1}:")
                print(f"  User ID: {user_session.user_id}")
                print(f"  Session ID: {user_session.id}")
                print(f"  Token: {user_session.token[:20]}...{user_session.token[-10:] if len(user_session.token) > 30 else user_session.token}")
                print(f"  Last activity: {user_session.last_activity}")
                print(f"  Expires at: {user_session.expires_at}")
            
            # Return the most recent token
            return sessions[0].token if sessions else None
        else:
            print("No authenticated sessions found")
            return None

if __name__ == "__main__":
    asyncio.run(list_session_tokens()) 