#!/usr/bin/env python3
"""
Script to create a dummy Telegram session for testing
This creates a fake session ID and stores it in the client_sessions
dictionary so you can use it for testing without logging in.
"""

import sys
import uuid
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.services.auth import client_sessions
from app.services.telegram import get_dialogs, get_recent_messages

# Create a dummy session that looks like a real authenticated session
def create_dummy_session():
    """Create a dummy session for testing purposes"""
    # Generate a random session ID (UUID)
    session_id = str(uuid.uuid4())
    
    # Create a dummy session with authenticated status
    client_sessions[session_id] = {
        "client": None,  # We won't have a real client
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=24),
        "status": "authenticated",
        "user_id": 12345678,  # Fake user ID
    }
    
    print(f"Created dummy session with ID: {session_id}")
    print(f"This session will expire at: {client_sessions[session_id]['expires_at'].isoformat()}")
    print("\nUse this session ID for testing API endpoints, for example:")
    print(f"  GET /api/dialogs/{session_id}")
    
    # Save the session ID to a file for easy reference
    with open("dummy_session.txt", "w") as f:
        f.write(session_id)
    
    print("\nSession ID saved to dummy_session.txt")
    
    return session_id

if __name__ == "__main__":
    session_id = create_dummy_session() 