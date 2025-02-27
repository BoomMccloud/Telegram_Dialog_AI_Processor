from telethon import TelegramClient, events
from typing import Dict, Optional
import os
import json
from datetime import datetime
from .auth import qr_sessions

class TelegramBot:
    def __init__(self):
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not all([self.api_id, self.api_hash, self.bot_token]):
            raise ValueError("Missing Telegram credentials in environment variables")
        
        self.client = TelegramClient('bot', self.api_id, self.api_hash)
        
    async def start(self):
        """Start the bot and register event handlers"""
        await self.client.start(bot_token=self.bot_token)
        
        # Register message handlers
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Handle /start command"""
            await event.respond('Welcome! Please scan a QR code to authenticate.')
            
        @self.client.on(events.NewMessage(pattern='/scan'))
        async def scan_handler(event):
            """Handle QR code scanning"""
            try:
                # Get session ID from message
                session_id = event.message.text.split()[1]
                if session_id not in qr_sessions:
                    await event.respond('Invalid or expired QR code.')
                    return
                
                # Get user's Telegram ID
                sender = await event.get_sender()
                telegram_id = sender.id
                
                # Update session with Telegram ID
                session = qr_sessions[session_id]
                session["status"] = "authenticated"
                session["telegram_id"] = telegram_id
                
                await event.respond('Authentication successful! You can now close this chat.')
                
            except Exception as e:
                await event.respond('Authentication failed. Please try again.')
                
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            """Handle incoming messages"""
            # Store message in telegram_data.json
            message_data = {
                "message_id": event.message.id,
                "chat_id": event.chat_id,
                "sender_id": event.sender_id,
                "text": event.message.text,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Append to telegram_data.json
            try:
                with open('telegram_data.json', 'r+') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = {"messages": []}
                    
                    data["messages"].append(message_data)
                    f.seek(0)
                    json.dump(data, f, indent=2)
                    f.truncate()
            except FileNotFoundError:
                with open('telegram_data.json', 'w') as f:
                    json.dump({"messages": [message_data]}, f, indent=2)
    
    async def stop(self):
        """Stop the bot"""
        await self.client.disconnect()

# Create bot instance
bot = TelegramBot()

# Function to get bot instance
def get_bot() -> TelegramBot:
    return bot 