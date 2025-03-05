#!/usr/bin/env python3
"""
Development utility script to inject a mock session into the main app.

This script creates a dummy authenticated session and adds it to the database,
allowing you to bypass the real Telegram authentication while still using
the real database for dialog selections.

Usage:
  python -m app.dev_utils.inject_mock_session

This will print the session ID that you can use with the real API endpoints.
"""

import sys
import uuid
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to Python path if needed
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Import required modules
from app.services.auth import client_sessions
from app.middleware.session import SessionMiddleware
from app.db.database import get_db, init_db
from fastapi import FastAPI

# Create a simple Mock client for development
class MockTelegramClient:
    def __init__(self):
        self._is_authorized = True
        
    async def is_user_authorized(self):
        return self._is_authorized
        
    async def connect(self):
        return True
        
    async def disconnect(self):
        return True
        
    # Add any other methods needed for testing
    async def iter_dialogs(self):
        # This won't be called in dev mode since dev_routes.py should handle it
        # But it's here as a fallback
        return []
        
    async def iter_messages(self, *args, **kwargs):
        # This won't be called in dev mode
        return []
        
    async def send_message(self, dialog_id, text):
        # Return a simple mock message
        return type('MockMessage', (), {
            'id': 12345,
            'date': datetime.utcnow(),
            'text': text,
        })

async def inject_mock_session():
    """Create and inject a mock session into the database"""
    # Initialize FastAPI app and database
    app = FastAPI()
    await init_db()
    app.state.db_pool = get_db
    app.state.session_middleware = SessionMiddleware(app)
    
    try:
        # Create session in database
        async with app.state.db_pool() as db:
            session = await app.state.session_middleware.create_session(db=db, is_qr=True)
            token = session.token
            
            # Auto-authenticate the session
            session = await app.state.session_middleware.update_session(
                token=token,
                telegram_id=12345678,  # Fake user ID
                db=db
            )
        
        # Create a mock client instance
        mock_client = MockTelegramClient()
        
        # Store client in memory
        client_sessions[token] = {
            "client": mock_client,
            "qr_login": None
        }
        
        print(f"\n✅ Successfully injected mock session into database")
        print(f"Token: {token}")
        print(f"Status: {session.status}")
        print(f"Telegram ID: {session.telegram_id}")
        print(f"Expires at: {session.expires_at.isoformat()}")
        print("\nYou can now use this token with the real API endpoints:")
        print(f"GET    http://localhost:8000/api/dialogs/{token}/selected")
        print(f"POST   http://localhost:8000/api/dialogs/{token}/select")
        print(f"DELETE http://localhost:8000/api/dialogs/{token}/selected/123456789")
        
        # Also save to a file for easy reference
        with open(Path(__file__).resolve().parent / "mock_session.txt", "w") as f:
            f.write(token)
        print(f"\nToken also saved to app/dev_utils/mock_session.txt")
        
        return token
        
    except Exception as e:
        print(f"Error injecting mock session: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the async function
    token = asyncio.run(inject_mock_session()) 