"""
Test script for the file storage implementation
"""

import asyncio
import sys
from uuid import UUID
from datetime import datetime

from app.db.database import async_session
from app.db.models.dialog import Dialog
from app.db.models.message import Message
from app.services.dialog_processor import DialogProcessor
from app.utils.storage import MessageFileStorage
from sqlalchemy import select

async def test_file_storage():
    """Test the file storage implementation"""
    print("Testing file storage implementation...")
    
    # Create a file storage instance
    storage = MessageFileStorage()
    
    # Create test data
    user_id = "test_user"
    dialog_id = "test_dialog"
    
    # Create a processing run
    metadata = storage.create_processing_run(user_id, dialog_id)
    print(f"Created processing run: {metadata.run_id}")
    
    # Create test messages
    messages = [
        Message(
            telegram_message_id=f"msg_{i}",
            dialog_id=dialog_id,
            text=f"Test message {i}",
            sender_id="sender_1",
            sender_name="Test Sender",
            date=datetime.utcnow(),
            is_outgoing=False
        )
        for i in range(5)
    ]
    
    # Get run directory
    run_dir = storage.get_dialog_dir(user_id, dialog_id) / f"processing_{metadata.timestamp.strftime('%Y%m%d_%H%M%S')}_{metadata.run_id}"
    
    # Save messages
    storage.save_messages(run_dir, messages)
    print(f"Saved {len(messages)} messages")
    
    # Load messages
    loaded_messages = storage.load_messages(run_dir)
    print(f"Loaded {len(loaded_messages)} messages")
    
    # Get latest messages
    latest_messages = storage.get_latest_messages(user_id, dialog_id)
    print(f"Latest messages: {len(latest_messages)}")
    
    # Print first message
    if latest_messages:
        print(f"First message: {latest_messages[0].text}")
    
    # Test cleanup
    deleted = await storage.cleanup_old_runs(max_age_days=30)  # Set high to avoid deleting our test
    print(f"Deleted {deleted} old runs")
    
    print("File storage test completed successfully!")

async def test_dialog_processor():
    """Test the dialog processor with file storage"""
    print("\nTesting dialog processor with file storage...")
    
    async with async_session() as session:
        # Get a dialog to test with
        query = select(Dialog).where(Dialog.is_processing_enabled == True)
        result = await session.execute(query)
        dialog = result.scalar_one_or_none()
        
        if not dialog:
            print("No enabled dialogs found. Please enable processing for at least one dialog.")
            return
        
        print(f"Testing with dialog: {dialog.title} (ID: {dialog.id})")
        
        # Create processor
        processor = DialogProcessor(session)
        
        # Get latest messages
        messages = processor.get_latest_messages(dialog)
        
        if messages:
            print(f"Found {len(messages)} messages in latest processing run")
            for i, msg in enumerate(messages[:3]):  # Show first 3 messages
                print(f"Message {i+1}: {msg.sender_name} - {msg.text[:50]}...")
        else:
            print("No messages found. Run the worker to process messages first.")
    
    print("Dialog processor test completed!")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_file_storage())
    
    # Only run dialog processor test if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--with-processor":
        asyncio.run(test_dialog_processor()) 