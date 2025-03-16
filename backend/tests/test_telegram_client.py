import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_telegram_client():
    """Test creating a Telegram client directly and fetching messages"""
    # Get API credentials from environment
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        logger.error("TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables are required")
        return
    
    # Create a new client instance
    client = TelegramClient('anon', int(api_id), api_hash)
    
    try:
        # Connect to Telegram
        await client.connect()
        
        # Check if already authorized
        if await client.is_user_authorized():
            logger.info("Client is already authorized")
        else:
            logger.info("Client is not authorized, starting QR login")
            # Start QR login
            qr_login = await client.qr_login()
            logger.info(f"Please scan this QR code: {qr_login.url}")
            
            # Wait for login
            await qr_login.wait()
            logger.info("Successfully logged in!")
        
        # Get session string for future use
        session_str = StringSession.save(client.session)
        logger.info(f"Session string: {session_str}")
        
        # Get dialogs
        logger.info("Fetching dialogs...")
        dialogs = []
        async for dialog in client.iter_dialogs():
            dialogs.append({
                "id": dialog.id,
                "name": dialog.name,
                "type": "group" if dialog.is_group else "private"
            })
            logger.info(f"Dialog: {dialog.name} (ID: {dialog.id})")
        
        # Get recent messages from first dialog
        if dialogs:
            dialog = dialogs[0]
            logger.info(f"Fetching messages from {dialog['name']}...")
            
            messages = []
            async for message in client.iter_messages(dialog['id'], limit=5):
                sender = await message.get_sender()
                sender_name = sender.first_name if hasattr(sender, 'first_name') else "Unknown"
                
                messages.append({
                    "id": message.id,
                    "text": message.text,
                    "date": message.date,
                    "sender": sender_name
                })
                
                logger.info(f"Message from {sender_name}: {message.text}")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
    
    finally:
        # Disconnect the client
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_telegram_client()) 