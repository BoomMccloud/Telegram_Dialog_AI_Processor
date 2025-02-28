#!/usr/bin/env python3
"""
Development utility script to inject a mock session into the main app.

This script creates a dummy authenticated session and adds it to the client_sessions 
dictionary of the main app, allowing you to bypass the real Telegram authentication 
while still using the real database for dialog selections.

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

# Import from auth module
from app.services.auth import client_sessions, save_session_to_file

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
    """Create and inject a mock session into client_sessions"""
    # Generate a session ID
    session_id = str(uuid.uuid4())
    
    # Create mock session data (similar to our mock_api)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Create a mock client instance
    mock_client = MockTelegramClient()
    
    # Create a fake authenticated session
    session_data = {
        "client": mock_client,  # Now using a mock client instead of None
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "status": "authenticated",
        "user_id": 12345678  # Fake user ID
    }
    
    # Store in memory
    client_sessions[session_id] = session_data
    
    # Also save to disk for persistence across restarts
    save_session_to_file(session_id, session_data)
    
    print(f"\n✅ Successfully injected mock session into main app")
    print(f"Session ID: {session_id}")
    print(f"Expires at: {expires_at.isoformat()}")
    print("\nYou can now use this session ID with the real API endpoints:")
    print(f"GET    http://localhost:8000/api/dialogs/{session_id}/selected")
    print(f"POST   http://localhost:8000/api/dialogs/{session_id}/select")
    print(f"DELETE http://localhost:8000/api/dialogs/{session_id}/selected/123456789")
    
    # Also save to a file for easy reference
    with open(Path(__file__).resolve().parent / "mock_session.txt", "w") as f:
        f.write(session_id)
    print(f"\nSession ID also saved to app/dev_utils/mock_session.txt")
    print(f"Session data also persisted to disk for access across server restarts")
    
    return session_id

if __name__ == "__main__":
    # Run the async function
    session_id = asyncio.run(inject_mock_session()) 