import os
from telethon import TelegramClient
import asyncio
from pathlib import Path

# Create sessions directory if it doesn't exist
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

async def test():
    try:
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            print('Error: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set')
            return
            
        print(f'Using API ID: {api_id}')
        
        # Create a new client instance with session file in sessions directory
        session_file = str(SESSIONS_DIR / 'test')
        client = TelegramClient(session_file, int(api_id), api_hash)
        
        print('Connecting to Telegram...')
        await client.connect()
        print('Connected successfully!')
        
        print('Testing QR login...')
        qr_login = await client.qr_login()
        print('QR login URL:', qr_login.url)
        
        await client.disconnect()
        print('Disconnected successfully!')
        
    except Exception as e:
        print(f'Error testing Telegram client: {str(e)}')

if __name__ == '__main__':
    asyncio.run(test()) 