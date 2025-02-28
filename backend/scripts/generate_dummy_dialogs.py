#!/usr/bin/env python3
"""
Script to generate dummy dialog data for testing
This creates mock implementations of the telegram service functions
to return dummy dialog and message data.
"""

import sys
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.services.auth import client_sessions
from app.services.telegram import get_dialogs, get_recent_messages

# Sample data for generating dialogs
NAMES = [
    "Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Helen",
    "Ivan", "Julia", "Kevin", "Laura", "Michael", "Nina", "Oscar", "Pamela"
]

GROUP_NAMES = [
    "Team Meeting", "Project Alpha", "Family Group", "Friends Chat",
    "Tech Support", "Travel Plans", "Book Club", "Gaming Squad",
    "Crypto Discussions", "Movie Night", "Developers", "Work Announcements"
]

MESSAGE_TEXTS = [
    "Hi there! How are you today?",
    "Can we discuss the project later?",
    "I've sent you the documents you requested.",
    "When is the next meeting scheduled?",
    "Thanks for your help yesterday!",
    "Did you see the news about the new release?",
    "I'm running late, start without me.",
    "What's the status of task #103?",
    "Happy birthday! 🎂",
    "Can someone explain how this feature works?",
    "I've fixed the bug in the main branch.",
    "Let's grab lunch tomorrow.",
    "The server is down again. Working on it.",
    "Please review my PR when you have time.",
    "Don't forget about the deadline on Friday.",
    "I'll be on vacation next week.",
    "How do I set up the development environment?",
    "The client loved our presentation!",
    "Who's responsible for the authentication module?",
    "Just pushed a minor update to fix some styling issues."
]

# Patch the real functions with our mock implementations
async def mock_get_dialogs(session_id: str) -> List[Dict]:
    """Mock implementation of get_dialogs to return dummy data"""
    # Check if the session exists first (just like the real function)
    session = client_sessions.get(session_id)
    if not session:
        raise ValueError("Invalid or expired session")
    
    # Generate random number of dialogs (between 5 and 15)
    num_dialogs = random.randint(5, 15)
    dialogs = []
    
    # Generate private chats (users)
    for i in range(num_dialogs // 2):
        dialogs.append({
            "id": -(i + 1) * 10000000,  # Negative IDs for users
            "name": random.choice(NAMES),
            "unread_count": random.randint(0, 5),
            "is_group": False,
            "is_channel": False,
            "is_user": True
        })
    
    # Generate group chats
    for i in range(num_dialogs - len(dialogs)):
        is_channel = random.choice([True, False])
        dialogs.append({
            "id": (i + 1) * 10000000,  # Positive IDs for groups/channels
            "name": random.choice(GROUP_NAMES),
            "unread_count": random.randint(0, 10),
            "is_group": not is_channel,
            "is_channel": is_channel,
            "is_user": False
        })
    
    return dialogs

async def mock_get_recent_messages(session_id: str, limit: int = 20) -> List[Dict]:
    """Mock implementation of get_recent_messages to return dummy data"""
    # Check if the session exists first (just like the real function)
    session = client_sessions.get(session_id)
    if not session:
        raise ValueError("Invalid or expired session")
    
    # First get the dialogs so we can associate messages with them
    dialogs = await mock_get_dialogs(session_id)
    
    messages = []
    now = datetime.now()
    
    # For each dialog, generate some messages
    for dialog in dialogs:
        # Randomly decide how many messages to generate for this dialog
        num_messages = random.randint(1, 5)
        
        for i in range(num_messages):
            # Generate a random timestamp within the last 24 hours
            message_time = now - timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            
            # Determine if this message is from the user or someone else
            is_outgoing = random.choice([True, False])
            sender_id = 12345678 if is_outgoing else dialog["id"]
            
            messages.append({
                "dialog_id": dialog["id"],
                "dialog_name": dialog["name"],
                "message_id": random.randint(1000000, 9999999),
                "date": message_time.isoformat(),
                "sender": sender_id,
                "text": random.choice(MESSAGE_TEXTS),
                "is_unread": random.choice([True, False]) and not is_outgoing
            })
    
    # Sort messages by date, newest first
    messages.sort(key=lambda x: x["date"], reverse=True)
    return messages[:limit]

# Monkey patch the real functions with our mock implementations
get_dialogs = mock_get_dialogs
get_recent_messages = mock_get_recent_messages

# Save the dummy data to a file for reference
async def save_dummy_data(session_id: str):
    """Generate and save dummy data to JSON files for reference"""
    dialogs = await mock_get_dialogs(session_id)
    messages = await mock_get_recent_messages(session_id)
    
    # Save dialogs
    with open("dummy_dialogs.json", "w") as f:
        json.dump(dialogs, f, indent=2)
    
    # Save messages
    with open("dummy_messages.json", "w") as f:
        json.dump(messages, f, indent=2)
    
    print(f"Generated {len(dialogs)} dummy dialogs and {len(messages)} dummy messages")
    print("Data saved to dummy_dialogs.json and dummy_messages.json")

# Main function to tie everything together
async def main():
    # Create a dummy session first
    from create_dummy_session import create_dummy_session
    session_id = create_dummy_session()
    
    # Generate and save dummy data
    await save_dummy_data(session_id)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 