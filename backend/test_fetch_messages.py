import asyncio
import sys
from uuid import UUID

from app.db.database import async_session
from app.db.models.dialog import Dialog
from app.services.dialog_processor import DialogProcessor
from app.db.models.session import Session
from sqlalchemy import select

async def get_latest_session_token():
    """Get the most recent session token"""
    async with async_session() as session:
        query = select(Session).where(Session.status == 'AUTHENTICATED').order_by(Session.last_activity.desc())
        result = await session.execute(query)
        user_session = result.scalars().first()
        
        if not user_session:
            print("No authenticated session found")
            return None
            
        return user_session.token

async def test_fetch_messages(dialog_id=None):
    """Test fetching messages for a specific dialog"""
    # Get session token
    session_token = await get_latest_session_token()
    if not session_token:
        print("Cannot proceed without a valid session token")
        return
        
    async with async_session() as session:
        # Get dialogs to process
        if dialog_id:
            # Get specific dialog
            try:
                dialog = await session.get(Dialog, UUID(dialog_id))
                if not dialog:
                    print(f"Dialog with ID {dialog_id} not found")
                    return
                dialogs = [dialog]
            except ValueError:
                print(f"Invalid dialog ID format: {dialog_id}")
                return
        else:
            # Get all enabled dialogs
            query = select(Dialog).where(Dialog.is_processing_enabled == True)
            result = await session.execute(query)
            dialogs = result.scalars().all()
            
            if not dialogs:
                print("No enabled dialogs found")
                return
                
        print(f"Testing message fetching for {len(dialogs)} dialog(s)")
        
        # Create processor and fetch messages
        processor = DialogProcessor(session)
        
        for dialog in dialogs:
            print(f"\nProcessing dialog: {dialog.title} (ID: {dialog.id})")
            try:
                messages = await processor.fetch_messages(dialog, session_token)
                print(f"Successfully fetched {len(messages)} messages")
                
                # Print first few messages
                for i, msg in enumerate(messages[:5]):
                    sender = msg.get('sender', {})
                    sender_name = sender.get('name', 'Unknown')
                    text = msg.get('text', '[No text]')
                    print(f"Message {i+1}: From {sender_name} - {text[:50]}{'...' if len(text) > 50 else ''}")
                    
            except Exception as e:
                print(f"Error fetching messages: {str(e)}")

if __name__ == "__main__":
    # Get dialog ID from command line if provided
    dialog_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    asyncio.run(test_fetch_messages(dialog_id)) 