#!/usr/bin/env python3
"""
Script to create a minimal API server with mocked endpoints for testing

This creates a standalone FastAPI server that mocks the real API
endpoints for dialog listing and message retrieval, making it easy
to test frontend components without a real Telegram connection.

Usage:
  python mock_api.py

The server will start on http://localhost:8001 by default.

Important Implementation Details:
--------------------------------
1. Session Management: The real application uses `client_sessions` dictionary in 
   auth.py to store Telegram client objects and session information. In this mock,
   we need to ensure our sessions are properly added to that dictionary for all 
   the telegram.py functions to work correctly.

2. Dictionary Synchronization: We maintain our own `mock_sessions` for simplicity,
   but must sync entries to `client_sessions` using the `sync_to_client_sessions()`
   helper function. Session data must exist in both dictionaries with consistent
   format and expiry times.
   
3. Authentication: All mock sessions are automatically authenticated (status="authenticated")
   with a fake user_id (12345678) to enable seamless testing.

4. Telegram Client: In the real app, `client_sessions[session_id]["client"]` contains
   an actual TelegramClient instance. In our mock, we set this to None since we don't
   need a real connection.

5. Common Issues:
   - "Invalid or expired session" error occurs when a session exists in mock_sessions
     but not in client_sessions, or if it's expired in client_sessions
   - API endpoints that use client_sessions will fail if the session synchronization
     is not properly maintained
"""

import sys
import json
import random
import uuid
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import FastAPI dependencies
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import and configure the local mocking
from generate_dummy_dialogs import mock_get_dialogs, mock_get_recent_messages

# Import the auth module's sessions dictionary
from app.services.auth import client_sessions

# Create FastAPI app
app = FastAPI(title="Telegram Dialog Processor Mock API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionary to store mock sessions
mock_sessions = {}

# Helper function to sync a session to client_sessions
def sync_to_client_sessions(session_id: str, session_data: dict):
    """
    Sync a mock session to the client_sessions dictionary
    
    This function is critical for making the mock API work correctly.
    The real application stores TelegramClient objects and session data
    in client_sessions, which the telegram.py functions check for authentication.
    
    Args:
        session_id: The UUID session identifier
        session_data: Session data from mock_sessions
    """
    client_sessions[session_id] = {
        "client": None,  # We won't have a real client
        "created_at": datetime.utcnow(),
        "expires_at": session_data["expires_at"],
        "status": session_data["status"],
        "user_id": session_data["user_id"]
    }
    print(f"Synced session {session_id} to client_sessions")

@app.post("/api/auth/qr")
async def create_mock_qr_auth():
    """Create a mock QR authentication session"""
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Store session data
    mock_sessions[session_id] = {
        "status": "authenticated",  # Auto-authenticate for testing
        "user_id": 12345678,
        "expires_at": expires_at
    }
    
    # Sync to client_sessions
    sync_to_client_sessions(session_id, mock_sessions[session_id])
    
    return {
        "session_id": session_id,
        "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",  # 1x1 transparent pixel
        "expires_at": expires_at.isoformat()
    }

@app.get("/api/auth/session/{session_id}")
async def check_mock_session_status(session_id: str):
    """Check the status of a mock authentication session"""
    if session_id not in mock_sessions:
        # For convenience in testing, auto-create missing sessions
        expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_sessions[session_id] = {
            "status": "authenticated",
            "user_id": 12345678,
            "expires_at": expires_at
        }
        # Sync to client_sessions
        sync_to_client_sessions(session_id, mock_sessions[session_id])
    
    session = mock_sessions[session_id]
    return {
        "status": session["status"],
        "user_id": session["user_id"],
        "expires_at": session["expires_at"].isoformat()
    }

@app.get("/api/dialogs/{session_id}")
async def list_mock_dialogs(session_id: str) -> List[Dict]:
    """Get list of mocked dialogs (chats)"""
    try:
        # Auto-create session if not exists
        if session_id not in mock_sessions:
            await check_mock_session_status(session_id)
        
        # Double-check session is synced to client_sessions
        if session_id not in client_sessions:
            sync_to_client_sessions(session_id, mock_sessions[session_id])
            
        dialogs = await mock_get_dialogs(session_id)
        return dialogs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in list_mock_dialogs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages/{session_id}")
async def list_mock_messages(session_id: str, limit: int = 20) -> List[Dict]:
    """Get mocked messages from all dialogs"""
    try:
        # Auto-create session if not exists
        if session_id not in mock_sessions:
            await check_mock_session_status(session_id)
        
        # Double-check session is synced to client_sessions
        if session_id not in client_sessions:
            sync_to_client_sessions(session_id, mock_sessions[session_id])
            
        messages = await mock_get_recent_messages(session_id, limit)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in list_mock_messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages/{session_id}/send")
async def create_mock_message(session_id: str, message: dict) -> Dict:
    """Mock sending a message to a specific dialog"""
    try:
        # Auto-create session if not exists
        if session_id not in mock_sessions:
            await check_mock_session_status(session_id)
        
        # Double-check session is synced to client_sessions
        if session_id not in client_sessions:
            sync_to_client_sessions(session_id, mock_sessions[session_id])
            
        # Create a mock message response
        return {
            "dialog_id": message["dialog_id"],
            "message_id": random.randint(1000000, 9999999),
            "date": datetime.now().isoformat(),
            "text": message["text"],
            "sent": True
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in create_mock_message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Default port is different from the main API (8000) to avoid conflicts
    mock_port = int(os.getenv("MOCK_API_PORT", 8001))
    print(f"Starting mock API server on http://localhost:{mock_port}")
    print(f"Auto-generating sessions as needed for testing")
    
    # Create a pre-configured session ID for convenience
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=24)
    mock_sessions[session_id] = {
        "status": "authenticated",
        "user_id": 12345678,
        "expires_at": expires_at
    }
    
    # Sync to client_sessions
    sync_to_client_sessions(session_id, mock_sessions[session_id])
    
    print(f"\nPre-configured session ID: {session_id}")
    print(f"Use this to test API endpoints, for example:")
    print(f"  GET http://localhost:{mock_port}/api/dialogs/{session_id}")
    
    # Save the session ID to a file for easy reference
    with open("dummy_session.txt", "w") as f:
        f.write(session_id)
    
    # Start the API server
    uvicorn.run("mock_api:app", host="0.0.0.0", port=mock_port, reload=True) 